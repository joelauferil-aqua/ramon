"""
Interfície de la demo — Generador de respostes Best Andorra Center.
Una sola pantalla: ressenya -> Claude -> resposta en l'estil del propietari.
"""

import os
import streamlit as st

# Carregar la clau d'API des de .env (local) o st.secrets (Streamlit Cloud).
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

from services.ai import generate_response, load_general_notes, save_general_notes

# --- Configuració de pàgina -------------------------------------------------
st.set_page_config(
    page_title="Best Andorra Center · Generador de respostes",
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

# --- Estat ------------------------------------------------------------------
if "answer" not in st.session_state:
    st.session_state.answer = ""
if "history" not in st.session_state:
    st.session_state.history = []
# Carreguem les notes generals guardades (una sola vegada).
if "general_notes_loaded" not in st.session_state:
    st.session_state["general_notes"] = load_general_notes()
    st.session_state["general_notes_loaded"] = True

# --- Barra lateral: NOTES ---------------------------------------------------
with st.sidebar:
    st.markdown("### 📝 Notes")

    st.text_area(
        "Notes generals",
        key="general_notes",
        height=150,
        help=("Informació general del negoci (serveis, ofertes, dades). La IA la "
              "farà servir només si encaixa amb la ressenya. Es guarda."),
        placeholder="Ex.: Tenim nova carta al restaurant. Oferta d'spa aquest mes.",
    )
    if st.button("💾 Desar notes generals", use_container_width=True):
        if save_general_notes(st.session_state.get("general_notes", "")):
            st.success("Notes generals desades.")
        else:
            st.warning("No s'han pogut desar (entorn de només lectura).")

    st.divider()

    st.text_area(
        "Notes puntuals (només per aquesta resposta)",
        key="punctual_notes",
        height=130,
        help=("Instruccions només per a aquesta resposta concreta. No es guarden "
              "i manen per sobre de les notes generals."),
        placeholder="Ex.: En aquesta resposta, demana disculpes de manera especial.",
    )
    if st.session_state.get("punctual_notes", "").strip():
        st.info("Notes puntuals actives (només per a la propera resposta).")

# --- Capçalera --------------------------------------------------------------
st.markdown('<div class="brand">Best Andorra Center · 4★ Andorra la Vella</div>',
            unsafe_allow_html=True)
st.title("Generador de respostes a ressenyes")
st.markdown(
    '<div class="subtitle">Enganxa una ressenya d\'un client i genera una resposta '
    "redactada en l'estil de l'hotel, en l'idioma del client.</div>",
    unsafe_allow_html=True,
)

# --- Entrades ---------------------------------------------------------------
col1, col2 = st.columns(2)
with col1:
    st.selectbox("Plataforma", ["Google", "TripAdvisor", "Booking", "Altra"],
                 key="platform")
with col2:
    st.text_input("Puntuació (opcional)", key="score",
                  placeholder="ex.: 4/5 o 9/10")

st.selectbox(
    "Idioma de la resposta",
    ["Auto (idioma del comentari)", "Espanyol", "Català", "English", "Français"],
    key="language",
    help="'Auto' respon sempre en el mateix idioma del comentari del client.",
)

st.text_area(
    "Ressenya del client",
    key="review",
    height=170,
    placeholder="Enganxa aquí la ressenya del client...",
)


def _generate(regenerate: bool = False):
    review = st.session_state.get("review", "")
    if not review.strip():
        st.warning("Escriu o enganxa primer una ressenya.")
        return

    language = st.session_state.get("language", "Auto (idioma del comentari)")
    language_value = "Auto" if language.startswith("Auto") else language

    try:
        with st.spinner("Generant una versió diferent..." if regenerate
                        else "Generant resposta..."):
            answer = generate_response(
                review=review,
                score=st.session_state.get("score", ""),
                platform=st.session_state.get("platform", "Google"),
                language=language_value,
                general_notes=st.session_state.get("general_notes", ""),
                punctual_notes=st.session_state.get("punctual_notes", ""),
                avoid=st.session_state.history if regenerate else None,
            )
        st.session_state.answer = answer
        if regenerate:
            st.session_state.history.append(answer)
        else:
            st.session_state.history = [answer]
    except Exception as e:  # noqa: BLE001
        st.error(f"No s'ha pogut generar la resposta: {e}")


# --- Botons -----------------------------------------------------------------
b1, b2 = st.columns([1, 1])
with b1:
    st.button("✨ Generar resposta", type="primary", use_container_width=True,
              on_click=_generate)
with b2:
    if st.session_state.answer:
        st.button("🔁 Regenerar (una de diferent)", use_container_width=True,
                  on_click=_generate, kwargs={"regenerate": True})

# --- Resultat ---------------------------------------------------------------
if st.session_state.answer:
    st.markdown("#### Resposta")
    st.markdown(f'<div class="answer-box">{st.session_state.answer}</div>',
                unsafe_allow_html=True)
    st.text_area(
        "Copiar / editar",
        value=st.session_state.answer,
        height=180,
        help="Pots editar el text abans de copiar-lo.",
    )
    n = len(st.session_state.history)
    if n > 1:
        st.caption(f"Versió {n} · «Regenerar» sempre en dóna una de diferent.")
    else:
        st.caption("Consell: fes servir «Regenerar» per obtenir-ne una de diferent.")
