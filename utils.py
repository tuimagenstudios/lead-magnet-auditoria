import re
from urllib.parse import urlparse


def dominio_o_handle(datos: dict | None, email: str) -> str:
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


def nombre_archivo_auditoria(valor_publico: str, email: str) -> str:
    base = valor_publico or email or "lead"
    base = base.lstrip("@")
    base = re.sub(r"[^a-zA-Z0-9_.-]+", "_", base).strip("._-")
    if not base:
        base = "lead"
    return f"auditoria-tuimagen-{base}.pdf"
