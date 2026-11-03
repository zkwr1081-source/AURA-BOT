import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import main


class CommerceHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_duplicate_order_callback_does_not_create_another_order(self):
        store = Mock()
        query = SimpleNamespace(
            data="order:7",
            answer=AsyncMock(),
            message=SimpleNamespace(reply_text=AsyncMock()),
            from_user=SimpleNamespace(id=123, full_name="Customer", username="customer"),
        )
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(
            application=SimpleNamespace(
                bot_data={"store": store, "currency": "USD"}
            ),
            user_data={"pending_order_id": 42},
        )

        await main.button_handler(update, context)

        store.create_order.assert_not_called()
        query.message.reply_text.assert_awaited()
        self.assertIn("42", query.message.reply_text.await_args.args[0])

    async def test_cancel_command_updates_pending_order_for_owner(self):
        store = Mock()
        store.cancel_order.return_value = True
        message = SimpleNamespace(reply_text=AsyncMock())
        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=123),
            effective_message=message,
        )
        context = SimpleNamespace(
            application=SimpleNamespace(bot_data={"store": store}),
            user_data={"pending_order_id": 7},
        )

        await main.cancel(update, context)

        store.cancel_order.assert_called_once_with(7, 123)
        self.assertNotIn("pending_order_id", context.user_data)
        self.assertIn("تم إلغاء الطلب", message.reply_text.await_args.args[0])

    async def test_failed_contact_persistence_is_not_reported_as_saved(self):
        store = Mock()
        store.attach_contact.return_value = False
        message = SimpleNamespace(text="contact@example.test", reply_text=AsyncMock())
        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=123),
            effective_message=message,
        )
        context = SimpleNamespace(
            application=SimpleNamespace(bot_data={"store": store}),
            user_data={"pending_order_id": 7},
        )

        await main.receive_text(update, context)

        self.assertNotIn("pending_order_id", context.user_data)
        response = message.reply_text.await_args.args[0]
        self.assertIn("لم يتم حفظ", response)
        self.assertNotIn("ستتواصل معك الإدارة للتأكيد", response)

    async def test_error_handler_omits_exception_details(self):
        error = RuntimeError("sensitive-token and customer phone data")
        context = SimpleNamespace(error=error)

        with self.assertLogs(main.logger, level="ERROR") as captured:
            await main.error_handler(None, context)

        self.assertIn("RuntimeError", captured.output[0])
        self.assertNotIn("sensitive-token", captured.output[0])
        self.assertNotIn("customer phone data", captured.output[0])

    def test_admin_output_chunks_fit_conservative_message_limit(self):
        lines = ["A" * 1500, "B" * 1500, "C" * 4000]
        chunks = main.chunk_lines(lines, max_chars=1800)

        self.assertTrue(chunks)
        self.assertTrue(all(len(chunk) <= 1800 for chunk in chunks))
        self.assertEqual(
            "".join(chunk.replace("\\n", "") for chunk in chunks),
            "".join(lines),
        )

    def test_currency_display_code_is_validated(self):
        self.assertEqual(main.normalize_currency(" usd "), "USD")
        self.assertEqual(main.normalize_currency("eur"), "EUR")
        with self.assertRaises(ValueError):
            main.normalize_currency("US\\nD")


if __name__ == "__main__":
    unittest.main()
