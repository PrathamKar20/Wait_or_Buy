import unittest
import os
import pandas as pd
from financial_engine import FinancialEngine
from plan_optimizer import PlanOptimizer

class TestIntegration(unittest.TestCase):
    def test_pipeline_instantiation(self):
        data_dir = 'dataset'
        if os.path.exists(os.path.join(data_dir, 'sample_requests.csv')):
            engine = FinancialEngine(data_dir=data_dir)
            optimizer = PlanOptimizer(engine=engine)
            samples = pd.read_csv(os.path.join(data_dir, 'sample_requests.csv'))
            self.assertGreater(len(samples), 0)
            res = optimizer.optimize_request(samples.iloc[0])
            self.assertIn('affordability_status', res)

if __name__ == "__main__":
    unittest.main()
