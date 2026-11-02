import asyncio
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import main as aura_main

from main import (
    delete_leads_for_user,
    leads_retention_days,
    purge_expired_leads,
    save_lead,
)


class SaveLeadTests(unittest.TestCase):
    def user(self, user_id=12345, username="shop_owner", full_name="Shop Owner"):
        return SimpleNamespace(id=user_id, username=username, full_name=full_name)

    def test_saves_lead_to_configured_sqlite_database(self):
        with tempfile.TemporaryDirectory() as directory:
            database = os.path.join(directory, "leads.sqlite3")
            with patch.dict(
                os.environ,
                {"LEADS_DB_PATH": database, "LEADS_RETENTION_DAYS": "90"},
            ):
                lead_id = save_lead(
                    self.user(),
                    "أريد بوتاً لمتجري مع قائمة منتجات",
                )
                self.assertEqual(lead_id, 1)
                with closing(sqlite3.connect(database)) as connection:
                    row = connection.execute(
                        "SELECT telegram_user_id, username, display_name, message, status "
                        "FROM leads WHERE id = ?",
                        (lead_id,),
                    ).fetchone()
                self.assertEqual(
                    row,
                    (
                        12345,
                        "shop_owner",
                        "Shop Owner",
                        "أريد بوتاً لمتجري مع قائمة منتجات",
                        "new",
                    ),
                )
                if os.name == "posix":
                    self.assertEqual(os.stat(database).st_mode & 0o777, 0o600)

    def test_save_prunes_expired_records_before_inserting_new_lead(self):
        with tempfile.TemporaryDirectory() as directory:
            database = os.path.join(directory, "leads.sqlite3")
            with patch.dict(
                os.environ,
                {"LEADS_DB_PATH": database, "LEADS_RETENTION_DAYS": "30"},
            ):
                save_lead(self.user(), "أريد بوتاً لمتجري مع قائمة منتجات")
                old_created_at = (
                    datetime.now(timezone.utc) - timedelta(days=31)
                ).isoformat()
                with closing(sqlite3.connect(database)) as connection:
                    with connection:
                        cursor = connection.execute(
                            """
                            INSERT INTO leads
                                (telegram_user_id, username, display_name, message, created_at)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (99999, "expired_user", "Expired", "old inquiry", old_created_at),
                        )
                        expired_id = cursor.lastrowid

                save_lead(
                    self.user(67890, "new_shop", "New Shop"),
                    "أحتاج بوتاً لعرض خدمات متجري",
                )
                with closing(sqlite3.connect(database)) as connection:
                    expired = connection.execute(
                        "SELECT 1 FROM leads WHERE id = ?", (expired_id,)
                    ).fetchone()
                    total = connection.execute(
                        "SELECT COUNT(*) FROM leads"
                    ).fetchone()[0]
                self.assertIsNone(expired)
                self.assertEqual(total, 2)

    def test_startup_purge_removes_expired_rows(self):
        with tempfile.TemporaryDirectory() as directory:
            database = os.path.join(directory, "leads.sqlite3")
            with patch.dict(
                os.environ,
                {"LEADS_DB_PATH": database, "LEADS_RETENTION_DAYS": "30"},
            ):
                save_lead(self.user(), "أريد بوتاً لمتجري مع قائمة منتجات")
                old_created_at = (
                    datetime.now(timezone.utc) - timedelta(days=31)
                ).isoformat()
                with closing(sqlite3.connect(database)) as connection:
                    with connection:
                        connection.execute(
                            """
                            INSERT INTO leads
                                (telegram_user_id, username, display_name, message, created_at)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (99999, "expired_user", "Expired", "old inquiry", old_created_at),
                        )
                self.assertEqual(purge_expired_leads(), 1)
                with closing(sqlite3.connect(database)) as connection:
                    count = connection.execute(
                        "SELECT COUNT(*) FROM leads"
                    ).fetchone()[0]
                self.assertEqual(count, 1)

    def test_forget_deletes_only_the_requesting_users_records(self):
        with tempfile.TemporaryDirectory() as directory:
            database = os.path.join(directory, "leads.sqlite3")
            with patch.dict(
                os.environ,
                {"LEADS_DB_PATH": database, "LEADS_RETENTION_DAYS": "90"},
            ):
                save_lead(self.user(), "أريد بوتاً لمتجري مع قائمة منتجات")
                save_lead(self.user(), "أريد إضافة أزرار لطلب الخدمة")
                save_lead(
                    self.user(67890, "other_shop", "Other Shop"),
                    "أحتاج بوتاً آخر لنشاطي التجاري",
                )

                self.assertEqual(delete_leads_for_user(12345), 2)
                self.assertEqual(delete_leads_for_user(12345), 0)
                with closing(sqlite3.connect(database)) as connection:
                    remaining = connection.execute(
                        "SELECT telegram_user_id FROM leads"
                    ).fetchall()
                self.assertEqual(remaining, [(67890,)])

    def test_purge_and_forget_do_not_create_missing_database(self):
        with tempfile.TemporaryDirectory() as directory:
            database = os.path.join(directory, "missing.sqlite3")
            with patch.dict(
                os.environ,
                {"LEADS_DB_PATH": database, "LEADS_RETENTION_DAYS": "90"},
            ):
                self.assertEqual(purge_expired_leads(), 0)
                self.assertEqual(delete_leads_for_user(12345), 0)
                self.assertFalse(os.path.exists(database))

    def test_conversation_state_does_not_accept_text_before_consent(self):
        conversation = aura_main.build_lead_conversation()
        consent_handlers = conversation.states[aura_main.LEAD_CONSENT]
        details_handlers = conversation.states[aura_main.LEAD_DETAILS]

        self.assertFalse(
            any(isinstance(handler, aura_main.MessageHandler) for handler in consent_handlers)
        )
        self.assertTrue(
            any(isinstance(handler, aura_main.CallbackQueryHandler) for handler in consent_handlers)
        )
        self.assertTrue(
            any(isinstance(handler, aura_main.MessageHandler) for handler in details_handlers)
        )

    def test_retention_setting_has_safe_bounds(self):
        for value in ("0", "3651", "not-a-number"):
            with self.subTest(value=value):
                with patch.dict(os.environ, {"LEADS_RETENTION_DAYS": value}):
                    with self.assertRaises(ValueError):
                        leads_retention_days()

        with patch.dict(os.environ, {"LEADS_RETENTION_DAYS": "90"}):
            self.assertEqual(leads_retention_days(), 90)


    def test_daily_retention_job_is_registered_at_startup(self):
        class FakeJobQueue:
            def __init__(self):
                self.calls = []

            def run_repeating(self, callback, interval, first, name):
                self.calls.append((callback, interval, first, name))

        class FakeApplication:
            def __init__(self, job_queue):
                self.job_queue = job_queue
                self.handlers = []
                self.error_handlers = []
                self.polling_started = False

            def add_handler(self, handler):
                self.handlers.append(handler)

            def add_error_handler(self, handler):
                self.error_handlers.append(handler)

            def run_polling(self):
                self.polling_started = True

        class FakeBuilder:
            def __init__(self, application):
                self.application = application
                self.configured_token = None

            def token(self, token):
                self.configured_token = token
                return self

            def build(self):
                return self.application

        with tempfile.TemporaryDirectory() as directory:
            database = os.path.join(directory, "missing.sqlite3")
            job_queue = FakeJobQueue()
            application = FakeApplication(job_queue)
            builder = FakeBuilder(application)
            with patch.dict(
                os.environ,
                {
                    "TELEGRAM_BOT_TOKEN": "test-token-not-used-for-network",
                    "LEADS_DB_PATH": database,
                    "LEADS_RETENTION_DAYS": "90",
                },
            ):
                with patch("main.ApplicationBuilder", return_value=builder):
                    aura_main.main()

            self.assertEqual(builder.configured_token, "test-token-not-used-for-network")
            self.assertTrue(application.polling_started)
            self.assertEqual(
                job_queue.calls,
                [(aura_main.retention_cleanup_job, 24 * 60 * 60, 60, "aura-lead-retention")],
            )
            self.assertFalse(os.path.exists(database))

    def test_retention_job_runs_cleanup_in_a_worker_thread(self):
        context = SimpleNamespace(application=SimpleNamespace())
        with patch("main.purge_expired_leads", return_value=2) as purge_mock:
            asyncio.run(aura_main.retention_cleanup_job(context))
        purge_mock.assert_called_once()

