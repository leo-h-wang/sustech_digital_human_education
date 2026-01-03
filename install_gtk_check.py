"""检查GTK安装状态并提供安装指南"""
import sys
import os
import platform
import ctypes.util


def check_gtk_installation():
    """检查GTK库是否已安装"""
    print("="*60)
    print("GTK3 安装状态检查")
    print("="*60)
    print(f"\n操作系统: {platform.system()} {platform.release()}")
    print(f"Python版本: {sys.version.split()[0]}")
    
    # 检查是否是Windows
    is_windows = platform.system() == 'Windows'
    print(f"Windows系统: {'是' if is_windows else '否'}")
    
    if not is_windows:
        print("\n✓ 非Windows系统，通常不需要额外安装GTK")
        return True
    
    print("\n" + "-"*60)
    print("检查GTK库...")
    print("-"*60)
    
    # 需要检查的库
    required_libs = [
        'libgobject-2.0-0',
        'libpango-1.0-0',
        'libpangocairo-1.0-0',
        'libgdk_pixbuf-2.0-0',
        'libcairo-2',
    ]
    
    missing_libs = []
    found_libs = []
    
    for lib in required_libs:
        lib_path = ctypes.util.find_library(lib)
        if lib_path:
            found_libs.append((lib, lib_path))
            print(f"✓ {lib}: 已找到")
        else:
            missing_libs.append(lib)
            print(f"✗ {lib}: 未找到")
    
    print("\n" + "="*60)
    
    if missing_libs:
        print("❌ GTK库未正确安装或未添加到PATH")
        print("="*60)
        print("\n缺失的库:")
        for lib in missing_libs:
            print(f"  - {lib}")
        
        print("\n📝 安装步骤:")
        print("-"*60)
        print("1. 访问下载页面:")
        print("   https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases")
        print("\n2. 下载最新版本的安装程序 (gtk3-runtime-xxx.exe)")
        print("\n3. 运行安装程序，确保勾选 'Add to PATH' 选项")
        print("\n4. 重启终端窗口")
        print("\n5. 重新运行此脚本验证安装")
        print("\n📖 详细说明请查看: WEASYPRINT_WINDOWS_SETUP.md")
        print("="*60)
        return False
    else:
        print("✓ GTK库已正确安装")
        print("="*60)
        
        if found_libs:
            print("\n已安装的库:")
            for lib, path in found_libs[:3]:  # 只显示前几个
                print(f"  - {lib}")
        
        print("\n✓ 您可以运行 test_pdf_mathml.py 测试PDF生成")
        return True


def test_weasyprint_import():
    """测试WeasyPrint导入"""
    print("\n" + "="*60)
    print("测试 WeasyPrint 导入")
    print("="*60)
    
    try:
        import weasyprint
        print("✓ WeasyPrint 导入成功")
        print(f"  版本: {weasyprint.__version__}")
        
        # 尝试创建一个简单的HTML对象
        try:
            html = weasyprint.HTML(string="<html><body>Test</body></html>")
            print("✓ WeasyPrint HTML 对象创建成功")
            print("\n🎉 WeasyPrint 完全可用！")
            return True
        except Exception as e:
            print(f"✗ WeasyPrint HTML 对象创建失败: {e}")
            return False
            
    except ImportError as e:
        print(f"✗ WeasyPrint 未安装: {e}")
        print("\n请运行: uv pip install weasyprint")
        return False
    except Exception as e:
        print(f"✗ WeasyPrint 导入失败: {e}")
        print("\n这通常是由于GTK库缺失导致的。")
        return False


def main():
    """主函数"""
    print("\n" + "="*60)
    print("WeasyPrint 环境检查工具")
    print("="*60)
    
    # 步骤1: 检查GTK
    gtk_ok = check_gtk_installation()
    
    # 步骤2: 测试WeasyPrint
    if gtk_ok:
        weasyprint_ok = test_weasyprint_import()
        
        if weasyprint_ok:
            print("\n" + "="*60)
            print("✅ 环境检查完成 - 一切正常！")
            print("="*60)
            print("\n下一步: 运行 python test_pdf_mathml.py 生成PDF测试")
        else:
            print("\n" + "="*60)
            print("⚠️  GTK已安装但WeasyPrint仍有问题")
            print("="*60)
            print("\n可能的原因:")
            print("  1. 需要重启计算机")
            print("  2. PATH环境变量未正确设置")
            print("  3. GTK版本不兼容")
    else:
        print("\n请先安装GTK后再继续。")
    
    print()


if __name__ == "__main__":
    main()

