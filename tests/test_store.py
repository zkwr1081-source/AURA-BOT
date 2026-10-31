import tempfile
import unittest
from pathlib import Path

from aura_store import Store


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.store = Store(str(Path(self.temp_dir.name) / "test.db"))

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_add_and_list_product(self):
        product_id = self.store.add_product("قهوة عربية", "12.50", "عبوة 250 غرام")
        products = self.store.list_products()
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["id"], product_id)
        self.assertEqual(products[0]["price"], "12.50")

    def test_reject_invalid_prices(self):
        for value in ("0", "-2", "abc", "NaN", "Infinity"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.store.add_product("منتج", value)

    def test_create_order_snapshots_product_price(self):
        product_id = self.store.add_product("اشتراك شهري", "9.99", "خدمة")
        order_id = self.store.create_order(product_id, 123, "عميل", "customer", "USD")
        order = self.store.list_orders()[0]
        self.assertEqual(order["id"], order_id)
        self.assertEqual(order["unit_price"], "9.99")
        self.assertEqual(order["status"], "new")

    def test_contact_can_only_be_attached_by_order_owner(self):
        product_id = self.store.add_product("منتج", "5")
        order_id = self.store.create_order(product_id, 123, "عميل")
        self.assertFalse(self.store.attach_contact(order_id, 456, "+100000000"))
        self.assertTrue(self.store.attach_contact(order_id, 123, "+100000000"))
        order = self.store.list_orders()[0]
        self.assertEqual(order["contact"], "+100000000")
        self.assertEqual(order["status"], "contacted")

    def test_status_validation(self):
        product_id = self.store.add_product("منتج", "5")
        order_id = self.store.create_order(product_id, 123, "عميل")
        self.assertTrue(self.store.update_order_status(order_id, "confirmed"))
        with self.assertRaises(ValueError):
            self.store.update_order_status(order_id, "paid_without_payment")


if __name__ == "__main__":
    unittest.main()
