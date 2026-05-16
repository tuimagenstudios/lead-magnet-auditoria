import unittest
from unittest.mock import Mock, patch

import requests

from analizador import analizar_instagram, analizar_web


class AnalizadorWebTests(unittest.TestCase):
    @patch("analizador.requests.get")
    @patch("analizador.time.perf_counter")
    def test_analizar_web_extrae_metricas_basicas(self, perf_counter, mock_get):
        perf_counter.side_effect = [10.0, 10.245]
        response = Mock()
        response.status_code = 200
        response.text = """
        <html>
          <head>
            <title>Marca digital</title>
            <meta name="description" content="Consultoria digital clara">
            <meta property="og:title" content="Marca digital OG">
            <meta name="twitter:card" content="summary_large_image">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <link rel="icon" href="/favicon.ico">
            <script type="application/ld+json">{"@context": "https://schema.org"}</script>
          </head>
          <body>
            <h1>Inicio</h1>
            <img src="/a.jpg" alt="Equipo">
            <img src="/b.jpg">
          </body>
        </html>
        """
        mock_get.return_value = response

        resultado = analizar_web("https://example.com")

        self.assertEqual(resultado["https"], True)
        self.assertEqual(resultado["tiempo_carga_ms"], 245)
        self.assertEqual(resultado["status_code"], 200)
        self.assertEqual(resultado["title"], "Marca digital")
        self.assertEqual(resultado["title_length"], 13)
        self.assertEqual(resultado["meta_description"], "Consultoria digital clara")
        self.assertEqual(resultado["meta_description_length"], 25)
        self.assertEqual(resultado["open_graph"], True)
        self.assertEqual(resultado["twitter_card"], True)
        self.assertEqual(resultado["schema_org"], True)
        self.assertEqual(resultado["viewport_responsive"], True)
        self.assertEqual(resultado["favicon"], True)
        self.assertEqual(resultado["cantidad_imagenes"], 2)
        self.assertEqual(resultado["imagenes_sin_alt"], 1)
        self.assertEqual(resultado["cantidad_h1"], 1)
        self.assertEqual(resultado["tiene_h1"], True)
        mock_get.assert_called_once()
        self.assertEqual(mock_get.call_args.kwargs["timeout"], 10)
        self.assertIn("User-Agent", mock_get.call_args.kwargs["headers"])

    @patch("analizador.requests.get")
    def test_analizar_web_retorna_error_claro_si_falla(self, mock_get):
        mock_get.side_effect = requests.Timeout("se agotó el tiempo")

        resultado = analizar_web("https://example.com")

        self.assertEqual(resultado, {"error": "No se pudo analizar la web: se agotó el tiempo"})


class AnalizadorInstagramTests(unittest.TestCase):
    def test_instagram_vacio_no_se_analiza(self):
        self.assertEqual(analizar_instagram(""), {"analizado": False})

    @patch("analizador.requests.get")
    def test_instagram_limpia_handle_y_extrae_open_graph(self, mock_get):
        response = Mock()
        response.status_code = 200
        response.text = """
        <html>
          <head>
            <meta property="og:title" content="Tu Imagen Studio (@tuimagen_studio)">
            <meta property="og:description" content="Branding y presencia digital">
            <meta property="og:image" content="https://cdn.example.com/profile.jpg">
          </head>
        </html>
        """
        mock_get.return_value = response

        resultado = analizar_instagram("@tuimagen_studio")

        self.assertEqual(resultado["analizado"], True)
        self.assertEqual(resultado["handle"], "tuimagen_studio")
        self.assertEqual(resultado["perfil_existe"], True)
        self.assertEqual(resultado["bio_snippet"], "Branding y presencia digital")
        self.assertEqual(resultado["imagen_perfil"], "https://cdn.example.com/profile.jpg")
        self.assertEqual(resultado["url_perfil"], "https://www.instagram.com/tuimagen_studio/")


if __name__ == "__main__":
    unittest.main()