class LeadFlowTests(unittest.IsolatedAsyncioTestCase):
    def user(self, user_id=12345, username="shop_owner", full_name="Shop Owner"):
        return SimpleNamespace(id=user_id, username=username, full_name=full_name)

    async def test_request_start_discloses_retention_and_returns_consent_state(self):
        with tempfile.TemporaryDirectory() as directory:
            database = os.path.join(directory, "leads.sqlite3")
            message = SimpleNamespace(reply_text=AsyncMock())
            update = SimpleNamespace(effective_message=message)
            with patch.dict(
                os.environ,
                {
                    "LEADS_DB_PATH": database,
                    "LEADS_RETENTION_DAYS": "30",
                    "ADMIN_CHAT_ID": "98765",
                },
            ):
                state = await aura_main.request_start(update, SimpleNamespace())

            self.assertEqual(state, aura_main.LEAD_CONSENT)
            consent_text = message.reply_text.await_args.args[0]
            self.assertIn("30 يوماً", consent_text)
            self.assertIn("/forget", consent_text)
            self.assertIn("إشعار الإدارة مفعّل", consent_text)
            callback_data = {
                button.callback_data
                for row in message.reply_text.await_args.kwargs["reply_markup"].inline_keyboard
                for button in row
            }
            self.assertEqual(callback_data, {"lead_consent", "lead_cancel"})
            self.assertFalse(os.path.exists(database))

    async def test_consent_callback_moves_to_details_without_saving(self):
        with tempfile.TemporaryDirectory() as directory:
            database = os.path.join(directory, "leads.sqlite3")
            query = SimpleNamespace(answer=AsyncMock(), edit_message_text=AsyncMock())
            update = SimpleNamespace(callback_query=query)
            with patch.dict(
                os.environ,
                {"LEADS_DB_PATH": database, "LEADS_RETENTION_DAYS": "90"},
            ):
                state = await aura_main.lead_consent(update, SimpleNamespace())

            self.assertEqual(state, aura_main.LEAD_DETAILS)
            query.answer.assert_awaited_once()
            prompt = query.edit_message_text.await_args.args[0]
            self.assertIn("اكتب طلبك", prompt)
            self.assertIn("لا تضع", prompt)
            self.assertFalse(os.path.exists(database))

    async def test_valid_details_save_and_notify_configured_admin(self):
        with tempfile.TemporaryDirectory() as directory:
            database = os.path.join(directory, "leads.sqlite3")
            message = SimpleNamespace(
                text="أريد بوتاً لمتجري مع قائمة منتجات",
                reply_text=AsyncMock(),
            )
            update = SimpleNamespace(
                effective_message=message,
                effective_user=self.user(),
            )
            bot = SimpleNamespace(send_message=AsyncMock())
            context = SimpleNamespace(bot=bot)
            with patch.dict(
                os.environ,
                {
                    "LEADS_DB_PATH": database,
                    "LEADS_RETENTION_DAYS": "90",
                    "ADMIN_CHAT_ID": "98765",
                },
            ):
                state = await aura_main.lead_details(update, context)

            self.assertEqual(state, aura_main.ConversationHandler.END)
            message.reply_text.assert_awaited_once()
            self.assertIn("#1", message.reply_text.await_args.args[0])
            bot.send_message.assert_awaited_once()
            kwargs = bot.send_message.await_args.kwargs
            self.assertEqual(kwargs["chat_id"], 98765)
            self.assertIn("Telegram ID: 12345", kwargs["text"])
            self.assertIn(message.text, kwargs["text"])
            with closing(sqlite3.connect(database)) as connection:
                count = connection.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
            self.assertEqual(count, 1)

    async def test_short_details_are_rejected_without_creating_database(self):
        with tempfile.TemporaryDirectory() as directory:
            database = os.path.join(directory, "leads.sqlite3")
            message = SimpleNamespace(text="short", reply_text=AsyncMock())
            update = SimpleNamespace(
                effective_message=message,
                effective_user=self.user(),
            )
            with patch.dict(
                os.environ,
                {"LEADS_DB_PATH": database, "LEADS_RETENTION_DAYS": "90"},
            ):
                state = await aura_main.lead_details(update, SimpleNamespace())

            self.assertEqual(state, aura_main.LEAD_DETAILS)
            self.assertIn("10 أحرف", message.reply_text.await_args.args[0])
            self.assertFalse(os.path.exists(database))

if __name__ == "__main__":
    unittest.main()
