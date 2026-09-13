"""
Buy or Wait? AI Financial Agent - Main Entry Point.
Processes dataset/requests.csv and produces predictions in dataset/output.csv & output.csv.
"""

import os
import sys
import pandas as pd
from financial_engine import FinancialEngine
from plan_optimizer import PlanOptimizer
from explanation_generator import ExplanationGenerator

def main():
    print("Initializing Buy or Wait? Financial Decision Agent...")
    
    data_dir = 'dataset'
    requests_path = os.path.join(data_dir, 'requests.csv')
    if not os.path.exists(requests_path):
        print(f"Error: {requests_path} not found.")
        sys.exit(1)

    requests_df = pd.read_csv(requests_path)
    print(f"Loaded {len(requests_df)} evaluation requests.")

    engine = FinancialEngine(data_dir=data_dir)
    optimizer = PlanOptimizer(engine=engine)
    explainer = ExplanationGenerator(engine=engine)

    results = []
    print("Evaluating requests...")
    for idx, row in requests_df.iterrows():
        opt_res = optimizer.optimize_request(row)
        opt_res['decision_explanation'] = explainer.generate_explanation(row, opt_res)
        results.append(opt_res)
        
        if (idx + 1) % 50 == 0 or (idx + 1) == len(requests_df):
            print(f"Processed {idx + 1}/{len(requests_df)} requests.")

    # Convert to DataFrame
    output_df = pd.DataFrame(results)
    
    # Enforce exact column order per contract
    required_cols = [
        'request_id',
        'amount_safe_to_pay',
        'affordability_status',
        'recommended_payment_method',
        'payment_plan',
        'earliest_date_for_full_payment',
        'spending_changes_needed',
        'decision_explanation'
    ]
    output_df = output_df[required_cols]

    # Fill NaN values with empty string or 'none' per schema
    output_df['earliest_date_for_full_payment'] = output_df['earliest_date_for_full_payment'].fillna('')
    output_df['payment_plan'] = output_df['payment_plan'].fillna('none')
    output_df['spending_changes_needed'] = output_df['spending_changes_needed'].fillna('none')

    # Save to dataset/output.csv and root output.csv
    dataset_output_path = os.path.join(data_dir, 'output.csv')
    root_output_path = 'output.csv'
    
    output_df.to_csv(dataset_output_path, index=False)
    output_df.to_csv(root_output_path, index=False)
    
    print(f"\nSuccessfully generated predictions!")
    print(f"Dataset Output: {dataset_output_path}")
    print(f"Root Output: {root_output_path}")

if __name__ == '__main__':
    main()
