import importlib
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch


def respuesta_openai(texto):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=texto),
            )
        ]
    )


class GeneradorTests(unittest.TestCase):
    def setUp(self):
        self.env_patch = patch.dict(
            os.environ,
            {
                "DEEPSEEK_MODEL": "deepseek-test",
                "DEEPSEEK_BASE_URL": "https://api.deepseek.com",
                "DEEPSEEK_API_KEY_1": "key-1",
                "DEEPSEEK_API_KEY_2": "key-2",
                "DEEPSEEK_API_KEY_3": "",
                "DEEPSEEK_API_KEY_4": "",
            },
            clear=False,
        )
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()

    def test_construye_prompt_omitiendo_secciones_faltantes(self):
        generador = importlib.reload(importlib.import_module("generador"))

        prompt = generador.construir_prompt_usuario(
            {
                "url": "",
                "instagram": "@tuimagen_studio",
                "email": "test@test.com",
                "frecuencia": "esporadica",
                "estrategia": "improvisado",
                "reto": "ideas",
                "datos_web": {"analizado": False},
                "datos_ig": {"analizado": True},
            }
        )

        self.assertIn("Email: test@test.com", prompt)
        self.assertIn("Instagram: @tuimagen_studio", prompt)
        self.assertIn("AUTODIAGN", prompt)
        self.assertNotIn("TECNICO DE LA WEB", prompt)
        self.assertNotIn("null", prompt)

    def test_generar_diagnostico_rota_keys_y_parsea_json_limpio(self):
        generador = importlib.reload(importlib.import_module("generador"))
        respuesta = {
            "puntaje_general": 72,
            "resumen_ejecutivo": "Hay una base clara y oportunidades visibles.",
            "fortalezas": ["Web activa", "Marca reconocible", "Canal social presente"],
            "oportunidades": [
                {
                    "titulo": "Ordenar contenidos",
                    "descripcion": "La frecuencia y el plan necesitan estructura.",
                    "prioridad": "alta",
                }
            ],
            "diagnostico_estrategico": "La presencia tiene senales valiosas.",
            "servicios_sugeridos": [
                {"nombre": "Marketing Digital", "razon": "Ayuda a convertir publicaciones aisladas en un plan."}
            ],
        }

        cliente_fallido = Mock()
        cliente_fallido.chat.completions.create.side_effect = RuntimeError("cuota")
        cliente_ok = Mock()
        cliente_ok.chat.completions.create.return_value = respuesta_openai(f"```json\n{json.dumps(respuesta)}\n```")

        with patch.object(generador, "OpenAI", side_effect=[cliente_fallido, cliente_ok]) as openai_cls:
            diagnostico = generador.generar_diagnostico(
                {
                    "url": "https://tuimagenstudios.com",
                    "instagram": "@tuimagen_studio",
                    "email": "test@test.com",
                    "frecuencia": "esporadica",
                    "estrategia": "improvisado",
                    "reto": "ideas",
                    "datos_web": {"status_code": 200},
                    "datos_ig": {"analizado": True},
                }
            )

        self.assertEqual(diagnostico["puntaje_general"], 72)
        self.assertEqual(
            openai_cls.call_args_list,
            [
                call(api_key="key-1", base_url="https://api.deepseek.com"),
                call(api_key="key-2", base_url="https://api.deepseek.com"),
            ],
        )
        cliente_ok.chat.completions.create.assert_called_once()
        kwargs = cliente_ok.chat.completions.create.call_args.kwargs
        self.assertEqual(kwargs["model"], "deepseek-test")
        self.assertEqual(kwargs["temperature"], 0.7)
        self.assertEqual(kwargs["max_tokens"], 2048)
        self.assertEqual(kwargs["response_format"], {"type": "json_object"})
        self.assertEqual(kwargs["messages"][0], {"role": "system", "content": generador.PROMPT_SISTEMA})
        self.assertEqual(kwargs["messages"][1]["role"], "user")

    def test_generar_diagnostico_emite_logs_de_debug(self):
        generador = importlib.reload(importlib.import_module("generador"))
        respuesta = {
            "puntaje_general": 72,
            "resumen_ejecutivo": "Hay una base clara.",
            "fortalezas": ["Web activa", "Marca reconocible", "Canal social presente"],
            "oportunidades": [],
            "diagnostico_estrategico": "La presencia tiene senales valiosas.",
            "servicios_sugeridos": [],
        }
        cliente = Mock()
        cliente.chat.completions.create.return_value = respuesta_openai(json.dumps(respuesta))

        with (
            patch.object(generador, "OpenAI", return_value=cliente),
            patch("generador.print") as print_mock,
        ):
            generador.generar_diagnostico(
                {
                    "url": "https://tuimagenstudios.com",
                    "instagram": "@tuimagen_studio",
                    "email": "test@test.com",
                    "frecuencia": "esporadica",
                    "estrategia": "improvisado",
                    "reto": "ideas",
                    "datos_web": {"status_code": 200},
                    "datos_ig": {"analizado": True},
                }
            )

        trazas = [" ".join(str(arg) for arg in call_obj.args) for call_obj in print_mock.call_args_list]

        self.assertTrue(any("Keys DeepSeek cargadas:" in traza for traza in trazas))
        self.assertTrue(any("Intentando DeepSeek con key" in traza for traza in trazas))
        self.assertTrue(any("Respuesta DeepSeek recibida:" in traza for traza in trazas))

    def test_generar_diagnostico_reintenta_una_vez_si_el_json_falla(self):
        generador = importlib.reload(importlib.import_module("generador"))
        respuesta_ok = {
            "puntaje_general": 61,
            "resumen_ejecutivo": "Hay base, pero falta orden.",
            "fortalezas": ["Tiene canal", "Tiene contacto", "Hay intencion"],
            "oportunidades": [],
            "diagnostico_estrategico": "El trabajo principal es ordenar los proximos pasos.",
            "servicios_sugeridos": [],
        }
        cliente = Mock()
        cliente.chat.completions.create.side_effect = [
            respuesta_openai("esto no es json"),
            respuesta_openai(json.dumps(respuesta_ok)),
        ]

        with patch.object(generador, "OpenAI", return_value=cliente):
            diagnostico = generador.generar_diagnostico(
                {
                    "url": "https://tuimagenstudios.com",
                    "instagram": "",
                    "email": "test@test.com",
                    "datos_web": {"status_code": 200},
                    "datos_ig": {"analizado": False},
                }
            )

        self.assertEqual(diagnostico["puntaje_general"], 61)
        self.assertEqual(cliente.chat.completions.create.call_count, 2)
        segundo_prompt = cliente.chat.completions.create.call_args.kwargs["messages"][1]["content"]
        self.assertIn("El JSON anterior tuvo error", segundo_prompt)

    def test_generar_diagnostico_devuelve_error_si_el_parseo_falla_dos_veces(self):
        generador = importlib.reload(importlib.import_module("generador"))
        cliente = Mock()
        cliente.chat.completions.create.return_value = respuesta_openai("sin json")

        with patch.object(generador, "OpenAI", return_value=cliente):
            diagnostico = generador.generar_diagnostico(
                {
                    "url": "https://tuimagenstudios.com",
                    "instagram": "",
                    "email": "test@test.com",
                    "datos_web": {"status_code": 200},
                    "datos_ig": {"analizado": False},
                }
            )

        self.assertEqual(
            diagnostico,
            {"error": "Diagnostico no generado", "detalle": "Parseo JSON fallo"},
        )


if __name__ == "__main__":
    unittest.main()
