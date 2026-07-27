"""
AutoLead Agent 种子数据
初始化车型、库存、知识库、演示客户
"""

import json
from backend.database import SessionLocal, init_db
from backend.models.models import Car, Inventory, KnowledgeDocument, KnowledgeChunk, Customer, CustomerProfile

# ─── 车型数据 ────────────────────────────────────

SEED_CARS = [
    {
        "brand": "比亚迪",
        "model": "宋PLUS DM-i",
        "price": 169800,
        "car_type": "SUV",
        "energy_type": "插电混动",
        "seat_count": 5,
        "fuel_consumption": "4.4 L/100km",
        "range_km": "1200km（综合）",
        "highlights": ["油耗低", "空间大", "配置丰富", "适合家用", "刀片电池"],
    },
    {
        "brand": "比亚迪",
        "model": "秦PLUS DM-i",
        "price": 99800,
        "car_type": "轿车",
        "energy_type": "插电混动",
        "seat_count": 5,
        "fuel_consumption": "3.8 L/100km",
        "range_km": "1245km（综合）",
        "highlights": ["性价比高", "油耗极低", "入门门槛低", "城市通勤首选"],
    },
    {
        "brand": "丰田",
        "model": "锋兰达双擎",
        "price": 179800,
        "car_type": "SUV",
        "energy_type": "混动",
        "seat_count": 5,
        "fuel_consumption": "4.5 L/100km",
        "range_km": "",
        "highlights": ["丰田品质", "油耗低", "保值率高", "可靠性强"],
    },
    {
        "brand": "本田",
        "model": "CR-V e:HEV",
        "price": 229800,
        "car_type": "SUV",
        "energy_type": "混动",
        "seat_count": 5,
        "fuel_consumption": "5.0 L/100km",
        "range_km": "",
        "highlights": ["空间宽敞", "品质可靠", "舒适性好", "品牌口碑好"],
    },
    {
        "brand": "哈弗",
        "model": "枭龙MAX",
        "price": 189800,
        "car_type": "SUV",
        "energy_type": "插电混动",
        "seat_count": 5,
        "fuel_consumption": "5.5 L/100km",
        "range_km": "1000km（综合）",
        "highlights": ["四驱", "配置丰富", "空间大", "性价比高"],
    },
    {
        "brand": "吉利",
        "model": "星越L",
        "price": 167800,
        "car_type": "SUV",
        "energy_type": "燃油",
        "seat_count": 5,
        "fuel_consumption": "7.8 L/100km",
        "range_km": "",
        "highlights": ["豪华内饰", "动力强劲", "科技配置丰富", "CMA架构"],
    },
    {
        "brand": "特斯拉",
        "model": "Model Y",
        "price": 249900,
        "car_type": "SUV",
        "energy_type": "纯电",
        "seat_count": 5,
        "fuel_consumption": "",
        "range_km": "554km（CLTC）",
        "highlights": ["智能驾驶", "纯电体验", "品牌影响力", "超充网络"],
    },
    {
        "brand": "小鹏",
        "model": "小鹏G6",
        "price": 209900,
        "car_type": "SUV",
        "energy_type": "纯电",
        "seat_count": 5,
        "fuel_consumption": "",
        "range_km": "580km（CLTC）",
        "highlights": ["XNGP智能驾驶", "超快充", "智能座舱", "性价比突出"],
    },
]

# ─── 库存数据 ────────────────────────────────────

SEED_INVENTORIES = [
    {"model": "宋PLUS DM-i", "city": "广州", "store": "广州天河体验店", "color": "白色", "stock": 5, "delivery": "3天内可提车"},
    {"model": "宋PLUS DM-i", "city": "广州", "store": "广州天河体验店", "color": "灰色", "stock": 3, "delivery": "7天内可提车"},
    {"model": "宋PLUS DM-i", "city": "广州", "store": "广州白云店", "color": "白色", "stock": 2, "delivery": "7天内可提车"},
    {"model": "锋兰达双擎", "city": "广州", "store": "广州天河体验店", "color": "白色", "stock": 3, "delivery": "5天内可提车"},
    {"model": "秦PLUS DM-i", "city": "广州", "store": "广州天河体验店", "color": "白色", "stock": 8, "delivery": "2天内可提车"},
    {"model": "枭龙MAX", "city": "广州", "store": "广州天河体验店", "color": "黑色", "stock": 1, "delivery": "7天内可提车"},
    {"model": "Model Y", "city": "广州", "store": "广州天河体验店", "color": "白色", "stock": 2, "delivery": "2周内可提车"},
    {"model": "星越L", "city": "广州", "store": "广州白云店", "color": "白色", "stock": 4, "delivery": "3天内可提车"},
]

