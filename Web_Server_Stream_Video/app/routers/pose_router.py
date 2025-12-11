from fastapi import APIRouter
from services import state

router = APIRouter()


@router.get('/pose')
async def pose_endpoint():
    with state.frame_lock:
        res = state.latest_result.copy() if state.latest_result else None

    if res is None:
        return {"persona_detectada": False, "pose": None}

    return {"persona_detectada": res["persona_real"], "pose": res["pose"]}
