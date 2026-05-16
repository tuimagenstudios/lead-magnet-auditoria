from json import JSONDecodeError
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel, EmailStr, ValidationError, field_validator


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
    url: str
    instagram: Optional[str] = None
    email: EmailStr

    @field_validator("url")
    @classmethod
    def validar_url(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("La URL es obligatoria")
        return value.strip()

    @field_validator("instagram")
    @classmethod
    def limpiar_instagram(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        limpio = value.strip()
        return limpio or None


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

    print(
        {
            "url": datos.url,
            "instagram": datos.instagram,
            "email": str(datos.email),
        }
    )

    return JSONResponse({"status": "recibido", "email": str(datos.email)})
