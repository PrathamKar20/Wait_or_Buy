"""
Plan Optimizer for Buy or Wait? Financial Agent.
Evaluates eligible payment plans, calculates safe amounts, earliest dates,
spending changes, and ranks safe options per problem specifications.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Tuple, Optional

from financial_engine import FinancialEngine

class PlanOptimizer:
    def __init__(self, engine: FinancialEngine):
        self.engine = engine

    def calculate_plan_penalty(self, num_payments: int, total_cost: float, requested_amount: float) -> float:
        """Calculate penalty score for plan comparison (lower score is preferred)."""
        extra_cost = max(0.0, total_cost - requested_amount)
        return (num_payments * 10.0) + extra_cost


    def get_daily_headroom_trajectory(self, user_id: str, request_date: str, spending_changes: List[str] = None) -> List[float]:
        """
        Computes (Balance[t] - min_bal) for t = 0..90 days without request payments.
        """
        profile = self.engine.get_user_profile(user_id)
        min_bal = float(profile['minimum_balance_to_keep'])
        _, _, daily_bals = self.engine.forecast_90_days(user_id, request_date, payment_schedule=[], spending_changes=spending_changes)
        return [b - min_bal for b in daily_bals]

    def find_amount_safe_to_pay(self, user_id: str, request_date: str, requested_amount: float) -> float:
        """Finds maximum safe amount to pay today without spending changes."""
        headrooms = self.get_daily_headroom_trajectory(user_id, request_date)
        min_headroom = min(headrooms)
        amount_safe = min(requested_amount, max(0.0, min_headroom))
        return round(amount_safe, 2)

    def find_earliest_date_for_full_payment(self, user_id: str, request_date: str, requested_amount: float) -> str:
        """
        Fast single-pass earliest safe date for full payment without spending changes.
        Full payment A on day d is safe iff min_{t >= d} headroom[t] >= A.
        """
        headrooms = self.get_daily_headroom_trajectory(user_id, request_date)
        req_dt = datetime.strptime(request_date, '%Y-%m-%d')
        
        # Suffix minimums: suffix_min[d] = min(headrooms[d..90])
        suffix_min = [0.0] * len(headrooms)
        curr_min = float('inf')
        for i in range(len(headrooms) - 1, -1, -1):
            if headrooms[i] < curr_min:
                curr_min = headrooms[i]
            suffix_min[i] = curr_min

        for d in range(len(headrooms)):
            if suffix_min[d] >= requested_amount:
                return (req_dt + timedelta(days=d)).strftime('%Y-%m-%d')
                
        return ""  # Empty string if not safe within 90 days

    def optimize_request(self, req_row: pd.Series) -> Dict[str, Any]:
        """
        Main optimizer logic for a single evaluation request.
        Returns dict matching required output schema.
        """
        req_id = str(req_row['request_id'])
        u_id = str(req_row['user_id'])
        req_date = str(req_row['request_date'])
        req_amt = float(req_row['requested_amount'])
        completion_date = str(req_row['desired_completion_date'])
        allows_partial = str(req_row['allows_partial_payment']).lower() in ['true', '1', 'yes']

        profile = self.engine.get_user_profile(u_id)
        considered_methods = [m.strip() for m in str(profile.get('payment_methods_user_will_consider', '')).split('|') if m.strip()]
        max_inst_months = profile.get('max_installment_months', None)
        if pd.notna(max_inst_months) and str(max_inst_months).strip():
            max_inst_months = int(float(max_inst_months))
        else:
            max_inst_months = None

        # 1. Fast calculation of safe_to_pay & earliest_date_for_full_payment
        safe_to_pay = self.find_amount_safe_to_pay(u_id, req_date, req_amt)
        earliest_full_date = self.find_earliest_date_for_full_payment(u_id, req_date, req_amt)

        # 2. Gather candidate plans
        candidates = []
        
        # A. Full Payment Today
        if 'full_payment' in considered_methods:
            is_safe, _, _ = self.engine.forecast_90_days(u_id, req_date, payment_schedule=[(req_date, req_amt)])
            if is_safe:
                candidates.append({
                    'status': 'affordable_now',
                    'method': 'full_payment',
                    'plan': f"{req_date}:{req_amt:g}",
                    'earliest_date': req_date,
                    'changes': 'none',
                    'total_cost': req_amt,
                    'start_date': req_date,
                    'num_payments': 1,
                    'option_id': 'option_00',
                    'completes_by_deadline': req_date <= completion_date,
                    'num_changes': 0
                })

        # B. Installment Options
        if 'installments' in considered_methods:
            req_options = self.engine.options[self.engine.options['request_id'] == req_id]
            for _, opt in req_options.iterrows():
                opt_method = str(opt['payment_method'])
                if opt_method != 'installments':
                    continue
                    
                n_payments = int(opt['number_of_payments'])
                if max_inst_months is not None and n_payments > max_inst_months:
                    continue  # Exceeds max installment months
                    
                first_date = str(opt['first_payment_date'])
                p_amt = float(opt['payment_amount'])
                freq_days = int(opt['payment_frequency_days']) if pd.notna(opt['payment_frequency_days']) else 30
                tot_amt = float(opt['total_payable_amount'])
                opt_id = str(opt['payment_option_id'])
                
                schedule = []
                f_dt = datetime.strptime(first_date, '%Y-%m-%d')
                for p_idx in range(n_payments):
                    p_dt = f_dt + timedelta(days=p_idx * freq_days)
                    schedule.append((p_dt.strftime('%Y-%m-%d'), p_amt))
                    
                last_payment_date = schedule[-1][0]
                
                is_safe, _, _ = self.engine.forecast_90_days(u_id, req_date, payment_schedule=schedule)
                if is_safe:
                    plan_str = '|'.join([f"{dt}:{amt:g}" for dt, amt in schedule])
                    candidates.append({
                        'status': 'affordable_with_plan',
                        'method': 'installments',
                        'plan': plan_str,
                        'earliest_date': earliest_full_date if earliest_full_date else last_payment_date,
                        'changes': 'none',
                        'total_cost': tot_amt,
                        'start_date': first_date,
                        'num_payments': n_payments,
                        'option_id': opt_id,
                        'completes_by_deadline': last_payment_date <= completion_date,
                        'num_changes': 0
                    })

        # C. Partial Payment
        if allows_partial and 'partial_payment' in considered_methods:
            if 0 < safe_to_pay < req_amt and earliest_full_date and earliest_full_date <= completion_date:
                remaining_amt = round(req_amt - safe_to_pay, 2)
                schedule = [(req_date, safe_to_pay), (earliest_full_date, remaining_amt)]
                is_safe, _, _ = self.engine.forecast_90_days(u_id, req_date, payment_schedule=schedule)
                if is_safe:
                    plan_str = f"{req_date}:{safe_to_pay:g}|{earliest_full_date}:{remaining_amt:g}"
                    candidates.append({
                        'status': 'affordable_with_plan',
                        'method': 'partial_payment',
                        'plan': plan_str,
                        'earliest_date': earliest_full_date,
                        'changes': 'none',
                        'total_cost': req_amt,
                        'start_date': req_date,
                        'num_payments': 2,
                        'option_id': 'option_00',
                        'completes_by_deadline': earliest_full_date <= completion_date,
                        'num_changes': 0
                    })

        # D. Wait (Deferred Full Payment)
        if 'full_payment' in considered_methods and earliest_full_date and earliest_full_date > req_date:
            candidates.append({
                'status': 'affordable_later',
                'method': 'wait',
                'plan': f"{earliest_full_date}:{req_amt:g}",
                'earliest_date': earliest_full_date,
                'changes': 'none',
                'total_cost': req_amt,
                'start_date': earliest_full_date,
                'num_payments': 1,
                'option_id': 'option_00',
                'completes_by_deadline': earliest_full_date <= completion_date,
                'num_changes': 0
            })

        # E. Flexible Spending Changes Check
        has_deadline_winner = any(c['completes_by_deadline'] and c['num_changes'] == 0 for c in candidates)
        if not has_deadline_winner:
            stop_categories = [c.strip() for c in str(profile.get('expense_categories_user_is_willing_to_stop', '')).split('|') if c.strip()]
            reduce_categories = [c.strip() for c in str(profile.get('expense_categories_user_is_willing_to_reduce', '')).split('|') if c.strip()]
            
            user_evs = self.engine.get_user_events(u_id)
            stoppable_evs = user_evs[user_evs['category'].isin(stop_categories) & (user_evs['flexibility'] == 'stoppable')]
            reducible_evs = user_evs[user_evs['category'].isin(reduce_categories) & (user_evs['flexibility'].str.contains('reducible', na=False))]

            for _, s_ev in stoppable_evs.iterrows():
                ev_id = s_ev['event_id']
                change_str = f"stop:{ev_id}"
                if 'full_payment' in considered_methods:
                    is_safe, _, _ = self.engine.forecast_90_days(u_id, req_date, payment_schedule=[(req_date, req_amt)], spending_changes=[change_str])
                    if is_safe:
                        candidates.append({
                            'status': 'affordable_with_plan',
                            'method': 'full_payment',
                            'plan': f"{req_date}:{req_amt:g}",
                            'earliest_date': req_date,
                            'changes': change_str,
                            'total_cost': req_amt,
                            'start_date': req_date,
                            'num_payments': 1,
                            'option_id': 'option_00',
                            'completes_by_deadline': req_date <= completion_date,
                            'num_changes': 1
                        })

            for _, r_ev in reducible_evs.iterrows():
                ev_id = r_ev['event_id']
                min_allowed = r_ev['minimum_allowed_amount']
                if pd.notna(min_allowed):
                    change_str = f"reduce_to:{ev_id}:{min_allowed:g}"
                    if 'full_payment' in considered_methods:
                        is_safe, _, _ = self.engine.forecast_90_days(u_id, req_date, payment_schedule=[(req_date, req_amt)], spending_changes=[change_str])
                        if is_safe:
                            candidates.append({
                                'status': 'affordable_with_plan',
                                'method': 'full_payment',
                                'plan': f"{req_date}:{req_amt:g}",
                                'earliest_date': req_date,
                                'changes': change_str,
                                'total_cost': req_amt,
                                'start_date': req_date,
                                'num_payments': 1,
                                'option_id': 'option_00',
                                'completes_by_deadline': req_date <= completion_date,
                                'num_changes': 1
                            })

        # 3. Fallback / Ranking Selection
        if not candidates:
            return {
                'request_id': req_id,
                'amount_safe_to_pay': safe_to_pay,
                'affordability_status': 'not_affordable',
                'recommended_payment_method': 'not_recommended',
                'payment_plan': 'none',
                'earliest_date_for_full_payment': earliest_full_date if earliest_full_date else '',
                'spending_changes_needed': 'none'
            }

        def sort_key(c):
            return (
                0 if c['completes_by_deadline'] else 1,
                c['num_changes'],
                c['total_cost'],
                c['start_date'],
                c['num_payments'],
                c['option_id']
            )
            
        candidates.sort(key=sort_key)
        best = candidates[0]
        
        return {
            'request_id': req_id,
            'amount_safe_to_pay': safe_to_pay,
            'affordability_status': best['status'],
            'recommended_payment_method': best['method'],
            'payment_plan': best['plan'],
            'earliest_date_for_full_payment': best['earliest_date'],
            'spending_changes_needed': best['changes']
        }
