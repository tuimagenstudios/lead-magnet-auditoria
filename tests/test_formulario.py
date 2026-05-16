from pathlib import Path
import unittest


class FormularioTemplateTests(unittest.TestCase):
    def setUp(self):
        self.html = Path("templates/formulario.html").read_text(encoding="utf-8")

    def test_incluye_preguntas_estrategicas_condicionales(self):
        self.assertIn("Contanos un poco m\u00e1s", self.html)
        self.assertIn('id="preguntas-extra"', self.html)
        self.assertIn("#preguntas-extra", self.html)
        self.assertIn("max-height: 0", self.html)
        self.assertIn("opacity: 0", self.html)
        self.assertIn("transition: all 300ms ease", self.html)
        self.assertIn("#preguntas-extra.visible", self.html)
        self.assertIn('name="frecuencia"', self.html)
        self.assertIn('name="estrategia"', self.html)
        self.assertIn('name="reto"', self.html)
        self.assertIn('value="diaria"', self.html)
        self.assertIn('value="con_plan"', self.html)
        self.assertIn('value="ventas"', self.html)
        self.assertIn("Por favor respond\u00e9 las 3 preguntas sobre tu Instagram", self.html)

    def test_js_muestra_limpia_y_envia_campos_condicionales(self):
        self.assertIn("const instagramInput = form.instagram;", self.html)
        self.assertIn('instagramInput.addEventListener("input", toggleStrategicQuestions);', self.html)
        self.assertIn("clearStrategicAnswers", self.html)
        self.assertIn("radio.checked = false", self.html)
        self.assertIn('preguntasExtra.classList.add("visible")', self.html)
        self.assertIn('preguntasExtra.classList.remove("visible")', self.html)
        self.assertIn('frecuencia: instagramActivo ? getRadioValue("frecuencia") : null', self.html)
        self.assertIn('estrategia: instagramActivo ? getRadioValue("estrategia") : null', self.html)
        self.assertIn('reto: instagramActivo ? getRadioValue("reto") : null', self.html)


if __name__ == "__main__":
    unittest.main()
