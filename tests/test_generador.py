import importlib
import json
import os
import unittest
from unittest.mock import Mock, patch


class GeneradorTests(unittest.TestCase):
    def setUp(self):
        self.env_patch = patch.dict(
            os.environ,
            {
                "GEMINI_MODEL": "modelo-test",
                "GEMINI_API_KEY_1": "key-1",
                "GEMINI_API_KEY_2": "key-2",
                "GEMINI_API_KEY_3": "",
                "GEMINI_API_KEY_4": "",
            },
        )
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop()

    def test_construye_prompt_omitiendo_secciones_faltantes(self):
        generador = importlib.import_module("generador")

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
        self.assertIn("AUTODIAGNÓSTICO DE REDES", prompt)
        self.assertNotIn("ANÁLISIS TÉCNICO DE LA WEB", prompt)
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
            "diagnostico_estrategico": "La presencia tiene señales valiosas. Conviene ordenar prioridades y sostener una rutina.",
            "servicios_sugeridos": [
                {"nombre": "Marketing Digital", "razon": "Ayuda a convertir publicaciones aisladas en un plan."}
            ],
        }

        modelo_fallido = Mock()
        modelo_fallido.generate_content.side_effect = RuntimeError("cuota")
        modelo_ok = Mock()
        modelo_ok.generate_content.return_value = Mock(text=f"```json\n{json.dumps(respuesta)}\n```")

        with patch.object(generador.genai, "configure") as configure, patch.object(
            generador.genai,
            "GenerativeModel",
            side_effect=[modelo_fallido, modelo_ok],
        ) as model_cls:
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
        self.assertEqual(configure.call_count, 2)
        self.assertEqual(model_cls.call_count, 2)
        model_cls.assert_called_with(
            model_name="modelo-test",
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 2048,
                "response_mime_type": "application/json",
            },
            system_instruction=generador.PROMPT_SISTEMA,
        )

    def test_generar_diagnostico_usa_fallback_si_modelo_configurado_no_existe(self):
        generador = importlib.reload(importlib.import_module("generador"))
        respuesta = {
            "puntaje_general": 74,
            "resumen_ejecutivo": "Hay buena base.",
            "fortalezas": ["Web activa", "Mensaje claro", "Identidad presente"],
            "oportunidades": [],
            "diagnostico_estrategico": "Conviene ordenar la estrategia de contenido.",
            "servicios_sugeridos": [],
        }
        modelo_no_encontrado = Mock()
        modelo_no_encontrado.generate_content.side_effect = RuntimeError("404 model is not found")
        modelo_ok = Mock()
        modelo_ok.generate_content.return_value = Mock(text=json.dumps(respuesta))

        with (
            patch.object(generador.genai, "configure"),
            patch.object(generador.genai, "GenerativeModel", side_effect=[modelo_no_encontrado, modelo_ok]) as model_cls,
        ):
            diagnostico = generador.generar_diagnostico(
                {
                    "url": "https://tuimagenstudios.com",
                    "instagram": "",
                    "email": "test@test.com",
                    "datos_web": {"status_code": 200},
                    "datos_ig": {"analizado": False},
                }
            )

        self.assertEqual(diagnostico["puntaje_general"], 74)
        modelos = [call.kwargs["model_name"] for call in model_cls.call_args_list]
        self.assertEqual(modelos, ["modelo-test", "gemini-2.0-flash"])

    def test_generar_diagnostico_emite_logs_de_debug(self):
        generador = importlib.reload(importlib.import_module("generador"))
        respuesta = {
            "puntaje_general": 72,
            "resumen_ejecutivo": "Hay una base clara.",
            "fortalezas": ["Web activa", "Marca reconocible", "Canal social presente"],
            "oportunidades": [],
            "diagnostico_estrategico": "La presencia tiene señales valiosas.",
            "servicios_sugeridos": [],
        }
        modelo = Mock()
        modelo.generate_content.return_value = Mock(text=json.dumps(respuesta))

        with (
            patch.object(generador.genai, "configure"),
            patch.object(generador.genai, "GenerativeModel", return_value=modelo),
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

        trazas = [" ".join(str(arg) for arg in call.args) for call in print_mock.call_args_list]

        self.assertTrue(any("✓ Keys cargadas:" in traza for traza in trazas))
        self.assertTrue(any("✓ Intentando con key" in traza for traza in trazas))
        self.assertTrue(any("✓ Respuesta recibida:" in traza for traza in trazas))

    def test_generar_diagnostico_reintenta_una_vez_si_el_json_falla(self):
        generador = importlib.reload(importlib.import_module("generador"))
        respuesta_ok = {
            "puntaje_general": 61,
            "resumen_ejecutivo": "Hay base, pero falta orden.",
            "fortalezas": ["Tiene canal", "Tiene contacto", "Hay intención"],
            "oportunidades": [],
            "diagnostico_estrategico": "El trabajo principal es ordenar los próximos pasos.",
            "servicios_sugeridos": [],
        }
        modelo = Mock()
        modelo.generate_content.side_effect = [
            Mock(text="esto no es json"),
            Mock(text=json.dumps(respuesta_ok)),
        ]

        with patch.object(generador.genai, "configure"), patch.object(
            generador.genai,
            "GenerativeModel",
            return_value=modelo,
        ):
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
        self.assertEqual(modelo.generate_content.call_count, 2)
        self.assertIn("El JSON anterior tuvo error", modelo.generate_content.call_args[0][0])

    def test_generar_diagnostico_devuelve_error_si_el_parseo_falla_dos_veces(self):
        generador = importlib.reload(importlib.import_module("generador"))
        modelo = Mock()
        modelo.generate_content.return_value = Mock(text="sin json")

        with patch.object(generador.genai, "configure"), patch.object(
            generador.genai,
            "GenerativeModel",
            return_value=modelo,
        ):
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
            {"error": "Diagnóstico no generado", "detalle": "Parseo JSON falló"},
        )


if __name__ == "__main__":
    unittest.main()
