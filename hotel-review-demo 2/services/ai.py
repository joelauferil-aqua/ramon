"""
Motor de generación de respuestas — Best Andorra Center.

Toma una reseña (+ puntuación, plataforma, idioma, notas de Ramon) y devuelve
una respuesta escrita en el estilo del propietario, usando:
  - config/owner_style.md   (cómo escribe)
  - config/hotel_facts.md   (hechos reales del hotel)
  - data/response_examples.json (ejemplos reales de referencia)

Este módulo es INDEPENDIENTE de la interfaz.
"""

import os
import re
import json
import random
from pathlib import Path

from anthropic import Anthropic

# --- Modelo -----------------------------------------------------------------
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
def _score_to_ten(score_raw):
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
    "Varía la estructura: no sigas el orden típico de una respuesta estándar.",
    "Haz esta respuesta algo más breve y directa de lo habitual, sin perder calidez.",
    "Empieza reaccionando a un detalle concreto de la reseña antes de saludar.",
    "Cierra con una fórmula de despedida distinta a la más habitual.",
    "Reordena las ideas: menciona primero lo secundario y luego lo principal.",
    "",  # a veces sin pista, para no forzar
]


def _build_system_prompt(platform, score_ten, sentiment, language,
                         examples, notes="", avoid=None) -> str:
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

    # Notas de Ramon (prioridad alta).
    notes_block = ""
    if notes and notes.strip():
        notes_block = f"""

=== NOTAS DE RAMON (PRIORIDAD ALTA — respétalas siempre) ===
{notes.strip()}

Estas notas las ha escrito la persona responsable del hotel. Tienen prioridad
sobre los ejemplos. Si son INFORMACIÓN (una oferta, un servicio disponible, un
dato actual), puedes usarla en la respuesta cuando encaje de forma natural. Si
son una INSTRUCCIÓN (p. ej. "no menciones las obras"), cúmplela estrictamente.
Puedes tratar estas notas como hechos ciertos del hotel."""

    # Evitar repetición (para que "Regenerar" dé algo realmente distinto).
    avoid_block = ""
    if avoid:
        prev = "\n\n--- versión anterior ---\n".join(
            a.strip()[:700] for a in list(avoid)[-3:] if a and a.strip()
        )
        if prev:
            avoid_block = f"""

=== EVITA REPETIRTE (MUY IMPORTANTE) ===
En intentos anteriores para ESTA MISMA reseña ya escribiste lo siguiente:
--- versión anterior ---
{prev}

Genera ahora una respuesta CLARAMENTE DIFERENTE: cambia el saludo/apertura, el
orden de las ideas, la estructura, la longitud y el vocabulario. Que no se
parezca a las versiones anteriores ni reutilice sus mismas frases — pero
manteniendo el MISMO estilo, el mismo idioma y los mismos hechos."""

    return f"""Eres la persona que gestiona y responde personalmente las reseñas del
Hotel Best Andorra Center. Escribe la respuesta como la escribiría ella, NO como
una IA. El lector debe pensar "esto lo habría escrito yo".

=== ESTILO (imítalo fielmente) ===
{style}

=== HECHOS DEL HOTEL (usa SOLO estos datos; nunca inventes nada) ===
{facts}

=== EJEMPLOS REALES DE REFERENCIA (imita el estilo, NO copies literalmente) ===
{examples_text}
{notes_block}{avoid_block}

=== INSTRUCCIONES PARA ESTA RESPUESTA ===
- Plataforma: {platform}. {score_line}
- {lang_line}
- Personaliza: menciona detalles concretos de la reseña.
- Aplica el CARÁCTER: si la crítica es cierta, reconócela y discúlpate; si es
  injusta o falsa, rebátela con educación usando SOLO hechos reales.
- Cuando encaje de forma natural, sugiere sutilmente un servicio del hotel.
- VARÍA apertura, estructura, longitud y cierre. Que no suene a plantilla ni a IA.
- Emojis: por defecto ninguno; solo alguno muy puntual si es una reseña positiva
  e informal (sobre todo en Google). Nunca en negativas.
- No inventes datos que no consten en la ficha de hechos ni en las notas de Ramon.
- Devuelve ÚNICAMENTE el texto de la respuesta, sin comillas ni comentarios.
{hint}"""


# --- Función principal ------------------------------------------------------
def generate_response(review: str, score=None, platform="Google",
                      language="Auto", notes="", avoid=None) -> str:
    """Genera una respuesta a una reseña en el estilo del propietario.

    notes: texto libre de Ramon (instrucciones/info) que se aplica con prioridad.
    avoid: lista de respuestas anteriores a evitar (para "Regenerar" distinto).
    """
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
        platform, score_ten, sentiment, language, examples,
        notes=notes, avoid=avoid,
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
