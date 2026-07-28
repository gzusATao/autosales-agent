"""
Agent 工具函数
封装车型查询、配置对比、分期试算、库存查询、试驾预约、线索保存、RAG检索
"""

import json
import datetime
from typing import Optional

from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models.models import Car, Inventory, Customer, CustomerProfile, TestDriveAppointment, KnowledgeChunk
from backend.rag.rag import simple_vector_search


# ─── 工具函数 ────────────────────────────────────


def search_car_tool(
    budget_max: float = 0,
    car_type: str = "",
    energy_type: str = "",
    usage: str = "",
    top_k: int = 5,
) -> dict:
    """
    根据预算、车型级别、能源偏好推荐车型
    """
    db: Session = SessionLocal()
    try:
        query = db.query(Car)

        if budget_max > 0:
            query = query.filter(Car.price <= budget_max)
        if car_type:
            query = query.filter(Car.car_type == car_type)
        if energy_type:
            query = query.filter(Car.energy_type.like(f"%{energy_type}%"))

        cars = query.limit(top_k).all()

        return {
            "cars": [
                {
                    "id": c.id,
                    "model": c.model,
                    "brand": c.brand,
                    "price": c.price,
                    "energy_type": c.energy_type,
                    "car_type": c.car_type,
                    "fuel_consumption": c.fuel_consumption,
                    "seat_count": c.seat_count,
                    "highlights": c.highlights or [],
                }
                for c in cars
            ]
        }
    finally:
        db.close()


def compare_car_tool(models: list[str]) -> dict:
    """
    对比多款车型
    """
    db: Session = SessionLocal()
    try:
        cars = db.query(Car).filter(Car.model.in_(models)).all()

        result = []
        for c in cars:
            recommendation = _generate_recommendation(c)
            result.append({
                "model": c.model,
                "brand": c.brand,
                "price": c.price,
                "energy_type": c.energy_type,
                "fuel_consumption": c.fuel_consumption,
                "seat_count": c.seat_count,
                "highlights": c.highlights or [],
                "recommendation": recommendation,
            })

        return {"cars": result}
    finally:
        db.close()


def _generate_recommendation(car: Car) -> str:
    """根据车型特点生成推荐理由"""
    recs = []
    if car.energy_type in ("混动", "插电混动"):
        recs.append("油耗低，适合城市通勤")
    if car.car_type == "SUV":
        recs.append("空间大，适合家用")
    if car.price and car.price < 150000:
        recs.append("性价比高")
    if car.highlights:
        recs.extend(car.highlights[:2])
    return "，".join(recs[:3]) if recs else "综合表现优秀"


def loan_calculator_tool(
    car_price: float,
    down_payment_rate: float = 0.3,
    years: int = 3,
    annual_rate: float = 0.045,
    model: str = "",
) -> dict:
    """
    分期试算：首付、月供、总利息、落地价
    """
    down_payment = round(car_price * down_payment_rate, 2)
    loan_amount = round(car_price - down_payment, 2)
    monthly_rate = annual_rate / 12
    months = years * 12

    if annual_rate == 0:
        monthly_payment = round(loan_amount / months, 2)
        total_interest = 0
    else:
        monthly_payment = round(
            loan_amount * monthly_rate * (1 + monthly_rate) ** months
            / ((1 + monthly_rate) ** months - 1),
            2,
        )
        total_interest = round(monthly_payment * months - loan_amount, 2)

    estimated_total_cost = round(car_price + total_interest, 2)

    return {
        "down_payment": down_payment,
        "loan_amount": loan_amount,
        "monthly_payment": monthly_payment,
        "total_interest": total_interest,
        "estimated_total_cost": estimated_total_cost,
    }


