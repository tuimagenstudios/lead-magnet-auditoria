import json
from json import JSONDecodeError
from typing import Optional

from analizador import analizar_instagram, analizar_web
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
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
    if datos.url:
        try:
            datos_web = analizar_web(datos.url)
        except Exception as exc:
            datos_web = {"error": f"Error inesperado en análisis web: {exc}"}

    try:
        datos_ig = analizar_instagram(datos.instagram or "")
    except Exception as exc:
        datos_ig = {"analizado": False, "error": f"Error inesperado en análisis de Instagram: {exc}"}

    datos_diagnostico = {
        "formulario": datos_formulario,
        "web": datos_web,
        "instagram": datos_ig,
    }

    print("DATOS FORMULARIO:")
    print(json.dumps(datos_formulario, indent=2, ensure_ascii=False))
    print("ANÁLISIS WEB:")
    print(json.dumps(datos_diagnostico["web"], indent=2, ensure_ascii=False))
    print("ANÁLISIS INSTAGRAM:")
    print(json.dumps(datos_diagnostico["instagram"], indent=2, ensure_ascii=False))

    return JSONResponse(
        {
            "status": "recibido",
            "email": str(datos.email),
            "preview": {
                "web_ok": datos_web.get("status_code") == 200,
                "ig_ok": datos_ig.get("analizado", False),
            },
        }
    )
