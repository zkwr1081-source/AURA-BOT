import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

import main as bot


class AuraBotTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_renders_all_main_sections(self):
        update = MagicMock()
        update.effective_message.reply_text = AsyncMock()

        await bot.start(update, MagicMock())

        update.effective_message.reply_text.assert_awaited_once()
        text, = update.effective_message.reply_text.await_args.args[:1]
        self.assertIn("AURA", text)
        self.assertIn("Enterprise", text)
        self.assertIn("Multi-Agent", text)
        self.assertIn("Analytics", text)

        markup = update.effective_message.reply_text.await_args.kwargs["reply_markup"]
        callback_values = {
            button.callback_data
            for row in markup.inline_keyboard
            for button in row
        }
        self.assertIn("pay_sub", callback_values)
        self.assertIn("serv_multi", callback_values)

    async def test_subscription_button_does_not_claim_payment_is_active(self):
        query = MagicMock()
        query.data = "pay_sub"
        query.answer = AsyncMock()
        query.message.reply_text = AsyncMock()
        update = MagicMock(callback_query=query)

        await bot.button_handler(update, MagicMock())

        query.answer.assert_awaited_once()
        query.message.reply_text.assert_awaited_once()
        response = query.message.reply_text.await_args.args[0]
        self.assertIn("غير مفعّل", response)
        self.assertNotIn("https://", response)

    async def test_unknown_callback_returns_safe_fallback(self):
        query = MagicMock()
        query.data = "unknown_action"
        query.answer = AsyncMock()
        query.message.reply_text = AsyncMock()
        update = MagicMock(callback_query=query)

        await bot.button_handler(update, MagicMock())

        self.assertEqual(
            query.message.reply_text.await_args.args[0],
            "الخيار غير معروف.",
        )

    def test_missing_token_fails_before_starting_polling(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "TELEGRAM_BOT_TOKEN"):
                bot.main()


if __name__ == "__main__":
    unittest.main()