def inventory_tool(model: str, city: str = "", color: str = "") -> dict:
    """
    查询车型库存
    """
    db: Session = SessionLocal()
    try:
        query = (
            db.query(Inventory, Car)
            .join(Car, Inventory.car_id == Car.id)
            .filter(Car.model.like(f"%{model}%"))
        )

        if city:
            query = query.filter(Inventory.city.like(f"%{city}%"))
        if color:
            query = query.filter(Inventory.color == color)

        results = query.limit(10).all()

        return {
            "results": [
                {
                    "model": car.model,
                    "brand": car.brand,
                    "price": car.price,
                    "city": inv.city,
                    "store_name": inv.store_name,
                    "color": inv.color,
                    "stock_count": inv.stock_count,
                    "delivery_time": inv.delivery_time,
                }
                for inv, car in results
            ]
        }
    finally:
        db.close()


def test_drive_tool(
    customer_name: str,
    phone: str,
    model: str,
    store: str,
    appointment_time: str,
) -> dict:
    """
    创建试驾预约
    """
    db: Session = SessionLocal()
    try:
        # 查找或创建客户
        customer = db.query(Customer).filter(Customer.phone == phone).first()
        if not customer:
            customer = Customer(name=customer_name, phone=phone)
            db.add(customer)
            db.flush()

        # 查找车型
        car = db.query(Car).filter(Car.model.like(f"%{model}%")).first()
        if not car:
            return {"appointment_id": "", "status": "失败", "message": f"未找到车型：{model}"}

        # 生成预约编号
        now = datetime.datetime.now()
        appointment_id = f"TD{now.strftime('%Y%m%d%H%M%S')}"

        appointment = TestDriveAppointment(
            appointment_id=appointment_id,
            customer_id=customer.id,
            car_id=car.id,
            store_name=store,
            appointment_time=appointment_time,
        )
        db.add(appointment)
        db.commit()

        return {
            "appointment_id": appointment_id,
            "status": "预约成功",
            "message": f"已为您预约 {store} 的 {model} 试驾，时间：{appointment_time}",
        }
    except Exception as e:
        db.rollback()
        return {"appointment_id": "", "status": "失败", "message": str(e)}
    finally:
        db.close()


def lead_save_tool(
    customer_id: int = 0,
    name: str = "",
    phone: str = "",
    budget: str = "",
    intent_models: list = None,
    concerns: list = None,
    purchase_time: str = "",
    follow_up_summary: str = "",
) -> dict:
    """
    保存客户线索和跟进摘要
    """
    if intent_models is None:
        intent_models = []
    if concerns is None:
        concerns = []

    db: Session = SessionLocal()
    try:
        customer = None
        if customer_id:
            customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer and phone:
            customer = db.query(Customer).filter(Customer.phone == phone).first()
        if not customer and name:
            customer = Customer(name=name, phone=phone)
            db.add(customer)
            db.flush()

        if not customer:
            return {"saved": False, "lead_level": "未知", "message": "无法定位客户"}

        # 更新/创建客户画像
        profile = db.query(CustomerProfile).filter(
            CustomerProfile.customer_id == customer.id
        ).first()
        if not profile:
            profile = CustomerProfile(customer_id=customer.id)
            db.add(profile)

        if budget:
            profile.budget = budget
        if intent_models:
            profile.intent_models = list(set(profile.intent_models + intent_models))
        if concerns:
            profile.concerns = list(set(profile.concerns + concerns))
        if purchase_time:
            profile.purchase_time = purchase_time
        if follow_up_summary:
            profile.follow_up_summary = follow_up_summary

        # 线索等级判定
        has_budget = bool(profile.budget)
        has_models = bool(profile.intent_models)
        has_time = bool(profile.purchase_time)

        if has_budget and has_models and has_time:
            profile.lead_level = "高意向"
        elif has_budget or has_models:
            profile.lead_level = "中意向"
        else:
            profile.lead_level = "低意向"

        db.commit()

        return {
            "saved": True,
            "lead_level": profile.lead_level,
            "customer_id": customer.id,
            "message": "客户线索已保存",
        }
    except Exception as e:
        db.rollback()
        return {"saved": False, "lead_level": "未知", "message": str(e)}
    finally:
        db.close()


