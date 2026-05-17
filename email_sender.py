import base64
import os
import time
from pathlib import Path

import resend
from dotenv import load_dotenv
from jinja2 import Environment, FileSystemLoader, select_autoescape
from requests.exceptions import ConnectionError as RequestsConnectionError
from requests.exceptions import Timeout as RequestsTimeout
from resend.http_client_requests import RequestsClient


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
RESEND_TIMEOUT_SECONDS = 90
EMAIL_MAX_INTENTOS = 2
EMAIL_RETRY_SLEEP_SECONDS = 3


def _template_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(["html", "xml"]),
    )


def _response_id(response) -> str:
    if isinstance(response, dict):
        return response.get("id", "")
    return getattr(response, "id", "") or ""


def _es_error_reintentable(exc: Exception) -> bool:
    actual = exc
    while actual:
        if isinstance(actual, (TimeoutError, ConnectionError, RequestsTimeout, RequestsConnectionError)):
            return True
        actual = actual.__cause__

    mensaje = str(exc).lower()
    return any(
        fragmento in mensaje
        for fragmento in [
            "timeout",
            "timed out",
            "connection aborted",
            "connectionerror",
            "connection error",
        ]
    )


def enviar_pdf_diagnostico(
    email_destinatario: str,
    pdf_bytes: bytes,
    nombre_archivo: str,
    dominio_o_handle: str,
) -> dict:
    load_dotenv(override=False)

    resend_api_key = os.getenv("RESEND_API_KEY", "").strip()
    email_from = os.getenv("EMAIL_FROM", "").strip()

    if not resend_api_key or not email_from:
        error = "Falta configurar RESEND_API_KEY o EMAIL_FROM"
        print(">> [email] Resultado:", error, flush=True)
        return {"enviado": False, "error": error}

    resend.api_key = resend_api_key
    resend.default_http_client = RequestsClient(timeout=RESEND_TIMEOUT_SECONDS)

    print(">> [email] Enviando a:", email_destinatario, flush=True)
    print(">> [email] PDF size:", len(pdf_bytes), "bytes", flush=True)
    inicio = time.perf_counter()

    html = _template_env().get_template("email_diagnostico.html").render(
        dominio_o_handle=dominio_o_handle
    )
    params = {
        "from": f"Naty de Tuimagen <{email_from}>",
        "to": [email_destinatario],
        "subject": "Tu auditor\u00eda digital est\u00e1 lista \u2726",
        "html": html,
        "attachments": [
            {
                "filename": nombre_archivo,
                "content": base64.b64encode(pdf_bytes).decode(),
            }
        ],
    }

    for intento in range(1, EMAIL_MAX_INTENTOS + 1):
        try:
            print(f">> [email] Intento {intento}/{EMAIL_MAX_INTENTOS}...", flush=True)
            response = resend.Emails.send(params)
            email_id = _response_id(response)
            if intento > 1:
                print(">> [email] Reintento exitoso", flush=True)
            print(">> [email] Resultado:", email_id, flush=True)
            print(">> [email] Tiempo total:", round(time.perf_counter() - inicio, 1), "s", flush=True)
            return {"enviado": True, "id": email_id}
        except Exception as exc:
            error = str(exc)
            if intento < EMAIL_MAX_INTENTOS and _es_error_reintentable(exc):
                time.sleep(EMAIL_RETRY_SLEEP_SECONDS)
                continue

            print(">> [email] Resultado:", error, flush=True)
            print(">> [email] Tiempo total:", round(time.perf_counter() - inicio, 1), "s", flush=True)
            return {"enviado": False, "error": error}
