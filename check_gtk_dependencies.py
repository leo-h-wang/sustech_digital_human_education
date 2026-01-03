"""检查GTK依赖完整性"""
import os
import sys
from pathlib import Path

def check_gtk_installation(gtk_bin_path):
    """检查GTK bin目录中的必需文件"""
    print("="*60)
    print("GTK 依赖完整性检查")
    print("="*60)
    
    # GTK和其依赖的关键DLL文件
    required_dlls = [
        # GObject相关
        'libgobject-2.0-0.dll',
        'libglib-2.0-0.dll',
        'libgio-2.0-0.dll',
        'libgmodule-2.0-0.dll',
        
        # Pango相关
        'libpango-1.0-0.dll',
        'libpangocairo-1.0-0.dll',
        'libpangowin32-1.0-0.dll',
        'libpangoft2-1.0-0.dll',
        
        # Cairo相关
        'libcairo-2.dll',
        'libcairo-gobject-2.dll',
        
        # 其他必需库
        'libgdk_pixbuf-2.0-0.dll',
        'libffi-8.dll',
        'libintl-8.dll',
        'libharfbuzz-0.dll',
        'libfontconfig-1.dll',
        'libfreetype-6.dll',
        'libpng16-16.dll',
        'zlib1.dll',
        'libiconv-2.dll',
        'libexpat-1.dll',
        'libbz2-1.dll',
        'libfribidi-0.dll',
    ]
    
    gtk_path = Path(gtk_bin_path)
    
    if not gtk_path.exists():
        print(f"✗ GTK bin目录不存在: {gtk_path}")
        return False
    
    print(f"\nGTK bin目录: {gtk_path}")
    print(f"\n检查必需的DLL文件:")
    print("-"*60)
    
    missing = []
    found = []
    
    for dll in required_dlls:
        dll_path = gtk_path / dll
        if dll_path.exists():
            size = dll_path.stat().st_size
            found.append((dll, size))
            print(f"  ✓ {dll:<30} ({size:,} bytes)")
        else:
            missing.append(dll)
            print(f"  ✗ {dll:<30} [缺失]")
    
    print("\n" + "="*60)
    print(f"统计: 找到 {len(found)}/{len(required_dlls)} 个文件")
    print("="*60)
    
    if missing:
        print(f"\n❌ 缺失 {len(missing)} 个关键文件:")
        for dll in missing:
            print(f"  - {dll}")
        
        print("\n🔧 建议解决方案:")
        print("-"*60)
        print("1. 重新下载并安装GTK3 Runtime")
        print("   下载地址: https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases")
        print("   确保下载的是完整的安装程序（约50-60MB）")
        print()
        print("2. 或者尝试从其他源安装GTK（如MSYS2）:")
        print("   https://www.msys2.org/")
        print()
        print("3. 如果文件存在但仍然报错，可能是架构不匹配")
        print("   确保GTK是64位版本（与Python 64位匹配）")
        
        return False
    else:
        print("\n✓ 所有必需文件都已找到")
        print("\n❓ 如果仍然出错，可能的原因:")
        print("  1. DLL架构不匹配（32位 vs 64位）")
        print("  2. Visual C++ Redistributable缺失")
        print("  3. 需要重启计算机使PATH生效")
        return True


def check_vcredist():
    """检查Visual C++ Redistributable"""
    print("\n" + "="*60)
    print("Visual C++ Redistributable 检查")
    print("="*60)
    
    # 检查常见的MSVC运行时DLL
    system32 = Path(os.environ.get('SystemRoot', 'C:\\Windows')) / 'System32'
    
    vcredist_dlls = [
        'vcruntime140.dll',
        'msvcp140.dll',
        'ucrtbase.dll',
    ]
    
    print("\n检查系统运行时库:")
    all_found = True
    for dll in vcredist_dlls:
        dll_path = system32 / dll
        if dll_path.exists():
            print(f"  ✓ {dll}")
        else:
            print(f"  ✗ {dll} [缺失]")
            all_found = False
    
    if not all_found:
        print("\n❌ 缺少Visual C++ Redistributable")
        print("请下载并安装:")
        print("  https://aka.ms/vs/17/release/vc_redist.x64.exe")
    else:
        print("\n✓ Visual C++ Redistributable 已安装")
    
    return all_found


def main():
    gtk_bin = r"E:\GTK3-Runtime Win64\bin"
    
    print("\n" + "="*60)
    print("WeasyPrint GTK 依赖诊断工具")
    print("="*60)
    print(f"\nPython版本: {sys.version}")
    print(f"Python架构: {sys.maxsize > 2**32 and '64位' or '32位'}")
    
    # 检查GTK安装
    gtk_ok = check_gtk_installation(gtk_bin)
    
    # 检查VC++ Redistributable
    vcredist_ok = check_vcredist()
    
    print("\n" + "="*60)
    if gtk_ok and vcredist_ok:
        print("✓ 基本检查通过")
        print("="*60)
        print("\n如果WeasyPrint仍然失败，请尝试:")
        print("  1. 重启计算机")
        print("  2. 使用Dependency Walker检查DLL依赖")
        print("     (https://www.dependencywalker.com/)")
    else:
        print("❌ 发现问题，请按照上述建议修复")
        print("="*60)


if __name__ == "__main__":
    main()

