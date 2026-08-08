"""
Motor de generación de respuestas — Best Andorra Center.

Toma una reseña (+ puntuación, plataforma, idioma) y devuelve una respuesta
escrita en el estilo del propietario, usando:
  - config/owner_style.md   (cómo escribe)
  - config/hotel_facts.md   (hechos reales del hotel)
  - data/response_examples.json (ejemplos reales de referencia)

Este módulo es INDEPENDIENTE de la interfaz: la misma función podría usarse
más adelante en el sistema con TrustYou sin reescribir nada.
"""

import os
import re
import json
import random
from pathlib import Path

from anthropic import Anthropic

# --- Modelo -----------------------------------------------------------------
# Sonnet 5 es el punto dulce calidad/precio para imitar estilo.
# Alternativas: "claude-opus-4-8" (máxima calidad) o
# "claude-haiku-4-5-20251001" (más barato).
MODEL = "claude-sonnet-5"
MAX_TOKENS = 800
TEMPERATURE = 1.0  # alto para dar variedad natural entre respuestas

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"


# --- Carga de configuración -------------------------------------------------
def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_examples() -> list:
    with open(DATA_DIR / "response_examples.json", encoding="utf-8") as f:
        return json.load(f)


# --- Utilidades -------------------------------------------------------------
def _score_to_ten(score_raw) -> float | None:
    """Normaliza una puntuación ('4/5', '9/10', '8', 4.5...) a base 10."""
    if score_raw is None:
        return None
    s = str(score_raw).strip().replace(",", ".")
    if not s:
        return None
    m = re.match(r"([\d.]+)\s*/\s*([\d.]+)", s)
    if m:
        num, den = float(m.group(1)), float(m.group(2))
        if den:
            return round(num / den * 10, 1)
    try:
        val = float(s)
    except ValueError:
        return None
    # Si es <= 5 asumimos escala /5; si no, escala /10.
    return round(val * 2, 1) if val <= 5 else round(val, 1)


def _sentiment(score_ten) -> str:
    if score_ten is None:
        return "desconocido"
    if score_ten >= 8:
        return "positivo"
    if score_ten >= 5:
        return "mixto"
    return "negativo"


def _select_examples(examples, platform, sentiment, k=4) -> list:
    """Elige ejemplos priorizando mismo sentimiento y plataforma, con variedad."""
    pool = list(examples)
    random.shuffle(pool)

    def score(ex):
        s = 0
        if ex.get("sentiment") == sentiment:
            s += 2
        if ex.get("platform", "").lower() == str(platform).lower():
            s += 1
        return s

    pool.sort(key=score, reverse=True)
    return pool[:k]


# Pistas de variación que se rotan para que no suenen todas iguales.
_VARIATION_HINTS = [
    "Para esta respuesta, NO empieces con 'Estimado/a'. Busca otra apertura natural.",
    "Varía la estructura respecto a una respuesta estándar: no sigas el orden típico.",
    "Haz esta respuesta algo más breve y directa de lo habitual, sin perder calidez.",
    "Empieza reaccionando a un detalle concreto de la reseña antes de saludar formalmente.",
    "Cierra con una fórmula de despedida distinta a la más habitual.",
    "",  # a veces sin pista, para no forzar
]


def _build_system_prompt(platform, score_ten, sentiment, language, examples) -> str:
    style = _load_text(CONFIG_DIR / "owner_style.md")
    facts = _load_text(CONFIG_DIR / "hotel_facts.md")

    ex_block = []
    for ex in examples:
        ex_block.append(
            f"[Plataforma: {ex.get('platform')} | Puntuación: {ex.get('score')} "
            f"| Tipo: {ex.get('sentiment')}]\n"
            f"RESEÑA: {ex.get('review')}\n"
            f"RESPUESTA DEL PROPIETARIO: {ex.get('response')}"
        )
    examples_text = "\n\n---\n\n".join(ex_block)

    lang_line = (
        "Detecta automáticamente el idioma de la reseña y responde en ESE idioma."
        if language in (None, "", "Auto")
        else f"Responde OBLIGATORIAMENTE en {language}."
    )
    score_line = (
        f"La puntuación es {score_ten}/10 ({sentiment})."
        if score_ten is not None
        else "No se ha indicado puntuación; dedúcela del tono de la reseña."
    )
    hint = random.choice(_VARIATION_HINTS)

    return f"""Eres la persona que gestiona y responde personalmente las reseñas del
Hotel Best Andorra Center. Escribe la respuesta como la escribiría ella, NO como
una IA. El lector debe pensar "esto lo habría escrito yo".

=== ESTILO (imítalo fielmente) ===
{style}

=== HECHOS DEL HOTEL (usa SOLO estos datos; nunca inventes nada) ===
{facts}

=== EJEMPLOS REALES DE REFERENCIA (imita el estilo, NO copies literalmente) ===
{examples_text}

=== INSTRUCCIONES PARA ESTA RESPUESTA ===
- Plataforma: {platform}. {score_line}
- {lang_line}
- Personaliza: menciona detalles concretos de la reseña.
- Aplica el CARÁCTER: si la crítica es cierta, reconócela y discúlpate; si es
  injusta o falsa, rebátela con educación usando SOLO hechos reales de la ficha.
- Cuando encaje de forma natural, sugiere sutilmente un servicio del hotel.
- VARÍA apertura, estructura, longitud y cierre. Que no suene a plantilla ni a IA.
- Emojis: por defecto ninguno; solo alguno muy puntual si es una reseña positiva
  e informal (sobre todo en Google). Nunca en negativas.
- No inventes servicios, acciones, promesas ni datos que no consten en la ficha.
- Devuelve ÚNICAMENTE el texto de la respuesta, sin comillas ni comentarios.
{hint}"""


# --- Función principal ------------------------------------------------------
def generate_response(review: str, score=None, platform="Google", language="Auto") -> str:
    """Genera una respuesta a una reseña en el estilo del propietario."""
    if not review or not review.strip():
        raise ValueError("La reseña está vacía.")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError(
            "Falta la clave de API. Configura ANTHROPIC_API_KEY "
            "(en .streamlit/secrets.toml o en un archivo .env)."
        )

    score_ten = _score_to_ten(score)
    sentiment = _sentiment(score_ten)
    examples = _select_examples(load_examples(), platform, sentiment, k=4)
    system_prompt = _build_system_prompt(
        platform, score_ten, sentiment, language, examples
    )

    client = Anthropic()  # lee ANTHROPIC_API_KEY del entorno automáticamente
    message = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
        system=system_prompt,
        messages=[{"role": "user", "content": f"RESEÑA DEL CLIENTE:\n{review.strip()}"}],
    )

    return "".join(
        block.text for block in message.content if getattr(block, "type", "") == "text"
    ).strip()
