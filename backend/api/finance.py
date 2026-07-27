"""
金融/分期试算 API + 库存查询 API + 试驾预约 API
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.agent.tools import loan_calculator_tool, inventory_tool, test_drive_tool
from backend.schemas.schemas import (
    LoanRequest, LoanResponse,
    InventoryQuery, InventoryResponse, InventoryItem,
    AppointmentCreate, AppointmentResponse,
)

router_finance = APIRouter(prefix="/api/finance", tags=["金融"])
router_inventory = APIRouter(prefix="/api/inventory", tags=["库存"])
router_appointments = APIRouter(prefix="/api/appointments", tags=["试驾预约"])


@router_finance.post("/calculate", response_model=LoanResponse)
def calculate_loan(req: LoanRequest):
    """分期试算"""
    result = loan_calculator_tool(
        car_price=req.car_price,
        down_payment_rate=req.down_payment_rate,
        years=req.years,
        annual_rate=req.annual_rate,
    )
    return LoanResponse(**result)


@router_inventory.get("", response_model=InventoryResponse)
def query_inventory(model: str = "", city: str = "", color: str = "", db: Session = Depends(get_db)):
    """查询库存"""
    result = inventory_tool(model=model, city=city, color=color)
    items = []
    for r in result.get("results", []):
        items.append(InventoryItem(**r))
    return InventoryResponse(results=items)


@router_appointments.post("", response_model=AppointmentResponse)
def create_appointment(req: AppointmentCreate):
    """创建试驾预约"""
    result = test_drive_tool(
        customer_name=req.customer_name,
        phone=req.phone,
        model=req.model,
        store=req.store,
        appointment_time=req.appointment_time,
    )
    return AppointmentResponse(
        appointment_id=result.get("appointment_id", ""),
        status=result.get("status", "失败"),
        message=result.get("message", ""),
    )


@router_appointments.get("", response_model=list[dict])
def list_appointments(db: Session = Depends(get_db)):
    """列出所有试驾预约"""
    from backend.models.models import TestDriveAppointment, Customer, Car
    results = (
        db.query(TestDriveAppointment, Customer, Car)
        .join(Customer, TestDriveAppointment.customer_id == Customer.id)
        .join(Car, TestDriveAppointment.car_id == Car.id)
        .order_by(TestDriveAppointment.created_at.desc())
        .all()
    )
    return [
        {
            "appointment_id": a.appointment_id,
            "customer_name": c.name,
            "phone": c.phone,
            "model": car.model,
            "brand": car.brand,
            "store_name": a.store_name,
            "appointment_time": a.appointment_time,
            "status": a.status,
        }
        for a, c, car in results
    ]
