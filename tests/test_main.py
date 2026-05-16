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
    def test_auditar_emite_trazas_del_flujo_completo(self):
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
            patch("main.analizar_web", return_value={"status_code": 200}, create=True),
            patch("main.analizar_instagram", return_value={"analizado": True}, create=True),
            patch("main.generar_diagnostico", return_value={"puntaje_general": 72}, create=True),
            patch("main.print") as print_mock,
        ):
            asyncio.run(auditar(request))

        trazas = [call.args[0] for call in print_mock.call_args_list if call.args]

        for esperado in [
            ">> Petición recibida",
            ">> Analizando web...",
            ">> Web OK",
            ">> Analizando Instagram...",
            ">> Instagram OK",
            ">> Llamando a Gemini...",
            ">> Diagnóstico generado",
            ">> Respondiendo al cliente",
        ]:
            self.assertIn(esperado, trazas)

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
            patch("main.generar_diagnostico", return_value={"puntaje_general": 72}, create=True) as generar,
        ):
            response = asyncio.run(auditar(request))

        body = json.loads(response.body)

        self.assertEqual(body["status"], "recibido")
        self.assertEqual(body["email"], "test@test.com")
        self.assertTrue(body["diagnostico_generado"])
        self.assertNotIn("preview", body)
        analizar_web.assert_called_once_with("https://tuimagenstudios.com")
        analizar_ig.assert_called_once_with("@tuimagen_studio")
        generar.assert_called_once()
        self.assertEqual(generar.call_args.args[0]["datos_web"], {"status_code": 200})
        self.assertEqual(generar.call_args.args[0]["datos_ig"], {"analizado": True})

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
            patch("main.generar_diagnostico", return_value={"puntaje_general": 80}, create=True),
        ):
            response = asyncio.run(auditar(request))

        body = json.loads(response.body)

        self.assertEqual(body["status"], "recibido")
        self.assertTrue(body["diagnostico_generado"])
        analizar_web.assert_called_once_with("https://tuimagenstudios.com")
        analizar_ig.assert_called_once_with("")

    def test_auditar_acepta_solo_instagram_con_preguntas(self):
        request = FakeRequest(
            {
                "url": "",
                "instagram": "@tuimagen_studio",
                "email": "test@test.com",
                "frecuencia": "diaria",
                "estrategia": "con_plan",
                "reto": "ventas",
            }
        )

        with (
            patch("main.analizar_web", return_value={"status_code": 200}, create=True) as analizar_web,
            patch("main.analizar_instagram", return_value={"analizado": True}, create=True) as analizar_ig,
            patch("main.generar_diagnostico", return_value={"puntaje_general": 67}, create=True),
        ):
            response = asyncio.run(auditar(request))

        body = json.loads(response.body)

        self.assertEqual(body["status"], "recibido")
        self.assertTrue(body["diagnostico_generado"])
        analizar_web.assert_not_called()
        analizar_ig.assert_called_once_with("@tuimagen_studio")

    def test_auditar_rechaza_sin_web_ni_instagram(self):
        request = FakeRequest(
            {
                "url": "",
                "instagram": "",
                "email": "test@test.com",
            }
        )

        with self.assertRaises(HTTPException) as context:
            asyncio.run(auditar(request))

        self.assertEqual(context.exception.status_code, 400)
        self.assertEqual(context.exception.detail, "Necesitamos al menos tu web o tu Instagram")

    def test_auditar_no_rompe_si_generador_falla(self):
        request = FakeRequest(
            {
                "url": "https://tuimagenstudios.com",
                "instagram": "",
                "email": "test@test.com",
            }
        )

        with (
            patch("main.analizar_web", return_value={"status_code": 200}, create=True),
            patch("main.analizar_instagram", return_value={"analizado": False}, create=True),
            patch("main.generar_diagnostico", side_effect=RuntimeError("Gemini caído"), create=True),
        ):
            response = asyncio.run(auditar(request))

        body = json.loads(response.body)

        self.assertEqual(body["status"], "recibido")
        self.assertFalse(body["diagnostico_generado"])


if __name__ == "__main__":
    unittest.main()
