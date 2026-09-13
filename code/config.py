import os
from dataclasses import dataclass

@dataclass
class Config:
    """Configuration class for financial decision agent runtime settings."""
    min_balance_default: float = 0.0
    forecast_days: int = 90
    media_dir: str = "dataset/media/images"
    gemini_model: str = "gemini-2.5-flash"
    log_level: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def load_from_env(cls) -> "Config":
        return cls(
            min_balance_default=float(os.getenv("MIN_BALANCE_DEFAULT", "0.0")),
            forecast_days=int(os.getenv("FORECAST_DAYS", "90")),
            media_dir=os.getenv("MEDIA_DIR", "dataset/media/images"),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        )
