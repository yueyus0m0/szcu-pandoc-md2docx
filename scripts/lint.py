import re
import os
import sys

# Force UTF-8 output for Windows console
if sys.platform.startswith('win'):
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

# ================= 配置区域 =================
DEFAULT_TARGET = "main.md"
# ===========================================

class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

class MarkdownLinter:
    def __init__(self, filepath):
        self.filepath = filepath
        self.lines = []
        self.content_str = "" # 全文内容字符串，用于跨行正则
        self.issues = {"error": 0, "warn": 0, "info": 0}
        
        # 核心：存储不需要检查的行号 (代码块内部)
        self.ignored_lines = set() 
        self.openxml_blocks = [] # 存储 (start_line, content_str)
        
        # 状态缓存
        self.bib_file = None
        self.bib_keys = set()
        self.headers_h1 = [] # [(line, text), ...]
        self.headers_h2 = []
        
        # --- 正则预编译 ---
        self.re_header_h1 = re.compile(r'^#\s+(.*)')
        self.re_header_h2 = re.compile(r'^##\s+(.*)')
        
        # 引用相关正则
        # 只匹配中括号包裹的文献引用格式: [@key] 或 [@key1; @key2]
        # 不匹配裸的 @xxx 交叉引用 (如 @fig:xxx, @tbl:xxx, @lst:xxx)
        self.re_cite = re.compile(r'\[@([a-zA-Z0-9_:\.\-]+)') 

        # Bib Key 匹配正则
        # 1. 增加 re.MULTILINE 标志，否则只能匹配文件开头的第一条文献
        # 2. 优化匹配逻辑，确保 Key 提取准确
        self.re_bib_key = re.compile(r'^\s*@\w+\s*\{\s*([^,]+),', re.MULTILINE) 
        
        # 脚注相关
        self.re_fn_use = re.compile(r'\[\^([^\]\s]+)\](?!:)') # [^1]
        self.re_fn_def = re.compile(r'^\[\^([^\]\s]+)\]:')   # [^1]:
        
        # 资源
        self.re_img = re.compile(r'!\[.*?\]\((.*?)\)')  # 用于提取图片路径
        self.re_img_full = re.compile(r'!\[([^\]]*)\]\(([^\)]+)\)')  # 捕获 alt text 和路径
        
        # 关键词行
        self.re_kw_cn = re.compile(r'^\*\*关键词[：:]\*\*(.*)')
        self.re_kw_en = re.compile(r'^\*\*Keywords[：:]\*\*(.*)')
        
        # 序号一致性校验正则
        # 匹配开头数字: "1", "1.1", "1.1.1" 等 (后面必须跟空格或行尾，防止匹配到 '2025年')
        self.re_num_start = re.compile(r'^(\d+(?:\.\d+)*\.?)(\s|$)')

    def load_file(self):
        if not os.path.exists(self.filepath):
            print(f"{Colors.FAIL}❌ 找不到目标文件: {self.filepath}{Colors.ENDC}")
            return False
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                self.lines = f.readlines()
            self.content_str = "".join(self.lines)
            return True
        except Exception as e:
            print(f"{Colors.FAIL}❌ 读取文件失败: {e}{Colors.ENDC}")
            return False

    def log_error(self, line, rule, msg, content=""):
        print(f"{Colors.FAIL}[Error] {rule} (Line {line}): {msg}{Colors.ENDC}")
        if content: print(f"    >>> {content.strip()[:60]}...")
        self.issues["error"] += 1

    def log_warn(self, line, rule, msg, content=""):
        print(f"{Colors.WARNING}[Warn]  {rule} (Line {line}): {msg}{Colors.ENDC}")
        if content: print(f"    >>> {content.strip()[:60]}...")
        self.issues["warn"] += 1

    def log_info(self, line, rule, msg, content=""):
        print(f"{Colors.OKBLUE}[Info]  {rule} (Line {line}): {msg}{Colors.ENDC}")
        if content: print(f"    >>> {content.strip()[:60]}...")
        self.issues["info"] += 1


    def _check_file_exists(self, path):
        # 简单处理相对路径
        clean_path = path.strip().split(' ')[0] # 移除可能的后面的参数
        return os.path.exists(clean_path)

    # ================= 预处理 =================

    def preprocess(self):
        """扫描代码块，分离 OpenXML"""
        in_block = False
        in_openxml = False
        openxml_buffer = []
        openxml_start = 0

        for i, line in enumerate(self.lines):
            stripped = line.strip()
            
            # 标记代码块开始/结束
            if stripped.startswith('```'):
                if not in_block:
                    in_block = True
                    
                    # R21: 代码块格式检查 (已放宽：允许不写ID)
                    line_num = i + 1
                    
                    # 跳过 OpenXML 代码块
                    if '{=openxml}' in stripped:
                        in_openxml = True
                        openxml_start = i + 1
                        openxml_buffer = []
                        self.ignored_lines.add(i)
                        continue
                    
                    # 检查是否有属性块 {...}
                    if '{' in stripped:
                        # 建议有caption（改为WARNING）
                        if 'caption=' not in stripped:
                            self.log_warn(line_num, "R21",
                                "代码块建议添加 caption 属性",
                                "标准格式: ```python {caption=\"说明\"} 或 ```python {#lst:id caption=\"说明\"}")
                        
                        # 提取属性块
                        attr_match = re.search(r'\{([^}]+)\}', stripped)
                        if attr_match:
                            attrs = attr_match.group(1)
                            
                            # 检查是否有ID (有ID才检查，没ID不报错)
                            if '#lst' in attrs:
                                # 检查空格规范（如果有完整 ID）
                                if re.search(r'#lst:\w+', attrs):
                                    # 只有在提供完整 ID 时才检查空格规范
                                    
                                    # 1. #lst 和 : 之间不能有空格
                                    if re.search(r'#lst\s+:', attrs):
                                        self.log_error(line_num, "R21",
                                            "ID格式错误：#lst 和 : 之间不能有空格",
                                            "正确格式: {#lst:id caption=\"...\"}或{#lst: caption=\"...\"}")
                                    
                                    # 2. : 后面紧跟ID，不能有空格
                                    if re.search(r'#lst:\s+\w', attrs):
                                        self.log_error(line_num, "R21",
                                            "ID格式错误：冒号后不能有空格",
                                            "正确格式: {#lst:id caption=\"...\"}")
                                    
                                    # 3. ID 和 caption 之间必须有空格
                                    if re.search(r'#lst:\w+caption=', attrs):
                                        self.log_error(line_num, "R21",
                                            "ID 和 caption 之间必须有空格",
                                            "正确格式: {#lst:id caption=\"...\"}")
                    
                    # 检查是否是 OpenXML 注入
                    if '{=openxml}' in stripped:
                        in_openxml = True
                        openxml_start = i + 1
                        openxml_buffer = []
                else:
                    in_block = False
                    if in_openxml:
                        # 结束 OpenXML 块，保存
                        self.openxml_blocks.append((openxml_start, "".join(openxml_buffer)))
                        in_openxml = False
                
                self.ignored_lines.add(i)
                continue
            
            if in_block:
                self.ignored_lines.add(i)
                if in_openxml:
                    openxml_buffer.append(line)

            # 同时收集标题信息（仅非忽略行）
            if not in_block and stripped.startswith('#'):
                if stripped.startswith('# '):
                    self.headers_h1.append((i + 1, stripped[2:].strip()))
                elif stripped.startswith('## '):
                    self.headers_h2.append((i + 1, stripped[3:].strip()))

    # ================= 🛑 致命错误检查 =================

    def check_yaml_and_bib(self):
        """R1-R4: YAML配置与文献库深度校验"""
        in_yaml = False
        bib_filename = None
        
        # R1: 第一行检查
        if not self.lines or self.lines[0].strip() != '---':
            self.log_error(1, "R1", "文件第一行必须是 '---' (YAML 头)")
            return

        # 解析 YAML
        for i, line in enumerate(self.lines):
            if i in self.ignored_lines: continue
            stripped = line.strip()
            
            if i == 0: 
                in_yaml = True
                continue
            if stripped == '---': 
                in_yaml = False
                break
            
            if in_yaml:
                # R2: CSL 路径
                if stripped.startswith('csl:'):
                    if 'config/' not in stripped and 'config\\' not in stripped:
                        self.log_error(i+1, "R2", "CSL 路径必须指向 config/ 文件夹", stripped)
                
                # R3: Bib 文件存在性
                if stripped.startswith('bibliography:'):
                    parts = stripped.split(':', 1)
                    if len(parts) > 1:
                        bib_filename = parts[1].strip().strip('"').strip("'")
                        if not self._check_file_exists(bib_filename):
                            self.log_error(i+1, "R3", f"找不到参考文献库文件: {bib_filename}", stripped)
                        else:
                            self.bib_file = bib_filename

        # R4: 文献 Key 有效性校验
        if self.bib_file:
            self._load_bib_keys()
            self._validate_citations_in_text()

    def _load_bib_keys(self):
        """读取 .bib 文件提取所有 Key"""
        try:
            with open(self.bib_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # 简单正则匹配 @type{key,
                keys = self.re_bib_key.findall(content)
                # 增加 strip() 去除可能存在的空格
                self.bib_keys = {k.strip() for k in keys}
        except Exception as e:
            print(f"{Colors.FAIL}❌ 读取 .bib 文件解析失败: {e}{Colors.ENDC}")

    def _validate_citations_in_text(self):
        """扫描全文引用并核对 Key"""
        for i, line in enumerate(self.lines):
            if i in self.ignored_lines: continue
            
            # 提取 [@key] 或 [@key; @key2]
            # 由于正则只匹配中括号包裹的引用，不会匹配到 @fig: @tbl: @lst: 等交叉引用
            if '@' in line:
                matches = self.re_cite.findall(line)
                for key in matches:
                    if key.isdigit(): continue 
                    
                    if key not in self.bib_keys:
                        self.log_error(i+1, "R4", f"引用了不存在的文献 Key: @{key}", line.strip())

    def check_openxml_structure(self):
        """R5-R6: OpenXML 注入代码检查"""
        has_sect_break_valid = False
        
        for start_line, content in self.openxml_blocks:
            # R5: 目录域检查
            if 'TOC' in content and 'instrText' in content:
                if r'\h' in content:
                    self.log_error(start_line, "R5", "目录域代码包含禁止的 '\\h' 开关 (导致无法显示黑体)", r"TOC \o ... \h ...")

            # R6: 分节符检查 (寻找 <w:sectPr>)
            if '<w:sectPr>' in content:
                has_next_page = 'w:val="nextPage"' in content
                
                if has_next_page:
                    # [修改] 只要有 nextPage 即可，不需要强制 w:start="1"
                    # 因为 change_header.py 脚本会自动处理页码重置
                    has_sect_break_valid = True
        
        # 如果全文都没有找到有效的分节符（且有足够长度），报错
        if len(self.headers_h1) > 3 and not has_sect_break_valid:
             self.log_error(0, "R6", "未检测到 OpenXML 分节符 <w:type w:val='nextPage'/>", "可能导致页眉/页码无法分节控制")

    def check_footnotes(self):
        """R7: 脚注配对检查"""
        used_ids = set()
        defined_ids = set()
        
        for i, line in enumerate(self.lines):
            if i in self.ignored_lines: continue
            
            # 收集引用 [^1]
            uses = self.re_fn_use.findall(line)
            for uid in uses: used_ids.add(uid)
            
            # 收集定义 [^1]:
            defn = self.re_fn_def.match(line)
            if defn:
                defined_ids.add(defn.group(1))

        # 差集分析
        missing_defs = used_ids - defined_ids
        unused_defs = defined_ids - used_ids
        
        for mid in missing_defs:
            self.log_error(0, "R7", f"使用了脚注 [^{mid}] 但未在文末定义内容")
        for uid in unused_defs:
            self.log_error(0, "R7", f"定义了脚注 [^{uid}]: 但文中未使用")

    def check_resources(self):
        """R8: 资源路径检查"""
        for i, line in enumerate(self.lines):
            if i in self.ignored_lines: continue
            
            # R8-1: 检查图片路径是否存在
            matches = self.re_img.findall(line)
            for path in matches:
                if path.startswith('http') or path.startswith('data:'): continue
                if not self._check_file_exists(path):
                    self.log_error(i+1, "R8", f"图片文件不存在: {path}")
            
            # R8-2: 检查图片名称（alt text）是否填写
            full_matches = self.re_img_full.findall(line)
            for alt_text, path in full_matches:
                # 去除首尾空格后检查
                if not alt_text.strip():
                    self.log_error(i+1, "R8", f"图片名称（alt text）不能为空，应填写有意义的描述: ![这里应该有描述]({path})")

    # ================= ⚠️ 完整性与结构检查 =================
    
    def check_build_dependencies(self):
        """R22-R23: 构建依赖文件深度校验"""
        print(f"{Colors.OKBLUE}正在检查构建依赖文件...{Colors.ENDC}")
        
        # R22: Lua 过滤器
        required_filters = [
            ("filters/heading_preprocess_filter.lua", "标题预处理过滤器"),
            ("filters/szcu_thesis_filter_v2.lua", "SZCU 论文样式过滤器")
        ]
        
        for filter_path, desc in required_filters:
            if not os.path.exists(filter_path):
                self.log_error(0, "R22", 
                    f"缺失必需的 Lua 过滤器 ({desc}): {filter_path}",
                    "Pandoc 构建时将报错 'Filter not found'")
        
        # R23: 配置文件
        required_configs = [
            ("config/reference.docx", "Word 参考文档模板"),
            ("config/crossref_config.yaml", "交叉引用配置文件")
        ]
        
        for config_path, desc in required_configs:
            if not os.path.exists(config_path):
                self.log_error(0, "R23", 
                    f"缺失必需的配置文件 ({desc}): {config_path}",
                    "构建流程将失败或输出格式不符合要求")
    
    def check_table_naming(self):
        """R24: 表格命名规范检测"""
        table_pattern = re.compile(r'^Table:\s*(.+)')
        pipe_table_pattern = re.compile(r'^\|')
        
        for i, line in enumerate(self.lines):
            if i in self.ignored_lines: continue
            stripped = line.strip()
            
            # 检测 Table: 前缀 (严格大小写)
            if stripped.lower().startswith('table:'):
                match = table_pattern.match(stripped)
                
                # 情况1: 格式错误 (小写table或缺少空格)
                if not match and stripped.startswith('table:'):
                    self.log_error(i+1, "R24", 
                        "表格命名格式错误: 'table'应为'Table'(大写T)",
                        stripped)
                elif not match:
                    self.log_error(i+1, "R24",
                        "表格命名格式错误: 'Table:'后缺少空格",
                        stripped)
                
                # 情况2: 有前缀但表名为空
                elif match:
                    table_name = match.group(1).strip()
                    if not table_name:
                        self.log_error(i+1, "R24",
                            "表格命名不能为空: 'Table:'后必须提供表名",
                            stripped)
                    
                    # 检查下一行是否是管道表
                    # 跳过空行
                    j = i + 1
                    while j < len(self.lines) and not self.lines[j].strip():
                        j += 1
                    
                    if j < len(self.lines):
                        table_start = self.lines[j].strip()
                        if not pipe_table_pattern.match(table_start):
                            self.log_warn(i+1, "R24",
                                f"'Table: {table_name}'后未检测到表格内容(应以'|'开头)",
                                f"第{j+1}行: {table_start[:40]}...")

    # ================= ⚠️ 完整性与结构检查 =================

    def check_structural_integrity(self):
        """R9-R14: 结构完整性分析"""
        print(f"{Colors.OKBLUE}正在进行结构完整性分析...{Colors.ENDC}")
        
        if len(self.headers_h1) < 6:
            self.log_warn(0, "Integrity", f"一级标题数量过少 ({len(self.headers_h1)} 个)，论文结构可能不完整")
            return

        # R9: 前置标题编号标记 {-} (已放宽：不写也可以，但写了必须规范)
        for idx in range(min(3, len(self.headers_h1))):
            line, text = self.headers_h1[idx]
            
            # 检查是否有标记
            has_short_marker = "{-}" in text
            has_long_marker = "{.unnumbered}" in text
            
            if has_short_marker or has_long_marker:
                # 已有标记，检查格式是否正确
                if has_short_marker:
                    # 检查 {-} 格式: 必须是 空格{-} 格式
                    if not re.search(r'\s+\{-\}', text):
                        self.log_error(line, "R9",
                            f"前置标题标记格式错误: {{-}}前缺少空格",
                            f"正确格式: '# 标题 {{-}}'  当前: '{text}'")
                    elif re.search(r'\{\s+-\s+\}', text):
                        self.log_error(line, "R9", 
                            f"前置标题标记格式错误: {{-}}内有多余空格",
                            f"正确格式: '# 标题 {{-}}'  当前: '{text}'")
                
                if has_long_marker:
                    # 检查 {.unnumbered} 格式
                    if not re.search(r'\s+\{\.unnumbered\}', text):
                        self.log_error(line, "R9",
                            f"前置标题标记格式错误: {{.unnumbered}}前缺少空格",
                            f"正确格式: '# 标题 {{.unnumbered}}'  当前: '{text}'")
            # else:
                # 未标记，仅提示（INFO级别）- 系统会自动处理
                # 未标记，仅提示（INFO级别）- 系统会自动处理 (已静音)
                # print(f"{Colors.OKBLUE}[Info]  R9 (Line {line}): 前置标题未标记 {{-}}，系统Lua过滤器会自动处理{Colors.ENDC}")


        # R10: 中文摘要检查 (增强关键词格式检测)
        if len(self.headers_h2) > 0:
            h2_line, h2_text = self.headers_h2[0]
            if "摘" not in h2_text:
                self.log_warn(h2_line, "R10", f"首个二级标题通常应为 '摘要'，当前识别为: '{h2_text}'")
            self._scan_for_keyword(h2_line, self.re_kw_cn, "R10", "未检测到 '**关键词：**' 行")
            # 增强：检测关键词格式
            self._validate_chinese_keywords(h2_line)
        else:
            self.log_warn(0, "R10", "缺失二级标题，摘要部分可能遗漏")

        # R11: 英文摘要检查 (增强关键词格式检测)
        has_en_kw = False
        en_kw_line = 0
        for i, line in enumerate(self.lines):
            if self.re_kw_en.match(line.strip()):
                has_en_kw = True
                en_kw_line = i + 1
                break
        if not has_en_kw:
            self.log_warn(0, "R11", "未检测到 '**Keywords:**' 行 (英文摘要部分)")
        else:
            # 增强：检测关键词格式
            self._validate_english_keywords(en_kw_line)

        # R12: 核心章节 (简化检测 - 只检查标题数量)
        if len(self.headers_h1) <= 3:
            self.log_warn(0, "R12",
                f"一级标题数量过少({len(self.headers_h1)}个),可能缺少正文章节 (至少应有: 中文题目、英文题目、目录 + 正文章节)")

        # R13: 文末结构 (简化：只检测参考文献)
        all_titles = [t[1] for t in self.headers_h1]
        combined_titles = " ".join(all_titles)
        if "参考" not in combined_titles and "Reference" not in combined_titles:
            self.log_warn(0, "R13", "文档中缺失 '参考文献' 章节 (必须项)")

        # R14: 引用锚点
        has_refs_div = False
        for line in self.lines:
            if "{#refs}" in line: has_refs_div = True; break
        if not has_refs_div:
            self.log_warn(0, "R14", "缺失参考文献锚点 ::: {#refs}，列表将无法生成")

    def _scan_for_keyword(self, start_line, regex, rule, msg):
        found = False
        for i in range(start_line, min(start_line + 50, len(self.lines))):
            if regex.match(self.lines[i].strip()):
                found = True; break
        if not found:
            self.log_warn(start_line, rule, msg)
    
    def _validate_chinese_keywords(self, start_line):
        """R10增强: 检测中文关键词格式 (全角分号、数量、标点等)"""
        for i in range(start_line, min(start_line + 50, len(self.lines))):
            line = self.lines[i].strip()
            
            if match := self.re_kw_cn.match(line):
                keywords_part = match.group(1).strip()
                
                # 1. 检查关键词前是否有空格
                if match.group(1).startswith(' '):
                    self.log_warn(i+1, "R10",
                        "中文关键词前不应有空格",
                        f"当前: '**关键词：**{keywords_part[:20]}...'")
                
                # 去除首尾空格后检查
                keywords_clean = keywords_part.strip()
                
                # 2. 检查分隔符 (应为全角分号 ；)
                if ',' in keywords_clean or '，' in keywords_clean:
                    self.log_warn(i+1, "R10",
                        "中文关键词应使用全角分号'；'分隔，不应使用逗号",
                        f"当前: '{keywords_clean}'")
                
                if ';' in keywords_clean:
                    self.log_warn(i+1, "R10",
                        "中文关键词应使用全角分号'；'而非半角分号';'",
                        f"当前: '{keywords_clean}'")
                
                # 3. 检查最后是否有标点符号
                if keywords_clean and keywords_clean[-1] in ['。', '.', '；', ';', ',', '，']:
                    self.log_warn(i+1, "R10",
                        "最后一个关键词后不应有标点符号",
                        f"当前末尾: '{keywords_clean[-1]}'")
                
                # 4. 检查关键词数量 (3-8个)
                keyword_list = [kw.strip() for kw in keywords_clean.split('；') if kw.strip()]
                if len(keyword_list) < 3:
                    self.log_warn(i+1, "R10",
                        f"关键词数量不足3个 (当前{len(keyword_list)}个)，建议3-8个",
                        f"当前: {keyword_list}")
                elif len(keyword_list) > 8:
                    self.log_warn(i+1, "R10",
                        f"关键词数量超过8个 (当前{len(keyword_list)}个)，建议3-8个",
                        f"当前: {keyword_list}")
                
                break
    
    def _validate_english_keywords(self, start_line):
        """R11增强: 检测英文关键词格式 (半角分号、标点等)"""
        for i in range(start_line - 1, min(start_line + 50, len(self.lines))):
            if i < 0: continue
            line = self.lines[i].strip()
            
            if match := self.re_kw_en.match(line):
                keywords_part = match.group(1).strip()
                
                # 1. 检查关键词前是否有空格
                if match.group(1).startswith(' '):
                    self.log_warn(i+1, "R11",
                        "英文关键词前不应有空格",
                        f"当前: '**Keywords:**{keywords_part[:20]}...'")
                
                # 去除首尾空格后检查
                keywords_clean = keywords_part.strip()
                
                # 2. 检查分隔符 (应为半角分号 ;)
                if ',' in keywords_clean:
                    self.log_warn(i+1, "R11",
                        "英文关键词应使用半角分号';'分隔，不应使用逗号','",
                        f"当前: '{keywords_clean}'")
                
                if '；' in keywords_clean:
                    self.log_warn(i+1, "R11",
                        "英文关键词应使用半角分号';'而非全角分号'；'",
                        f"当前: '{keywords_clean}'")
                
                # 3. 检查最后是否有标点符号
                if keywords_clean and keywords_clean[-1] in ['.', ';', ',', '。', '；', '，']:
                    self.log_warn(i+1, "R11",
                        "最后一个关键词后不应有标点符号",
                        f"当前末尾: '{keywords_clean[-1]}'")
                
                break

    # ================= ℹ️ 规范提示 =================

    def check_conventions(self):
        """R15-R18: 规范性提示"""
        ids_seen = set()
        
        for i, line in enumerate(self.lines):
            if i in self.ignored_lines: continue
            line_num = i + 1
            stripped = line.strip()

            # R15: 手动编号疑似粘连检测
            if stripped.startswith('#'):
                # 去掉井号和首尾空格，获取标题内容
                content = stripped.lstrip('#').strip()
                
                # 去除 Markdown 格式符号 (**, *, ~~, 等)，以便检测被格式化的标题
                # 先保存原始内容用于警告显示
                content_for_check = content
                # 去除加粗 **text** 和斜体 *text*
                content_for_check = re.sub(r'\*\*(.+?)\*\*', r'\1', content_for_check)
                content_for_check = re.sub(r'\*(.+?)\*', r'\1', content_for_check)
                # 去除删除线 ~~text~~
                content_for_check = re.sub(r'~~(.+?)~~', r'\1', content_for_check)
                content_for_check = content_for_check.strip()
                
                # 模式1: 数字编号粘连 (如 "1.1背景", "1.背景")
                # Lua 逻辑: match("^%d+[%.%d]*%.$") or match("^%d+%.%d+[%.%d]*$")
                # 这里我们需要检测这些模式后面紧跟了非空格字符
                
                # 情况A: "1.背景" or "1.1.背景" (以点结尾的数字串)
                if re.match(r'^\d+(\.\d+)*\.[^\s\d]', content_for_check):
                     self.log_warn(line_num, "R15", "标题编号与文字之间疑似缺少空格 (如 '1.1.背景')", stripped)
                
                # 情况B: "1.1背景" (不以点结尾，但全是数字和点)
                # 这种比较难，因为 "1.1" 本身可能是标题内容的一部分。
                # 但通常标题不会以纯数字开头紧接文字，除非是年份。
                # 假设：如果开头是 x.x.x 且紧接非数字非点非空格
                elif re.match(r'^\d+\.\d+(\.\d+)*[^\s\d\.]', content_for_check):
                     self.log_warn(line_num, "R15", "标题编号与文字之间疑似缺少空格 (如 '1.1背景')", stripped)

                # 模式2: 中文编号粘连 (如 "第一章绪论", "第一节背景", "第 1.1 节背景")
                # Lua 逻辑: match("^第.+[章节]$")
                # 允许 "第" 和 "节/章" 之间存在的空格
                elif re.match(r'^第\s*[0-9%.一二三四五六七八九十百]+\s*[章节][^\s]', content_for_check):
                    self.log_warn(line_num, "R15", "标题编号与文字之间疑似缺少空格 (如 '第一章绪论' 或 '第 1.1 节背景')", stripped)
                
                # 模式3: 顿号间隔 (如 "一、背景")
                # Lua 逻辑: match("^[一二三四五六七八九十]+、")
                elif re.match(r'^[一二三四五六七八九十]+、[^\s]', content_for_check):
                    self.log_warn(line_num, "R15", "标题编号与文字之间疑似缺少空格 (如 '一、背景')", stripped)
                
                # [暂时注释] 检测标题编号是否被加粗
                # 标准格式应该是: ## 1.2.2 标题文字
                # 而不是: ## **1.2.2 标题文字**
                # if content.startswith('**') and re.match(r'^\*\*\d+(\.\d+)*\s+', content):
                #     self.log_warn(line_num, "R15", "标题编号不应该被加粗，建议格式: '## 1.2.2 标题' 而非 '## **1.2.2 标题**'", stripped)


            # R16: 图表 ID 前缀
            if '![' in stripped and ']{#' in stripped:
                # 更新: 支持 {#fig}, {#fig:}, {#fig:xxx}
                if ']{#fig:' not in stripped and ']{#fig}' not in stripped:
                    self.log_warn(line_num, "R16", "图片 ID 缺少 'fig' 或 'fig:' 前缀，将被视为无编号图片", stripped)
            
            if stripped.startswith('Table:') and '{#' in stripped:
                 # 更新: 支持 {#tbl}, {#tbl:}, {#tbl:xxx}
                 if '{#tbl:' not in stripped and '{#tbl}' not in stripped:
                     self.log_warn(line_num, "R16", "表格缺少 'tbl' 或 'tbl:' ID，将无法自动编号", stripped)

            # R17: 关键词分隔符
            if stripped.startswith('**关键词：**'):
                if '，' in stripped:
                    self.log_warn(line_num, "R17", "关键词建议统一使用全角分号 '；'", stripped)

            # R18: ID 唯一性与空格
            id_matches = re.findall(r'\{#([^\}]+)\}', stripped)
            for raw_id in id_matches:
                if ' ' in raw_id:
                    self.log_warn(line_num, "R18", f"ID 包含空格，可能导致引用失效: '{raw_id}'")
                
                # [新增] 忽略自动编号占位符 (fig, tbl, lst, fig:, tbl:, lst:)
                # 这不是重复定义，而是触发自动编号的合法语法
                if raw_id in ['fig:', 'tbl:', 'lst:', 'fig', 'tbl', 'lst']: 
                    continue

                if raw_id in ids_seen:
                    self.log_warn(line_num, "R18", f"ID 重复定义: '{raw_id}'")
                ids_seen.add(raw_id)


    # ================= 🧹 排版格式检查 =================

    def check_spacing(self):
        """R19: 标题前后空行检查"""
        for i, line in enumerate(self.lines):
            if i in self.ignored_lines: continue
            stripped = line.strip()
            
            # 检测是否为标题 (1-6级)
            if re.match(r'^#{1,6}\s', stripped):
                # 1. 检查上一行 (排除第一行)
                if i > 0:
                    prev_line = self.lines[i-1].strip()
                    # 上一行不为空，且不是标题，且不是 '---'
                    if prev_line and not re.match(r'^#{1,6}\s', prev_line) and prev_line != '---':
                        self.log_warn(i+1, "R19", "标题前缺失空行 (正文粘连)", f"上文: ...{prev_line[-10:]} -> 标题: {stripped[:20]}...")

                # 2. 检查下一行 (排除最后一行)
                if i + 1 < len(self.lines):
                    next_line = self.lines[i+1].strip()
                    # 下一行不为空，且不是标题 (允许紧凑标题)
                    if next_line and not re.match(r'^#{1,6}\s', next_line):
                        self.log_warn(i+1, "R19", "标题后缺失空行 (建议空一行)", f"标题: ...{stripped[-10:]} -> 下文: {next_line[:20]}...")

    def check_header_numbering_consistency(self):
        """R20: 标题层级与序号一致性检查"""
        for i, line in enumerate(self.lines):
            if i in self.ignored_lines: continue
            stripped = line.strip()
            
            # 1. 判定这是一行"Markdown 标题"
            header_match = re.match(r'^([#]{1,6})\s+(.*)', stripped)
            if not header_match:
                continue
                
            md_hashes = header_match.group(1)
            title_text = header_match.group(2).strip()
            md_level = len(md_hashes)
            
            # [修复] 去除 Markdown 格式符号，以便正确提取数字序号
            # 这样可以处理 ## **1.2.2 标题** 这种情况
            title_text_clean = title_text
            # 去除加粗 **text** 和斜体 *text*
            title_text_clean = re.sub(r'\*\*(.+?)\*\*', r'\1', title_text_clean)
            title_text_clean = re.sub(r'\*(.+?)\*', r'\1', title_text_clean)
            # 去除删除线 ~~text~~
            title_text_clean = re.sub(r'~~(.+?)~~', r'\1', title_text_clean)
            title_text_clean = title_text_clean.strip()
            
            # 2. 提取文本中的"数字序号"
            num_match = self.re_num_start.match(title_text_clean)
            if not num_match:
                continue # 没有数字开头，跳过
                
            num_str = num_match.group(1)
            
            # 3. 计算"序号隐含层级"
            # 去除末尾的点 (如 "1." -> "1")
            clean_num_str = num_str.rstrip('.')
            parts = clean_num_str.split('.')
            # 过滤空项 (防卫性)
            parts = [p for p in parts if p]
            
            implied_level = len(parts)
            
            # 4. 最终比对
            if implied_level > 0 and md_level != implied_level:
                self.log_warn(i+1, "R20", 
                              f"标题层级与序号不一致: Markdown是 {md_level} 级(#{md_level})，但序号 '{num_str}' 暗示是 {implied_level} 级", 
                              stripped)

    # ================= Markdown 格式规范检查 =================
    
    def check_markdown_formatting(self):
        """R25-R38: Markdown 输入格式规范检查"""
        print(f"{Colors.OKBLUE}正在检查 Markdown 格式规范...{Colors.ENDC}")
        
        # 阶段1: 高优先级规则
        self._check_paragraph_indent()      # R25
        self._check_image_path_convention() # R27
        self._check_table_type()            # R29
        self._check_yaml_spacing()          # R32
        self._check_required_headings()     # R36
        
        # 阶段2: 中优先级规则
        self._check_blockquote_format()     # R26
        self._check_crossref_format()       # R28
        self._check_citation_format()       # R30
        self._check_punctuation_width()     # R31
        self._check_list_format()           # R37
        
        # 阶段3: 低优先级规则
        self._check_trailing_spaces()       # R33
        self._check_heading_case()          # R35
        self._check_emphasis_pairing()      # R38
        
    def _check_blockquote_format(self):
        """R26: 引用块格式检测"""
        # 检测是否紧跟在图表后的引用块
        # 但简化为检测所有引用块的前缀格式
        for i, line in enumerate(self.lines):
            if i in self.ignored_lines: continue
            stripped = line.strip()
            
            if stripped.startswith('>'):
                content = stripped[1:].strip()
                # 检查是否是图表说明类型的引用块 (包含 '注' 或 '来源')
                if '注' in content or '来源' in content or 'Source' in content or 'Note' in content:
                    # 检查前缀
                    if not (content.startswith('注：') or content.startswith('数据来源：') or 
                            content.startswith('Note:') or content.startswith('Source:')):
                        # 排除完全不相关的引用块
                        pass 
                        # 这里比较难严格判定，仅对非常像但不规范的报警
                        if content.startswith('注:') or content.startswith('数据来源:'):
                             self.log_warn(i+1, "R26",
                                "引用块建议使用中文全角冒号 '：'",
                                f"建议修改为: >注：... 或 >数据来源：...")

    def _check_crossref_format(self):
        """R28: 交叉引用格式检测"""
        for i, line in enumerate(self.lines):
            if i in self.ignored_lines: continue
            
            # 检测 {{fig: xxx}} 冒号后的空格
            if re.search(r'\{\{(fig|tbl|lst):\s+', line):
                self.log_warn(i+1, "R28",
                    "交叉引用冒号后不应有空格",
                    f"建议修改为: {{{{fig:name}}}} (当前: {line.strip()})")
            
            # 检测冒号前的空格
            if re.search(r'\{\{(fig|tbl|lst)\s+:', line):
                self.log_warn(i+1, "R28",
                    "交叉引用冒号前不应有空格",
                    f"建议修改为: {{{{fig:name}}}}")

            # 检测全角花括号
            if '｛｛' in line or '｝｝' in line:
                 self.log_warn(i+1, "R28",
                    "检测到全角花括号，交叉引用必须使用半角花括号",
                    f"建议修改为: {{{{ ... }}}}")

    def _check_citation_format(self):
        """R30: 文献引用格式检测"""
        # 检测 [数字] 格式，排除 [^数字] (脚注) 和 ![alt] (图片)
        # 简单的正则无法完美区分，这里只做基础检测
        # (?!^...) 排除行首的 [1] 假如是列表
        manual_cite_pattern = re.compile(r'(?<!^)\[\d+\]')
        
        for i, line in enumerate(self.lines):
            if i in self.ignored_lines: continue
            
            # 排除已知的 legitimate uses 
            # 排除 markdown 链接 define [1]: url
            if re.match(r'^\s*\[\d+\]:', line): continue
            
            matches = manual_cite_pattern.findall(line)
            if matches:
                 # 再次确认不是 [^1]
                 if re.search(r'\[\^', line): continue
                 
                 self.log_warn(i+1, "R30",
                    "检测到类似手动编号的引用 [N]，建议使用 BibTeX 引用 [@key]",
                    f"位置: {line[:40]}...")

    def _check_punctuation_width(self):
        """R31: 半角/全角符号混用检测"""
        for i, line in enumerate(self.lines):
            if i in self.ignored_lines: continue
            
            # Table：全角冒号
            if line.strip().startswith('Table：'):
                self.log_warn(i+1, "R31",
                    "表格定义应使用半角冒号",
                    f"建议: Table: Name")
            
            # 图片/链接的全角括号
            if re.search(r'!\[.*?\]（.*?）', line) or re.search(r'\[.*?\]（.*?）', line):
                 self.log_warn(i+1, "R31",
                    "Markdown 链接/图片语法使用了全角括号",
                    f"必须使用半角括号 ()")

    def _check_list_format(self):
        """R37: 列表格式检测"""
        for i, line in enumerate(self.lines):
            if i in self.ignored_lines: continue
            
            # 有序列表: 数字.没有空格
            if re.match(r'^\s*\d+\.\S', line):
                 self.log_warn(i+1, "R37",
                    "有序列表符号后需要一个空格",
                    f"建议: 1. 项目... (当前: {line.strip()[:20]})")

    def _check_trailing_spaces(self):
        """R33: 行尾空格检测"""
        for i, line in enumerate(self.lines):
            if i in self.ignored_lines: continue
            
            if line.rstrip('\r\n').endswith(' ') or line.rstrip('\r\n').endswith('\t'):
                # 排除空行（只包含空格的行）
                if not line.strip(): continue
                # 排除两个空格强制换行的情况 (如果只想检测意外的单空格)
                # 这里我们根据规则建议清理所有行尾空格，除非用户确实想换行
                # 仅提示
                pass
                # 由于Markdown语义中双空格有意义，这里作为Low Priority，只检测由单个空格结尾的情况可能是误触?
                # 实现: 检测行尾有空白
                # 由于Markdown语义中双空格有意义，这里作为Low Priority，只检测由单个空格结尾的情况可能是误触?
                # 实现: 检测行尾有空白 (已静音，根据用户反馈)
                # self.log_info(i+1, "R33", "检测到行尾有多余空格")


    def _check_heading_case(self):
        """R35: 标题大小写一致性检测"""
        for line, text in self.headers_h2:
            if "abstract" in text.lower() and text != "ABSTRACT":
                 self.log_info(0, "R35",
                    f"英文摘要标题建议全大写: ABSTRACT",
                    f"当前: {text}")

    def _check_emphasis_pairing(self):
        """R38: 强调符号配对检测"""
        for i, line in enumerate(self.lines):
            if i in self.ignored_lines: continue
            
            # 简单检测: * 的数量应该是偶数 (排除代码块内已经是ignored)
            # 排除 * 作为列表符 (行首)
            content = line.strip()
            if content.startswith('* '):
                content = content[2:]
            
            # 统计 * 和 ~ 的数量
            if content.count('**') % 2 != 0:
                 self.log_info(i+1, "R38", "粗体标记 ** 似乎没有正确闭合")
            elif content.replace('**', '').count('*') % 2 != 0:
                 pass # 斜体太容易误判（如公式中），暂不检测单星号
            
            if content.count('~~') % 2 != 0:
                 self.log_info(i+1, "R38", "删除线标记 ~~ 似乎没有正确闭合")
    
    def _check_paragraph_indent(self):
        """R25: 段落缩进检测"""
        for i, line in enumerate(self.lines):
            if i in self.ignored_lines: continue
            
            # 检测行首是否有4个或更多空格/Tab
            if re.match(r'^(\s{4,}|\t+)\S', line):
                # 排除列表项 (-, *, 数字.)
                if not re.match(r'^\s*[-*\d]+[\.\)]\s', line):
                    self.log_warn(i+1, "R25",
                        "检测到段落首行缩进，Markdown中段落间空行即表示换行",
                        f"当前行: {line[:50]}...")
    
    def _check_image_path_convention(self):
        """R27: 图片路径规范检测"""
        img_pattern = re.compile(r'!\[([^\]]*)\]\(([^)]+)\)')
        
        for i, line in enumerate(self.lines):
            if i in self.ignored_lines: continue
            
            matches = img_pattern.findall(line)
            for alt, path in matches:
                # 排除网络链接和data URI
                if path.startswith(('http://', 'https://', 'data:')):
                    continue
                
                # 检查路径是否以 ./media/ 或 media/ 开头
                if not (path.startswith('./media/') or path.startswith('media/')):
                    self.log_warn(i+1, "R27",
                        f"图片路径应存放在 ./media/ 目录下: {path}",
                        "建议统一管理图片资源")
    
    def _check_table_type(self):
        """R29: 表格类型检测"""
        table_pattern = re.compile(r'^Table:\s*(.+)')
        pipe_table_pattern = re.compile(r'^\|')
        grid_table_pattern = re.compile(r'^\+[-=]+\+')
        
        for i, line in enumerate(self.lines):
            if i in self.ignored_lines: continue
            stripped = line.strip()
            
            # 检测 Table: 行
            if table_pattern.match(stripped):
                # 检查后续行的表格类型
                j = i + 1
                # 跳过空行
                while j < len(self.lines) and not self.lines[j].strip():
                    j += 1
                
                if j < len(self.lines):
                    next_line = self.lines[j].strip()
                    
                    # 检测是否为 grid table
                    if grid_table_pattern.match(next_line):
                        self.log_warn(i+1, "R29",
                            "检测到 grid table 格式，请使用管道表（pipe table）",
                            "grid table 可能无法正确解析或编号")
                    # 检查是否为管道表
                    elif not pipe_table_pattern.match(next_line):
                        self.log_warn(i+1, "R29",
                            f"Table: 后未检测到管道表格式（应以 | 开头）",
                            f"第{j+1}行: {next_line[:40]}...")
    
    def _check_yaml_spacing(self):
        """R32: YAML 头部多余空行检测"""
        if not self.lines or self.lines[0].strip() != '---':
            return  # R1已检查
        
        # 查找YAML块的结束位置
        yaml_end = -1
        for i in range(1, min(50, len(self.lines))):
            if self.lines[i].strip() == '---':
                yaml_end = i
                break
        
        if yaml_end == -1:
            return
        
        # 检查YAML块内部是否有空行
        for i in range(1, yaml_end):
            if not self.lines[i].strip():
                self.log_warn(i+1, "R32",
                    "YAML 配置块内部不应有空行",
                    "空行可能影响YAML解析")
        
        # 检查YAML开头是否有空行 (第2行应该有内容)
        if yaml_end > 1 and not self.lines[1].strip():
            self.log_warn(2, "R32",
                "YAML 配置块开头不应有空行",
                "第一行 --- 后应直接是配置内容")
        
        # 检查YAML结束前是否有空行
        if yaml_end > 1 and not self.lines[yaml_end - 1].strip():
            self.log_warn(yaml_end, "R32",
                "YAML 配置块结尾前不应有空行",
                "配置内容和结束 --- 之间不应有空行")
    
    def _check_required_headings(self):
        """R36: 必要标题关键词检测"""
        if len(self.headers_h1) < 3:
            return  # 标题太少，R12已检查
        
        # 检查标题顺序和关键词
        has_toc = False  # 目录
        
        for line, text in self.headers_h1:
            if "目录" in text.replace(' ', '') or "目錄" in text.replace(' ', '') or "Contents" in text.upper():

                has_toc = True
                break
        
        if not has_toc:
            self.log_warn(0, "R36",
                "未检测到 '目录' 章节标题",
                "建议添加 # 目录 章节")
        
        # 检查H2是否包含摘要
        has_cn_abstract = False
        has_en_abstract = False
        
        for line, text in self.headers_h2:
            if "摘要" in text.replace(' ', '') or "摘  要" in text:
                has_cn_abstract = True
            if "ABSTRACT" in text.upper().replace(' ', ''):
                has_en_abstract = True
        
        if not has_cn_abstract:
            self.log_warn(0, "R36",
                "未检测到中文摘要章节（二级标题 ## 摘要）",
                "论文结构可能不完整")
        
        if not has_en_abstract:
            self.log_warn(0, "R36",
                "未检测到英文摘要章节（二级标题 ## ABSTRACT）",
                "论文结构可能不完整")

    # ================= 运行入口 =================

    def run(self):
        print(f"{Colors.OKBLUE}🔍 正在对 {self.filepath} 进行深度合规性检查...{Colors.ENDC}")
        print("-" * 60)
        
        if not self.load_file(): return

        # 0. 预处理
        self.preprocess()

        # 1. 致命错误检查
        self.check_yaml_and_bib()
        self.check_openxml_structure()
        self.check_footnotes()
        self.check_resources()
        self.check_build_dependencies()  # 🆕 R22-R23: 构建依赖检测
        self.check_table_naming()        # 🆕 R24: 表格命名检测

        # 2. 结构完整性检查
        self.check_structural_integrity()

        # 3. 规范提示
        self.check_conventions()
        self.check_spacing()
        self.check_header_numbering_consistency()
        self.check_markdown_formatting()  # 🆕 R25-R36: Markdown格式规范检查

        print("-" * 60)
        if self.issues["error"] == 0:
            if self.issues["warn"] == 0:
                print(f"{Colors.OKGREEN}✅ 完美！文档完全符合标准，可以放心生成。{Colors.ENDC}")
                sys.exit(0)
            else:
                print(f"{Colors.WARNING}⚠️  检查通过，但发现 {self.issues['warn']} 个完整性/规范性警告。{Colors.ENDC}")
                print("    (建议修正警告项以获得最佳排版效果，但您可以尝试生成)")
                sys.exit(0)
        else:
            print(f"{Colors.FAIL}❌ 检测到 {self.issues['error']} 个致命错误！{Colors.ENDC}")
            print(f"{Colors.FAIL}    这些错误会导致转换失败或格式崩坏，必须修正。{Colors.ENDC}")
            sys.exit(1)

if __name__ == "__main__":
    target = DEFAULT_TARGET
    if len(sys.argv) > 1:
        target = sys.argv[1]
    
    linter = MarkdownLinter(target)
    linter.run()