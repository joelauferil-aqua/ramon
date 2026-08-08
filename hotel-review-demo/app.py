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

# --- Cabecera ---------------------------------------------------------------
st.markdown('<div class="brand">Best Andorra Center · 4★ Andorra la Vella</div>',
            unsafe_allow_html=True)
st.title("Generador de respuestas a reseñas")
st.markdown(
    '<div class="subtitle">Pega una reseña de un cliente y genera una respuesta '
    "redactada en el estilo del hotel, en el idioma del cliente.</div>",
    unsafe_allow_html=True,
)

# --- Estado -----------------------------------------------------------------
if "answer" not in st.session_state:
    st.session_state.answer = ""

# --- Entradas ---------------------------------------------------------------
col1, col2 = st.columns(2)
with col1:
    platform = st.selectbox("Plataforma", ["Google", "TripAdvisor", "Booking", "Otra"])
with col2:
    score = st.text_input("Puntuación (opcional)", placeholder="p. ej. 4/5 o 9/10")

language = st.selectbox(
    "Idioma de la respuesta",
    ["Auto (detectar)", "Español", "Català", "English", "Français"],
    help="'Auto' responde en el mismo idioma de la reseña.",
)
language_value = "Auto" if language.startswith("Auto") else language

review = st.text_area(
    "Reseña del cliente",
    height=170,
    placeholder="Pega aquí la reseña del cliente...",
)


def _run():
    if not review.strip():
        st.warning("Escribe o pega primero una reseña.")
        return
    try:
        with st.spinner("Generando respuesta..."):
            st.session_state.answer = generate_response(
                review=review,
                score=score,
                platform=platform,
                language=language_value,
            )
    except Exception as e:  # noqa: BLE001
        st.error(f"No se ha podido generar la respuesta: {e}")


# --- Botones ----------------------------------------------------------------
b1, b2 = st.columns([1, 1])
with b1:
    st.button("✨ Generar respuesta", type="primary", use_container_width=True,
              on_click=_run)
with b2:
    if st.session_state.answer:
        st.button("🔁 Regenerar", use_container_width=True, on_click=_run)

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
    st.caption("Consejo: usa «Regenerar» para obtener una versión distinta.")
