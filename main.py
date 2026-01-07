"""南科大高等数学数字人教学项目 - FastAPI 主入口"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, Response
import uvicorn
import os
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

from app.routers import api, web

# 加载环境变量
load_dotenv()

# 配置日志系统
def setup_logging():
    """配置日志系统"""
    # 获取项目根目录（main.py 所在目录）
    project_root = Path(__file__).parent.absolute()
    
    # 创建 logs 目录（使用绝对路径）
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # 日志文件名（按日期）
    log_file = log_dir / f"app_{datetime.now().strftime('%Y%m%d')}.log"
    
    # 确保日志文件可以被创建和写入
    try:
        # 测试写入权限
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"日志系统初始化于: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"日志文件路径: {log_file}\n")
            f.write(f"{'='*60}\n")
    except Exception as e:
        print(f"⚠️  警告：无法写入日志文件 {log_file}: {e}")
        # 如果无法写入，只使用控制台日志
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
            handlers=[logging.StreamHandler()]
        )
        return None
    
    # 配置日志格式
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"
    
    # 配置日志级别（从环境变量读取，默认 INFO）
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # 创建一个自定义的 FileHandler，每次写入后立即刷新
    class ImmediateFlushFileHandler(logging.FileHandler):
        def emit(self, record):
            super().emit(record)
            self.flush()
    
    # 配置日志
    file_handler = ImmediateFlushFileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(getattr(logging, log_level, logging.INFO))
    
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level, logging.INFO))
    
    # 设置格式
    formatter = logging.Formatter(log_format, datefmt=date_format)
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level, logging.INFO))
    root_logger.handlers = []  # 清除现有处理器
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # 过滤掉 watchfiles 的日志（uvicorn 自动重载功能产生的噪音）
    watchfiles_logger = logging.getLogger("watchfiles")
    watchfiles_logger.setLevel(logging.WARNING)  # 只显示警告和错误
    
    return log_file

# 初始化日志
log_file = setup_logging()
logger = logging.getLogger(__name__)

# 测试日志写入（确保文件能被创建）
if log_file:
    logger.info(f"✅ 日志系统已初始化，日志文件: {log_file}")
    # 强制刷新所有处理器
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.FileHandler):
            handler.flush()
else:
    logger.warning("⚠️  日志文件初始化失败，仅使用控制台输出")

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


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """返回空 favicon 避免 404 错误"""
    return Response(status_code=204)


@app.get("/")
async def root():
    """根路径重定向到主页"""
    return RedirectResponse(url="/")


@app.on_event("startup")
async def startup_event():
    """启动事件"""
    logger.info("=" * 60)
    logger.info("🚀 南科大高等数学数字人教学工具已启动")
    logger.info("=" * 60)
    logger.info(f"📝 API 文档: http://localhost:8000/docs")
    logger.info(f"🌐 Web 界面: http://localhost:8000/")
    if log_file:
        logger.info(f"📋 日志文件: {log_file}")
        logger.info(f"📋 日志目录: {log_file.parent}")
    logger.info("=" * 60)
    
    # 初始化 LLM 客户端以显示模型信息
    try:
        from app.llm_providers.factory import create_llm_client
        llm_client = create_llm_client()
        logger.info(f"🤖 LLM 提供商: {llm_client.get_provider_name()}")
    except Exception as e:
        logger.warning(f"⚠️  无法初始化 LLM 客户端: {e}")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
