from fastapi import APIRouter
from services import state

router = APIRouter()


@router.get('/persona')
async def persona():
    with state.frame_lock:
        res = state.latest_result.copy() if state.latest_result else None

    if res is None:
        return {"persona_detectada": False, "pose": None}

    return {
        "persona_detectada": res["persona_real"],
        "pose": res["pose"],
        "meta": {
            "visibility_count": res.get("visibility_count"),
            "head_tilt": res.get("head_tilt"),
            "shoulder_px": res.get("shoulder_px"),
            "angle_torso_deg": res.get("angle_torso_deg")
        }
    }
