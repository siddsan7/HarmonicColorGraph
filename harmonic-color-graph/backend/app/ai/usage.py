"""Request-scoped model usage and estimated direct Anthropic API cost."""

from __future__ import annotations

import os
from dataclasses import dataclass
from decimal import ROUND_UP, Decimal
from typing import Any

# Standard, uncached API rates in USD per million tokens as of September 2026.
# Override when a deployment uses a different model or contract.
MODEL_RATES = {
    "claude-haiku-4-5-20251001": (Decimal("1"), Decimal("5")),
    "claude-sonnet-5": (Decimal("3"), Decimal("15")),
}

FAST_MAX_PROMPT_BYTES = 12_000
MAIN_MAX_PROMPT_BYTES = 80_000
# Covers fixed structured-output schemas and provider framing beyond the
# bounded prompt strings. It is deliberately much larger than either schema.
PROTOCOL_OVERHEAD_TOKENS = 50_000
FAST_MAX_OUTPUT_TOKENS = 512
MAIN_MAX_OUTPUT_TOKENS = 1024
MAIN_MAX_CALLS = 2
MISSING_USAGE_CHARGE_USD = Decimal("0.25")


def configured_rates(model: str, prefix: str) -> tuple[Decimal, Decimal]:
    defaults = MODEL_RATES.get(model, (Decimal("10"), Decimal("50")))
    raw_input = os.getenv(f"{prefix}_INPUT_USD_PER_MTOK")
    raw_output = os.getenv(f"{prefix}_OUTPUT_USD_PER_MTOK")
    rates = (
        Decimal(raw_input) if raw_input else defaults[0],
        Decimal(raw_output) if raw_output else defaults[1],
    )
    if any(not rate.is_finite() or rate <= 0 for rate in rates):
        raise ValueError("Model token rates must be positive finite numbers")
    return rates


def request_cost_bound() -> Decimal:
    """Conservative maximum for the bounded one-fast, two-main call workflow."""
    if not os.getenv("ANTHROPIC_API_KEY"):
        return Decimal("0")
    fast_name = os.getenv("HCG_LLM_FAST_MODEL", "claude-haiku-4-5-20251001")
    main_name = os.getenv("HCG_LLM_MODEL", "claude-sonnet-5")
    fast_in, fast_out = configured_rates(fast_name, "HCG_LLM_FAST")
    main_in, main_out = configured_rates(main_name, "HCG_LLM")
    tokens = (
        (FAST_MAX_PROMPT_BYTES + PROTOCOL_OVERHEAD_TOKENS) * fast_in
        + FAST_MAX_OUTPUT_TOKENS * fast_out
        + MAIN_MAX_CALLS
        * (
            (MAIN_MAX_PROMPT_BYTES + PROTOCOL_OVERHEAD_TOKENS) * main_in
            + MAIN_MAX_OUTPUT_TOKENS * main_out
        )
    )
    metered = (tokens / 1_000_000).quantize(Decimal("0.00000001"), rounding=ROUND_UP)
    missing_usage = MISSING_USAGE_CHARGE_USD * (1 + MAIN_MAX_CALLS)
    return max(metered, missing_usage)


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
            self.cost_usd += MISSING_USAGE_CHARGE_USD
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
