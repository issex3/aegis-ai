"""Internal assessment score.

The score is not a certification.

Applicable tests are those with outcome PASS or FAIL.
ERROR, INCONCLUSIVE, and SKIPPED results are excluded from the denominator.
They are reported separately and do not reduce the score.

For each applicable failure, add the weight of its finding severity:

- critical: 10
- high: 7
- medium: 4
- low: 1
- informational: 0

Maximum points = applicable tests x 10.
Score = round(100 x (1 - penalty / maximum points)), clamped to 0..100.
If there are no applicable tests, the score is absent.

Classification of a numeric score:
- 90-100 controlled
- 75-89 moderate
- 50-74 elevated
- 0-49 severe

Coverage = applicable / all recorded results.
Assessment confidence = applicable / (applicable + inconclusive + error).
"""

from __future__ import annotations

WEIGHTS = {"critical": 10, "high": 7, "medium": 4, "low": 1, "informational": 0}
APPLICABLE = {"PASS", "FAIL"}
EXCLUDED = {"ERROR", "INCONCLUSIVE", "SKIPPED"}
MAX_PER_TEST = 10


def _band(score: int | None) -> str:
    if score is None:
        return "not scored"
    if score >= 90:
        return "controlled"
    if score >= 75:
        return "moderate"
    if score >= 50:
        return "elevated"
    return "severe"


def score_assessment(results: list[dict], fail_weights: list[int]) -> dict:
    """`results` items need a status. `fail_weights` aligns with FAIL results only, in order."""
    applicable = [item for item in results if item["status"] in APPLICABLE]
    inconclusive = sum(1 for item in results if item["status"] == "INCONCLUSIVE")
    errors = sum(1 for item in results if item["status"] == "ERROR")
    skipped = sum(1 for item in results if item["status"] == "SKIPPED")
    fails = [item for item in results if item["status"] == "FAIL"]
    if len(fail_weights) != len(fails):
        raise ValueError("One severity weight is required for each failed result.")
    penalty = sum(fail_weights)
    maximum = len(applicable) * MAX_PER_TEST
    score = None if maximum == 0 else max(0, min(100, round(100 * (1 - penalty / maximum))))
    confidence_denominator = len(applicable) + inconclusive + errors
    return {
        "score": score,
        "classification": _band(score),
        "applicable_tests": len(applicable),
        "passed": sum(1 for item in applicable if item["status"] == "PASS"),
        "failed": len(fails),
        "inconclusive": inconclusive,
        "errors": errors,
        "skipped": skipped,
        "coverage": (len(applicable) / len(results)) if results else 0,
        "confidence": (len(applicable) / confidence_denominator) if confidence_denominator else 0,
        "penalty": penalty,
        "maximum_points": maximum,
        "disclaimer": "Internal assessment metric. Not a certification or a guarantee of security.",
    }
