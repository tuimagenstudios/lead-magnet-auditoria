import json
import os
import re
from json import JSONDecodeError
from datetime import datetime
from pathlib import Path
from typing import Optional

from analizador import analizar_instagram, analizar_web
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from generador import generar_diagnostico
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pdf_generador import generar_pdf
from pydantic import BaseModel, EmailStr, ValidationError, field_validator, model_validator


app = FastAPI()
templates = Environment(
    loader=FileSystemLoader("templates"),
    autoescape=select_autoescape(["html", "xml"]),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def trace(message: str) -> None:
    print(message, flush=True)


def fecha_larga(fecha: datetime | None = None) -> str:
    meses = [
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    ]
    actual = fecha or datetime.now()
    return f"{actual.day} de {meses[actual.month - 1]} de {actual.year}"


def guardar_pdf_temporal(pdf: bytes, email: str) -> str:
    output_dir = Path(os.getenv("PDF_OUTPUT_DIR", "/tmp"))
    output_dir.mkdir(parents=True, exist_ok=True)
    email_seguro = re.sub(r"[^a-zA-Z0-9_.-]+", "_", email).strip("_") or "lead"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta = output_dir / f"auditoria_{email_seguro}_{timestamp}.pdf"
    ruta.write_bytes(pdf)
    return str(ruta)


class AuditoriaRequest(BaseModel):
    url: Optional[str] = None
    instagram: str = ""
    email: EmailStr
    frecuencia: Optional[str] = None
    estrategia: Optional[str] = None
    reto: Optional[str] = None

    @field_validator("url", mode="before")
    @classmethod
    def limpiar_url(cls, value: Optional[str]) -> str:
        return value.strip() if value else ""

    @field_validator("instagram", mode="before")
    @classmethod
    def limpiar_instagram(cls, value: Optional[str]) -> str:
        return value.strip() if value else ""

    @field_validator("frecuencia", "estrategia", "reto")
    @classmethod
    def limpiar_pregunta_estrategica(cls, value: Optional[str]) -> Optional[str]:
        if not value or not value.strip():
            return None
        return value.strip()

    @model_validator(mode="after")
    def validar_preguntas_si_hay_instagram(self):
        if self.instagram and not all([self.frecuencia, self.estrategia, self.reto]):
            raise ValueError("Las preguntas estratégicas son obligatorias si hay Instagram")
        return self


@app.get("/")
async def formulario(request: Request):
    template = templates.get_template("formulario.html")
    return HTMLResponse(template.render(request=request))


@app.post("/auditar")
async def auditar(request: Request):
    trace(">> Petición recibida")

    try:
        payload = await request.json()
    except JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="JSON inválido") from exc

    try:
        datos = AuditoriaRequest.model_validate(payload)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail="Datos inválidos") from exc

    if not datos.url and not datos.instagram:
        raise HTTPException(status_code=400, detail="Necesitamos al menos tu web o tu Instagram")

    datos_formulario = {
        "url": datos.url,
        "instagram": datos.instagram,
        "email": str(datos.email),
        "frecuencia": datos.frecuencia,
        "estrategia": datos.estrategia,
        "reto": datos.reto,
    }

    datos_web = {"analizado": False}
    trace(">> Analizando web...")
    if datos.url:
        try:
            datos_web = analizar_web(datos.url)
        except Exception as exc:
            datos_web = {"error": f"Error inesperado en análisis web: {exc}"}
    trace(">> Web OK")

    trace(">> Analizando Instagram...")
    try:
        datos_ig = analizar_instagram(datos.instagram or "")
    except Exception as exc:
        datos_ig = {"analizado": False, "error": f"Error inesperado en análisis de Instagram: {exc}"}
    trace(">> Instagram OK")

    datos_diagnostico = {
        "formulario": datos_formulario,
        "web": datos_web,
        "instagram": datos_ig,
    }

    print("DATOS FORMULARIO:", flush=True)
    print(json.dumps(datos_formulario, indent=2, ensure_ascii=False), flush=True)
    print("ANÁLISIS WEB:", flush=True)
    print(json.dumps(datos_diagnostico["web"], indent=2, ensure_ascii=False), flush=True)
    print("ANÁLISIS INSTAGRAM:", flush=True)
    print(json.dumps(datos_diagnostico["instagram"], indent=2, ensure_ascii=False), flush=True)

    trace(">> Llamando a DeepSeek...")
    try:
        diagnostico = generar_diagnostico(
            {
                "url": datos.url,
                "instagram": datos.instagram,
                "email": str(datos.email),
                "frecuencia": datos.frecuencia,
                "estrategia": datos.estrategia,
                "reto": datos.reto,
                "datos_web": datos_web,
                "datos_ig": datos_ig,
            }
        )
    except Exception as exc:
        diagnostico = {"error": "Diagnóstico no generado", "detalle": str(exc)}
    trace(">> Diagnóstico generado")

    print("DIAGNÓSTICO:", flush=True)
    print(json.dumps(diagnostico, indent=2, ensure_ascii=False), flush=True)

    pdf_path = None
    if "error" not in diagnostico:
        trace(">> Generando PDF...")
        try:
            pdf = generar_pdf(diagnostico, str(datos.email), fecha_larga())
            tamano_kb = len(pdf) / 1024
            trace(f">> PDF generado: {tamano_kb:.1f} KB")
            pdf_path = guardar_pdf_temporal(pdf, str(datos.email))
            trace(f">> PDF guardado en: {pdf_path}")
        except Exception as exc:
            trace(f">> PDF no generado: {exc}")

    trace(">> Respondiendo al cliente")

    return JSONResponse(
        {
            "status": "recibido",
            "email": str(datos.email),
            "diagnostico_generado": "error" not in diagnostico,
            "pdf_generado": pdf_path is not None,
            "pdf_path": pdf_path,
        }
    )
