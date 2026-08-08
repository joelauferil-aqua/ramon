# Generador de respuestas — Best Andorra Center (demo)

Aplicación web sencilla: pegas una reseña de un cliente, pulsas **Generar
respuesta** y obtienes una respuesta redactada en el estilo del hotel, en el
idioma del cliente. Usa la API de Claude (Anthropic).

---

## ¿Qué hay dentro?

- `app.py` — la pantalla que ve el usuario.
- `services/ai.py` — el motor que construye el prompt y llama a Claude.
- `config/owner_style.md` — cómo escribe el hotel (su estilo).
- `config/hotel_facts.md` — hechos reales del hotel (para no inventar nada).
- `data/response_examples.json` — ejemplos reales de reseña → respuesta.

---

## Necesitas 1 cosa: una clave de API de Anthropic

1. Entra en https://console.anthropic.com
2. Crea una **API key** (empieza por `sk-ant-...`).
3. Asegúrate de tener un poco de saldo (crédito gratis o unos 5 $). Cada
   respuesta cuesta menos de un céntimo.

---

## Opción A (recomendada): publicarla en internet con un enlace

Ideal para enviar un enlace al propietario. Es gratis.

1. Sube esta carpeta a un repositorio en https://github.com (puede ser privado).
2. Entra en https://share.streamlit.io y conéctalo con tu GitHub.
3. Pulsa **New app**, elige el repositorio y el archivo `app.py`.
4. En **Advanced settings → Secrets**, pega:
   ```
   ANTHROPIC_API_KEY = "sk-ant-TU-CLAVE"
   ```
5. Pulsa **Deploy**. En un par de minutos tendrás una URL pública para compartir.

---

## Opción B: ejecutarla en tu ordenador

Necesitas tener Python instalado.

1. Copia `.env.example` como `.env` y pon tu clave dentro.
2. Instala lo necesario:
   ```
   pip install -r requirements.txt
   ```
3. Arranca la app:
   ```
   streamlit run app.py
   ```
4. Se abre en el navegador en `http://localhost:8501`.
5. Para pararla: cierra la ventana o pulsa `Ctrl + C` en la terminal.

---

## Cómo se usa

1. Elige la **plataforma** (Google, TripAdvisor, Booking...).
2. Pon la **puntuación** (opcional): `4/5`, `9/10`...
3. Pega la **reseña** del cliente.
4. Pulsa **Generar respuesta**.
5. Si no te convence, pulsa **Regenerar** para otra versión.

---

## Notas

- La clave NUNCA va escrita dentro del código: va en `.env` (local) o en los
  *Secrets* de Streamlit (en la nube). No subas tu `.env` ni tu `secrets.toml`.
- Para cambiar el estilo o los datos del hotel, edita los archivos de `config/`.
- Modelo por defecto: `claude-sonnet-5` (equilibrio calidad/precio). Se puede
  cambiar en `services/ai.py`.
