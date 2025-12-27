@echo off
chcp 65001 >nul

:: ========================================
:: 参数处理
:: ========================================
:: 用法: build.bat [输入文件] [输出文件]
:: 示例: build.bat main.md output.docx
::       build.bat thesis.md

set INPUT_FILE=%1
set OUTPUT_FILE=%2

:: 如果没有指定输入文件，使用默认值
if "%INPUT_FILE%"=="" (
    set INPUT_FILE=main.md
    echo ℹ️  未指定输入文件，使用默认: %INPUT_FILE%
)

:: 如果没有指定输出文件，使用默认值
if "%OUTPUT_FILE%"=="" (
    set OUTPUT_FILE=main.docx
    echo ℹ️  未指定输出文件，使用默认: %OUTPUT_FILE%
)

echo.
echo =======================================================
echo        SZCU Thesis Builder (One-Click Build)
echo =======================================================
echo 📄 输入文件: %INPUT_FILE%
echo 📝 输出文件: %OUTPUT_FILE%
echo =======================================================
echo.

:: 版本检测
echo [环境检测] 正在检查工具版本...
echo ------------------------------------------------------------

:: 检测 Pandoc 版本
pandoc --version 2>nul | findstr /C:"pandoc" >nul
if %errorlevel% equ 0 (
    for /f "tokens=2" %%v in ('pandoc --version ^| findstr /C:"pandoc"') do (
        echo ✅ Pandoc:          %%v
        goto :pandoc_ok
    )
) else (
    echo ❌ Pandoc:          未安装或不在 PATH 中
    echo    请访问: https://pandoc.org/installing.html
    pause
    exit /b 1
)
:pandoc_ok

:: 检测 Pandoc-Crossref 版本
pandoc-crossref --version 2>nul | findstr /C:"pandoc-crossref" >nul
if %errorlevel% equ 0 (
    for /f "tokens=2" %%v in ('pandoc-crossref --version ^| findstr /C:"pandoc-crossref"') do (
        echo ✅ Pandoc-Crossref: %%v
        goto :crossref_ok
    )
) else (
    echo ⚠️  Pandoc-Crossref: 未安装或不在 PATH 中
    echo    警告：图表交叉引用功能将无法使用
    echo    安装方法：运行 installer\install_complete.ps1
)
:crossref_ok

echo ------------------------------------------------------------
echo.

:: 1. Syntax Check
echo [1/4] 正在进行语法检查 (Linting)...
python scripts/lint.py %INPUT_FILE%
if %errorlevel% neq 0 (
    echo.
    echo ❌ 语法检查未通过，请修复上述错误后再试。
    pause
    exit /b %errorlevel%
)
echo ✅ 语法检查通过。
echo.

:: 2. Auto Cross-Reference Processing (生成中间文件)
echo [2/4] 正在生成图表ID和交叉引用 (auto_cross_ref.py)...
set PROCESSED_FILE=%INPUT_FILE:.md=.processed.md%
python scripts/auto_cross_ref.py %INPUT_FILE% -o %PROCESSED_FILE% -v
if %errorlevel% neq 0 (
    echo.
    echo ❌ ID生成失败，请检查错误信息。
    pause
    exit /b %errorlevel%
)
echo ✅ ID生成完成，中间文件: %PROCESSED_FILE%
echo.

echo [3/4] 正在调用 Pandoc 生成文档...
echo ------------------------------------------------------------
echo 📌 过滤器执行顺序说明:
echo    1. heading_preprocess_filter.lua  - 标题预处理（编号清理、unnumbered标记）
echo    2. pandoc-crossref                - 交叉引用处理
echo    3. citeproc                       - 引用处理
echo    4. szcu_thesis_filter_v2_merged   - 样式应用
echo ------------------------------------------------------------
pandoc %PROCESSED_FILE% --reference-doc=./config/reference.docx -o %OUTPUT_FILE% --lua-filter=./filters/heading_preprocess_filter.lua --filter pandoc-crossref --metadata-file=./config/crossref_config.yaml --citeproc --lua-filter=./filters/szcu_thesis_filter_v2.lua
if %errorlevel% neq 0 (
    echo.
    echo ------------------------------------------------------------
    echo ❌ Pandoc 转换失败！
    echo 📍 请查看上方的详细错误信息（包括文件名、行号和错误描述）
    echo ------------------------------------------------------------
    pause
    exit /b %errorlevel%
)
echo ✅ 初稿生成成功。
echo.

:: 3. Layout Fix
echo [4/4] 正在修复 Word 版式 (Headers/Margins)...
python scripts/fix_word_layout.py %OUTPUT_FILE% %OUTPUT_FILE%
if %errorlevel% neq 0 (
    echo.
    echo ❌ 版式修复脚本执行失败。
    pause
    exit /b %errorlevel%
)

echo.
echo =======================================================
echo 🎉 全部完成！请查看生成的文件：%OUTPUT_FILE%
echo =======================================================
pause
