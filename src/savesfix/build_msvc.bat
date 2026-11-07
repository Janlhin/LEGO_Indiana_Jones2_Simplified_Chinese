@echo off
REM 用 Visual Studio 的 32 位 (x86) 工具链编译 savesfix.c 为 dinput8.dll
REM 用法：双击或 cmd /c 本文件（需先安装 VS2022 构建工具）
call "C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvarsall.bat" x86
if errorlevel 1 (
  echo [!] vcvarsall.bat 失败，请确认已安装 VS2022 的"使用 C++ 的桌面开发"工作负载
  exit /b 1
)
cd /d "%~dp0"
cl /LD /O2 /utf-8 /nologo savesfix.c savesfix.def /Fe:dinput8.dll
if errorlevel 1 (
  echo [!] 编译失败
  exit /b 1
)
echo [ok] 已生成 dinput8.dll
dumpbin /exports dinput8.dll
