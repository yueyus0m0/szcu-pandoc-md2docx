# Pandoc + Crossref + 7-Zip Total Installer
# Requires -RunAsAdministrator (Only needed if 7-Zip installation is required)

# ==========================================
# 1. Configuration
# ==========================================
$ErrorActionPreference = "Stop"
$ProgressPreference = 'SilentlyContinue'

$PANDOC_VERSION = "3.8.2.1"
$CROSSREF_VERSION = "v0.3.22a"
$SEVENZIP_VERSION = "2408" # 7-Zip 24.08
# Pandoc MSI 默认安装到用户的 LocalAppData 目录
$INSTALL_DIR = Join-Path $env:LOCALAPPDATA "Pandoc"
$TEMP_DIR = Join-Path $env:TEMP "pandoc_install_$(Get-Random)"

# ==========================================
# 2. Helper Functions
# ==========================================
function Write-ColorOutput {
    param([string]$Message, [string]$Color = "White")
    Write-Host $Message -ForegroundColor $Color
}

function Test-CommandExists {
    param([string]$Command)
    $null = Get-Command $Command -ErrorAction SilentlyContinue
    return $?
}

# 刷新当前会话的 PATH 环境变量
function Update-SessionPath {
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + 
    [System.Environment]::GetEnvironmentVariable("Path", "User")
}

