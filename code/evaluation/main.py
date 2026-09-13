"""
Evaluation Pipeline for Buy or Wait? Financial Agent.
Evaluates agent predictions against dataset/sample_requests.csv ground truth.
Computes field-by-field accuracy, confusion matrices, and metrics report.
"""

import os
import sys
import pandas as pd
import numpy as np

# Add parent directory to path so modules can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from financial_engine import FinancialEngine
from plan_optimizer import PlanOptimizer
from explanation_generator import ExplanationGenerator

def evaluate_sample_set():
    print("=== Buy or Wait? Agent Evaluation Pipeline ===")
    data_dir = 'dataset'
    sample_path = os.path.join(data_dir, 'sample_requests.csv')
    
    if not os.path.exists(sample_path):
        print(f"Error: {sample_path} not found.")
        sys.exit(1)
        
    sample_df = pd.read_csv(sample_path)
    print(f"Loaded {len(sample_df)} sample requests with ground truth.")

    engine = FinancialEngine(data_dir=data_dir)
    optimizer = PlanOptimizer(engine=engine)
    explainer = ExplanationGenerator(engine=engine)

    correct_status = 0
    correct_method = 0
    correct_plan = 0
    correct_earliest = 0
    correct_safe_amount = 0
    correct_changes = 0
    total = len(sample_df)

    failures = []

    for idx, row in sample_df.iterrows():
        req_id = row['request_id']
        pred = optimizer.optimize_request(row)
        pred['decision_explanation'] = explainer.generate_explanation(row, pred)

        gt_status = str(row['affordability_status'])
        gt_method = str(row['recommended_payment_method'])
        gt_plan = str(row['payment_plan'])
        gt_earliest = str(row['earliest_date_for_full_payment']) if pd.notna(row['earliest_date_for_full_payment']) else ''
        gt_safe_amt = float(row['amount_safe_to_pay'])
        gt_changes = str(row['spending_changes_needed'])

        # Field comparisons
        m_status = pred['affordability_status'] == gt_status
        m_method = pred['recommended_payment_method'] == gt_method
        m_plan = str(pred['payment_plan']) == gt_plan
        m_earliest = str(pred['earliest_date_for_full_payment']) == gt_earliest
        m_safe = abs(float(pred['amount_safe_to_pay']) - gt_safe_amt) < 1.0  # Tolerance check
        m_changes = str(pred['spending_changes_needed']) == gt_changes

        if m_status: correct_status += 1
        if m_method: correct_method += 1
        if m_plan: correct_plan += 1
        if m_earliest: correct_earliest += 1
        if m_safe: correct_safe_amount += 1
        if m_changes: correct_changes += 1

        if not (m_status and m_method and m_plan):
            failures.append({
                'req_id': req_id,
                'gt_status': gt_status, 'pred_status': pred['affordability_status'],
                'gt_method': gt_method, 'pred_method': pred['recommended_payment_method'],
                'gt_plan': gt_plan, 'pred_plan': pred['payment_plan'],
                'gt_safe': gt_safe_amt, 'pred_safe': pred['amount_safe_to_pay']
            })

    print("\n--- Field-by-Field Evaluation Results ---")
    print(f"1. amount_safe_to_pay Accuracy      : {correct_safe_amount}/{total} ({correct_safe_amount/total*100:.1f}%)")
    print(f"2. affordability_status Accuracy     : {correct_status}/{total} ({correct_status/total*100:.1f}%)")
    print(f"3. recommended_payment_method Acc  : {correct_method}/{total} ({correct_method/total*100:.1f}%)")
    print(f"4. payment_plan Accuracy           : {correct_plan}/{total} ({correct_plan/total*100:.1f}%)")
    print(f"5. earliest_date_for_full_payment  : {correct_earliest}/{total} ({correct_earliest/total*100:.1f}%)")
    print(f"6. spending_changes_needed Accuracy  : {correct_changes}/{total} ({correct_changes/total*100:.1f}%)")

    overall_acc = (correct_status + correct_method + correct_plan + correct_earliest + correct_safe_amount + correct_changes) / (total * 6)
    print(f"\nOverall Metric Score: {overall_acc*100:.1f}%")

    if failures:
        print(f"\nFound {len(failures)} mismatch(es):")
        for f in failures:
            print(f"  {f['req_id']}: GT Method={f['gt_method']} / Pred Method={f['pred_method']} | GT Plan={f['gt_plan']} / Pred Plan={f['pred_plan']}")

if __name__ == '__main__':
    evaluate_sample_set()
