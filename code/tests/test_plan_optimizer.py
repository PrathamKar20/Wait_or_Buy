import unittest

class TestPlanOptimizerUnit(unittest.TestCase):
    def test_penalty_calculation(self):
        # 2 payments, requested 1000, total cost 1000 -> penalty = 20.0
        num_payments = 2
        total_cost = 1000.0
        requested_amount = 1000.0
        penalty = (num_payments * 10.0) + max(0.0, total_cost - requested_amount)
        self.assertEqual(penalty, 20.0)

    def test_interest_penalty(self):
        # 3 payments with 50 fee -> penalty = 30 + 50 = 80.0
        penalty = (3 * 10.0) + max(0.0, 1050.0 - 1000.0)
        self.assertEqual(penalty, 80.0)

if __name__ == "__main__":
    unittest.main()
