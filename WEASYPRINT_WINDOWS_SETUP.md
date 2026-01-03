# WeasyPrint Windows 安装指南

## 问题描述

在Windows上运行WeasyPrint时，您可能会遇到以下错误：
```
OSError: cannot load library 'libgobject-2.0-0': error 0x7e
```

这是因为WeasyPrint依赖GTK3运行时库，Windows系统默认不包含这些库。

## 解决方案

### 方案1：安装GTK3运行时（推荐）

#### 步骤1：下载GTK3运行时安装程序

访问以下链接下载最新版本的GTK3 Runtime安装程序：
https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases

下载文件名类似：`gtk3-runtime-3.24.xx-xxxx-xx-xx-ts-win64.exe`

#### 步骤2：运行安装程序

1. 双击下载的`.exe`文件
2. 按照安装向导的提示进行安装
3. **重要**：选择"Add to PATH"选项（添加到系统环境变量）
4. 完成安装

#### 步骤3：重启PowerShell/终端

关闭所有PowerShell窗口，重新打开一个新的终端窗口。

#### 步骤4：验证安装

运行测试脚本：
```powershell
python test_pdf_mathml.py
```

### 方案2：使用MSYS2安装GTK（开发者选项）

如果您已经安装了MSYS2，可以使用以下命令：

```bash
# 在MSYS2终端中运行
pacman -S mingw-w64-x86_64-gtk3
```

然后将MSYS2的bin目录添加到PATH：
```powershell
# 在PowerShell中运行（根据您的MSYS2安装路径调整）
$env:PATH = "C:\msys64\mingw64\bin;" + $env:PATH
```

### 方案3：使用Conda环境（如果适用）

如果您使用Conda，可以尝试：
```bash
conda install -c conda-forge weasyprint
```

Conda版本会自动处理GTK依赖。

## 验证安装成功

运行测试脚本后，您应该看到：
```
✓ PDF 生成成功！
  文件路径: test_output_mathml.pdf
  文件大小: XX.XX KB
```

打开生成的PDF文件，检查数学公式是否正确渲染为符号而非纯文本。

## 常见问题

### Q: 安装GTK后仍然报错？
A: 确保：
1. 已重启终端/PowerShell
2. GTK的bin目录已添加到PATH环境变量
3. 尝试完全重启计算机

### Q: 不想安装GTK怎么办？
A: 可以考虑使用备选方案：
- Playwright + HTML to PDF（需要安装浏览器）
- 使用云端PDF生成服务
- 在Linux/WSL环境中运行（GTK依赖更容易处理）

### Q: 企业环境无法安装GTK？
A: 联系系统管理员，或者：
1. 使用Docker容器运行（容器内预装GTK）
2. 部署到Linux服务器
3. 使用在线PDF转换服务

## 技术细节

WeasyPrint需要以下GTK组件：
- libgobject-2.0-0
- libpango-1.0-0
- libpangocairo-1.0-0
- libgdk_pixbuf-2.0-0
- libcairo-2
- libffi-8

GTK3 Runtime安装程序会自动安装所有这些依赖。

## 参考链接

- WeasyPrint官方文档：https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows
- GTK Windows Runtime：https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer
- WeasyPrint疑难解答：https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#troubleshooting

