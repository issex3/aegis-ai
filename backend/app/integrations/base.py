from dataclasses import dataclass, field


@dataclass
class ToolCall:
    name: str
    arguments: dict
    id: str | None = None


@dataclass
class AdapterResult:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_channel: str = "unsupported"
    limitations: list[str] = field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None

    @property
    def failed(self) -> bool:
        return self.error_code is not None


@dataclass
class AgentRequest:
    endpoint: str
    model: str
    credential: str | None
    timeout_seconds: int
    max_output_tokens: int
    temperature: float | None
    messages: list[dict]
    tools: list[dict]
    config: dict


IMPLEMENTED = ("openai_compatible", "aegis_demo")
UNAVAILABLE = {
    "anthropic": "Anthropic",
    "azure_openai": "Azure OpenAI",
    "amazon_bedrock": "Amazon Bedrock",
    "custom_http": "Custom HTTP",
    "n8n": "n8n",
    "langchain": "LangChain",
    "crewai": "CrewAI",
    "custom_python": "Custom Python",
}
