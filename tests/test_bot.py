import os
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import main as aura


class AuraBotTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_shows_all_primary_sections_and_payment_entry(self):
        message = MagicMock()
        message.reply_text = AsyncMock()
        update = MagicMock()
        update.effective_message = message

        await aura.start(update, MagicMock())

        message.reply_text.assert_awaited_once()
        kwargs = message.reply_text.await_args.kwargs
        self.assertEqual(kwargs["parse_mode"], "Markdown")
        callback_data = {
            button.callback_data
            for row in kwargs["reply_markup"].inline_keyboard
            for button in row
        }
        self.assertTrue({
            "serv_enterprise",
            "serv_multi",
            "serv_chat",
            "serv_code",
            "serv_analytics",
            "serv_automation",
            "pay_sub",
        }.issubset(callback_data))

    async def test_payment_is_explicitly_disabled(self):
        query = MagicMock()
        query.data = "pay_sub"
        query.answer = AsyncMock()
        query.message.reply_text = AsyncMock()
        update = MagicMock()
        update.callback_query = query

        await aura.button_handler(update, MagicMock())

        query.answer.assert_awaited_once()
        response = query.message.reply_text.await_args.args[0]
        self.assertIn("غير مفعّل", response)
        self.assertNotIn("https://", response)

    async def test_unknown_callback_has_safe_fallback(self):
        query = MagicMock()
        query.data = "unexpected_callback"
        query.answer = AsyncMock()
        query.message.reply_text = AsyncMock()
        update = MagicMock()
        update.callback_query = query

        await aura.button_handler(update, MagicMock())

        self.assertIn("غير معروف", query.message.reply_text.await_args.args[0])

    def test_startup_fails_clearly_when_token_is_missing(self):
        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": ""}):
            with self.assertRaisesRegex(RuntimeError, "TELEGRAM_BOT_TOKEN is missing"):
                aura.main()

    def test_startup_registers_handlers_and_starts_polling(self):
        application = MagicMock()
        builder = MagicMock()
        builder.token.return_value = builder
        builder.build.return_value = application

        with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "test-token"}), patch.object(
            aura, "ApplicationBuilder", return_value=builder
        ), patch.object(aura, "CommandHandler"), patch.object(aura, "CallbackQueryHandler"):
            aura.main()

        builder.token.assert_called_once_with("test-token")
        self.assertEqual(application.add_handler.call_count, 2)
        application.add_error_handler.assert_called_once()
        application.run_polling.assert_called_once()


if __name__ == "__main__":
    unittest.main()
