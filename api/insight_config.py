"""Documented settings for deterministic, rule-based insights."""

# Require a complete 10-year reference window before making the overview comparison.
OVERVIEW_REFERENCE_YEARS = 10

# V1 uses numeric comparisons only; it does not emit strength labels such as
# "tăng mạnh" or "giảm nhẹ". If approved later, add metric-specific thresholds
# here rather than applying one threshold to different indicators.
QUALITATIVE_CHANGE_THRESHOLDS: dict[str, dict[str, float]] = {}

# These terms are prohibited in generated insight sentences.
FORBIDDEN_CAUSAL_PHRASES = (
    "do",
    "vì",
    "nhờ",
    "bởi",
    "dẫn đến",
    "kéo theo",
)
