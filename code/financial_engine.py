"""
Financial Engine for Buy or Wait? Financial Agent.
Reconstructs user financial position, handles currency conversions,
and executes high-performance 90-day daily cashflow forecasting and safety evaluation.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
from typing import Dict, Any, List, Tuple, Optional

from image_handler import ImageHandler
from message_parser import MessageParser

class FinancialEngine:
    def __init__(self, data_dir: str = 'dataset'):
        self.data_dir = data_dir
        self.profiles = pd.read_csv(os.path.join(data_dir, 'financial_profiles.csv')).set_index('user_id')
        self.events = pd.read_csv(os.path.join(data_dir, 'financial_events.csv'))
        self.rates = pd.read_csv(os.path.join(data_dir, 'exchange_rates.csv'))
        self.options = pd.read_csv(os.path.join(data_dir, 'request_payment_options.csv'))
        self.messages = pd.read_csv(os.path.join(data_dir, 'messages.csv'))
        self.images = pd.read_csv(os.path.join(data_dir, 'images.csv'))
        
        self.image_handler = ImageHandler(self.images)
        self.message_parser = MessageParser(self.messages)

        # Fill missing amounts from image handler
        def resolve_amount(row):
            if pd.isna(row['amount']):
                img_amt = self.image_handler.get_event_amount(row['event_id'])
                if img_amt is not None:
                    return img_amt
            return row['amount']
        self.events['amount'] = self.events.apply(resolve_amount, axis=1)

        self.user_events_map = {u_id: df for u_id, df in self.events.groupby('user_id')}
        self.exchange_rate_cache = {}

    def convert_currency(self, amount: float, from_curr: str, to_curr: str, date_str: str) -> float:
        """Converts amount from_curr to to_curr on date_str using exchange_rates.csv with caching."""
        if from_curr == to_curr or pd.isna(from_curr) or not from_curr:
            return amount
            
        cache_key = (from_curr, to_curr, date_str)
        if cache_key in self.exchange_rate_cache:
            return amount * self.exchange_rate_cache[cache_key]

        match = self.rates[(self.rates['from_currency'] == from_curr) & (self.rates['to_currency'] == to_curr)]
        if not match.empty:
            rate = match.iloc[0]['rate']
            self.exchange_rate_cache[cache_key] = rate
            return amount * rate
            
        inv_match = self.rates[(self.rates['from_currency'] == to_curr) & (self.rates['to_currency'] == from_curr)]
        if not inv_match.empty:
            rate = 1.0 / inv_match.iloc[0]['rate']
            self.exchange_rate_cache[cache_key] = rate
            return amount * rate
            
        self.exchange_rate_cache[cache_key] = 1.0
        return amount

    def get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Returns user financial profile dict."""
        return self.profiles.loc[user_id].to_dict()

    def get_user_events(self, user_id: str) -> pd.DataFrame:
        """Returns user financial events."""
        return self.user_events_map.get(user_id, pd.DataFrame())

    def forecast_90_days(self, user_id: str, request_date_str: str, 
                         payment_schedule: List[Tuple[str, float]] = None,
                         spending_changes: List[str] = None) -> Tuple[bool, float, List[float]]:
        """
        Forecasts daily cash flow for 90 days from request_date.
        """
        profile = self.get_user_profile(user_id)
        home_curr = profile['home_currency']
        min_bal = float(profile['minimum_balance_to_keep'])
        start_bal = float(profile['current_available_balance'])
        
        stopped_events = set()
        reduced_events = {}
        if spending_changes:
            for change in spending_changes:
                parts = change.split(':')
                if parts[0] == 'stop' and len(parts) >= 2:
                    stopped_events.add(parts[1])
                elif parts[0] == 'reduce_to' and len(parts) >= 3:
                    reduced_events[parts[1]] = float(parts[2])

        msg_updates = self.message_parser.parse_user_updates(user_id)
        user_events = self.get_user_events(user_id)

        req_dt = datetime.strptime(request_date_str, '%Y-%m-%d')
        
        # Filter future events (or recurring items) landing on/after request_date_str
        def get_event_date(row):
            if pd.notna(row['settlement_date']):
                return str(row['settlement_date'])
            return str(row['event_date'])

        # Debits landing on/after request_date
        future_evs = []
        if not user_events.empty:
            for _, ev in user_events.iterrows():
                ev_dt_str = get_event_date(ev)
                ev_st = str(ev['status'])
                ev_dr = str(ev['direction'])
                ev_cat = str(ev['category'])
                
                # Check message overrides
                if ev_dr == 'debit' and ev_st in ['settled', 'scheduled', 'pending']:
                    if ev_dt_str >= request_date_str:
                        future_evs.append((ev_dt_str, ev_dr, ev_cat, float(ev['amount']), ev['currency'], ev['event_id']))
                elif ev_dr == 'credit' and ev_st in ['settled', 'scheduled'] and ev_cat in ['salary', 'income']:
                    sal_dt = msg_updates['salary_date_override'] if msg_updates['salary_date_override'] else ev_dt_str
                    sal_amt = msg_updates['salary_amount_override'] if msg_updates['salary_amount_override'] else float(ev['amount'])
                    if sal_dt >= request_date_str and not msg_updates['contract_ended']:
                        future_evs.append((sal_dt, ev_dr, ev_cat, sal_amt, ev['currency'], ev['event_id']))

        # Add one-time confirmed income from messages
        for inc_dt, inc_amt in msg_updates['confirmed_one_time_income']:
            if inc_dt >= request_date_str:
                future_evs.append((inc_dt, 'credit', 'income', inc_amt, home_curr, 'msg_inc'))

        # Map plan debits
        plan_debits_by_date = {}
        if payment_schedule:
            for p_date, p_amt in payment_schedule:
                plan_debits_by_date[p_date] = plan_debits_by_date.get(p_date, 0.0) + p_amt

        current_bal = start_bal
        min_projected = current_bal
        daily_balances = []
        is_safe = True

        for day_idx in range(91):
            curr_dt = req_dt + timedelta(days=day_idx)
            curr_date_str = curr_dt.strftime('%Y-%m-%d')

            # Process future events for today
            for ev_dt_s, ev_dr, ev_cat, ev_amt, ev_curr, ev_id in future_evs:
                if ev_dt_s == curr_date_str:
                    if ev_dr == 'debit':
                        if ev_id in stopped_events:
                            continue
                        if ev_id in reduced_events:
                            ev_amt = reduced_events[ev_id]
                        elif ev_cat == 'rent' and msg_updates['rent_increase_percentage'] > 0:
                            ev_amt *= (1.0 + msg_updates['rent_increase_percentage'])

                        ev_amt_conv = self.convert_currency(ev_amt, ev_curr, home_curr, curr_date_str)
                        current_bal -= ev_amt_conv
                    elif ev_dr == 'credit':
                        ev_amt_conv = self.convert_currency(ev_amt, ev_curr, home_curr, curr_date_str)
                        current_bal += ev_amt_conv

            # Process plan payments for today
            if curr_date_str in plan_debits_by_date:
                current_bal -= plan_debits_by_date[curr_date_str]

            daily_balances.append(current_bal)
            if current_bal < min_projected:
                min_projected = current_bal

            if current_bal < min_bal:
                is_safe = False

        return is_safe, min_projected, daily_balances
