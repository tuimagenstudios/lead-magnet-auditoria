import unittest
from unittest.mock import patch


DIAGNOSTICO = {
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
    "diagnostico_estrategico": "La presencia tiene senales valiosas y margen para crecer.",
    "servicios_sugeridos": [
        {"nombre": "Marketing Digital", "razon": "Ayuda a convertir publicaciones aisladas en un plan."}
    ],
}


class PdfGeneradorTests(unittest.TestCase):
    def test_generar_pdf_renderiza_siete_paginas_y_devuelve_bytes(self):
        import pdf_generador

        html_mock = patch.object(pdf_generador, "HTML").start()
        self.addCleanup(patch.stopall)
        html_mock.return_value.write_pdf.return_value = b"%PDF-test"

        pdf = pdf_generador.generar_pdf(DIAGNOSTICO, "test@test.com", "17 de mayo de 2026")

        self.assertEqual(pdf, b"%PDF-test")
        html_mock.assert_called_once()
        html = html_mock.call_args.kwargs["string"]
        self.assertEqual(html.count('class="page'), 7)
        self.assertIn("Auditoría Digital", html)
        self.assertIn("lead_magnet.png", html)
        self.assertIn("logo-tuimagen.png", html)
        self.assertIn("family=Manrope:wght@400;500;600;700", html)
        self.assertIn("--font-display: Arial, Helvetica, sans-serif", html)
        self.assertIn("--font-body: 'Manrope', Arial, sans-serif", html)
        self.assertIn("--font-mono: 'JetBrains Mono', Arial, sans-serif", html)
        self.assertIn("width: 72%", html)
        self.assertIn("test@test.com", html)
        html_mock.return_value.write_pdf.assert_called_once()


if __name__ == "__main__":
    unittest.main()
