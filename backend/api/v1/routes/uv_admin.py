"""Operator review UI uses the existing UV deployment workflow."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from backend.api.deps import require_model_reviewer
from backend.services import uv_lifecycle as lifecycle
from scripts import uv_mlops

router = APIRouter(dependencies=[Depends(require_model_reviewer)])
Version = Field(pattern=r"^uv-[A-Za-z0-9-]{1,80}$")


def optional_json(path):
    return lifecycle.read_json(path) if path.exists() else None


@router.get("")
def overview(response: Response) -> dict:
    response.headers["Cache-Control"] = "no-store"
    try:
        state = lifecycle.deployment()
        pipeline = optional_json(lifecycle.ARTIFACTS / "pipeline_status.json")
        snapshot = optional_json(lifecycle.ARTIFACTS / "forecast_snapshot.json") or {}
        active_manifest = (
            lifecycle.read_json(lifecycle.bundle_path(state["active"]) / "manifest.json")
            if state["active"]
            else None
        )
        candidate = None
        if pipeline and pipeline.get("version"):
            version = pipeline["version"]
            bundle = lifecycle.bundle_path(version)
            gate = optional_json(bundle / "gate.json")
            ready = False
            issue = None
            try:
                checked = uv_mlops.review_candidate(version)
                ready = checked["base_version"] == state["active"] and version != state["active"]
                if not ready:
                    issue = "รุ่นใช้งานเปลี่ยนแล้ว กรุณารอ candidate ที่ประเมินเทียบรุ่นปัจจุบัน"
            except (OSError, ValueError, KeyError, TypeError):
                issue = "Candidate ยังไม่ผ่านเกณฑ์ หรือไฟล์ผลประเมินไม่ครบ/ไม่ตรงกัน"
            candidate = {
                "version": version,
                "gate": gate,
                "can_promote": ready,
                "issue": issue,
                "evaluation": optional_json(bundle / "artifacts/evaluation.json"),
                "tracking": optional_json(bundle / "tracking.json"),
            }
        previous = state["history"][-1]["from"] if state["history"] else None
        return {
            **state,
            "previous": previous,
            "active_manifest": active_manifest,
            "pipeline": pipeline,
            "candidate": candidate,
            "monitoring": optional_json(lifecycle.ARTIFACTS / "monitoring.json"),
            "data_dates": {c: v.get("data_date") for c, v in snapshot.get("cities", {}).items()},
            "forecast_generated_at": snapshot.get("generated_at"),
        }
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise HTTPException(503, "อ่านข้อมูล UV ไม่สำเร็จ กรุณาตรวจ registry แล้วลองใหม่") from error


class DeploymentAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["promote", "rollback"]
    version: str = Version
    expected_active: str = Version


@router.post("")
def deploy(
    payload: DeploymentAction, response: Response, actor: str = Depends(require_model_reviewer)
) -> dict:
    response.headers["Cache-Control"] = "no-store"
    try:
        if payload.action == "promote":
            gate = uv_mlops.review_candidate(payload.version)
            if gate["base_version"] != payload.expected_active:
                raise ValueError("Candidate base version changed")
            uv_mlops.promote(payload.version, actor)
        else:
            uv_mlops.rollback(
                actor, expected_active=payload.expected_active, expected_target=payload.version
            )
    except FileExistsError as error:
        raise HTTPException(409, "มีงาน UV กำลังทำงาน กรุณารอสักครู่แล้วลองใหม่") from error
    except (ValueError, KeyError, TypeError) as error:
        raise HTTPException(
            409, "เปลี่ยนรุ่นไม่ได้: รุ่นหรือผลประเมินอาจเปลี่ยน กรุณาโหลดข้อมูลใหม่และตรวจ gate"
        ) from error
    except OSError as error:
        raise HTTPException(503, "เข้าถึงข้อมูลหรือสร้าง forecast ไม่สำเร็จ กรุณาตรวจบริการ UV") from error
    return {"active": lifecycle.deployment()["active"], "actor": actor}
