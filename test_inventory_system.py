import unittest
import sqlite3
from datetime import datetime
from inventory_management_system import InventoryManagementSystem

class TestInventoryManagementSystem(unittest.TestCase):
    def setUp(self):
        # Create a new database for each test
        self.ims = InventoryManagementSystem(':memory:')

    def test_add_item(self):
        self.ims.add_item("Test Item", 10, 9.99)
        self.ims.cursor.execute("SELECT * FROM inventory WHERE name='Test Item'")
        item = self.ims.cursor.fetchone()
        self.assertIsNotNone(item)
        self.assertEqual(item[1], "Test Item")
        self.assertEqual(item[2], 10)
        self.assertEqual(item[3], 9.99)

    def test_add_duplicate_item(self):
        self.ims.add_item("Test Item", 10, 9.99)
        with self.assertRaises(sqlite3.IntegrityError):
            self.ims.add_item("Test Item", 20, 19.99)

    def test_remove_item(self):
        self.ims.add_item("Test Item", 10, 9.99)
        self.ims.remove_item("Test Item")
        self.ims.cursor.execute("SELECT * FROM inventory WHERE name='Test Item'")
        item = self.ims.cursor.fetchone()
        self.assertIsNone(item)

    def test_remove_nonexistent_item(self):
        self.ims.remove_item("Nonexistent Item")
        # This should not raise an exception

    def test_update_item(self):
        self.ims.add_item("Test Item", 10, 9.99)
        self.ims.update_item("Test Item", quantity=20, price=19.99)
        self.ims.cursor.execute("SELECT * FROM inventory WHERE name='Test Item'")
        item = self.ims.cursor.fetchone()
        self.assertEqual(item[2], 20)
        self.assertEqual(item[3], 19.99)

    def test_update_nonexistent_item(self):
        self.ims.update_item("Nonexistent Item", quantity=20, price=19.99)
        self.ims.cursor.execute("SELECT * FROM inventory WHERE name='Nonexistent Item'")
        item = self.ims.cursor.fetchone()
        self.assertIsNone(item)

    def test_display_inventory(self):
        self.ims.add_item("Item 1", 10, 9.99)
        self.ims.add_item("Item 2", 20, 19.99)
        # Redirect stdout to capture print output
        import io
        import sys
        captured_output = io.StringIO()
        sys.stdout = captured_output
        self.ims.display_inventory()
        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()
        self.assertIn("Item 1", output)
        self.assertIn("Item 2", output)

    def test_generate_report(self):
        self.ims.add_item("Item 1", 10, 9.99)
        self.ims.add_item("Item 2", 20, 19.99)
        import io
        import sys
        captured_output = io.StringIO()
        sys.stdout = captured_output
        self.ims.generate_report()
        sys.stdout = sys.__stdout__
        output = captured_output.getvalue()
        self.assertIn("Total number of items: 30", output)
        self.assertIn("Total inventory value: $499.70", output)  # Note the added $ sign

if __name__ == '__main__':
    unittest.main()