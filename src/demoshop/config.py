"""Payment retry configuration, loaded from config/payment.json.

This is real, load-bearing configuration: `PaymentProcessor` calls
`load_payment_config()` whenever it isn't handed an explicit config, so
changing config/payment.json changes retry behaviour without a code change.
"""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

_MODULE_DIR = Path(__file__).resolve().parent


def _find_default_config_path(start: Path, max_levels: int = 6) -> Path:
    """Searches upward from `start` for a `config/payment.json`.

    Deliberately does not hardcode a fixed number of parent directories
    between this module and the repo root: that breaks whenever the
    module isn't installed exactly two levels below the repo root (e.g.
    a non-editable install, where site-packages/demoshop/config.py sits
    next to, not two levels below, its config directory).
    """
    current = start
    for _ in range(max_levels + 1):
        candidate = current / "config" / "payment.json"
        if candidate.exists():
            return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent
    raise FileNotFoundError(
        f"could not locate config/payment.json searching upward from {start} "
        f"(searched {max_levels + 1} directory levels)"
    )


@dataclass(frozen=True)
class PaymentConfig:
    max_retries: int
    retry_on_timeout: bool = True
    retry_on_decline: bool = True

    def __post_init__(self) -> None:
        if self.max_retries < 0:
            raise ValueError("payment.max_retries must be >= 0")


def load_payment_config(path: Optional[Path] = None) -> PaymentConfig:
    config_path = Path(path) if path is not None else _find_default_config_path(_MODULE_DIR)
    with open(config_path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    return PaymentConfig(
        max_retries=raw["max_retries"],
        retry_on_timeout=raw.get("retry_on_timeout", True),
        retry_on_decline=raw.get("retry_on_decline", True),
    )
