"""AutoLead Agent 完整演示测试脚本"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

import httpx

BASE = "http://127.0.0.1:8000"

def test():
    client = httpx.Client(base_url=BASE, timeout=30)

    # 步骤1: 车型推荐
    print("=" * 50)
    r1 = client.post("/api/chat/message", json={
        "session_id": "", "customer_id": "",
        "message": "我想买20万以内家用SUV，省油一点"
    }).json()
    print(f"[1] 意图={r1['current_intent']}, 工具={len(r1['tool_trace'])}次")
    assert r1['current_intent'] == 'car_recommendation'
    assert len(r1['tool_trace']) >= 2
    sid, cid = r1.get("session_id",""), r1.get("customer_id","")
    print(f"    OK - 会话={sid}, 客户={cid}")

    # 步骤2: 车型对比
    r2 = client.post("/api/chat/message", json={
        "session_id": sid, "customer_id": cid,
        "message": "宋PLUS和锋兰达怎么选？"
    }).json()
    print(f"[2] 意图={r2['current_intent']}, 工具={len(r2['tool_trace'])}次")
    tools2 = [t['tool_name'] for t in r2.get('tool_trace',[])]
    print(f"    工具: {tools2}")
    assert len(r2['tool_trace']) >= 1

    # 步骤3: 分期试算
    r3 = client.post("/api/chat/message", json={
        "session_id": sid, "customer_id": cid,
        "message": "首付30%贷款3年月供多少？"
    }).json()
    print(f"[3] 意图={r3['current_intent']}, 工具={len(r3['tool_trace'])}次")
    print(f"    工具: {[t['tool_name'] for t in r3.get('tool_trace',[])]}")

    # 步骤4: 库存查询
    r4 = client.post("/api/chat/message", json={
        "session_id": sid, "customer_id": cid,
        "message": "广州有现车吗？"
    }).json()
    print(f"[4] 意图={r4['current_intent']}, 工具={len(r4['tool_trace'])}次")
    print(f"    工具: {[t['tool_name'] for t in r4.get('tool_trace',[])]}")

    # 步骤5: 试驾预约
    r5 = client.post("/api/chat/message", json={
        "session_id": sid, "customer_id": cid,
        "message": "帮我预约周六下午试驾宋PLUS DM-i"
    }).json()
    print(f"[5] 意图={r5['current_intent']}, 工具={len(r5['tool_trace'])}次")
    print(f"    工具: {[t['tool_name'] for t in r5.get('tool_trace',[])]}")

    # 客户画像验证
    print("\n" + "=" * 50)
    try:
        profile = client.get(f"/api/customers/{cid}/profile").json()
        print(f"客户画像: 预算={profile.get('budget')}, "
              f"线索等级={profile.get('lead_level')}, "
              f"跟进摘要={profile.get('follow_up_summary','')[:50]}")
    except Exception as e:
        print(f"画像获取失败: {e}")

    print("\n" + "=" * 10 + " 演示测试完成! " + "=" * 10)

if __name__ == "__main__":
    test()
