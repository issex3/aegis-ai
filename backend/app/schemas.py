from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.security import credential_hint

INTEGRATION_TYPES = (
    "openai_compatible",
    "anthropic",
    "azure_openai",
    "amazon_bedrock",
    "custom_http",
)
AGENT_STATUSES = ("active", "disabled")
ASSESSMENT_STATUSES = ("draft", "pending", "queued", "running", "completed", "failed", "cancelled")
MEMBERSHIP_ROLES = ("owner", "admin", "member", "viewer")
ADMIN_ROLES = ("owner", "admin", "administrator")
CONSENT_POLICY_VERSION = "2026-11-01"
CONSENT_SCOPE = "validated_assessment_outcomes"


def _clean_text(value: str) -> str:
    return value.strip()


class RegisterRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    organisation_name: str = Field(min_length=2, max_length=160)
    invite_token: str | None = Field(default=None, max_length=128)

    @field_validator("full_name", "organisation_name")
    @classmethod
    def strip_names(cls, value: str) -> str:
        cleaned = _clean_text(value)
        if len(cleaned) < 2:
            raise ValueError("Enter at least 2 characters.")
        return cleaned

    @field_validator("password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if not any(character.isalpha() for character in value) or not any(character.isdigit() for character in value):
            raise ValueError("Use at least one letter and one number.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str = Field(min_length=16, max_length=256)
    new_password: str = Field(min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def reset_password_strength(cls, value: str) -> str:
        if not any(character.isalpha() for character in value) or not any(character.isdigit() for character in value):
            raise ValueError("Use at least one letter and one number.")
        return value


class MfaCodeRequest(BaseModel):
    code: str = Field(min_length=6, max_length=64)


class MfaVerifyRequest(BaseModel):
    challenge_id: str = Field(min_length=16, max_length=256)
    code: str = Field(min_length=6, max_length=64)


class MfaDisableRequest(BaseModel):
    password: str = Field(min_length=1, max_length=128)
    code: str = Field(min_length=6, max_length=64)


class MemberInviteRequest(BaseModel):
    email: EmailStr
    role: str = Field(min_length=4, max_length=32)


class MemberRoleUpdate(BaseModel):
    role: str = Field(min_length=4, max_length=32)


class LicensedKeyCreate(BaseModel):
    name: str = Field(default="Licensed access", min_length=1, max_length=120)


class OrganisationRetentionUpdate(BaseModel):
    retention_days: int = Field(ge=30, le=2555)


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=12, max_length=128)

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, value: str) -> str:
        if not any(character.isalpha() for character in value) or not any(character.isdigit() for character in value):
            raise ValueError("Use at least one letter and one number.")
        return value


class ProfileUpdate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = _clean_text(value)
        if len(cleaned) < 2:
            raise ValueError("Enter at least 2 characters.")
        return cleaned


class OrganisationUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=160)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = _clean_text(value)
        if len(cleaned) < 2:
            raise ValueError("Enter at least 2 characters.")
        return cleaned


class UserOut(BaseModel):
    id: str
    email: EmailStr
    full_name: str
    is_platform_operator: bool
    mfa_enabled: bool = False

    model_config = {"from_attributes": True}


class OrganisationOut(BaseModel):
    id: str
    name: str
    slug: str
    retention_days: int = 365

    model_config = {"from_attributes": True}


class MembershipOut(BaseModel):
    role: str


class SessionOut(BaseModel):
    user: UserOut
    organisation: OrganisationOut
    role: str


