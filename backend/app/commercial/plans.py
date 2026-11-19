"""Configurable plan limits. Prices are hypotheses, not validated commercial rates."""

PLANS = {
    "starter": {
        "name": "Starter",
        "price_label": "£49/month",
        "agents": 2,
        "monthly_assessments": 10,
        "sandboxes": False,
        "regression": False,
        "schedules": False,
        "users": 2,
    },
    "professional": {
        "name": "Professional",
        "price_label": "£149/month",
        "agents": 10,
        "monthly_assessments": 50,
        "sandboxes": True,
        "regression": True,
        "schedules": False,
        "users": 10,
    },
    "business": {
        "name": "Business",
        "price_label": "£399/month",
        "agents": 40,
        "monthly_assessments": 200,
        "sandboxes": True,
        "regression": True,
        "schedules": True,
        "users": 50,
    },
    "enterprise": {
        "name": "Enterprise",
        "price_label": "Custom",
        "agents": 1000,
        "monthly_assessments": 10000,
        "sandboxes": True,
        "regression": True,
        "schedules": True,
        "users": 1000,
    },
}

ACTIVE_STATUSES = {"active", "trialing"}
MIN_BENCHMARK_SAMPLE = 5
