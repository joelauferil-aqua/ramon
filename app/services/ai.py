"""
Motor de generación de respuestas — Best Andorra Center.

Toma una reseña (+ puntuación, plataforma, idioma, notas) y devuelve una
respuesta escrita en el estilo del propietario.

Dos tipos de notas:
  - general_notes  : información del negocio; se usa SOLO si encaja. Se guarda.
  - punctual_notes : instrucciones solo para esta respuesta; NO se guardan y
                     tienen PRIORIDAD sobre las notas generales.
"""

import os
import re
import json
import random
from pathlib import Path

from anthropic import Anthropic

# --- Modelo -----------------------------------------------------------------
MODEL = "claude-sonnet-5"
MAX_TOKENS = 1400          # amplio para que la respuesta nunca quede cortada
TEMPERATURE = 1.0          # alto para dar variedad natural

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"
DATA_DIR = BASE_DIR / "data"
GENERAL_NOTES_FILE = DATA_DIR / "general_notes.txt"


# --- Carga de configuración -------------------------------------------------
def _load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def load_examples() -> list:
    with open(DATA_DIR / "response_examples.json", encoding="utf-8") as f:
        return json.load(f)


# --- Notas generales: persistencia en fichero local (Opción A) --------------
def load_general_notes() -> str:
    try:
        if GENERAL_NOTES_FILE.exists():
            return GENERAL_NOTES_FILE.read_text(encoding="utf-8")
    except Exception:
        pass
    return ""


def save_general_notes(text: str) -> bool:
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        GENERAL_NOTES_FILE.write_text(text or "", encoding="utf-8")
        return True
    except Exception:
        return False


# --- Utilidades -------------------------------------------------------------
def _score_to_ten(score_raw):
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


_VARIATION_HINTS = [
    "Para esta respuesta, NO empieces con 'Estimado/a'. Busca otra apertura natural.",
    "Varía la estructura: no sigas el orden típico de una respuesta estándar.",
    "Haz esta respuesta algo más breve y directa de lo habitual, sin perder calidez.",
    "Empieza reaccionando a un detalle concreto de la reseña antes de saludar.",
    "Cierra con una fórmula de despedida distinta a la más habitual.",
    "Reordena las ideas: menciona primero lo secundario y luego lo principal.",
    "",
]


def _build_system_prompt(platform, score_ten, sentiment, language, examples,
                         general_notes="", punctual_notes="", avoid=None) -> str:
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
        "Responde OBLIGATORIAMENTE en el MISMO idioma en el que está escrita la "
        "reseña del cliente, sea cual sea (español, catalán, inglés, francés...). "
        "Es una regla estricta: nunca cambies de idioma."
        if language in (None, "", "Auto")
        else f"Responde OBLIGATORIAMENTE en {language}."
    )
    score_line = (
        f"La puntuación es {score_ten}/10 ({sentiment})."
        if score_ten is not None
        else "No se ha indicado puntuación; dedúcela del tono de la reseña."
    )
    hint = random.choice(_VARIATION_HINTS)

    # Notas generales (contexto, subordinadas).
    general_block = ""
    if general_notes and general_notes.strip():
        general_block = f"""

=== NOTAS GENERALES DEL NEGOCIO (contexto) ===
{general_notes.strip()}

Usa esta información SOLO si encaja de forma natural con la reseña. Si no viene a
cuento, ignórala. Puedes tratarla como cierta. Están SUBORDINADAS a las notas
puntuales."""

    # Notas puntuales (máxima prioridad).
    punctual_block = ""
    if punctual_notes and punctual_notes.strip():
        punctual_block = f"""

=== NOTAS PUNTUALES — PRIORIDAD MÁXIMA (solo para esta respuesta) ===
{punctual_notes.strip()}

Estas instrucciones tienen PRIORIDAD sobre las notas generales y sobre los
ejemplos. Cúmplelas en esta respuesta, salvo que te obliguen a inventar hechos
falsos o a ser grosero (eso no se hace nunca)."""

    # Evitar repetición (para "Regenerar" distinto).
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
parezca a las versiones anteriores — pero mantén el MISMO estilo, el mismo idioma
y los mismos hechos."""

    return f"""Eres la persona que gestiona y responde personalmente las reseñas del
Hotel Best Andorra Center. Escribe la respuesta como la escribiría ella, NO como
una IA. El lector debe pensar "esto lo habría escrito yo".

=== ESTILO (imítalo fielmente) ===
{style}

=== HECHOS DEL HOTEL (usa SOLO estos datos; nunca inventes nada) ===
{facts}

=== EJEMPLOS REALES DE REFERENCIA (imita el estilo, NO copies literalmente) ===
{examples_text}
{general_block}{punctual_block}{avoid_block}

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
- No inventes datos que no consten en la ficha de hechos ni en las notas.
- TERMINA SIEMPRE la respuesta por completo; no la dejes cortada a media frase.
- Devuelve ÚNICAMENTE el texto de la respuesta, sin comillas ni comentarios.
{hint}"""


# --- Función principal ------------------------------------------------------
def generate_response(review: str, score=None, platform="Google", language="Auto",
                      general_notes="", punctual_notes="", avoid=None) -> str:
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
        general_notes=general_notes, punctual_notes=punctual_notes, avoid=avoid,
    )

    client = Anthropic()
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
