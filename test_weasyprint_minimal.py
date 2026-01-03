"""最小化WeasyPrint测试 - 直接测试能否工作"""
import sys

print("="*60)
print("最小化 WeasyPrint 测试")
print("="*60)

# 测试1: 导入
print("\n步骤1: 导入 WeasyPrint...")
try:
    from weasyprint import HTML
    print("✓ WeasyPrint 导入成功")
except Exception as e:
    print(f"✗ 导入失败: {e}")
    sys.exit(1)

# 测试2: 创建简单HTML
print("\n步骤2: 创建简单的HTML对象...")
try:
    html_string = """
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body>
        <h1>测试文档</h1>
        <p>这是一个测试段落。</p>
    </body>
    </html>
    """
    html = HTML(string=html_string)
    print("✓ HTML 对象创建成功")
except Exception as e:
    print(f"✗ HTML对象创建失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 测试3: 生成PDF
print("\n步骤3: 生成PDF文件...")
try:
    output_file = "test_minimal.pdf"
    html.write_pdf(output_file)
    import os
    file_size = os.path.getsize(output_file)
    print(f"✓ PDF 生成成功!")
    print(f"  文件: {output_file}")
    print(f"  大小: {file_size:,} bytes")
except Exception as e:
    print(f"✗ PDF生成失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("🎉 所有测试通过！WeasyPrint 完全可用！")
print("="*60)
print("\n现在可以运行完整测试:")
print("  uv run python test_pdf_mathml.py")

