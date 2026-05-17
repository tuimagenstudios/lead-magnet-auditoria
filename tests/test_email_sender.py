import base64
import unittest
from requests.exceptions import Timeout
from unittest.mock import patch

import email_sender


class EmailSenderTests(unittest.TestCase):
    def test_enviar_pdf_diagnostico_envia_con_adjunto_y_html_sanitizado(self):
        pdf_bytes = b"%PDF-test"
        response = {"id": "email_123"}

        with (
            patch.dict(
                "os.environ",
                {
                    "RESEND_API_KEY": "re_test_key",
                    "EMAIL_FROM": "naty@tuimagenstudios.com",
                },
                clear=False,
            ),
            patch.object(email_sender.resend.Emails, "send", return_value=response) as send_mock,
            patch("email_sender.print"),
        ):
            resultado = email_sender.enviar_pdf_diagnostico(
                "lead@example.com",
                pdf_bytes,
                "auditoria-tuimagen-test.pdf",
                "<script>alert(1)</script>",
            )

        self.assertEqual(resultado, {"enviado": True, "id": "email_123"})
        self.assertEqual(email_sender.resend.api_key, "re_test_key")
        self.assertEqual(email_sender.resend.default_http_client._timeout, 90)

        params = send_mock.call_args.args[0]
        self.assertEqual(params["from"], "Naty de Tuimagen <naty@tuimagenstudios.com>")
        self.assertEqual(params["to"], ["lead@example.com"])
        self.assertEqual(params["subject"], "Tu auditoría digital está lista ✦")
        self.assertEqual(params["attachments"][0]["filename"], "auditoria-tuimagen-test.pdf")
        self.assertEqual(
            params["attachments"][0]["content"],
            base64.b64encode(pdf_bytes).decode(),
        )
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", params["html"])
        self.assertNotIn("<script>alert(1)</script>", params["html"])

    def test_enviar_pdf_diagnostico_devuelve_error_si_falta_configuracion(self):
        with (
            patch.dict("os.environ", {"RESEND_API_KEY": "", "EMAIL_FROM": ""}, clear=False),
            patch.object(email_sender.resend.Emails, "send") as send_mock,
            patch("email_sender.print"),
        ):
            resultado = email_sender.enviar_pdf_diagnostico(
                "lead@example.com",
                b"%PDF-test",
                "auditoria.pdf",
                "tuimagenstudios.com",
            )

        self.assertFalse(resultado["enviado"])
        self.assertIn("RESEND_API_KEY", resultado["error"])
        send_mock.assert_not_called()

    def test_enviar_pdf_diagnostico_captura_error_de_resend(self):
        with (
            patch.dict(
                "os.environ",
                {
                    "RESEND_API_KEY": "re_test_key",
                    "EMAIL_FROM": "naty@tuimagenstudios.com",
                },
                clear=False,
            ),
            patch.object(email_sender.resend.Emails, "send", side_effect=RuntimeError("resend down")),
            patch("email_sender.print"),
        ):
            resultado = email_sender.enviar_pdf_diagnostico(
                "lead@example.com",
                b"%PDF-test",
                "auditoria.pdf",
                "tuimagenstudios.com",
            )

        self.assertEqual(resultado, {"enviado": False, "error": "resend down"})

    def test_enviar_pdf_diagnostico_reintenta_una_vez_si_hay_timeout(self):
        with (
            patch.dict(
                "os.environ",
                {
                    "RESEND_API_KEY": "re_test_key",
                    "EMAIL_FROM": "naty@tuimagenstudios.com",
                },
                clear=False,
            ),
            patch.object(
                email_sender.resend.Emails,
                "send",
                side_effect=[RuntimeError("Request failed: write operation timed out"), {"id": "email_retry"}],
            ) as send_mock,
            patch("email_sender.time.sleep") as sleep_mock,
            patch("email_sender.time.perf_counter", side_effect=[10.0, 13.5]),
            patch("email_sender.print") as print_mock,
        ):
            resultado = email_sender.enviar_pdf_diagnostico(
                "lead@example.com",
                b"%PDF-test",
                "auditoria.pdf",
                "tuimagenstudios.com",
            )

        self.assertEqual(resultado, {"enviado": True, "id": "email_retry"})
        self.assertEqual(send_mock.call_count, 2)
        sleep_mock.assert_called_once_with(3)
        trazas = [" ".join(str(arg) for arg in call.args) for call in print_mock.call_args_list]
        self.assertIn(">> [email] Intento 1/2...", trazas)
        self.assertIn(">> [email] Intento 2/2...", trazas)
        self.assertIn(">> [email] Reintento exitoso", trazas)
        self.assertIn(">> [email] Tiempo total: 3.5 s", trazas)

    def test_enviar_pdf_diagnostico_no_reintenta_errores_no_transitorios(self):
        with (
            patch.dict(
                "os.environ",
                {
                    "RESEND_API_KEY": "re_test_key",
                    "EMAIL_FROM": "naty@tuimagenstudios.com",
                },
                clear=False,
            ),
            patch.object(email_sender.resend.Emails, "send", side_effect=RuntimeError("API key is invalid")) as send_mock,
            patch("email_sender.time.sleep") as sleep_mock,
            patch("email_sender.time.perf_counter", side_effect=[10.0, 10.2]),
            patch("email_sender.print"),
        ):
            resultado = email_sender.enviar_pdf_diagnostico(
                "lead@example.com",
                b"%PDF-test",
                "auditoria.pdf",
                "tuimagenstudios.com",
            )

        self.assertEqual(resultado, {"enviado": False, "error": "API key is invalid"})
        send_mock.assert_called_once()
        sleep_mock.assert_not_called()

    def test_es_error_reintentable_detecta_timeout_anidado(self):
        exc = RuntimeError("Request failed")
        exc.__cause__ = Timeout("The write operation timed out")

        self.assertTrue(email_sender._es_error_reintentable(exc))


if __name__ == "__main__":
    unittest.main()
