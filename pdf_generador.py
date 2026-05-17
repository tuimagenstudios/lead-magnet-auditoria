from pathlib import Path
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML


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


def _destinatario(datos: dict | None, email: str) -> str:
    datos = datos or {}
    url = (datos.get("url") or "").strip()
    instagram = (datos.get("instagram") or "").strip()

    if url:
        parsed = urlparse(url if "://" in url else f"https://{url}")
        dominio = (parsed.netloc or parsed.path).split("/")[0].lower()
        dominio = dominio.removeprefix("www.").strip()
        if dominio:
            return dominio

    if instagram:
        handle = instagram.lstrip("@").strip().strip("/")
        if handle:
            return f"@{handle}"

    return email


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
        destinatario=_destinatario(datos, email),
        fecha=fecha,
        puntaje=puntaje,
        progreso=puntaje,
        background_path=BACKGROUND_ASSET,
        logo_path=LOGO_ASSET,
    )

    return HTML(string=html, base_url=str(BASE_DIR)).write_pdf()
