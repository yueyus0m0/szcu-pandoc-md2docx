#!/bin/bash

# ========================================
# SZCU Thesis Builder (Linux/macOS 版本)
# ========================================
# 用法: ./build.sh [输入文件] [输出文件]
# 示例: ./build.sh main.md output.docx
#       ./build.sh thesis.md

set -e  # 遇到错误立即停止

# 颜色定义
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

# ========================================
# 参数处理
# ========================================
INPUT_FILE="${1:-main.md}"
OUTPUT_FILE="${2:-main.docx}"

if [ "$1" == "" ]; then
    echo -e "${BLUE}ℹ️  未指定输入文件，使用默认: ${INPUT_FILE}${NC}"
fi

if [ "$2" == "" ]; then
    echo -e "${BLUE}ℹ️  未指定输出文件，使用默认: ${OUTPUT_FILE}${NC}"
fi

echo
echo "======================================================="
echo "       SZCU Thesis Builder (One-Click Build)"
echo "======================================================="
echo "📄 输入文件: ${INPUT_FILE}"
echo "📝 输出文件: ${OUTPUT_FILE}"
echo "======================================================="
echo

# ========================================
# 环境检测
# ========================================
echo "[环境检测] 正在检查工具版本..."
echo "------------------------------------------------------------"

# 检测 Pandoc 版本
if command -v pandoc &> /dev/null; then
    PANDOC_VERSION=$(pandoc --version | head -n 1 | awk '{print $2}')
    echo -e "${GREEN}✅ Pandoc:          ${PANDOC_VERSION}${NC}"
else
    echo -e "${RED}❌ Pandoc:          未安装或不在 PATH 中${NC}"
    echo "   请访问: https://pandoc.org/installing.html"
    exit 1
fi

# 检测 Pandoc-Crossref 版本
if command -v pandoc-crossref &> /dev/null; then
    CROSSREF_VERSION=$(pandoc-crossref --version 2>/dev/null | head -n 1 | awk '{print $2}')
    echo -e "${GREEN}✅ Pandoc-Crossref: ${CROSSREF_VERSION}${NC}"
else
    echo -e "${YELLOW}⚠️  Pandoc-Crossref: 未安装或不在 PATH 中${NC}"
    echo "   警告：图表交叉引用功能将无法使用"
    echo "   安装方法：运行项目根目录的 install_pandoc.sh"
fi

# 检测 Python 环境
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    echo -e "${GREEN}✅ Python:          ${PYTHON_VERSION}${NC}"
else
    echo -e "${RED}❌ Python3:         未安装${NC}"
    exit 1
fi

echo "------------------------------------------------------------"
echo

# ========================================
# 1. 语法检查
# ========================================
echo "[1/4] 正在进行语法检查 (Linting)..."
if ! python3 scripts/lint.py "${INPUT_FILE}"; then
    echo
    echo -e "${RED}❌ 语法检查未通过，请修复上述错误后再试。${NC}"
    exit 1
fi
echo -e "${GREEN}✅ 语法检查通过。${NC}"
echo

# ========================================
# 2. 自动交叉引用处理
# ========================================
echo "[2/4] 正在生成图表ID和交叉引用 (auto_cross_ref.py)..."

# 生成中间文件名 (将 .md 替换为 .processed.md)
PROCESSED_FILE="${INPUT_FILE%.md}.processed.md"

if ! python3 scripts/auto_cross_ref.py "${INPUT_FILE}" -o "${PROCESSED_FILE}" -v; then
    echo
    echo -e "${RED}❌ ID生成失败，请检查错误信息。${NC}"
    exit 1
fi
echo -e "${GREEN}✅ ID生成完成，中间文件: ${PROCESSED_FILE}${NC}"
echo

# ========================================
# 3. Pandoc 转换
# ========================================
echo "[3/4] 正在调用 Pandoc 生成文档..."
echo "------------------------------------------------------------"
echo "📌 过滤器执行顺序说明:"
echo "   1. heading_preprocess_filter.lua  - 标题预处理（编号清理、unnumbered标记）"
echo "   2. pandoc-crossref                - 交叉引用处理"
echo "   3. citeproc                       - 引用处理"
echo "   4. szcu_thesis_filter_v2.lua      - 样式应用"
echo "------------------------------------------------------------"

if ! pandoc "${PROCESSED_FILE}" \
    --reference-doc=./config/reference.docx \
    -o "${OUTPUT_FILE}" \
    --lua-filter=./filters/heading_preprocess_filter.lua \
    --filter pandoc-crossref \
    --metadata-file=./config/crossref_config.yaml \
    --citeproc \
    --lua-filter=./filters/szcu_thesis_filter_v2.lua; then
    echo
    echo "------------------------------------------------------------"
    echo -e "${RED}❌ Pandoc 转换失败！${NC}"
    echo "📍 请查看上方的详细错误信息（包括文件名、行号和错误描述）"
    echo "------------------------------------------------------------"
    exit 1
fi
echo -e "${GREEN}✅ 初稿生成成功。${NC}"
echo

# ========================================
# 4. Word 版式修复
# ========================================
echo "[4/4] 正在修复 Word 版式 (Headers/Margins)..."
if ! python3 scripts/fix_word_layout.py "${OUTPUT_FILE}" "${OUTPUT_FILE}"; then
    echo
    echo -e "${RED}❌ 版式修复脚本执行失败。${NC}"
    exit 1
fi

# ========================================
# 完成
# ========================================
echo
echo "======================================================="
echo -e "${GREEN}🎉 全部完成！请查看生成的文件：${OUTPUT_FILE}${NC}"
echo "======================================================="
