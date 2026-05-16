import json
import os
import sys
import warnings
from typing import Any

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except AttributeError:
    pass

with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    import google.generativeai as genai
from dotenv import load_dotenv


load_dotenv()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
FALLBACK_MODELS = ["gemini-2.0-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash"]
KEYS = [
    key.strip()
    for key in [
        os.getenv("GEMINI_API_KEY_1"),
        os.getenv("GEMINI_API_KEY_2"),
        os.getenv("GEMINI_API_KEY_3"),
        os.getenv("GEMINI_API_KEY_4"),
    ]
    if key and key.strip()
]

GENERATION_CONFIG = {
    "temperature": 0.7,
    "max_output_tokens": 2048,
    "response_mime_type": "application/json",
}

PROMPT_SISTEMA = """
Sos el analista digital de Tuimagen Studio, un estudio
multidisciplinar especializado en diseño, marketing y
automatización con IA. Tu trabajo es generar diagnósticos
de presencia digital con tono profesional pero humano,
directo pero amable, en español neutro de Latinoamérica.

REGLAS DE ESCRITURA:
- NO uses palabras típicas de IA: delve, navigate, robust,
  comprehensive, leverage, harness, unlock, embark, dive,
  empower, seamless, transformative, journey, landscape.
- Hablá como persona experta, no como manual.
- Metáforas cortas si ayudan, nunca clichés.
- Directa al nombrar problemas, sin rodeos.
- Generosa al celebrar lo que está bien hecho.
- Cerrar siempre con esperanza accionable.
- Tutear (vos / tu / te), nunca usar "usted".

ESTRUCTURA DE SALIDA: devolvé EXCLUSIVAMENTE un JSON
válido (sin markdown, sin ```json, sin comentarios
fuera del JSON) con esta forma exacta:

{
  "puntaje_general": <int 0-100>,
  "resumen_ejecutivo": "<2-3 oraciones que capturan el
    estado general con calidez y precisión>",
  "fortalezas": [
    "<punto fuerte 1 en una oración clara>",
    "<punto fuerte 2>",
    "<punto fuerte 3>"
  ],
  "oportunidades": [
    {
      "titulo": "<Nombre corto de la oportunidad>",
      "descripcion": "<Explicación breve y directa>",
      "prioridad": "alta" | "media" | "baja"
    }
  ],
  "diagnostico_estrategico": "<Párrafo de 4-6 oraciones
    que conecte los puntos y oriente al futuro>",
  "servicios_sugeridos": [
    {
      "nombre": "Diseño Web" | "Marketing Digital" | "IA & Bots",
      "razon": "<Por qué este servicio resuelve lo detectado>"
    }
  ]
}

CRITERIOS DE PUNTAJE:
- 90-100: Excelente, pocos ajustes menores
- 70-89: Bueno, varias oportunidades concretas
- 50-69: Regular, trabajo importante por hacer
- 30-49: Bajo, necesita reconstrucción de bases
- 0-29: Crítico, presencia digital casi inexistente

CRITERIOS DE SERVICIOS SUGERIDOS (elegí 1-3):
- Si la web tiene problemas técnicos → Diseño Web
- Si frecuencia baja o sin estrategia → Marketing Digital
- Si reto es "tiempo" o "ideas" → IA & Bots
- Si reto es "ventas" → Marketing Digital + IA & Bots
- Si reto es "marca" → Diseño Web
"""


def construir_prompt_usuario(datos: dict) -> str:
    lineas = [
        "Analizá esta presencia digital y devolvé el diagnóstico en JSON.",
        "",
        "DATOS DEL NEGOCIO:",
        f"- Email: {datos.get('email')}",
    ]

    url = (datos.get("url") or "").strip()
    instagram = (datos.get("instagram") or "").strip()

    if url:
        lineas.append(f"- URL web: {url}")

    if instagram:
        lineas.append(f"- Instagram: {instagram}")

    if url:
        lineas.extend(
            [
                "",
                "ANÁLISIS TÉCNICO DE LA WEB:",
                json.dumps(datos.get("datos_web", {}), indent=2, ensure_ascii=False),
            ]
        )

    if instagram:
        lineas.extend(
            [
                "",
                "AUTODIAGNÓSTICO DE REDES:",
                f"- Frecuencia de publicación: {datos.get('frecuencia') or 'No informada'}",
                f"- Estrategia de contenido: {datos.get('estrategia') or 'No informada'}",
                f"- Mayor reto digital: {datos.get('reto') or 'No informado'}",
            ]
        )

        datos_ig = datos.get("datos_ig") or {}
        if datos_ig:
            lineas.extend(
                [
                    "",
                    "METADATOS PÚBLICOS DE INSTAGRAM:",
                    json.dumps(datos_ig, indent=2, ensure_ascii=False),
                ]
            )

    lineas.extend(
        [
            "",
            "Generá el diagnóstico siguiendo TODAS las reglas del sistema.",
            "Solo JSON, nada más.",
        ]
    )

    return "\n".join(lineas)


