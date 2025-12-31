"""Web 界面路由"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os

router = APIRouter(tags=["web"])

# 确保模板目录存在
template_dir = "app/templates"
if os.path.exists(template_dir):
    templates = Jinja2Templates(directory=template_dir)
else:
    templates = None


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页"""
    if templates is None:
        # 如果模板目录不存在，返回简单的 HTML
        html_content = """
        <!DOCTYPE html>
        <html>
        <head><title>模板未找到</title></head>
        <body><h1>请确保 app/templates/index.html 文件存在</h1></body>
        </html>
        """
        return HTMLResponse(content=html_content)
    return templates.TemplateResponse("index.html", {"request": request})

