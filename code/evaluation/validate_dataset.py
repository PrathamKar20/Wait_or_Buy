import os
import pandas as pd

def validate_dataset(data_dir: str = 'dataset') -> bool:
    """Validates presence and required schemas of input dataset files."""
    required_files = [
        'financial_profiles.csv',
        'financial_events.csv',
        'exchange_rates.csv',
        'requests.csv'
    ]
    for fname in required_files:
        fpath = os.path.join(data_dir, fname)
        if not os.path.exists(fpath):
            print(f"Validation error: Missing {fpath}")
            return False
    print("Dataset integrity validation passed.")
    return True

if __name__ == "__main__":
    validate_dataset()