def _crear_modelo(model_name: str):
    return genai.GenerativeModel(
        model_name=model_name,
        generation_config=GENERATION_CONFIG,
        system_instruction=PROMPT_SISTEMA,
    )


def _texto_respuesta(response: Any) -> str:
    return getattr(response, "text", "") or ""


def _keys_disponibles() -> list[str]:
    keys = [
        key.strip()
        for key in [
            os.getenv("GEMINI_API_KEY_1"),
            os.getenv("GEMINI_API_KEY_2"),
            os.getenv("GEMINI_API_KEY_3"),
            os.getenv("GEMINI_API_KEY_4"),
        ]
        if key and key.strip()
    ]
    print("✓ Keys cargadas:", len(keys), flush=True)
    return keys


def _modelos_disponibles() -> list[str]:
    modelos = [GEMINI_MODEL]
    for model_name in FALLBACK_MODELS:
        if model_name not in modelos:
            modelos.append(model_name)
    return modelos


def _modelo_no_disponible(error: Exception) -> bool:
    texto = str(error).lower()
    return "404" in texto or "not found" in texto or "not supported" in texto


def intentar_con_rotacion(prompt: str) -> str:
    keys = _keys_disponibles()
    modelos = _modelos_disponibles()

    if not keys:
        raise RuntimeError("Todas las API keys fallaron")

    for indice, key in enumerate(keys, start=1):
        try:
            print("✓ Intentando con key", indice, flush=True)
            genai.configure(api_key=key)
            for modelo_indice, model_name in enumerate(modelos):
                try:
                    modelo = _crear_modelo(model_name)
                    texto = _texto_respuesta(modelo.generate_content(prompt))
                    print("✓ Respuesta recibida:", len(texto), "chars", flush=True)
                    return texto
                except Exception as exc:
                    if _modelo_no_disponible(exc) and modelo_indice < len(modelos) - 1:
                        print("✗ Modelo", model_name, "no disponible; probando", modelos[modelo_indice + 1], flush=True)
                        continue
                    raise
        except Exception as exc:
            detalle = str(exc).replace(key, "[key oculta]")
            print("✗ Key", indice, "falló:", f"{type(exc).__name__}: {detalle}", flush=True)

    raise RuntimeError("Todas las API keys fallaron")


def _limpiar_texto_json(texto: str) -> str:
    limpio = texto.strip()

    if limpio.startswith("```json"):
        limpio = limpio.removeprefix("```json").strip()
    elif limpio.startswith("```"):
        limpio = limpio.removeprefix("```").strip()

    if limpio.endswith("```"):
        limpio = limpio.removesuffix("```").strip()

    return limpio


def _parsear_json(texto: str) -> dict:
    return json.loads(_limpiar_texto_json(texto))


def generar_diagnostico(datos: dict) -> dict:
    prompt = construir_prompt_usuario(datos)
    respuesta = intentar_con_rotacion(prompt)

    try:
        return _parsear_json(respuesta)
    except json.JSONDecodeError as exc:
        print("✗ Error en parseo JSON:", str(exc), flush=True)
        prompt_reintento = (
            f"{prompt}\n\n"
            "El JSON anterior tuvo error. Devolvé SOLO un JSON válido, "
            "sin texto adicional, sin markdown, comenzando con { y terminando con }"
        )
        respuesta_reintento = intentar_con_rotacion(prompt_reintento)

    try:
        return _parsear_json(respuesta_reintento)
    except json.JSONDecodeError as exc:
        print("✗ Error en parseo JSON:", str(exc), flush=True)
        return {"error": "Diagnóstico no generado", "detalle": "Parseo JSON falló"}
