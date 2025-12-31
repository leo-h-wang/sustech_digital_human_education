"""南科大高等数学数字人教学项目 - FastAPI 主入口"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import uvicorn
import os
from dotenv import load_dotenv

from app.routers import api, web

# 加载环境变量
load_dotenv()

app = FastAPI(
    title="南科大高等数学数字人教学工具",
    description="AI 解题与课件生成系统",
    version="0.1.0"
)

# 注册路由
app.include_router(api.router)
app.include_router(web.router)

# 静态文件服务（如果需要）
# app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def root():
    """根路径重定向到主页"""
    return RedirectResponse(url="/")


@app.on_event("startup")
async def startup_event():
    """启动事件"""
    print("=" * 60)
    print("🚀 南科大高等数学数字人教学工具已启动")
    print("=" * 60)
    print(f"📝 API 文档: http://localhost:8000/docs")
    print(f"🌐 Web 界面: http://localhost:8000/")
    print("=" * 60)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