# ==========================================
# 3. Main Script Logic
# ==========================================
try {
    Write-ColorOutput "=== Starting Comprehensive Installation ===" "Cyan"

    # 创建临时工作目录
    if (Test-Path $TEMP_DIR) { Remove-Item $TEMP_DIR -Recurse -Force }
    New-Item -ItemType Directory -Path $TEMP_DIR -Force | Out-Null

    # --- 步骤 A: 确保 7-Zip 可用 (解压 Crossref 必需) ---
    $sevenZipExe = "7z"
    if (Test-CommandExists "7z") {
        Write-ColorOutput "[SKIP] 7-Zip is already available in PATH." "Green"
    }
    else {
        $default7zPath = "C:\Program Files\7-Zip\7z.exe"
        if (Test-Path $default7zPath) {
            $sevenZipExe = $default7zPath
            Write-ColorOutput "[SKIP] 7-Zip found at default location." "Green"
        }
        else {
            Write-ColorOutput "[INFO] 7-Zip not found. Installing now..." "Yellow"
            $szUrl = "https://www.7-zip.org/a/7z$SEVENZIP_VERSION-x64.msi"
            $szMsi = Join-Path $TEMP_DIR "7zip.msi"
            
            Invoke-WebRequest -Uri $szUrl -OutFile $szMsi -UseBasicParsing
            Start-Process "msiexec.exe" -ArgumentList "/i", "`"$szMsi`"", "/qn", "/norestart" -Wait
            
            if (-not (Test-Path $default7zPath)) { throw "7-Zip installation failed." }
            $sevenZipExe = $default7zPath
            Write-ColorOutput "[OK] 7-Zip installed successfully." "Green"
        }
    }

    # --- 步骤 B: 安装 Pandoc (ZIP) ---
    Write-ColorOutput "[1/3] Checking Pandoc..." "Cyan"
    
    $needsInstall = $false
    $needsUpdate = $false
    
    if (Test-CommandExists "pandoc") {
        # 获取当前安装的版本
        $currentVersion = (pandoc --version | Select-Object -First 1) -replace '^pandoc\s+', ''
        Write-ColorOutput "[INFO] Current Pandoc version: $currentVersion" "White"
        Write-ColorOutput "[INFO] Target Pandoc version: $PANDOC_VERSION" "White"
        
        if ($currentVersion -ne $PANDOC_VERSION) {
            Write-ColorOutput "[UPDATE] Version mismatch detected. Will update Pandoc." "Yellow"
            $needsUpdate = $true
            $needsInstall = $true
        }
        else {
            Write-ColorOutput "[SKIP] Pandoc $PANDOC_VERSION is already installed." "Green"
        }
    }
    else {
        Write-ColorOutput "[INFO] Pandoc not found. Will install." "White"
        $needsInstall = $true
    }
    
    if ($needsInstall) {
        # 使用 ZIP 包而不是 MSI
        $pUrl = "https://github.com/jgm/pandoc/releases/download/$PANDOC_VERSION/pandoc-$PANDOC_VERSION-windows-x86_64.zip"
        $pZip = Join-Path $TEMP_DIR "pandoc.zip"
        
        Write-ColorOutput "[DOWNLOAD] Downloading Pandoc $PANDOC_VERSION ZIP..." "White"
        Invoke-WebRequest -Uri $pUrl -OutFile $pZip -UseBasicParsing
        
        if ($needsUpdate) {
            Write-ColorOutput "[INSTALL] Updating Pandoc..." "Yellow"
            # 删除旧版本
            if (Test-Path $INSTALL_DIR) { Remove-Item $INSTALL_DIR -Recurse -Force }
        }
        else {
            Write-ColorOutput "[INSTALL] Installing Pandoc..." "Yellow"
        }
        
        # 解压 ZIP 包
        $extractPath = Join-Path $TEMP_DIR "pandoc_extract"
        Expand-Archive -Path $pZip -DestinationPath $extractPath -Force
        
        # 确保安装目录存在
        if (-not (Test-Path $INSTALL_DIR)) { New-Item -ItemType Directory -Path $INSTALL_DIR -Force | Out-Null }
        
        # 查找解压后的 pandoc.exe（可能在子目录中）
        $pandocExe = Get-ChildItem -Path $extractPath -Filter "pandoc.exe" -Recurse | Select-Object -First 1
        if ($pandocExe) {
            # 复制整个 Pandoc 目录的内容到目标位置
            $sourceDir = $pandocExe.DirectoryName
            Get-ChildItem -Path $sourceDir -Recurse | ForEach-Object {
                $targetPath = Join-Path $INSTALL_DIR $_.FullName.Substring($sourceDir.Length)
                if ($_.PSIsContainer) {
                    New-Item -ItemType Directory -Path $targetPath -Force | Out-Null
                }
                else {
                    Copy-Item $_.FullName -Destination $targetPath -Force
                }
            }
        }
        
        # 添加到系统 PATH（用户级环境变量）- Prepend to ensure priority
        $currentPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
        if ($currentPath -notlike "*$INSTALL_DIR*") {
            # Put new path at the BEGINNING
            $newPath = "$INSTALL_DIR;$currentPath"
            [System.Environment]::SetEnvironmentVariable("Path", $newPath, "User")
            Write-ColorOutput "[OK] Added Pandoc to the BEGINNING of USER PATH." "Green"
        }
        
        # 核心：安装后刷新路径，否则后续步骤找不到 pandoc
        Update-SessionPath
        
        # 验证安装
        if (Test-CommandExists "pandoc") {
            $installedVersion = (pandoc --version | Select-Object -First 1) -replace '^pandoc\s+', ''
            Write-ColorOutput "[OK] Pandoc $installedVersion installed successfully and PATH updated." "Green"
        }
        else {
            throw "Pandoc installation verification failed."
        }
    }
    
    # --- 验证 Pandoc 路径优先级 ---
    Write-ColorOutput "[INFO] Verifying Pandoc location priority..." "White"
    $pandocCommand = Get-Command pandoc -ErrorAction SilentlyContinue
    if ($pandocCommand) {
        $detectedPath = Split-Path $pandocCommand.Source -Parent
        if ($detectedPath -ne $INSTALL_DIR) {
            Write-ColorOutput "[WARNING] Another Pandoc detected at: $detectedPath" "Yellow"
            Write-ColorOutput "[WARNING] The installed portable version ($INSTALL_DIR) might be shadowed." "Yellow"
            Write-ColorOutput "[TIP] We have prepended the new path, but a restart might be needed for some apps." "White"
            # Do NOT update INSTALL_DIR here, we must install Crossref to OUR directory
        }
        else {
            Write-ColorOutput "[OK] Pandoc is correctly active from: $INSTALL_DIR" "Green"
        }
    }
    else {
        Write-ColorOutput "[WARNING] Pandoc command not found in current session yet." "Yellow"
    }

    # --- 步骤 C: 安装 Pandoc-Crossref (7z) ---
    Write-ColorOutput "[2/3] Installing Pandoc-Crossref..." "Cyan"
    $crUrl = "https://github.com/lierdakil/pandoc-crossref/releases/download/$CROSSREF_VERSION/pandoc-crossref-Windows-X64.7z"
    $cr7z = Join-Path $TEMP_DIR "crossref.7z"
    $extractPath = Join-Path $TEMP_DIR "extract"

    Invoke-WebRequest -Uri $crUrl -OutFile $cr7z -UseBasicParsing
    
    # 使用刚刚确认安装的 7z.exe 解压
    & $sevenZipExe x $cr7z "-o$extractPath" -y | Out-Null

    # 确保安装目录存在 
    if (-not (Test-Path $INSTALL_DIR)) { New-Item -ItemType Directory -Path $INSTALL_DIR -Force | Out-Null }
    
    $exe = Get-ChildItem -Path $extractPath -Filter "pandoc-crossref.exe" -Recurse | Select-Object -First 1
    if ($exe) {
        Copy-Item $exe.FullName (Join-Path $INSTALL_DIR "pandoc-crossref.exe") -Force
        Write-ColorOutput "[OK] Pandoc-Crossref integrated into $INSTALL_DIR" "Green"
    }

    # --- 步骤 D: Python 库配置 ---
    Write-ColorOutput "[3/3] Configuring Python docx..." "Cyan"
    if (Test-CommandExists "python") {
        # 自动安装 python-docx
        python -m pip install python-docx --quiet --disable-pip-version-check
        Write-ColorOutput "[OK] python-docx is ready." "Green"
    }
    else {
        Write-ColorOutput "[WARNING] Python not found. Some scripts may not work." "Yellow"
        Write-ColorOutput "[INFO] Please install Python from: https://www.python.org/downloads/" "Yellow"
        Write-ColorOutput "[INFO] After installation, run: python -m pip install python-docx" "White"
    }

}
catch {
    Write-ColorOutput "[FATAL ERROR] $($_.Exception.Message)" "Red"
}
finally {
    # 清理临时文件
    if (Test-Path $TEMP_DIR) { Remove-Item $TEMP_DIR -Recurse -Force -ErrorAction SilentlyContinue }
    Write-ColorOutput "`n=== ALL TASKS COMPLETED SUCCESSFULLY ===" "Green"
    Read-Host "Press Enter to exit"
}