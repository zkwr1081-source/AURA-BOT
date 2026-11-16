import unittest

from aura_core import (
    MENU_ROWS,
    PAYMENT_DISABLED_MESSAGE,
    SECTIONS,
    UNKNOWN_CALLBACK_MESSAGE,
    get_section_text,
    is_supported_callback,
)


class AuraCoreTests(unittest.TestCase):
    def test_all_six_sections_are_registered(self):
        self.assertEqual(len(SECTIONS), 6)
        self.assertEqual(set(SECTIONS), {
            "serv_enterprise", "serv_multi", "serv_chat",
            "serv_code", "serv_analytics", "serv_automation",
        })

    def test_every_section_has_nonempty_arabic_description(self):
        for callback, description in SECTIONS.items():
            with self.subTest(callback=callback):
                self.assertTrue(description.strip())
                self.assertIn("قسم", description)

    def test_menu_callbacks_are_unique(self):
        callbacks = [callback for row in MENU_ROWS for _, callback in row]
        self.assertEqual(len(callbacks), len(set(callbacks)))

    def test_menu_contains_all_sections_and_subscription(self):
        callbacks = {callback for row in MENU_ROWS for _, callback in row}
        self.assertEqual(callbacks, set(SECTIONS) | {"pay_sub"})

    def test_supported_section_callback_returns_description(self):
        self.assertEqual(get_section_text("serv_chat"), SECTIONS["serv_chat"])

    def test_unknown_section_returns_none(self):
        self.assertIsNone(get_section_text("serv_admin"))
        self.assertIsNone(get_section_text(""))

    def test_payment_callback_is_explicitly_supported(self):
        self.assertTrue(is_supported_callback("pay_sub"))
        self.assertIn("غير مفعّل", PAYMENT_DISABLED_MESSAGE)

    def test_unknown_callbacks_are_rejected(self):
        for value in ("", "serv_admin", "pay_sub_extra", "../../admin"):
            with self.subTest(value=value):
                self.assertFalse(is_supported_callback(value))
        self.assertIn("/start", UNKNOWN_CALLBACK_MESSAGE)


if __name__ == "__main__":
    unittest.main(verbosity=2)
