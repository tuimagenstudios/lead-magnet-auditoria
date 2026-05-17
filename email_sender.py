import base64
import os
from pathlib import Path

import resend
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"


def _template_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )


def _response_id(response) -> str:
    if isinstance(response, dict):
        return response.get("id", "")
    return getattr(response, "id", "") or ""


def enviar_pdf_diagnostico(
    email_destinatario: str,
    pdf_bytes: bytes,
    nombre_archivo: str,
    dominio_o_handle: str,
) -> dict:
    load_dotenv()

    resend_api_key = os.getenv("RESEND_API_KEY", "").strip()
    email_from = os.getenv("EMAIL_FROM", "").strip()

    if not resend_api_key or not email_from:
        error = "Falta configurar RESEND_API_KEY o EMAIL_FROM"
        print(">> [email] Resultado:", error, flush=True)
        return {"enviado": False, "error": error}

    resend.api_key = resend_api_key

    print(">> [email] Enviando a:", email_destinatario, flush=True)
    print(">> [email] PDF size:", len(pdf_bytes), "bytes", flush=True)

    try:
        html = _template_env().get_template("email_diagnostico.html").render(
            dominio_o_handle=dominio_o_handle
        )
        params = {
            "from": f"Naty de Tuimagen <{email_from}>",
            "to": [email_destinatario],
            "subject": "Tu auditoría digital está lista ✦",
            "html": html,
            "attachments": [
                {
                    "filename": nombre_archivo,
                    "content": base64.b64encode(pdf_bytes).decode(),
                }
            ],
        }
        response = resend.Emails.send(params)
        email_id = _response_id(response)
        print(">> [email] Resultado:", email_id, flush=True)
        return {"enviado": True, "id": email_id}
    except Exception as exc:
        error = str(exc)
        print(">> [email] Resultado:", error, flush=True)
        return {"enviado": False, "error": error}
