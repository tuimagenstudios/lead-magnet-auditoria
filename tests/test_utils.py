import unittest

from utils import dominio_o_handle, nombre_archivo_auditoria


class UtilsTests(unittest.TestCase):
    def test_dominio_o_handle_prefiere_url_limpia(self):
        datos = {"url": "https://www.tuimagenstudios.com/contacto", "instagram": "@tuimagen_studio"}

        self.assertEqual(dominio_o_handle(datos, "test@test.com"), "tuimagenstudios.com")

    def test_dominio_o_handle_usa_instagram_si_no_hay_url(self):
        datos = {"url": "", "instagram": "@tuimagen_studio/"}

        self.assertEqual(dominio_o_handle(datos, "test@test.com"), "@tuimagen_studio")

    def test_dominio_o_handle_usa_email_como_fallback(self):
        self.assertEqual(dominio_o_handle({}, "test@test.com"), "test@test.com")

    def test_nombre_archivo_auditoria_sanitiza_valor_publico(self):
        self.assertEqual(
            nombre_archivo_auditoria("tuimagenstudios.com", "test@test.com"),
            "auditoria-tuimagen-tuimagenstudios.com.pdf",
        )
        self.assertEqual(
            nombre_archivo_auditoria("@tuimagen_studio", "test@test.com"),
            "auditoria-tuimagen-tuimagen_studio.pdf",
        )


if __name__ == "__main__":
    unittest.main()
