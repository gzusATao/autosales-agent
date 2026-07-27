"""
客户/线索 API
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.memory.memory import LongTermMemory
from backend.schemas.schemas import CustomerProfileResponse, LeadItem

router = APIRouter(prefix="/api", tags=["客户"])


@router.get("/customers/{customer_id}/profile", response_model=CustomerProfileResponse)
def get_customer_profile(customer_id: int):
    """获取客户画像"""
    profile = LongTermMemory.get_profile(customer_id)
    if not profile:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="客户不存在")

    from datetime import datetime
    return CustomerProfileResponse(
        id=profile["id"],
        name=profile.get("name", ""),
        phone=profile.get("phone", ""),
        city=profile.get("city", ""),
        budget=profile.get("budget", ""),
        car_type=profile.get("car_type", ""),
        energy_type=profile.get("energy_type", ""),
        usage=profile.get("usage", ""),
        concerns=profile.get("concerns", []),
        intent_models=profile.get("intent_models", []),
        purchase_time=profile.get("purchase_time", ""),
        lead_level=profile.get("lead_level", ""),
        follow_up_summary=profile.get("follow_up_summary", ""),
        created_at=datetime.now(),
        updated_at=datetime.fromisoformat(profile.get("updated_at", datetime.now().isoformat())) if profile.get("updated_at") else datetime.now(),
    )


@router.get("/leads", response_model=list[LeadItem])
def get_leads():
    """获取所有线索列表"""
    leads = LongTermMemory.get_all_leads()
    result = []
    for l in leads:
        from datetime import datetime
        try:
            last_time = datetime.fromisoformat(l["last_contact_time"]) if l.get("last_contact_time") else None
        except (ValueError, TypeError):
            last_time = None
        result.append(LeadItem(
            id=l["id"],
            customer_id=l["id"],
            name=l.get("name", ""),
            phone=l.get("phone", ""),
            budget=l.get("budget", ""),
            intent_models=l.get("intent_models", []),
            lead_level=l.get("lead_level", ""),
            purchase_time=l.get("purchase_time", ""),
            follow_up_summary=l.get("follow_up_summary", ""),
            last_contact_time=last_time,
        ))
    return result
