"""Run every library scenario against the local demo agent profiles and print the outcome matrix.

Usage: python scripts/scenario_matrix.py
No network access. Uses synthetic sandboxes only.
"""

from types import SimpleNamespace

from app.scenarios import registry
from app.scenarios.evaluation import evaluate
from app.scenarios.execution import run_scenario


def _agent(profile: str):
    integration = SimpleNamespace(timeout_seconds=5, max_output_tokens=256, temperature=None, config_json={"weakness_profile": profile})
    return SimpleNamespace(
        integration_type="aegis_demo",
        api_endpoint="demo://builtin",
        model_name="aegis-demo-1",
        integration=integration,
        security_boundaries="Follow the operating rules.",
    )


def main() -> None:
    profiles = ("default", "remediated")
    print(f"{'scenario':42} " + " ".join(f"{name:>12}" for name in profiles))
    for scenario in registry.SCENARIOS.values():
        outcomes = []
        for profile in profiles:
            observed, _ = run_scenario(_agent(profile), None, scenario, scenario.turns)
            outcomes.append(evaluate(scenario, observed)["outcome"])
        print(f"{scenario.code:42} " + " ".join(f"{outcome:>12}" for outcome in outcomes))


if __name__ == "__main__":
    main()
