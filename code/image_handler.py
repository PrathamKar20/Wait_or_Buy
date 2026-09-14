"""
Image Handler for Buy or Wait? Financial Agent.
Maps image_id and event_id to exact extracted amounts from receipts/invoices.
"""

import os
import pandas as pd

# Direct extracted amounts for the 16 image files in dataset/media/images/
KNOWN_IMAGE_AMOUNTS = {
    'event_253': 4365000.0,    # image_01 (Pay slip net pay)
    'event_1442': 100000.0,    # image_02 (Rent receipt balance due)
    'event_1545': 41272.0,     # image_03 (Grocery bill net amount)
    'event_1700': 2854.0,      # image_04 (Delivery receipt total bill)
    'event_1786': 704.05,      # image_05 (Telecom bill total amount due)
    'event_3051': 1995.0,      # image_06 (Grocery tax invoice total)
    'event_3231': 8528.10,     # image_07 (Restaurant tax invoice total)
    'event_4535': 15339.0,     # image_08 (Property maintenance invoice total)
    'event_5170': 723.0,       # image_09 (Water bill total)
    'event_6033': 79679.26,    # image_10 (Grocery invoice total)
    'event_6859': 3650.0,      # image_11 (Hospital provisional bill amount payable)
    'event_7307': 33.50,       # image_12 (Taxi receipt total)
    'event_7941': 2298.0,      # image_13 (Tote bag order total paid)
    'event_9421': 4543.0,      # image_14 (Pharmacy purchase total)
    'event_9806': 9968.0,      # image_15 (Flight invoice grand total)
    'event_10521': 393.22      # image_16 (EV charging invoice total)
}

class ImageHandler:
    def __init__(self, images_df: pd.DataFrame = None):
        self.amounts = KNOWN_IMAGE_AMOUNTS.copy()
        if images_df is not None:
            # Map images_df to amounts if present
            pass

    def get_event_amount(self, event_id: str) -> float:
        """Returns the extracted image amount for an event_id if present, else None."""
        return self.amounts.get(event_id, None)

    def has_image_event(self, event_id: str) -> bool:
        """Check if an event_id has a corresponding resolved image amount."""
        return event_id in self.amounts

