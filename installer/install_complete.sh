#!/bin/bash

# ==========================================
# Pandoc, Crossref & Python-docx 自动安装脚本
# (智能路径识别版)
# ==========================================

set -e # 遇到错误立即停止

GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

PANDOC_VERSION="3.8.2.1"
CROSSREF_VERSION="v0.3.22a"
INSTALL_DIR="/usr/local/bin"
MAN_DIR="/usr/local/share/man/man1"
TEMP_DIR=$(mktemp -d)

if [ "$EUID" -ne 0 ]; then 
  echo -e "${RED}[ERROR] 请使用 sudo 运行此脚本。${NC}"
  exit 1
fi

echo -e "${GREEN}[INFO] 工作目录: ${TEMP_DIR}${NC}"
cd "$TEMP_DIR"

# 1. 架构检测
ARCH=$(uname -m)
echo -e "${GREEN}[INFO] 架构: ${ARCH}${NC}"

if [ "$ARCH" == "x86_64" ]; then
    PANDOC_URL="https://github.com/jgm/pandoc/releases/download/${PANDOC_VERSION}/pandoc-${PANDOC_VERSION}-linux-amd64.tar.gz"
    CROSSREF_URL="https://github.com/lierdakil/pandoc-crossref/releases/download/${CROSSREF_VERSION}/pandoc-crossref-Linux-X64.tar.xz"
elif [ "$ARCH" == "aarch64" ]; then
    PANDOC_URL="https://github.com/jgm/pandoc/releases/download/${PANDOC_VERSION}/pandoc-${PANDOC_VERSION}-linux-arm64.tar.gz"
    CROSSREF_URL="https://github.com/lierdakil/pandoc-crossref/releases/download/${CROSSREF_VERSION}/pandoc-crossref-Linux-ARM64.tar.xz"
else
    echo -e "${RED}[ERROR] 不支持的架构: ${ARCH}${NC}"
    exit 1
fi

# ==========================================
# 2. 安装 Pandoc (智能查找路径)
# ==========================================
# 检查是否已安装 Pandoc 且版本匹配
if command -v pandoc &> /dev/null; then
    INSTALLED_VERSION=$(pandoc --version | head -n 1 | awk '{print $2}')
    if [ "$INSTALLED_VERSION" == "$PANDOC_VERSION" ]; then
        echo -e "${GREEN}[SKIP] Pandoc $PANDOC_VERSION 已安装，跳过下载${NC}"
        SKIP_PANDOC=true
    else
        echo -e "${GREEN}[INFO] 检测到 Pandoc $INSTALLED_VERSION，将升级到 $PANDOC_VERSION${NC}"
        SKIP_PANDOC=false
    fi
else
    SKIP_PANDOC=false
fi

if [ "$SKIP_PANDOC" = false ]; then
    echo -e "${GREEN}[INFO] 下载 Pandoc...${NC}"
    if command -v wget &> /dev/null; then
        wget -O pandoc.tar.gz "$PANDOC_URL"
    else
        curl -L -v -o pandoc.tar.gz "$PANDOC_URL"
    fi

echo -e "${GREEN}[INFO] 解压 Pandoc...${NC}"
tar -xzf pandoc.tar.gz

# --- 修正点：自动寻找 pandoc 二进制文件，不依赖固定文件夹名 ---
echo -e "${GREEN}[INFO] 正在定位 pandoc 二进制文件...${NC}"
# 在当前目录下查找名为 pandoc 的可执行文件 (排除 tar.gz 自己)
PANDOC_BIN=$(find . -type f -name "pandoc" -executable | head -n 1)

if [ -z "$PANDOC_BIN" ]; then
    echo -e "${RED}[ERROR] 解压后找不到 pandoc 二进制文件！以下是当前目录结构：${NC}"
    ls -R
    exit 1
fi

echo "找到文件: $PANDOC_BIN"
cp "$PANDOC_BIN" "$INSTALL_DIR/"
echo -e "${GREEN}[OK] Pandoc 主程序已安装${NC}"

# 尝试安装 man page (也是自动查找)
MAN_FILE=$(find . -type f -name "pandoc.1" | head -n 1)
if [ -n "$MAN_FILE" ]; then
    mkdir -p "$MAN_DIR"
    cp "$MAN_FILE" "$MAN_DIR/"
fi
fi  # 结束 SKIP_PANDOC 判断

