import asyncio
import json
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from main import auditar


class FakeRequest:
    def __init__(self, payload):
        self.payload = payload

    async def json(self):
        return self.payload


class AuditarEndpointTests(unittest.TestCase):
    def test_auditar_incluye_preview_de_analisis(self):
        request = FakeRequest(
            {
                "url": "https://tuimagenstudios.com",
                "instagram": "@tuimagen_studio",
                "email": "test@test.com",
                "frecuencia": "semanal_alta",
                "estrategia": "parcial",
                "reto": "ventas",
            }
        )

        with (
            patch("main.analizar_web", return_value={"status_code": 200}, create=True) as analizar_web,
            patch("main.analizar_instagram", return_value={"analizado": True}, create=True) as analizar_ig,
        ):
            response = asyncio.run(auditar(request))

        body = json.loads(response.body)

        self.assertEqual(body["status"], "recibido")
        self.assertEqual(body["email"], "test@test.com")
        self.assertEqual(body["preview"], {"web_ok": True, "ig_ok": True})
        analizar_web.assert_called_once_with("https://tuimagenstudios.com")
        analizar_ig.assert_called_once_with("@tuimagen_studio")

    def test_auditar_rechaza_si_faltan_preguntas_estrategicas(self):
        request = FakeRequest(
            {
                "url": "https://tuimagenstudios.com",
                "instagram": "@tuimagen_studio",
                "email": "test@test.com",
                "frecuencia": "semanal_alta",
                "estrategia": "",
                "reto": "ventas",
            }
        )

        with self.assertRaises(HTTPException) as context:
            asyncio.run(auditar(request))

        self.assertEqual(context.exception.status_code, 400)

    def test_auditar_acepta_sin_preguntas_si_instagram_esta_vacio(self):
        request = FakeRequest(
            {
                "url": "https://tuimagenstudios.com",
                "instagram": "",
                "email": "test@test.com",
            }
        )

        with (
            patch("main.analizar_web", return_value={"status_code": 200}, create=True) as analizar_web,
            patch("main.analizar_instagram", return_value={"analizado": False}, create=True) as analizar_ig,
        ):
            response = asyncio.run(auditar(request))

        body = json.loads(response.body)

        self.assertEqual(body["status"], "recibido")
        self.assertEqual(body["preview"], {"web_ok": True, "ig_ok": False})
        analizar_web.assert_called_once_with("https://tuimagenstudios.com")
        analizar_ig.assert_called_once_with("")


if __name__ == "__main__":
    unittest.main()
