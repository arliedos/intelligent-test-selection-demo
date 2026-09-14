"""Payment retry configuration, loaded from config/payment.json.

This is real, load-bearing configuration: `PaymentProcessor` calls
`load_payment_config()` whenever it isn't handed an explicit config, so
changing config/payment.json changes retry behaviour without a code change.
"""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PAYMENT_CONFIG_PATH = _REPO_ROOT / "config" / "payment.json"


@dataclass(frozen=True)
class PaymentConfig:
    max_retries: int
    retry_on_timeout: bool = True
    retry_on_decline: bool = True

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise ValueError("payment.max_retries must be >= 0")


def load_payment_config(path: Optional[Path] = None) -> PaymentConfig:
    config_path = Path(path) if path is not None else DEFAULT_PAYMENT_CONFIG_PATH
    with open(config_path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    return PaymentConfig(
        max_retries=raw["max_retries"],
        retry_on_timeout=raw.get("retry_on_timeout", True),
        retry_on_decline=raw.get("retry_on_decline", True),
    )
