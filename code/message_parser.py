"""
Message Parser for Buy or Wait? Financial Agent.
Extracts financial amendments, salary date shifts, pay updates, rent adjustments,
and payout confirmations from structured and unstructured messages.
"""

import re
import pandas as pd
from typing import Dict, Any, List, Optional

class MessageParser:
    def __init__(self, messages_df: pd.DataFrame):
        self.messages_df = messages_df if messages_df is not None else pd.DataFrame()

    def get_user_messages(self, user_id: str, request_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve all relevant messages for a user and optional request_id."""
        if self.messages_df.empty:
            return []
        
        user_msgs = self.messages_df[self.messages_df['user_id'] == user_id]
        if request_id:
            # Match specific request_id OR general user messages (where request_id is blank/NaN)
            req_msgs = user_msgs[(user_msgs['request_id'] == request_id) | (user_msgs['request_id'].isna())]
            return req_msgs.to_dict('records')
        return user_msgs.to_dict('records')

    def parse_user_updates(self, user_id: str, request_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Parses messages to return financial updates for a user:
        - salary_date_override
        - salary_amount_override
        - rent_increase_percentage
        - confirmed_one_time_income: list of (date, amount)
        - contract_ended: bool
        """
        updates = {
            'salary_date_override': None,
            'salary_amount_override': None,
            'rent_increase_percentage': 0.0,
            'confirmed_one_time_income': [],
            'contract_ended': False
        }
        
        msgs = self.get_user_messages(user_id, request_id)
        for msg in msgs:
            text = str(msg.get('message_text', ''))
            
            # Check for salary date override (YYYY-MM-DD)
            # e.g., "expected on 2024-09-23", "confirmed credit date is 2025-02-15", "mulai 2025-08-15"
            date_match = re.search(r'(?:expected on|confirmed credit date is|berlaku mulai|resumes on)\s+(\d{4}-\d{2}-\d{2})', text, re.IGNORECASE)
            if date_match:
                updates['salary_date_override'] = date_match.group(1)
                
            # Check for salary amount override
            # e.g., "naik menjadi IDR 42750000", "monthly pay is EUR 1037.52", "next salary is reduced to EUR 1422.85", "first salary will be ZAR 54120"
            amount_match = re.search(r'(?:naik menjadi|monthly pay is|next salary is reduced to|first salary will be|gaji pokok.*adalah)\s+(?:[A-Z]{3}\s+)?([\d,]+(?:\.\d+)?)', text, re.IGNORECASE)
            if amount_match:
                amt_str = amount_match.group(1).replace(',', '')
                try:
                    updates['salary_amount_override'] = float(amt_str)
                except ValueError:
                    pass

            # Check for rent increase
            # e.g., "increases monthly rent by 12%"
            rent_match = re.search(r'increases monthly rent by\s+(\d+)%', text, re.IGNORECASE)
            if rent_match:
                try:
                    updates['rent_increase_percentage'] = float(rent_match.group(1)) / 100.0
                except ValueError:
                    pass
                    
            # Check for contract end
            if "contract has ended" in text.lower() or "no off-season income" in text.lower():
                updates['contract_ended'] = True

            # Check for confirmed invoice payout
            # e.g. "Klien menyetujui pembayaran faktur sebesar IDR 30780000. Penyelesaian diperkirakan pada 2025-08-15"
            # e.g. "client approved an invoice payment of INR 196000. Settlement is expected on 2024-12-15"
            inv_match = re.search(r'(?:pembayaran faktur sebesar|approved an invoice payment of)\s+(?:[A-Z]{3}\s+)?([\d,]+(?:\.\d+)?).*(?:Penyelesaian diperkirakan pada|Settlement is expected on)\s+(\d{4}-\d{2}-\d{2})', text, re.IGNORECASE)
            if inv_match:
                amt = float(inv_match.group(1).replace(',', ''))
                dt = inv_match.group(2)
                updates['confirmed_one_time_income'].append((dt, amt))
                
        return updates