# ==========================================
# 3. 安装 Pandoc-Crossref
# ==========================================
# 检查是否已安装 Pandoc-Crossref 且版本匹配
if command -v pandoc-crossref &> /dev/null; then
    # 获取已安装版本并去掉 'v' 前缀
    INSTALLED_CROSSREF=$(pandoc-crossref --version 2>/dev/null | head -n 1 | awk '{print $2}' | sed 's/^v//')
    # 去掉期望版本号前的 'v'
    EXPECTED_CROSSREF=$(echo "$CROSSREF_VERSION" | sed 's/^v//')
    # 对于 0.3.22a，接受 0.3.22 作为匹配（因为二进制文件报告为 0.3.22）
    EXPECTED_CROSSREF_BASE=$(echo "$EXPECTED_CROSSREF" | sed 's/a$//')
    
    if [ "$INSTALLED_CROSSREF" == "$EXPECTED_CROSSREF" ] || [ "$INSTALLED_CROSSREF" == "$EXPECTED_CROSSREF_BASE" ]; then
        echo -e "${GREEN}[SKIP] Pandoc-Crossref $INSTALLED_CROSSREF 已安装，跳过下载${NC}"
        SKIP_CROSSREF=true
    else
        echo -e "${GREEN}[INFO] 检测到 Pandoc-Crossref $INSTALLED_CROSSREF，将升级到 $EXPECTED_CROSSREF${NC}"
        SKIP_CROSSREF=false
    fi
else
    SKIP_CROSSREF=false
fi

if [ "$SKIP_CROSSREF" = false ]; then
    echo -e "${GREEN}[INFO] 下载 Pandoc-Crossref...${NC}"
    if command -v wget &> /dev/null; then
        wget -O pandoc-crossref.tar.xz "$CROSSREF_URL"
    else
        curl -L -v -o pandoc-crossref.tar.xz "$CROSSREF_URL"
    fi

    echo -e "${GREEN}[INFO] 解压 Crossref...${NC}"
    tar -xf pandoc-crossref.tar.xz

    echo -e "${GREEN}[INFO] 安装 Crossref...${NC}"
    # Crossref 解压后通常直接在当前目录
    if [ -f "./pandoc-crossref" ]; then
        cp "./pandoc-crossref" "$INSTALL_DIR/"
        echo -e "${GREEN}[OK] Crossref 已安装${NC}"
    else
        echo -e "${RED}[ERROR] 找不到 pandoc-crossref 文件。${NC}"
        ls -F
        exit 1
    fi

    if [ -f "pandoc-crossref.1" ]; then
        mkdir -p "$MAN_DIR"
        cp pandoc-crossref.1 "$MAN_DIR/" || true
    fi
fi  # 结束 SKIP_CROSSREF 判断

# ==========================================
# 4. Python 环境
# ==========================================
echo -e "${GREEN}[INFO] 配置 Python 环境...${NC}"

if ! command -v pip3 &> /dev/null; then
    echo -e "${GREEN}[INFO] 安装 pip3...${NC}"
    apt-get update || true  # 即使有源错误也继续
    apt-get install -y python3-pip || {
        echo -e "${RED}[ERROR] pip3 安装失败${NC}"
        exit 1
    }
fi

# 检查 python-docx 是否已安装
if python3 -c "import docx" 2>/dev/null; then
    echo -e "${GREEN}[SKIP] Python-docx 已安装，跳过安装${NC}"
else
    echo -e "${GREEN}[INFO] 安装 python-docx...${NC}"
    # 先尝试使用 --break-system-packages (pip 22.1+)
    # 如果失败则回退到不带该选项的安装方式（兼容旧版本 pip）
    if ! pip3 install python-docx --break-system-packages 2>/dev/null; then
        echo -e "${GREEN}[INFO] 回退到传统安装方式...${NC}"
        pip3 install python-docx || {
            echo -e "${RED}[ERROR] python-docx 安装失败${NC}"
            exit 1
        }
    fi
fi

# ==========================================
# 5. 最终验证
# ==========================================
echo -e "${GREEN}[INFO] 清理临时文件...${NC}"
cd ~
rm -rf "$TEMP_DIR"

echo "----------------------------------------"
echo "Pandoc 版本: $(pandoc --version | head -n 1)"
echo "Crossref 版本: $(pandoc-crossref --version | head -n 1)"
python3 -c "import docx; print('Python-docx: 导入成功')"
echo "----------------------------------------"