def rag_search_tool(query: str, top_k: int = 5) -> dict:
    """
    检索知识库（车型知识、销售话术、优惠政策等）
    """
    try:
        docs = simple_vector_search(query, top_k=top_k)
        return {
            "docs": [
                {
                    "id": d.id,
                    "title": d.title,
                    "content": d.chunk_text[:300],
                    "doc_type": d.doc_type if hasattr(d, 'doc_type') else "general",
                    "score": d.score if hasattr(d, 'score') else 0.0,
                }
                for d in docs
            ]
        }
    except Exception as e:
        print(f"[RAG Search Error] {e}")
        return {"docs": []}


# ─── 工具注册表 ──────────────────────────────────

TOOL_REGISTRY = {
    "search_car_tool": {
        "name": "search_car_tool",
        "description": "根据预算、车型级别、能源偏好推荐车型",
        "parameters": {
            "budget_max": {"type": "number", "description": "预算上限（元）"},
            "car_type": {"type": "string", "description": "车型：SUV/轿车/MPV"},
            "energy_type": {"type": "string", "description": "能源类型：燃油/混动/纯电/插电混动"},
            "usage": {"type": "string", "description": "用途：家用/商务"},
        },
        "function": search_car_tool,
    },
    "compare_car_tool": {
        "name": "compare_car_tool",
        "description": "对比两到三款车型的配置和特点",
        "parameters": {
            "models": {"type": "array", "description": "待对比的车型名称列表", "items": {"type": "string"}},
        },
        "function": compare_car_tool,
    },
    "loan_calculator_tool": {
        "name": "loan_calculator_tool",
        "description": "计算分期购车的首付、月供和总利息",
        "parameters": {
            "car_price": {"type": "number", "description": "车价（元）"},
            "down_payment_rate": {"type": "number", "description": "首付比例，默认0.3"},
            "years": {"type": "integer", "description": "贷款年限，默认3"},
            "annual_rate": {"type": "number", "description": "年利率，默认0.045"},
        },
        "function": loan_calculator_tool,
    },
    "inventory_tool": {
        "name": "inventory_tool",
        "description": "查询车型的库存情况",
        "parameters": {
            "model": {"type": "string", "description": "车型名称"},
            "city": {"type": "string", "description": "城市"},
            "color": {"type": "string", "description": "颜色"},
        },
        "function": inventory_tool,
    },
    "test_drive_tool": {
        "name": "test_drive_tool",
        "description": "创建试驾预约记录",
        "parameters": {
            "customer_name": {"type": "string", "description": "客户姓名"},
            "phone": {"type": "string", "description": "手机号"},
            "model": {"type": "string", "description": "试驾车型"},
            "store": {"type": "string", "description": "门店"},
            "appointment_time": {"type": "string", "description": "预约时间"},
        },
        "function": test_drive_tool,
    },
    "lead_save_tool": {
        "name": "lead_save_tool",
        "description": "保存客户线索和跟进摘要",
        "parameters": {
            "customer_id": {"type": "integer", "description": "客户ID"},
            "budget": {"type": "string", "description": "预算范围"},
            "intent_models": {"type": "array", "description": "意向车型", "items": {"type": "string"}},
            "concerns": {"type": "array", "description": "关注点", "items": {"type": "string"}},
            "purchase_time": {"type": "string", "description": "购车周期"},
            "follow_up_summary": {"type": "string", "description": "跟进摘要"},
        },
        "function": lead_save_tool,
    },
    "rag_search_tool": {
        "name": "rag_search_tool",
        "description": "检索车型知识、销售话术、优惠政策等",
        "parameters": {
            "query": {"type": "string", "description": "检索关键词"},
            "top_k": {"type": "integer", "description": "返回结果数量，默认5"},
        },
        "function": rag_search_tool,
    },
}
