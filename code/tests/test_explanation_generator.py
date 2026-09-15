import unittest
from explanation_generator import ExplanationGenerator

class TestExplanationGeneratorUnit(unittest.TestCase):
    def test_currency_formatter(self):
        formatted = ExplanationGenerator.format_currency(1250.0, "USD")
        self.assertEqual(formatted, "USD 1,250")
        
        formatted_dec = ExplanationGenerator.format_currency(1250.50, "EUR")
        self.assertEqual(formatted_dec, "EUR 1,250.50")

if __name__ == "__main__":
    unittest.main()
