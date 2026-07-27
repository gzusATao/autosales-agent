"""
车型 API
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.models import Car
from backend.schemas.schemas import CarItem, CompareRequest, CompareResponse, CompareResult

router = APIRouter(prefix="/api/cars", tags=["车型"])


@router.get("", response_model=list[CarItem])
def list_cars(db: Session = Depends(get_db)):
    """获取所有车型"""
    cars = db.query(Car).all()
    return [
        CarItem(
            id=c.id,
            brand=c.brand,
            model=c.model,
            price=c.price,
            car_type=c.car_type,
            energy_type=c.energy_type,
            seat_count=c.seat_count,
            fuel_consumption=c.fuel_consumption,
            range_km=c.range_km,
            highlights=c.highlights or [],
        )
        for c in cars
    ]


@router.post("/compare", response_model=CompareResponse)
def compare_cars(req: CompareRequest, db: Session = Depends(get_db)):
    """对比多款车型（API 模式，直接查库）"""
    from backend.agent.tools import compare_car_tool
    result = compare_car_tool(req.models)
    cars = result.get("cars", [])
    return CompareResponse(
        cars=[
            CompareResult(**c)
            for c in cars
        ]
    )
