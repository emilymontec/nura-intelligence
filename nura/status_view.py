"""
Vista de estado para la raíz del backend.

Antes de este cambio no existía NINGUNA ruta para '/' en nura/urls.py, así
que visitar http://localhost:8000/ devolvía el 404 técnico de Django (que
en DEBUG=True lista los urlpatterns disponibles). Como 'admin/' es el único
patrón fácilmente reconocible en esa lista, daba la sensación de que "todo
redirige al panel de admin". Esta vista da una respuesta real y explica
cómo acceder a la aplicación (el frontend corre aparte, en Vite).
"""
from django.http import HttpResponse
from django.urls import get_resolver


STATUS_PAGE_HTML = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Nura // API Backend</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0;
    min-height: 100vh;
    background: #030303;
    background-image:
      linear-gradient(to right, rgba(255,255,255,0.02) 1px, transparent 1px),
      linear-gradient(to bottom, rgba(255,255,255,0.02) 1px, transparent 1px);
    background-size: 40px 40px;
    color: #E5E5E7;
    font-family: 'IBM Plex Mono', 'Courier New', monospace;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
  }}
  .card {{
    max-width: 640px;
    width: 100%;
    background: rgba(10, 10, 11, 0.75);
    backdrop-filter: blur(20px);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 40px;
  }}
  .dot {{
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #22C55E;
    margin-right: 8px;
    box-shadow: 0 0 8px #22C55E;
  }}
  .status {{
    font-size: 11px;
    letter-spacing: 0.1em;
    color: #22C55E;
    text-transform: uppercase;
    margin-bottom: 20px;
  }}
  h1 {{
    font-size: 24px;
    font-weight: 500;
    margin: 0 0 8px 0;
    background: linear-gradient(90deg, #4F7BFF, #6C4DFF);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }}
  p.lead {{
    color: rgba(255,255,255,0.5);
    font-size: 13px;
    line-height: 1.6;
    margin: 0 0 28px 0;
  }}
  .warn {{
    border: 1px solid rgba(108, 77, 255, 0.3);
    background: rgba(108, 77, 255, 0.08);
    border-radius: 10px;
    padding: 14px 16px;
    font-size: 12px;
    color: #B9AFFF;
    margin-bottom: 28px;
    line-height: 1.6;
  }}
  .warn code {{
    background: rgba(255,255,255,0.08);
    padding: 1px 6px;
    border-radius: 4px;
    color: #fff;
  }}
  ul {{ list-style: none; padding: 0; margin: 0; }}
  li {{
    display: flex;
    justify-content: space-between;
    padding: 10px 0;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    font-size: 12px;
  }}
  li:last-child {{ border-bottom: none; }}
  li span:first-child {{ color: rgba(255,255,255,0.85); }}
  li span:last-child {{ color: rgba(255,255,255,0.4); }}
  a {{ color: #4F7BFF; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
  <div class="card">
    <div class="status"><span class="dot"></span>API operativa</div>
    <h1>Nura // Backend</h1>
    <p class="lead">Este es el servidor de API (Django). La interfaz de usuario vive en un proyecto aparte (React + Vite) y no se sirve desde aquí.</p>
    <div class="warn">
      Para ver la aplicación, corre el frontend en otra terminal:<br>
      <code>cd frontend && npm install && npm run dev</code><br>
      y abre <a href="http://localhost:5173">http://localhost:5173</a>.
    </div>
    <ul>
      <li><span>Panel de administración</span><span><a href="/admin/">/admin/</a></span></li>
      <li><span>API — chat</span><span>/chat/</span></li>
      <li><span>API — autenticación</span><span>/auth/</span></li>
      <li><span>Base de datos activa</span><span>{db_engine}</span></li>
    </ul>
  </div>
</body>
</html>"""


def api_status(request):
    from django.conf import settings
    engine = settings.DATABASES.get('default', {}).get('ENGINE', 'desconocido')
    engine_label = 'SQLite (desarrollo local)' if 'sqlite' in engine else 'PostgreSQL'
    return HttpResponse(STATUS_PAGE_HTML.format(db_engine=engine_label))
