# Nura Intelligence

Plataforma de Business Intelligence conversacional: carga tus datos, la IA los analiza y te responde en lenguaje natural.

## Cómo correr el proyecto en local (sin Docker)

**1. Backend (Django)**
```bash
cp .env.example .env
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser   # opcional, para /admin/
python manage.py runserver
```
Por defecto, si no configuras `DATABASE_URL` en `.env`, el proyecto usa **SQLite** automáticamente — no necesitas instalar Postgres para probar en local.

**2. Frontend (React + Vite)**, en otra terminal:
```bash
cd frontend
cp .env.example .env
pnpm install
pnpm dev
```

**3. Abre la app en el navegador:**
👉 **http://localhost:5173** — esta es la interfaz de usuario.

`http://localhost:8000` es solo la API del backend (verás una página de estado, no la aplicación). Si visitas esa URL directamente esperando ver la app, es normal que no encuentres la interfaz ahí.

### Chat / IA
El chat necesita al menos una API key de un proveedor de LLM configurada en `.env` (`GROQ_API_KEY`, `CEREBRAS_API_KEY` u `OPENROUTER_API_KEY`). Sin ninguna, el resto de la plataforma (auth, carga de datasets, etc.) funciona igual, pero el chat devolverá error.

---

## License

Apache License 2.0

See the [LICENSE](LICENSE) file for additional information.

---

<p align="center">
  <strong>The system is not deployed.</strong>
</p>