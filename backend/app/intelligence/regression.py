"""Compare assessments by stable test-case code, not by wording."""

from __future__ import annotations


def _verdict(baseline: str | None, current: str | None) -> str:
    if baseline in {None, "ERROR", "INCONCLUSIVE", "SKIPPED"} or current in {None, "ERROR", "INCONCLUSIVE", "SKIPPED"}:
        if baseline is None:
            return "new_test"
        if current is None:
            return "no_longer_supported"
        return "inconclusive_comparison"
    if baseline == "FAIL" and current == "FAIL":
        return "persistent_vulnerability"
    if baseline != "FAIL" and current == "FAIL":
        return "new_vulnerability"
    if baseline == "FAIL" and current != "FAIL":
        return "resolved_vulnerability"
    return "no_change"


def compare_results(baseline: list[dict], current: list[dict]) -> dict:
    base = {item["code"]: item for item in baseline if item.get("code")}
    cur = {item["code"]: item for item in current if item.get("code")}
    codes = sorted(set(base) | set(cur))
    rows = []
    for code in codes:
        left = base.get(code)
        right = cur.get(code)
        status = _verdict(left["outcome"] if left else None, right["outcome"] if right else None)
        severity_increased = False
        if left and right and status == "persistent_vulnerability":
            order = ["informational", "low", "medium", "high", "critical"]
            before = order.index(left.get("severity") or "low") if left.get("severity") in order else 1
            after = order.index(right.get("severity") or "low") if right.get("severity") in order else 1
            severity_increased = after > before
        rows.append(
            {
                "code": code,
                "status": status,
                "baseline_outcome": left["outcome"] if left else None,
                "current_outcome": right["outcome"] if right else None,
                "severity_increased": severity_increased,
            }
        )
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["status"]] = counts.get(row["status"], 0) + 1
    return {"items": rows, "counts": counts, "severity_increases": sum(1 for row in rows if row["severity_increased"])}