# ─── 知识库数据 ──────────────────────────────────

SEED_KNOWLEDGE = [
    {
        "title": "宋PLUS DM-i 车型配置说明",
        "doc_type": "car_config",
        "content": """比亚迪宋PLUS DM-i 是一款插电混动SUV，搭载比亚迪超级混动DM-i系统。
核心配置：1.5L 骁云高效发动机 + EHS电混系统，综合功率可达145kW。
油耗表现：WLTC综合油耗4.4L/100km，综合续航可达1200公里。
空间表现：长宽高4705×1890×1680mm，轴距2765mm，后排空间宽敞，适合家用。
安全配置：搭载刀片电池，L2级智能驾驶辅助系统，6安全气囊。
价格区间：15.48万-21.88万，首任车主享三电终身质保。
适合人群：城市通勤、家庭用车、注重油耗和空间的消费者。""",
    },
    {
        "title": "锋兰达双擎 车型配置说明",
        "doc_type": "car_config",
        "content": """丰田锋兰达双擎是一款油电混动SUV，搭载丰田第五代THS混动系统。
核心配置：2.0L混动系统，综合功率144kW，E-CVT变速箱。
油耗表现：WLTC综合油耗4.5L/100km。
空间表现：长宽高4485×1825×1620mm，轴距2640mm。
安全配置：Toyota Safety Sense智驾系统，7安全气囊。
价格区间：17.98万-21.98万。
适合人群：注重品牌保值率、可靠性和低油耗的消费者。""",
    },
    {
        "title": "混动SUV车型选购指南",
        "doc_type": "sales_script",
        "content": """混动SUV选购关注要点：
1. 能耗：插电混动日常可纯电通勤，综合油耗更低；油电混动不用充电，使用更方便。
2. 空间：有小孩的家庭建议关注后排空间和后备箱容量，建议带家人实际试乘。
3. 预算：20万以内首选宋PLUS DM-i（性价比高），20万以上可看CR-V混动或Model Y。
4. 充电条件：有家用充电桩可优先考虑插电混动或纯电。
5. 保值率：丰田、本田混动车型保值率在行业内领先。
6. 使用成本：纯电 ≈ 插混 < 混动 < 燃油（综合成本）。""",
    },
    {
        "title": "分期购车常见问题",
        "doc_type": "policy",
        "content": """分期购车常见问题解答：
Q：首付最低多少？
A：一般最低30%，部分品牌有低首付方案（20%起）。
Q：贷款期限多久？
A：常见1-5年，3年最普遍。
Q：利率多少？
A：厂家金融常有免息或低息方案，银行车贷年利率约4%-6%。
Q：月供怎么算？
A：月供 = [贷款本金 × 月利率 × (1+月利率)^期数] / [(1+月利率)^期数 - 1]。
Q：提前还款有违约金吗？
A：大部分银行满一年后可提前还款无违约金，具体看合同。""",
    },
    {
        "title": "试驾预约流程",
        "doc_type": "policy",
        "content": """试驾预约流程：
1. 客户确认意向车型和门店
2. 销售顾问登记客户姓名、手机号、意向车型
3. 确认试驾时间（建议提前1-2天预约）
4. 预约成功后发送提醒短信
5. 试驾当天：客户出示驾照 → 签署试驾协议 → 陪驾讲解 → 试驾体验
6. 试驾后跟进：了解客户感受，解答疑问，推进购车决策
试驾注意事项：携带本人有效驾照，试驾全程有专业顾问陪同。""",
    },
    {
        "title": "竞品对比：宋PLUS DM-i vs 锋兰达双擎",
        "doc_type": "competitor",
        "content": """宋PLUS DM-i vs 锋兰达双擎对比分析：
价格：宋PLUS 15.48-21.88万 vs 锋兰达 17.98-21.98万
能源：插电混动（可纯电） vs 油电混动（不充电）
油耗：4.4L vs 4.5L（均为亏电/综合油耗）
空间：宋PLUS全面领先（车长4705mm vs 4485mm）
动力：宋PLUS 145kW vs 锋兰达 144kW 表现相当
配置：宋PLUS更丰富（大屏、全景天窗、L2驾驶辅助）
品牌：比亚迪新能源领导品牌 vs 丰田传统合资大厂
保值率：丰田保值率更高
适合人群：注重空间和性价比选宋PLUS；注重品牌和保值选锋兰达""",
    },
    {
        "title": "价格异议处理话术",
        "doc_type": "sales_script",
        "content": """价格异议处理话术：
客户觉得贵：'我理解您对价格的关注。这款车的性价比其实很高，同级别混动SUV中，它的综合配置和油耗表现都是领先的。而且现在还有置换补贴和金融免息方案，综合下来非常划算。'
客户等优惠：'目前已经是厂家直销价，价格非常透明。早买早享受，现在订车还可以享受赠品礼包。'
客户对比竞品：'每款车各有优势，我帮您分析过对比数据，这款车在您关注的几个方面都更符合您的需求。'""",
    },
    {
        "title": "比亚迪宋PLUS DM-i 优惠政策",
        "doc_type": "policy",
        "content": """当前优惠政策（2026年7月）：
1. 置换补贴：同品牌置换享8000元补贴，他品置换享5000元
2. 金融方案：首付30%起，2年0息（限指定银行）
3. 充电桩赠送：免费赠送家用充电桩（价值3000元）
4. 首任车主三电终身质保
5. 赠送随车精品礼包（脚垫、玻璃膜、行车记录仪）
以上优惠可叠加使用，具体以门店实际政策为准。""",
    },
]

