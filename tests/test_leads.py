import os
import tempfile
import unittest
from types import SimpleNamespace

from main import save_lead


class SaveLeadTests(unittest.TestCase):
    def test_saves_lead_to_configured_sqlite_database(self):
        with tempfile.TemporaryDirectory() as directory:
            database = os.path.join(directory, "leads.sqlite3")
            old_path = os.environ.get("LEADS_DB_PATH")
            os.environ["LEADS_DB_PATH"] = database
            try:
                user = SimpleNamespace(
                    id=12345,
                    username="shop_owner",
                    full_name="Shop Owner",
                )
                lead_id = save_lead(user, "أريد بوتاً لمتجري مع قائمة منتجات")
                self.assertEqual(lead_id, 1)
                import sqlite3
                with sqlite3.connect(database) as connection:
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
            finally:
                if old_path is None:
                    os.environ.pop("LEADS_DB_PATH", None)
                else:
                    os.environ["LEADS_DB_PATH"] = old_path


if __name__ == "__main__":
    unittest.main()
