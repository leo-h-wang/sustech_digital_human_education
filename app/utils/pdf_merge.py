"""PDF 合并工具"""
from io import BytesIO
from typing import List
try:
    from PyPDF2 import PdfReader, PdfWriter
except ImportError:
    # 如果 PyPDF2 不可用，使用 pypdf（PyPDF2 的新版本）
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        raise ImportError("需要安装 PyPDF2 或 pypdf 库才能使用 PDF 合并功能")


def merge_pdfs(pdf_bytes_list: List[BytesIO]) -> BytesIO:
    """
    合并多个 PDF 文件
    
    Args:
        pdf_bytes_list: PDF 字节流列表
        
    Returns:
        合并后的 PDF 字节流
    """
    writer = PdfWriter()
    
    for pdf_bytes in pdf_bytes_list:
        pdf_bytes.seek(0)  # 确保从开头读取
        reader = PdfReader(pdf_bytes)
        for page in reader.pages:
            writer.add_page(page)
    
    merged_pdf = BytesIO()
    writer.write(merged_pdf)
    merged_pdf.seek(0)
    
    return merged_pdf

