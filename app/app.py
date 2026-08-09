"""
Interfaz de la demo — Generador de respuestas Best Andorra Center.
Una sola pantalla: reseña -> Claude -> respuesta en el estilo del propietario.
"""

import os
import streamlit as st

# Cargar la clave de API desde .env (local) o st.secrets (Streamlit Cloud).
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    if "ANTHROPIC_API_KEY" in st.secrets:
        os.environ["ANTHROPIC_API_KEY"] = st.secrets["ANTHROPIC_API_KEY"]
except Exception:
    pass

from services.ai import generate_response

# --- Configuración de página ------------------------------------------------
st.set_page_config(
    page_title="Best Andorra Center · Generador de respuestas",
    page_icon="🏔️",
    layout="centered",
)

st.markdown(
    """
    <style>
    .block-container {max-width: 780px; padding-top: 2.5rem;}
    h1 {font-size: 1.6rem !important;}
    .subtitle {color:#6b7280; margin-top:-0.6rem; margin-bottom:1.6rem; font-size:0.95rem;}
    .brand {letter-spacing:0.14em; text-transform:uppercase; color:#9a7b3f;
            font-weight:600; font-size:0.8rem;}
    .answer-box {background:#f7f4ee; border:1px solid #e7e0d3; border-radius:12px;
                 padding:1.1rem 1.25rem; white-space:pre-wrap; line-height:1.5;
                 font-size:0.98rem;}
    div.stButton > button {border-radius:10px; padding:0.5rem 1.1rem; font-weight:600;}
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Estado -----------------------------------------------------------------
if "answer" not in st.session_state:
    st.session_state.answer = ""
if "history" not in st.session_state:
    st.session_state.history = []   # versiones ya generadas para la reseña actual

# --- Barra lateral: NOTAS DE RAMON ------------------------------------------
with st.sidebar:
    st.markdown("### 📝 Notas de Ramon")
    st.caption(
        "Escribe aquí información o instrucciones y la IA las tendrá en cuenta "
        "en cada respuesta. Ejemplos: «Este mes hay oferta de spa», «El parking "
        "vuelve a estar disponible», «No menciones las obras»."
    )
    st.text_area(
        "Notas",
        key="notes",
        height=200,
        label_visibility="collapsed",
        placeholder="Ej.: Tenemos nueva carta en el restaurante. No hablar del ruido de obras.",
    )
    if st.session_state.get("notes", "").strip():
        st.success("Notas activas: se aplican a todas las respuestas.")

# --- Cabecera ---------------------------------------------------------------
st.markdown('<div class="brand">Best Andorra Center · 4★ Andorra la Vella</div>',
            unsafe_allow_html=True)
st.title("Generador de respuestas a reseñas")
st.markdown(
    '<div class="subtitle">Pega una reseña de un cliente y genera una respuesta '
    "redactada en el estilo del hotel, en el idioma del cliente.</div>",
    unsafe_allow_html=True,
)

# --- Entradas ---------------------------------------------------------------
col1, col2 = st.columns(2)
with col1:
    st.selectbox("Plataforma", ["Google", "TripAdvisor", "Booking", "Otra"],
                 key="platform")
with col2:
    st.text_input("Puntuación (opcional)", key="score",
                  placeholder="p. ej. 4/5 o 9/10")

st.selectbox(
    "Idioma de la respuesta",
    ["Auto (detectar)", "Español", "Català", "English", "Français"],
    key="language",
    help="'Auto' responde en el mismo idioma de la reseña.",
)

st.text_area(
    "Reseña del cliente",
    key="review",
    height=170,
    placeholder="Pega aquí la reseña del cliente...",
)


def _generate(regenerate: bool = False):
    review = st.session_state.get("review", "")
    if not review.strip():
        st.warning("Escribe o pega primero una reseña.")
        return

    language = st.session_state.get("language", "Auto (detectar)")
    language_value = "Auto" if language.startswith("Auto") else language

    try:
        with st.spinner("Generando una versión distinta..." if regenerate
                        else "Generando respuesta..."):
            answer = generate_response(
                review=review,
                score=st.session_state.get("score", ""),
                platform=st.session_state.get("platform", "Google"),
                language=language_value,
                notes=st.session_state.get("notes", ""),
                avoid=st.session_state.history if regenerate else None,
            )
        st.session_state.answer = answer
        if regenerate:
            st.session_state.history.append(answer)
        else:
            st.session_state.history = [answer]   # nueva reseña: empezamos de cero
    except Exception as e:  # noqa: BLE001
        st.error(f"No se ha podido generar la respuesta: {e}")


# --- Botones ----------------------------------------------------------------
b1, b2 = st.columns([1, 1])
with b1:
    st.button("✨ Generar respuesta", type="primary", use_container_width=True,
              on_click=_generate)
with b2:
    if st.session_state.answer:
        st.button("🔁 Regenerar (otra distinta)", use_container_width=True,
                  on_click=_generate, kwargs={"regenerate": True})

# --- Resultado --------------------------------------------------------------
if st.session_state.answer:
    st.markdown("#### Respuesta")
    st.markdown(f'<div class="answer-box">{st.session_state.answer}</div>',
                unsafe_allow_html=True)
    st.text_area(
        "Copiar / editar",
        value=st.session_state.answer,
        height=180,
        help="Puedes editar el texto antes de copiarlo.",
    )
    n = len(st.session_state.history)
    if n > 1:
        st.caption(f"Versión {n} · «Regenerar» siempre da una versión diferente.")
    else:
        st.caption("Consejo: usa «Regenerar» para obtener una versión distinta.")
