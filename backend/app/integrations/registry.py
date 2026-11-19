from app.integrations.base import UNAVAILABLE, AdapterResult, AgentRequest
from app.integrations.demo_agent import complete as demo_complete
from app.integrations.openai_chat import complete as openai_complete


def adapter_availability(integration_type: str) -> str:
    if integration_type == "aegis_demo":
        return "demo"
    if integration_type == "openai_compatible":
        return "runnable"
    if integration_type in UNAVAILABLE:
        return "not_implemented"
    return "not_implemented"


def run_adapter(integration_type: str, request: AgentRequest, **kwargs) -> AdapterResult:
    if integration_type == "aegis_demo":
        return demo_complete(request)
    if integration_type == "openai_compatible":
        return openai_complete(request, **kwargs)
    label = UNAVAILABLE.get(integration_type, integration_type)
    return AdapterResult(
        error_code="adapter_not_implemented",
        error_message=f"The {label} adapter is not implemented. No assessment traffic was sent.",
    )
