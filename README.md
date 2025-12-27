![Pandoc](https://img.shields.io/badge/Pandoc-3.8.2.1-blue?logo=pandoc&logoColor=white)
![Pandoc-Crossref](https://img.shields.io/badge/Pandoc--Crossref-v0.3.22a-orange)
![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-0078D6?logo=windows&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![SZCU](https://img.shields.io/badge/SZCU-Thesis-red)
# SZCU 毕业论文 Markdown 写作模板

> **适用对象**：苏州城市学院（SZCU）本科生 | **适配格式**：2026 理工类毕业论文（设计）
>
> **核心功能**：专注于 Markdown 写作，一键生成符合学校格式要求的完美 Word 文档（自动页眉页脚、自动参考文献、自动图表编号）。

---

## 📖 目录

- [⚡ 快速查阅](#-快速查阅-quick-cheat-sheet)
- [✨ 特性亮点](#-特性亮点)
- [💻 环境要求](#-环境要求)
- [🚀 新手入门](#-新手入门-getting-started)
- [📂 项目结构](#-项目结构)
- [📝 书写全流程记录](#书写全流程记录)
- [⚠️ 生成后需手动调整](#-生成后需手动调整)
- [❓ 常见问题](#-常见问题-faq)
- [🤝 贡献与反馈](#-贡献与反馈)

---

## ⚡ 快速查阅 (Quick Cheat Sheet)

### 快速跳转链接

| 功能 | 链接 |
|:-----|:-----|
| 📸 图片语法 | [点击跳转](#11-图片) |
| 📊 表格语法 | [点击跳转](#12-表格) |
| 💻 代码块 | [点击跳转](#13-代码块) |
| 📚 文献引用 | [点击跳转](#-14-文献引用写法) |
| 📝 脚注 | [点击跳转](#-15-脚注写法) |
| ⚠️ 手动调整 | [点击跳转](#-生成后需手动调整) |

### 一键生成 (推荐)

**Windows 用户：**
```powershell
.\build.bat
```

**Linux 用户：**
```bash
bash build.sh
```

### 📝 文档自检 (Lint)

在生成之前，建议使用检查脚本对 Markdown 文件进行格式和规范性自检，提前发现问题：

**Windows / Linux:**
```bash
# 检查默认文档 (main.md)
python scripts/lint.py

# 检查指定文档
python scripts/lint.py your-file.md
```


---

## ✨ 特性亮点

✅ **智能交叉引用**：使用简洁的 `{{fig:图名}}` 语法，自动转换为正确的图表引用
- 支持全角和半角花括号（`｛｛ ｝｝` 和 `{{ }}`）
- 智能处理重名图表，自动添加序号区分
- 支持向前和向后引用

✅ **自动格式清理**：
- 自动清理手动输入的标题编号（如 `# 第一章 绪论` → `# 绪论`）
- 自动识别前置标题（摘要、目录等），自动添加 `{-}` 标记防止编号
- 兼容多种标题编号格式

✅ **一键生成**：
- 集成语法检查、格式转换、版式修复全流程
- 自动生成符合学校要求的页眉页脚
- 自动应用参考文献国标格式 (GB/T 7714-2015)

✅ **完善的错误检查**：
- 运行前自动检查 Markdown 语法规范
- 检测缺失的图表 ID
- 检测未定义的引用

---

## 💻 环境要求

### 必需软件

| 软件                                                              | 版本要求      | 用途            |
| :-------------------------------------------------------------- | :-------- | :------------ |
| [Pandoc](https://pandoc.org/)                                   | ≥ 3.8.2.1 | Markdown 转换引擎 |
| [Pandoc-Crossref](https://github.com/lierdakil/pandoc-crossref) | v0.3.22a  | 图表交叉引用        |
| [Python](https://www.python.org/)                               | ≥ 3.8     | 运行自动化脚本       |
| [Python-docx](https://python-docx.readthedocs.io/)              | 自动安装      | Word 文档处理     |

### 支持平台

- ✅ Windows 10/11
- ✅ Linux (Ubuntu, Debian, CentOS 等)
- ⚠️ macOS (未充分测试，理论可用)

---
```text
szcu-pandoc-md2docx/
├── 📁 installer/                    # 💾 一键安装脚本
│   ├── install_complete.ps1         # Windows 一键安装脚本
│   └── install_complete.sh          # Linux 一键安装脚本
│
├── 📁 docs/                         # 📖 项目文档
│   ├── 下载安装指南.md               # 环境配置教程
│   ├── 检测规则.md                   # 📋 Markdown 检测规则规范
│   ├── img/                         # 📸 文档配图文件夹
│   └── official/                    # 🏫 学校官方参考文档
│       ├── 苏州城市学院本科生毕业论文（设计）打印格式.doc
│       └── 苏州城市学院本科生毕业论文（设计）模板-2026理工类.doc
│
├── 📁 media/                        # 🖼️ **【核心】图片资源文件夹**
│   └── (所有论文图片都存放在这里)
│
├── 📁 scripts/                      # 🔧 自动化脚本工具
│   ├── auto_cross_ref.py            # 🔗 自动生成图表 ID 和交叉引用
│   ├── fix_word_layout.py           # 🛠️ Word 版式修复 (页眉/页脚/页边距)
│   └── lint.py                      # 🔍 Markdown 语法检查器
│
├── 📁 config/                       # ⚙️ 配置文件 (一般不需修改)
│   ├── crossref_config.yaml         # 🔗 图表交叉引用配置
│   ├── gb7714.csl                   # 📝 参考文献国标样式
│   └── reference.docx               # 🎨 Word 样式模板文档
│
├── 📁 filters/                      # 🔧 Pandoc Lua 过滤器 (不要修改)
│   ├── heading_preprocess_filter.lua # 🔧 标题预处理过滤器
│   └── szcu_thesis_filter_v2.lua    # ⚡ 论文格式核心过滤器
│
├── 📄 main.md                       # ✍️ **【核心】论文正文写作文件**
├── 📄 references.bib                # 📚 **【核心】参考文献数据库**
├── 📄 build.bat                     # 🚀 Windows 一键构建脚本
├── 📄 build.sh                      # 🚀 Linux 一键构建脚本
└── 📄 thesis-template.md            # 📋 论文结构模板 (参考用)
```

### 核心文件说明

| 文件/文件夹 | 用途 | 是否需要修改 |
|:-----------|:-----|:-----------|
| `main.md` | 论文正文写作 | ✅ **必须编辑** |
| `references.bib` | 参考文献数据库 | ✅ **必须添加** |
| `media/` | 存放所有图片 | ✅ **必须使用** |
| `config/` | 系统配置和样式 | ⚠️ **高级用户可修改** |
| `filters/` | Pandoc Lua 过滤器 | ❌ **不要修改** |
| `build.bat` / `build.sh` | 一键构建脚本 | ⚠️ **通常不需要** |

---
## <a id="手动调整"></a>⚠️ 生成后需手动调整

以下内容必须在 Word 中人工修改：

1.  **更新目录**：
    *   选中目录 -> 右键 -> **更新域** -> **更新整个目录**。
    *   *目的*：确保目录页码和图表引用编号正确。


## 开始使用

### ☑ 1. 下载项目到你想要存放的文件夹

**方式一：使用 Git（推荐）**
```bash
git clone https://github.com/yueyus0m0/szcu-pandoc-md2docx.git
cd szcu-pandoc-md2docx
```

**方式二：直接下载 ZIP**
1. 访问 [项目主页](https://github.com/yueyus0m0/szcu-pandoc-md2docx)
2. 点击 "Code" → "Download ZIP"
3. 解压到任意文件夹

---

### ☑ 2. 运行安装脚本配置环境

**Windows 用户（推荐自动安装）：**

在项目根目录，以**管理员权限**运行 PowerShell，执行：
```powershell
.\installer\install_complete.ps1
```

该脚本会自动完成：
- ✅ 检测并安装 7-Zip（如需要）
- ✅ 下载并安装 Pandoc 3.8.2.1
- ✅ 下载并安装 Pandoc-Crossref v0.3.22a
- ✅ 安装 Python 库 python-docx
- ✅ 配置系统 PATH 环境变量

**Linux 用户：**
```bash
sudo bash installer/install_complete.sh
```

**手动安装：**

如果自动安装失败，请查看 [docs/下载安装指南.md](docs/下载安装指南.md) 手动安装各组件。

---

### ☑ 3. 阅读相关书写指南

开始写作前，强烈建议阅读以下文档：

1. **[thesis-template.md](thesis-template.md)** ⭐ **必读** - 论文结构模板
   - 完整的论文结构示例
   - 可以复制到 `main.md` 作为起点
   - Markdown 语法规范和图表、文献引用写法

2. **[docs/下载安装指南.md](docs/下载安装指南.md)** - 环境配置教程
   - 详细的安装步骤说明

---

### ☑ 4. 添加参考文献

将参考文献以 **BibTeX 格式**添加到 `references.bib` 文件中。

**获取 BibTeX 的方法：**

1. **知网（CNKI）：**
   - 搜索文献 → 导出 → 选择 "RefWorks" 格式
   - 使用在线工具转换为 BibTeX：[https://www.convertio.co/zh/](https://www.convertio.co/zh/)

2. **谷歌学术（Google Scholar）：**
   - 搜索文献 → 点击引用 → 选择 "BibTeX"
   - 复制内容到 `references.bib`

3. **其他数据库：**
   - 大多数学术数据库都支持导出 BibTeX 格式

**示例 BibTeX 条目：**
```bibtex
@article{li2024survey,
  title={深度学习在图像识别中的应用综述},
  author={李明 and 王华},
  journal={计算机学报},
  volume={45},
  number={3},
  pages={456--478},
  year={2024}
}
```

⚠️ **注意**：
- BibTeX Key（`@article{` 后的 `li2024survey`）必须唯一
- 引用时使用 `[@li2024survey]` 格式，Key 必须完全一致

---

### ☑ 5. 在 main.md 中书写论文

打开 `main.md` 文件，按照模板结构开始写作。

**核心要点：**
- 不要修改文档开头的 YAML 配置（`---` 包裹的部分）
- 不要修改"论文题目、摘要、目录"等前置结构的标题
- 图片统一存放在 `media/` 文件夹
- 遵循 Markdown 书写规范（详见 [书写全流程记录](#书写全流程记录)）

---

### ☑ 6. 执行转换

完成写作后，运行构建脚本生成 Word 文档。

**Windows 用户：**

双击 `build.bat` 或在 PowerShell 中执行：
```powershell
# 使用默认文件 (main.md → main.docx)
.\build.bat

# 指定输入文件
.\build.bat thesis.md

# 指定输入和输出文件
.\build.bat thesis.md output.docx
```

**Linux 用户：**
```bash
# 使用默认文件 (main.md → main.docx)
bash build.sh

# 指定输入文件
bash build.sh thesis.md

# 指定输入和输出文件
bash build.sh thesis.md output.docx
```

**参数说明：**
- **输入文件**（可选）：默认为 `main.md`
- **输出文件**（可选）：默认为 `main.docx`

**构建过程说明：**

构建脚本会自动执行以下 4 个步骤：

1. **[1/4] 语法检查 (Linting)**
   - 检查 Markdown 格式规范
   - 检测潜在的格式问题
   - 给出警告和建议

2. **[2/4] 生成图表 ID 和交叉引用**
   - 为图片、表格、代码块自动生成唯一 ID
   - 替换 `{{fig:图名}}` 为标准 Pandoc 引用
   - 生成中间文件 `main.processed.md`

3. **[3/4] Pandoc 转换**
   - 执行标题预处理（清理编号、标记 unnumbered）
   - 处理交叉引用（图表编号）
   - 处理参考文献引用
   - 应用 SZCU 论文样式
   - 生成初稿 `main.docx`

4. **[4/4] 修复 Word 版式**
   - 自动修复页眉页脚
   - 调整页边距
   - 应用参考文献样式

**完成后：**
- ✅ 生成的文档为 `main.docx`
- ⚠️ 记得按 `Ctrl+A` + `F9` 更新所有域（[详见手动调整](#-生成后需手动调整)）

---
## 书写全流程记录
### ✅0. 基本书写规则

* **两个段落之间空一行 = Word 新段落**
* 不要用空格或 Tab 模拟缩进

示例 ✅：

```markdown
这是第一段。

这是第二段。
````

示例 ❌：

```markdown
(开头加空格)
    这是错误写法
```


### ✅0. 文章结构

以下结构是不准改动的（除了{ }这个括号中的）

````markdown
# {论文题目}

## 摘要

{中文摘要...}

**关键词：**{词1；词2...}

# {Title}

## ABSTRACT

{English Abstract...}

**Keywords:**{keyword1,keyword2...}

# 目   录

```{=openxml}
<w:p>
  <w:pPr>
    <w:pStyle w:val="Normal"/> 
    <w:jc w:val="left"/>
  </w:pPr>
  <w:r>
    <w:fldChar w:fldCharType="begin"/>
  </w:r>
  <w:r>
    <w:instrText xml:space="preserve"> TOC \o "1-3"  \z \u </w:instrText>
  </w:r>
  <w:r>
    <w:fldChar w:fldCharType="separate"/>
  </w:r>
  <w:r>
    <w:fldChar w:fldCharType="end"/>
  </w:r>
</w:p>
```

```{=openxml}
<w:p>
  <w:pPr>
    <w:sectPr>
      <w:type w:val="nextPage"/>
    </w:sectPr>
  </w:pPr>
</w:p>
```

{正文区域}

# 参考文献

::: {#refs}
:::

# {文末标题}
````

### ✅1. 文件头配置
````
---
bibliography: references.bib
link-citations: "true"
csl: ./config/gb7714.csl
---
````

### ✅2. 论文题目_中文

替换论文题目成你的论文题目

### ✅3. 中文摘要内容

1. 替换摘要内容
2. 不同段落直接要空一行，空一行映射到word上才表示换行

### ✅4. 中文关键词

1. 注意`**关键词：**`不要动，只替换后面的关键词
2. 关键词前面不要有空格
3. 每一关键词之间用==全角分号隔开(；)==最后一个关键词后不打标点符号。关键词3-8个。

### ✅5. 论文题目_英文

替换论文题目成你的英文论文题目

### ✅6. 英文摘要内容

1. 替换摘要内容
2. 不同段落直接要空一行，空一行映射到word上才表示换行

### ✅7. 英文关键词

1. 注意`**Keywords:**`不要动，只替换后面的关键词
2. 关键词前面不要有空格
3. 每一关键词之间用==半角分号隔开(;)==最后一个关键词后不打标点符号。

### ✅8.目录（别动)

别动

### ✅9. 正文标题

| 层级       | Markdown 格式 | 推荐写法 (最整洁) ✅ | 兼容写法 (自动清洗) 🆗   |
| :------- | :---------- | :----------- | :--------------- |
| 一级标题（章）  | `#`         | `# 系统设计`     | `# 第 2 章 系统设计`   |
| 二级标题（节）  | `##`        | `## 实现原理`    | `## 2.1 实现原理`    |
| 三级标题（小节） | `###`       | `### 方法说明`   | `### 2.1.1 方法说明` |

1. 序号和标题名之间要有空格
2. 只使用支持的序号编号方式
3. 只最多使用三级标题
4. 一级标题和三级标题直接一定要有二级标题

### ✅10. 正文

1. 📌 **再次强调：Markdown 中的一行空行 = Word 中的一个新段落**

### ✅11. 图片

所有图片统一存放在[media]文件夹下

图片写法（必须写完整）
```markdown
![图名](./media/image.png)
```
1. 保持使用半角符合
2. 不要有多余的空格
3. `[ ]`中填写的是图名
4. ( )中填写的相对路径

交叉引用写法
```Markdown
{{fig:图名}}
```

1. 要有`fig:`前缀，和`{{ }}`,包裹着图名
2. `:`是英文冒号
3. `:`和图名之间不要有空格
4. **引用方式**：`如图 {{fig:系统架构图}} 所示`。
5. **注意**：如果有两张图片都叫“系统架构图”，脚本会智能根据上下文匹配最近的一张，或者添加序号。

完整写法
```
如{{fig:图名}}所示，你真的太厉害啦！

![图名](./media/image.png)

>数据来源：(可选项)

>注：(可选项)
```

### ✅12. 表格

只使用管道表(pipe table)

表格写法（必须写完整）
```markdown
Table: 表名

| 列名1 | 列名2 |
| :--- | :--- |
|   1  |  2   |
|   3  |  4   |
```

1. 在表格的前一行填写好表名
2. 表名前必须要有`Table:`前缀

交叉引用写法
```Markdown
{{tbl:表名}}
```
1. 要有`tbl:`前缀，和`{{ }}`,包裹着表名
2. `:`是英文冒号
3. `:`和表名之间不要有空格

完整写法
```markdown
如{{tbl:表名}}所示，你真的太厉害啦！

Table: 表名

| 列名1 | 列名2 |
| :--- | :--- |
|   1  |  2   |
|   3  |  4   |

>数据来源：(可选项)

>注：(可选项)
```

### ✅13. 代码块

代码块写法（必须写完整）
````markdown
```{caption="代码块名"}
hello world!
```
````

交叉引用写法
```Markdown
{{lst:代码块名}}
```

完整写法
````markdown
哇！你这{{lst:代码块名}}一看就是自己写的

```{caption="代码块名"}
hello world!
```
>数据来源：ai
````

### ✅ 14. 文献引用写法

单文件引用：

```markdown
这是引用[@li2022survey]的示例。
```

多个引用：

```markdown
……[@1025686450.nh; @JJYJ202506003]……
```

📌 不要手动输入 `[1]`
📌 引用中的 ID（如 `@li2024survey`）必须对应 `references.bib` 中的 **BibTeX Key**（即 `@article{` 紧挨着的那个单词）。

参考文献插入位置（保持原样）：

```markdown
# 参考文献

::: {#refs}
:::
```

### ✅ 15. 脚注写法

使用md默认脚注写法就好

推荐：

```markdown
正文内容[^1]

[^1]: 这是脚注内容
```

行内脚注：

```markdown
正文内容^[行内脚注文本]
```

### ✅16.引用块

写法
```
>注：这是一个一个很好的引用块

>数据来源：ai
```

### ✅17. 文末标题

必须存在
```
# 参考文献

::: {#refs}
:::
```

其他的文末标题一定要放在`# 参考文献`后面写

### ✅ 18. 禁止事项（避免排版错误）

  * **调整一级标题顺序**：请严格保持“中文题目 -> 英文题目 -> 目录 -> 正文 -> 参考文献 -> 其他文末标题”的结构。
  * **删除 `::: {#refs}`**：这是参考文献生成的锚点，必须保留。
  * **YAML 格式错误**：在文档顶部的 YAML 配置块上下留有多余空行。

---

## ❓ 常见问题 (FAQ)

### Q1: 运行 `build.bat` 提示找不到 Pandoc 怎么办？

**A:** 说明 Pandoc 未安装或未添加到系统 PATH。

**解决方法：**
1. **Windows 用户**：以管理员权限运行 PowerShell，执行：
   ```powershell
   .\installer\install_complete.ps1
   ```
2. **Linux 用户**：执行：
   ```bash
   sudo bash installer/install_complete.sh
   ```
3. 如果自动安装失败，请查看 [docs/下载安装指南.md](docs/下载安装指南.md) 手动安装。

### Q2: 提示 `'pandoc-crossref' is not recognized` 怎么办？

**A:** Pandoc-Crossref 未安装或未添加到 PATH。

**解决方法：**
- 运行 `.\installer\install_complete.ps1` 会自动下载并配置
- 或者从 [Pandoc-Crossref Releases](https://github.com/lierdakil/pandoc-crossref/releases) 下载对应版本，解压后将 `pandoc-crossref.exe` 放到 Pandoc 安装目录

### Q3: 图片/表格引用显示为 `??` 或者编号错误？

**A:** Word 域未更新。

**解决方法：**
1. 打开生成的 `main.docx`
2. 按 `Ctrl+A` 全选文档
3. 按 `F9` 更新所有域
4. 选择"更新整个目录"

### Q4: 参考文献格式不对，或者没有生成？

**A:** 检查以下几点：
1. ✅ `references.bib` 文件是否包含了所有引用的文献
2. ✅ BibTeX 格式是否正确（推荐从知网/谷歌学术直接导出）
3. ✅ 引用的 Key（如 `@li2024survey`）与 bib 文件中的 Key 是否完全一致
4. ✅ `main.md` 开头的 YAML 配置是否包含 `bibliography: references.bib`

### Q5: 图片/表格没有自动编号？

**A:** 缺少 ID 标记。

**解决方法：**
- **图片**：确保写法为 `![图名](./media/img.png)`，脚本会自动添加 ID
- **表格**：确保写法为 `Table: 表名`，注意 `Table:` 后面有空格
- **代码**：确保写法为 ` ```{caption="代码名"} `

自动交叉引用脚本 `auto_cross_ref.py` 会自动为符合格式的图表生成 ID。

### Q6: 使用 `{{fig:图名}}` 引用后没有替换？

**A:** 可能的原因：
1. ✅ 图名拼写错误（区分大小写）
2. ✅ 图片定义格式不正确
3. ✅ 脚本执行失败（查看构建日志）

**调试方法：**
- 查看 `main.processed.md` 文件，检查是否正确生成了 `@fig:id_xxx` 格式的引用
- 查看构建日志中的 "处理报告"，确认图片是否被正确识别

### Q7: 如何处理重名的图表？

**A:** 系统会自动处理重名情况：
- 第一个"系统架构图" → `fig:id_系统架构图_1`
- 第二个"系统架构图" → `fig:id_系统架构图_2`
- 引用时，系统会智能匹配距离最近的定义

**最佳实践**：给每个图表起独特的名字，避免重名。

### Q8: 想要自定义样式（字体、行距等）怎么办？

**A:** 修改 `config/reference.docx` 样式模板：
1. 打开 `config/reference.docx`
2. 修改样式（例如：修改"正文"样式的字体、行距）
3. 保存后重新运行 `build.bat`

⚠️ 注意：不要删除或重命名任何样式，只修改现有样式的格式。

### Q9: Linux 下运行报错怎么办？

**A:** 确保已安装所有依赖：
```bash
# 安装 Pandoc (Ubuntu/Debian)
sudo apt-get install pandoc

# 安装 Python 和 pip
sudo apt-get install python3 python3-pip

# 安装 python-docx
pip3 install python-docx
```

然后手动下载 [Pandoc-Crossref](https://github.com/lierdakil/pandoc-crossref/releases) 对应 Linux 版本。

### Q10: 生成的 Word 文档页眉页脚不正确？

**A:** 构建脚本中的 `fix_word_layout.py` 会自动修复页眉页脚。如果仍有问题：
1. 检查是否成功执行了第 4 步："正在修复 Word 版式"
2. 查看是否有错误提示
3. 如果问题依旧，可以在 Word 中手动调整页眉页脚

---

## 🤝 贡献与反馈

如果您发现以下问题，欢迎贡献：
- 📝 样式与学校最新要求不符
- 🐛 发现 Bug 或功能异常
- 💡 有改进建议或新功能需求
- 📖 文档说明不清楚

**贡献方式：**
1. 提交 [Issue](https://github.com/yueyus0m0/szcu-pandoc-md2docx/issues)
2. Fork 本项目，修改后提交 [Pull Request](https://github.com/yueyus0m0/szcu-pandoc-md2docx/pulls)

---

## 🙏 致谢

本项目基于以下开源项目：
- [Pandoc](https://pandoc.org/) - Universal document converter
- [Pandoc-Crossref](https://github.com/lierdakil/pandoc-crossref) - Cross-reference filter
- [Python-docx](https://python-docx.readthedocs.io/) - Python library for Word documents

感谢所有为本项目提供建议和反馈的同学们！

---

## 📄 License

MIT License

Copyright (c) 2025 yueyus0m0

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

---

## 📞 联系方式

- **项目主页**: [https://github.com/yueyus0m0/szcu-pandoc-md2docx](https://github.com/yueyus0m0/szcu-pandoc-md2docx)
- **问题反馈**: [Issues](https://github.com/yueyus0m0/szcu-pandoc-md2docx/issues)

---

**祝您写作顺利！🎓**
