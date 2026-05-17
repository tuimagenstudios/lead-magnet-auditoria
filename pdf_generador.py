from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML

from utils import dominio_o_handle


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
BACKGROUND_ASSET = "assets/lead_magnet.png"
LOGO_ASSET = "assets/logo-tuimagen.png"


def _puntaje(diagnostico: dict) -> int:
    try:
        puntaje = int(diagnostico.get("puntaje_general", 0))
    except (TypeError, ValueError):
        return 0

    return max(0, min(100, puntaje))


def generar_pdf(diagnostico: dict, email: str, fecha: str, *, datos: dict | None = None) -> bytes:
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("pdf_diagnostico.html")
    puntaje = _puntaje(diagnostico)
    html = template.render(
        diagnostico=diagnostico,
        email=email,
        destinatario=dominio_o_handle(datos, email),
        fecha=fecha,
        puntaje=puntaje,
        progreso=puntaje,
        background_path=BACKGROUND_ASSET,
        logo_path=LOGO_ASSET,
    )

    return HTML(string=html, base_url=str(BASE_DIR)).write_pdf()
