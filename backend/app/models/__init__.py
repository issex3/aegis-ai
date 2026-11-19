"""Import all models so metadata is complete for Alembic."""

from app.commercial import models as commercial_models  # noqa: F401
from app.scenarios import models as scenario_models  # noqa: F401
from app.models.agents import Agent, AgentCredential, AgentIntegration
from app.models.assessments import (
    Assessment,
    AssessmentComparison,
    AssessmentResult,
    AssessmentSuite,
    Finding,
    FindingEvidence,
    Remediation,
    Report,
    TestCase,
    test_case_industries,
)
from app.models.base import Base
from app.models.identity import (
    MfaChallenge,
    Organisation,
    OrganisationInvite,
    OrganisationMembership,
    PasswordResetToken,
    Session,
    User,
)
from app.models.intelligence import (
    AuditEvent,
    DataContributionConsent,
    DatasetVersion,
    IntelligenceDataset,
    IntelligenceRecord,
)
from app.models.sandboxes import (
    Industry,
    Sandbox,
    SandboxDataset,
    SandboxTool,
    SandboxVersion,
    SandboxWorkflow,
)

__all__ = [
    "Agent",
    "AgentCredential",
    "AgentIntegration",
    "Assessment",
    "AssessmentComparison",
    "AssessmentResult",
    "AssessmentSuite",
    "AuditEvent",
    "Base",
    "DataContributionConsent",
    "DatasetVersion",
    "Finding",
    "FindingEvidence",
    "Industry",
    "IntelligenceDataset",
    "IntelligenceRecord",
    "Organisation",
    "OrganisationMembership",
    "Remediation",
    "Report",
    "Sandbox",
    "SandboxDataset",
    "SandboxTool",
    "SandboxVersion",
    "SandboxWorkflow",
    "Session",
    "TestCase",
    "User",
    "test_case_industries",
]
