"""
AutoLead Agent — FastAPI 主应用入口
"""

import os
import sys

# 确保 backend 包可导入
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from backend.config import settings
from backend.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库"""
    print(f"[{settings.APP_NAME}] 正在启动...")
    init_db()
    print(f"[{settings.APP_NAME}] 数据库初始化完成")

    # 导入并运行种子数据
    from backend.seed_data import seed_all
    seed_all()

    yield
    print(f"[{settings.APP_NAME}] 正在关闭...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS 配置 — 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── 注册 API 路由 ──────────────────────────────

from backend.api.chat import router as chat_router
from backend.api.customers import router as customer_router
from backend.api.cars import router as car_router
from backend.api.finance import router_finance, router_inventory, router_appointments
from backend.api.knowledge import router as knowledge_router

app.include_router(chat_router)
app.include_router(customer_router)
app.include_router(car_router)
app.include_router(router_finance)
app.include_router(router_inventory)
app.include_router(router_appointments)
app.include_router(knowledge_router)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "llm_provider": settings.LLM_PROVIDER,
        "llm_model": settings.OPENAI_MODEL,
    }

# ─── 挂载前端静态文件 ───────────────────────────

frontend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


# ─── 健康检查 ───────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