class AgentWrite(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str = Field(min_length=10, max_length=4000)
    integration_type: str
    api_endpoint: str = Field(min_length=8, max_length=2048)
    model_name: str = Field(min_length=1, max_length=160)
    purpose: str = Field(min_length=10, max_length=4000)
    behaviour: str = Field(min_length=10, max_length=4000)
    security_boundaries: str = Field(min_length=10, max_length=4000)
    secret: str | None = Field(default=None, max_length=4096)
    timeout_seconds: int = Field(default=30, ge=5, le=60)
    max_output_tokens: int = Field(default=512, ge=16, le=2048)
    temperature: float | None = Field(default=None, ge=0, le=2)

    @field_validator(
        "name",
        "description",
        "model_name",
        "purpose",
        "behaviour",
        "security_boundaries",
        "api_endpoint",
    )
    @classmethod
    def strip_text(cls, value: str) -> str:
        return _clean_text(value)

    @field_validator("integration_type")
    @classmethod
    def known_integration(cls, value: str) -> str:
        if value not in INTEGRATION_TYPES:
            raise ValueError("Select a supported integration type.")
        return value

    @field_validator("api_endpoint")
    @classmethod
    def endpoint_must_be_https_or_local(cls, value: str) -> str:
        lowered = value.lower()
        if not (lowered.startswith("https://") or lowered.startswith("http://127.0.0.1") or lowered.startswith("http://localhost")):
            raise ValueError("Use an https endpoint. Local http is allowed only for localhost.")
        if " " in value:
            raise ValueError("Enter a valid endpoint URL.")
        return value

    @field_validator("secret")
    @classmethod
    def secret_length(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if cleaned == "":
            return None
        if len(cleaned) < 8:
            raise ValueError("Credential must be at least 8 characters.")
        return cleaned


class AgentUpdate(AgentWrite):
    secret: str | None = None

    @field_validator("secret")
    @classmethod
    def reject_secret_on_update(cls, value: str | None) -> None:
        if value:
            raise ValueError("Update credentials with the credential action.")
        return None


class CredentialWrite(BaseModel):
    secret: str = Field(min_length=8, max_length=4096)

    @field_validator("secret")
    @classmethod
    def strip_secret(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < 8:
            raise ValueError("Credential must be at least 8 characters.")
        return cleaned


class CredentialOut(BaseModel):
    configured: bool
    hint: str | None = None
    updated_at: datetime | None = None


class AgentOut(BaseModel):
    id: str
    name: str
    description: str
    integration_type: str
    api_endpoint: str
    model_name: str
    purpose: str
    behaviour: str
    security_boundaries: str
    status: str
    created_at: datetime
    updated_at: datetime
    credential: CredentialOut
    timeout_seconds: int = 30
    max_output_tokens: int = 512
    temperature: float | None = None
    adapter_status: str = "not_implemented"
    demo_profile: str | None = None

    model_config = {"from_attributes": True}


class AgentStatusUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def known_status(cls, value: str) -> str:
        if value not in AGENT_STATUSES:
            raise ValueError("Status must be active or disabled.")
        return value


class AssessmentPlan(BaseModel):
    agent_id: str = Field(min_length=36, max_length=36)
    name: str = Field(min_length=2, max_length=200)
    sandbox_id: str | None = None
    categories: list[str] = Field(default_factory=list)
    simulated_role: str | None = None
    authorised: bool
    authorisation_note: str = Field(min_length=10, max_length=500)

    @field_validator("name", "authorisation_note")
    @classmethod
    def strip_plan_text(cls, value: str) -> str:
        return _clean_text(value)

    @field_validator("categories")
    @classmethod
    def known_categories(cls, value: list[str]) -> list[str]:
        from app.engine.catalog import CATEGORIES

        unknown = [item for item in value if item not in CATEGORIES]
        if unknown:
            raise ValueError("Choose a supported test category.")
        return value


class AssessmentCreate(BaseModel):
    agent_id: str = Field(min_length=36, max_length=36)
    name: str = Field(min_length=2, max_length=200)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = _clean_text(value)
        if len(cleaned) < 2:
            raise ValueError("Enter at least 2 characters.")
        return cleaned


class AssessmentOut(BaseModel):
    id: str
    agent_id: str
    agent_name: str
    name: str
    status: str
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class FindingOut(BaseModel):
    id: str
    title: str
    severity: str
    status: str
    category: str = ""
    confidence: str = "medium"
    stable_key: str | None = None
    agent_id: str
    assessment_id: str
    created_at: datetime


class ReportOut(BaseModel):
    id: str
    title: str
    status: str
    assessment_id: str | None
    created_at: datetime


class IndustryOut(BaseModel):
    id: str
    slug: str
    name: str
    description: str

    model_config = {"from_attributes": True}


class SandboxOut(BaseModel):
    id: str
    name: str
    description: str
    status: str
    industry_name: str
    current_version_number: int | None


class AuditEventOut(BaseModel):
    id: str
    action: str
    resource_type: str
    resource_id: str | None
    created_at: datetime


class ConsentOut(BaseModel):
    granted: bool
    policy_version: str
    scope: str
    recorded_at: datetime | None
    permitted_categories: list[str] = []
    intended_use: str = ""


class ConsentWrite(BaseModel):
    granted: bool
    permitted_categories: list[str] = []
    intended_use: str = ""


class DashboardSummary(BaseModel):
    agents: dict
    assessments: dict
    findings: dict
    reports: dict
    recent_assessments: list[AssessmentOut]
    recent_audit_events: list[AuditEventOut]
    posture: dict | None = None


class DatasetOut(BaseModel):
    id: str
    name: str
    description: str
    classification: str
    version_count: int


class LabSessionCreate(BaseModel):
    role: str | None = Field(default=None, max_length=64)


class LabToolInvoke(BaseModel):
    tool: str = Field(min_length=1, max_length=120)
    arguments: dict = Field(default_factory=dict)


def public_credential(hint: str | None, updated_at: datetime | None) -> CredentialOut:
    if hint is None:
        return CredentialOut(configured=False)
    return CredentialOut(configured=True, hint=f"••••{hint}", updated_at=updated_at)


def assert_hint_is_masked(secret: str, published_hint: str | None) -> None:
    """Guard used by tests to ensure only the stored suffix is published."""
    if published_hint is None:
        return
    if secret in published_hint:
        raise RuntimeError("Credential material leaked into a hint.")
    if published_hint != f"••••{credential_hint(secret)}":
        raise RuntimeError("Hint format is incorrect.")
