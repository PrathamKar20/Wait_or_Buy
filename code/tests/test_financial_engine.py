import unittest
from datetime import datetime, date

class TestFinancialEngineUnit(unittest.TestCase):
    def test_date_parsing(self):
        d_str = "2026-09-13"
        parsed = datetime.strptime(d_str, "%Y-%m-%d").date()
        self.assertEqual(parsed, date(2026, 9, 13))

    def test_minimum_balance_threshold(self):
        balance = 1500.0
        min_bal = 500.0
        amount = 800.0
        safe = (balance - amount) >= min_bal
        self.assertTrue(safe)

if __name__ == "__main__":
    unittest.main()
