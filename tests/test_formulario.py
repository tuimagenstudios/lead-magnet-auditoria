from pathlib import Path
import unittest


class FormularioTemplateTests(unittest.TestCase):
    def setUp(self):
        self.html = Path("templates/formulario.html").read_text(encoding="utf-8")

    def test_incluye_preguntas_estrategicas_obligatorias(self):
        self.assertIn("Contanos un poco más", self.html)
        self.assertIn('name="frecuencia"', self.html)
        self.assertIn('name="estrategia"', self.html)
        self.assertIn('name="reto"', self.html)
        self.assertIn('value="diaria"', self.html)
        self.assertIn('value="con_plan"', self.html)
        self.assertIn('value="ventas"', self.html)
        self.assertIn("Por favor respondé las 3 preguntas.", self.html)

    def test_payload_js_envia_los_tres_campos(self):
        self.assertIn("frecuencia: getRadioValue(\"frecuencia\")", self.html)
        self.assertIn("estrategia: getRadioValue(\"estrategia\")", self.html)
        self.assertIn("reto: getRadioValue(\"reto\")", self.html)


if __name__ == "__main__":
    unittest.main()
