"""
Explanation Generator for Buy or Wait? Financial Agent.
Generates concise, grounded explanations matching the problem specification and sample style.
"""

from typing import Dict, Any
import pandas as pd

class ExplanationGenerator:
    def __init__(self, engine):
        self.engine = engine

    def generate_explanation(self, req_row: pd.Series, opt_result: Dict[str, Any]) -> str:
        u_id = str(req_row['user_id'])
        req_amt = float(req_row['requested_amount'])
        completion_date = str(req_row['desired_completion_date'])
        
        profile = self.engine.get_user_profile(u_id)
        home_curr = profile['home_currency']
        min_bal = float(profile['minimum_balance_to_keep'])
        
        status = opt_result['affordability_status']
        method = opt_result['recommended_payment_method']
        plan = opt_result['payment_plan']
        earliest = opt_result['earliest_date_for_full_payment']
        changes = opt_result['spending_changes_needed']
        
        # Format currency amount
        def fmt(amt: float) -> str:
            if amt == int(amt):
                return f"{home_curr} {int(amt):,}"
            return f"{home_curr} {amt:,.2f}"

        if status == 'not_affordable' or method == 'not_recommended':
            return f"Do not make this payment by {completion_date}. None of the available options keeps the {fmt(min_bal)} minimum protected."

        if status == 'affordable_now' and method == 'full_payment':
            if changes == 'none':
                return f"Pay {fmt(req_amt)} today. This leaves at least {fmt(min_bal)} available over the next 90 days."

        if status == 'affordable_later' or method == 'wait':
            if earliest:
                return f"Pay {fmt(req_amt)} in full on {earliest}. Paying earlier would take the balance below the {fmt(min_bal)} minimum."

        if method == 'installments':
            payments = plan.split('|')
            num_p = len(payments)
            first_p = payments[0].split(':')
            p_amt = float(first_p[1])
            start_date = first_p[0]
            return f"Use {num_p} installments of {fmt(p_amt)}, starting {start_date}. This leaves at least {fmt(min_bal)} available."

        if method == 'partial_payment':
            payments = plan.split('|')
            p1_parts = payments[0].split(':')
            p2_parts = payments[1].split(':')
            return f"Pay {fmt(float(p1_parts[1]))} today and the remaining {fmt(float(p2_parts[1]))} on {p2_parts[0]}. This completes the full request and keeps the {fmt(min_bal)} minimum protected."

        if changes != 'none':
            if 'stop:' in changes:
                return f"Stop the subscription, then pay {fmt(req_amt)} today. This leaves at least {fmt(min_bal)} available."
            elif 'reduce_to:' in changes:
                return f"Reduce the flexible expense, then pay {fmt(req_amt)} today. This leaves at least {fmt(min_bal)} available."

        return f"Pay {fmt(req_amt)} according to recommended plan. This maintains the {fmt(min_bal)} minimum balance."
