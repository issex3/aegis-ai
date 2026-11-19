"""Stripe is the only writer of subscription status. Clients cannot set a plan directly."""

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.commercial.models import Subscription
from app.commercial.plans import ACTIVE_STATUSES, PLANS
from app.config import Settings
from app.errors import AppError
from app.models.agents import Agent
from app.models.assessments import Assessment
from app.models.base import utcnow


def get_subscription(db: Session, organisation_id: str) -> Subscription | None:
    return db.scalar(select(Subscription).where(Subscription.organisation_id == organisation_id))


def enforce_agent_limit(db: Session, settings: Settings, organisation_id: str) -> None:
    if not settings.billing_enforce:
        return
    subscription = get_subscription(db, organisation_id)
    if subscription is None or subscription.status not in ACTIVE_STATUSES:
        raise AppError(402, "subscription_required", "An active subscription is required.")
    limit = PLANS[subscription.plan_code]["agents"]
    count = db.scalar(
        select(func.count()).select_from(Agent).where(Agent.organisation_id == organisation_id, Agent.deleted_at.is_(None))
    ) or 0
    if int(count) >= int(limit):
        raise AppError(402, "plan_limit", "This plan has reached its agent limit.")


def enforce_assessment_limit(db: Session, settings: Settings, organisation_id: str, sandbox: bool, regression: bool, schedule: bool) -> None:
    if not settings.billing_enforce:
        return
    subscription = get_subscription(db, organisation_id)
    if subscription is None or subscription.status not in ACTIVE_STATUSES:
        raise AppError(402, "subscription_required", "An active subscription is required.")
    plan = PLANS[subscription.plan_code]
    if sandbox and not plan["sandboxes"]:
        raise AppError(402, "plan_limit", "Industry sandboxes are not included in this plan.")
    if regression and not plan["regression"]:
        raise AppError(402, "plan_limit", "Regression testing is not included in this plan.")
    if schedule and not plan["schedules"]:
        raise AppError(402, "plan_limit", "Scheduled assessments are not included in this plan.")
    start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    used = db.scalar(
        select(func.count()).select_from(Assessment).where(
            Assessment.organisation_id == organisation_id,
            Assessment.created_at >= start,
            Assessment.status.in_(("running", "completed", "failed")),
        )
    ) or 0
    if int(used) >= int(plan["monthly_assessments"]):
        raise AppError(402, "plan_limit", "This plan has reached its monthly assessment allowance.")


def apply_stripe_subscription(db: Session, *, organisation_id: str, plan_code: str, status: str, customer_id: str | None, subscription_id: str | None) -> Subscription:
    if plan_code not in PLANS:
        plan_code = "starter"
    row = get_subscription(db, organisation_id)
    if row is None:
        row = Subscription(organisation_id=organisation_id, plan_code=plan_code, status=status)
        db.add(row)
    row.plan_code = plan_code
    row.status = status
    row.stripe_customer_id = customer_id or row.stripe_customer_id
    row.stripe_subscription_id = subscription_id or row.stripe_subscription_id
    row.updated_at = utcnow()
    db.commit()
    db.refresh(row)
    return row


def create_checkout(settings: Settings, organisation_id: str, plan_code: str) -> str:
    prices = {
        "starter": settings.stripe_price_starter,
        "professional": settings.stripe_price_professional,
        "business": settings.stripe_price_business,
    }
    if plan_code == "enterprise":
        raise AppError(400, "contact_sales", "Enterprise plans are arranged directly. Checkout is not available.")
    price = prices.get(plan_code)
    if not settings.stripe_secret_key or not price:
        raise AppError(503, "billing_not_configured", "Stripe checkout is not configured for this environment.")
    import stripe

    stripe.api_key = settings.stripe_secret_key
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": price, "quantity": 1}],
        success_url=f"{settings.public_app_url}/settings?billing=success",
        cancel_url=f"{settings.public_app_url}/settings?billing=cancel",
        metadata={"organisation_id": organisation_id, "plan_code": plan_code},
        subscription_data={"metadata": {"organisation_id": organisation_id, "plan_code": plan_code}},
    )
    return session.url


def create_portal(settings: Settings, customer_id: str) -> str:
    if not settings.stripe_secret_key or not customer_id:
        raise AppError(503, "billing_not_configured", "The billing portal is not available yet.")
    import stripe

    stripe.api_key = settings.stripe_secret_key
    session = stripe.billing_portal.Session.create(customer=customer_id, return_url=f"{settings.public_app_url}/settings")
    return session.url


def verify_webhook(settings: Settings, payload: bytes, signature: str | None) -> dict:
    if not settings.stripe_webhook_secret or not signature:
        raise AppError(400, "invalid_webhook", "The billing webhook could not be verified.")
    import stripe

    try:
        event = stripe.Webhook.construct_event(payload, signature, settings.stripe_webhook_secret)
    except Exception as exc:
        raise AppError(400, "invalid_webhook", "The billing webhook could not be verified.") from exc
    return event