# ─── 演示客户数据 ────────────────────────────────

SEED_CUSTOMERS = [
    {
        "name": "张先生",
        "phone": "13800000001",
        "city": "广州",
        "profile": {
            "budget": "18-22万",
            "car_type": "SUV",
            "energy_type": "插电混动",
            "usage": "家用",
            "concerns": ["油耗", "空间", "安全性"],
            "intent_models": ["宋PLUS DM-i", "锋兰达双擎"],
            "purchase_time": "1个月内",
            "lead_level": "高意向",
            "follow_up_summary": "客户关注混动SUV，预算20万左右，有小孩，已咨询月供和库存，意向较高。",
        },
    },
    {
        "name": "李女士",
        "phone": "13800000002",
        "city": "广州",
        "profile": {
            "budget": "15万以内",
            "car_type": "轿车",
            "energy_type": "混动",
            "usage": "家用",
            "concerns": ["油耗", "性价比"],
            "intent_models": ["秦PLUS DM-i"],
            "purchase_time": "3个月内",
            "lead_level": "中意向",
            "follow_up_summary": "客户想买混动轿车用于通勤，关注油耗和性价比。",
        },
    },
]


def seed_all():
    """初始化所有种子数据"""
    db = SessionLocal()
    try:
        # 检查是否已有数据
        if db.query(Car).count() > 0:
            print("[Seed] 数据库中已有数据，跳过种子数据")
            return

        print("[Seed] 开始初始化种子数据...")

        # 导入车型
        car_map = {}
        for car_data in SEED_CARS:
            car = Car(**car_data)
            db.add(car)
            db.flush()
            car_map[car.model] = car.id
        print(f"[Seed] 已导入 {len(SEED_CARS)} 款车型")

        # 导入库存
        for inv_data in SEED_INVENTORIES:
            car_id = car_map.get(inv_data["model"])
            if car_id:
                inv = Inventory(
                    car_id=car_id,
                    city=inv_data["city"],
                    store_name=inv_data["store"],
                    color=inv_data["color"],
                    stock_count=inv_data["stock"],
                    delivery_time=inv_data["delivery"],
                )
                db.add(inv)
        print(f"[Seed] 已导入 {len(SEED_INVENTORIES)} 条库存记录")

        # 导入知识库
        for doc_data in SEED_KNOWLEDGE:
            doc = KnowledgeDocument(
                title=doc_data["title"],
                doc_type=doc_data["doc_type"],
                content=doc_data["content"],
            )
            db.add(doc)
            db.flush()

            # 简单分块
            paragraphs = [p.strip() for p in doc_data["content"].split("\n") if p.strip()]
            for i, para in enumerate(paragraphs):
                chunk = KnowledgeChunk(
                    document_id=doc.id,
                    chunk_text=para,
                    chunk_metadata={"chunk_index": i, "title": doc_data["title"]},
                )
                db.add(chunk)
        print(f"[Seed] 已导入 {len(SEED_KNOWLEDGE)} 篇知识文档")

        # 导入演示客户
        for cust_data in SEED_CUSTOMERS:
            customer = Customer(
                name=cust_data["name"],
                phone=cust_data["phone"],
                city=cust_data.get("city", ""),
            )
            db.add(customer)
            db.flush()

            profile_data = cust_data["profile"]
            profile = CustomerProfile(
                customer_id=customer.id,
                **profile_data,
            )
            db.add(profile)
        print(f"[Seed] 已导入 {len(SEED_CUSTOMERS)} 个演示客户")

        db.commit()
        print("[Seed] 种子数据初始化完成")

    except Exception as e:
        db.rollback()
        print(f"[Seed Error] {e}")
    finally:
        db.close()
