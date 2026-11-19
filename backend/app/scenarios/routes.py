from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api import current_principal, request_context, settings_dep
from app.config import Settings
from app.database import get_db
from app.errors import AppError
from app.sandboxes.definitions import SANDBOXES
from app.scenarios import registry
from app.scenarios.api_schemas import ProfileAnalyse, ProfileWrite, ProgrammeCreate, ProgrammeLaunch, ProgrammeUpdate
from app.scenarios.profiling import analyse
from app.scenarios.selection import INTENSITIES
from app.scenarios.service import (
    assessment_logs,
    create_programme,
    get_profile,
    get_programme,
    launch_programme,
    list_programmes,
    profile_out,
    programme_out,
    programme_report,
    save_profile,
    update_programme,
)
from app.scenarios.taxonomy import CAPABILITIES, DATA_CLASSES, INDUSTRIES, SCENARIO_CATEGORIES, THREATS
from app.services import WRITE_ROLES, require_role

router = APIRouter(prefix="/api/v1")


def _summary(scenario) -> dict:
    return {
        "code": scenario.code,
        "version": scenario.version,
        "name": scenario.name,
        "industry": scenario.industry,
        "category": scenario.category,
        "threat": scenario.threat,
        "threat_name": THREATS[scenario.threat]["name"],
        "risk": scenario.risk,
        "description": scenario.description,
        "technique": scenario.technique,
        "exposure": list(scenario.exposure),
        "sandbox": scenario.environment.sandbox,
        "variants": len(scenario.variants),
    }


@router.get("/scenario-library")
def library_index(principal=Depends(current_principal)):
    industries = []
    for slug, industry in INDUSTRIES.items():
        scenarios = registry.for_industry(slug)
        industries.append(
            {
                "slug": slug,
                "name": industry.name,
                "summary": industry.summary,
                "sandbox": industry.sandbox,
                "sandbox_name": SANDBOXES[industry.sandbox]["name"],
                "scenarios": len(scenarios),
                "by_risk": {level: sum(1 for item in scenarios if item.risk == level) for level in ("critical", "high", "medium", "low")},
                "threats": sorted({item.threat for item in scenarios}),
                "typical_capabilities": list(industry.typical_capabilities),
                "typical_data": list(industry.typical_data),
            }
        )
    return {
        "industries": industries,
        "threats": [{"key": key, **meta} for key, meta in THREATS.items()],
        "categories": list(SCENARIO_CATEGORIES),
        "capabilities": [{"key": item.key, "label": item.label, "kind": item.kind} for item in CAPABILITIES.values()],
        "data_classes": [{"key": key, "label": label} for key, label in DATA_CLASSES.items()],
        "intensities": INTENSITIES,
        "scenarios": [_summary(item) for item in registry.SCENARIOS.values()],
    }


@router.get("/scenario-library/{code}")
def library_detail(code: str, principal=Depends(current_principal)):
    scenario = registry.get(code)
    if scenario is None:
        raise AppError(404, "not_found", "Scenario not found.")
    sandbox = SANDBOXES[scenario.environment.sandbox]
    body = scenario.to_dict()
    body.update(
        {
            "threat_name": THREATS[scenario.threat]["name"],
            "threat_reference": THREATS[scenario.threat]["reference"],
            "industry_name": INDUSTRIES[scenario.industry].name,
            "sandbox_name": sandbox["name"],
            "sandbox_boundaries": sandbox["boundaries"],
            "exposure_labels": [CAPABILITIES[key].label for key in scenario.exposure],
            "content_hash": scenario.content_hash(),
        }
    )
    return body


@router.get("/agents/{agent_id}/profile")
def read_profile(agent_id: str, principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, _membership, _session = principal
    profile = get_profile(db, organisation.id, agent_id)
    return {"profile": profile_out(profile) if profile else None}


@router.put("/agents/{agent_id}/profile")
def write_profile(agent_id: str, payload: ProfileWrite, request: Request, principal=Depends(current_principal), db: Session = Depends(get_db)):
    user, organisation, membership, _session = principal
    require_role(membership, WRITE_ROLES)
    _, ip_address = request_context(request)
    profile = save_profile(db, organisation.id, user.id, agent_id, payload.model_dump(), ip_address)
    return {"profile": profile_out(profile)}


@router.post("/profile-analysis")
def analyse_profile(payload: ProfileAnalyse, principal=Depends(current_principal)):
    return analyse(payload.model_dump())


@router.get("/programmes")
def programmes(principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, _membership, _session = principal
    return list_programmes(db, organisation.id)


@router.post("/programmes", status_code=201)
def programme_create(payload: ProgrammeCreate, request: Request, principal=Depends(current_principal), db: Session = Depends(get_db)):
    user, organisation, membership, _session = principal
    require_role(membership, WRITE_ROLES)
    _, ip_address = request_context(request)
    programme = create_programme(db, organisation.id, user.id, payload.agent_id, payload.intensity, payload.include_generic, ip_address)
    return programme_out(db, programme)


@router.get("/programmes/{programme_id}")
def programme_detail(programme_id: str, principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, _membership, _session = principal
    return programme_out(db, get_programme(db, organisation.id, programme_id))


@router.patch("/programmes/{programme_id}")
def programme_update(programme_id: str, payload: ProgrammeUpdate, principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, membership, _session = principal
    require_role(membership, WRITE_ROLES)
    programme = update_programme(db, organisation.id, programme_id, payload.model_dump())
    return programme_out(db, programme)


@router.post("/programmes/{programme_id}/launch", status_code=201)
def programme_launch(
    programme_id: str,
    payload: ProgrammeLaunch,
    request: Request,
    principal=Depends(current_principal),
    db: Session = Depends(get_db),
    settings: Settings = Depends(settings_dep),
):
    user, organisation, membership, _session = principal
    require_role(membership, WRITE_ROLES)
    _, ip_address = request_context(request)
    assessment = launch_programme(
        db,
        settings,
        organisation_id=organisation.id,
        user_id=user.id,
        programme_id=programme_id,
        name=payload.name,
        authorised=payload.authorised,
        authorisation_note=payload.authorisation_note,
        ip_address=ip_address,
    )
    return {"assessment_id": assessment.id, "status": assessment.status}


@router.get("/assessments/{assessment_id}/intelligence")
def assessment_intelligence(assessment_id: str, principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, _membership, _session = principal
    return programme_report(db, organisation.id, assessment_id)


@router.get("/assessments/{assessment_id}/logs")
def assessment_log(assessment_id: str, after: int = 0, principal=Depends(current_principal), db: Session = Depends(get_db)):
    _user, organisation, _membership, _session = principal
    return assessment_logs(db, organisation.id, assessment_id, max(after, 0))
