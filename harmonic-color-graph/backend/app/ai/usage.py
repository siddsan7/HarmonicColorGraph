"""Request-scoped model usage and estimated direct Anthropic API cost."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

# Standard, uncached API rates in USD per million tokens as of September 2026.
# Override when a deployment uses a different model or contract.
MODEL_RATES = {
    "claude-haiku-4-5-20251001": (Decimal("1"), Decimal("5")),
    "claude-sonnet-5": (Decimal("3"), Decimal("15")),
}


@dataclass
class UsageMeter:
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: Decimal = Decimal("0")
    model: str | None = None

    def record(
        self,
        raw: Any,
        model: str,
        *,
        input_rate: Decimal | None = None,
        output_rate: Decimal | None = None,
    ) -> None:
        usage = getattr(raw, "usage_metadata", None) or {}
        if not usage:
            response_metadata = getattr(raw, "response_metadata", None) or {}
            usage = response_metadata.get("usage") or response_metadata.get("token_usage") or {}
        self.model = model
        if not usage:
            # A model response without usage must never appear free to the
            # daily cap. Keep a conservative charge in the audit record.
            self.cost_usd += Decimal("0.25")
            return
        incoming = int(usage.get("input_tokens", 0))
        outgoing = int(usage.get("output_tokens", 0))
        self.tokens_in += incoming
        self.tokens_out += outgoing
        # An operator-selected model without explicit rates is charged at a
        # conservative ceiling until its actual contract rate is configured.
        rates = MODEL_RATES.get(model, (Decimal("10"), Decimal("50")))
        if input_rate is None or output_rate is None:
            input_rate, output_rate = rates
        self.cost_usd += (incoming * input_rate + outgoing * output_rate) / 1_000_000

    def as_log(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost_usd": self.cost_usd,
        }
