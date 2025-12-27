--[[
================================================================================
文件名: szcu_thesis_filter_v2_merged.lua
版本: 2.1 (样式应用专用版)
功能: SZCU 毕业论文 Pandoc Lua 过滤器 - 样式和格式应用层
================================================================================

【职责边界】
本过滤器负责 SZCU 论文的样式应用和业务逻辑处理：
  ✅ H1 自定义样式应用（Title_cn, Title_en, TTOOCC Title, UnnumberedHeading）
  ✅ 分页符插入
  ✅ 摘要处理（标题、正文、关键词格式化）
  ✅ 图表注检测和样式包裹
  ✅ 列表样式映射
  ✅ 检测参考文献区域（用于样式选择）

【不再处理】（已迁移到 heading_preprocess_filter.lua）
  ❌ 标题编号清理
  ❌ unnumbered 属性添加

【过滤器执行顺序】
  1. heading_preprocess_filter.lua  ← 标题预处理（编号清理、unnumbered 标记）
  2. pandoc-crossref                ← 交叉引用处理
  3. citeproc                       ← 引用处理
  4. szcu_thesis_filter_v2_merged.lua ← 样式应用（本过滤器）

【版本历史】
v2.1 (2025-12-27): 职责重构
  - 移除标题编号清理逻辑（迁移到 heading_preprocess_filter.lua）
  - 专注于样式应用和业务逻辑
  - 简化代码，提升可维护性

v2.0: 完全优化版
  - 实施所有 4 个阶段的优化
  - 模块化架构设计
  - 单文件打包

================================================================================
]]

local utils = require 'pandoc.utils'
local stringify = utils.stringify

---------------------------------------------------------
-- 模块: CONFIG (配置中心)
-- 优化: #1 配置系统抽离, #8 魔法数值提取
---------------------------------------------------------

local Config = {
  debug = true,
  auto_clean_numbering = true,

  styles = {
    abstract_title = "Abstract Title",
    abstract_body  = "Abstract",
    abstract_kw    = "Keywords",
    h1_cn        = "Title_cn",
    h1_en        = "Title_en",
    h1_toc       = "TTOOCC Title",
    h1_no_num    = "UnnumberedHeading",
    figure_note  = "Table Figure Note",
    figure_table = "FigureTable",
    pagebreak_xml = '<w:p><w:r><w:br w:type="page"/></w:r></w:p>',
    list_paragraph = "Body Text"
  },

  cleaning = {
    scan_limit = 10,
    convert_softbreak = false,
  },

  note_detection = {
    prefixes = {
      "注：", "说明：", "数据来源：", 
      "Note:", "Notes:", "Remark:", "Source:", "Data source:",
      "注:", "说明:", "数据来源:",
    }
  },

  abstracts = {
    {
      style_title    = "abstract_title",
      style_body     = "abstract_body",
      style_kw       = "abstract_kw",
      keyword_prefix = "关键词：",
      separator      = "；",
      validate_range = {3, 8},
      bold_prefix    = true,
      dirty_separators = "[,，;；、|/ .]"
    },
    {
      style_title    = "abstract_title",
      style_body     = "abstract_body",
      style_kw       = "abstract_kw",
      keyword_prefix = "Keywords:",
      separator      = ";",
      validate_range = nil, 
      bold_prefix    = true,
      dirty_separators = "[,，;；、|/.]"
    },
  },

  first = {
    { style_key = "h1_cn",      pagebreak = false },
    { style_key = "h1_en",      pagebreak = true  },
    { style_key = "h1_toc",     pagebreak = true  },
    { style_key = nil,          pagebreak = false },
  },

  ref_trigger_titles = {
    "参考文献", "References", "Reference", "Bibliography", "参考资料"
  },

  middle = {
    style_key = nil,
    pagebreak = true,
  },
}

-- 优化 #8: 常量提取
local CONSTANTS = {
  MAX_SPECIAL_H1_COUNT = 4,
  PROGRESS_UPDATE_INTERVAL = 10,  -- 进度报告间隔（百分比）
}

---------------------------------------------------------
-- 模块: UTILS (工具函数)
-- 优化: #10 消除重复代码, #4 哈希表优化
---------------------------------------------------------

local Utils = {}

function Utils.ltrim(s)
  return (s:gsub("^%s+", ""))
end

function Utils.trim(s)
  return (s:gsub("^%s*(.-)%s*$", "%1"))
end

function Utils.normalize_text(text)
  return (text or ""):gsub("[%s　]+", ""):lower()
end

-- 注：is_pure_numbering 已迁移到 heading_preprocess_filter.lua
-- 标题编号清理现由预处理过滤器负责

-- 优化 #4: 哈希表构建
function Utils.build_prefix_set(prefixes)
  if not prefixes then return {} end
  
  local set = {}
  for _, prefix in ipairs(prefixes) do
    local key = (prefix or ""):gsub("[%s　]+", ""):lower()
    if key ~= "" then
      set[key] = true
    end
  end
  return set
end

function Utils.debug_log(msg)
  if Config.debug then
    io.stderr:write(msg .. "\n")
  end
end

function Utils.pagebreak_block()
  return pandoc.RawBlock('openxml', Config.styles.pagebreak_xml)
end

function Utils.block_has_image(block)
  local has_img = false
  pandoc.walk_block(block, {
    Image = function(_) has_img = true end
  })
  return has_img
end

function Utils.load_prefixes(meta)
  local m = meta["note-prefixes"]
  if not m then return end

  local new = {}
  if m.t == "MetaList" then
    for _, item in ipairs(m) do 
      table.insert(new, stringify(item)) 
    end
  else
    table.insert(new, stringify(m))
  end
  
  if #new > 0 then
    Config.note_detection.prefixes = new
    Utils.debug_log("[Config] Note prefixes updated from YAML")
  end
end

---------------------------------------------------------
-- 模块: HEADING (标题处理)
-- 优化: #10 消除重复代码, #4 O(1)查找
---------------------------------------------------------

local Heading = {}

-- 注：clean_heading_number 已迁移到 heading_preprocess_filter.lua
-- 标题编号清理现由预处理过滤器统一处理

-- 检测参考文献触发词（用于样式选择，不再用于 unnumbered 属性）
-- 注：unnumbered 属性标记已迁移到 heading_preprocess_filter.lua
function Heading.is_ref_trigger(header_text)
  if not header_text or not Config.ref_trigger_set then return false end
  local h_norm = Utils.normalize_text(header_text)
  return Config.ref_trigger_set[h_norm] == true
end

function Heading.apply_h1_config(cfg, header)
  local blocks = {}
  
  if cfg and cfg.pagebreak then
    table.insert(blocks, Utils.pagebreak_block())
  end

  local real_style = nil
  if cfg and cfg.style_key then
    real_style = Config.styles[cfg.style_key]
  end

  if real_style and real_style ~= "" then
    local div = pandoc.Div({ pandoc.Para(header.content) }, { ["custom-style"] = real_style })
    table.insert(blocks, div)
  else
    table.insert(blocks, header)
  end
  
  return blocks
end

---------------------------------------------------------
-- 模块: ABSTRACT (摘要处理)
-- 优化: #9 函数职责拆分, #5 错误处理
---------------------------------------------------------

local Abstract = {}

function Abstract.is_keywords_of(nb, acfg)
  if not (nb.t == 'Para' or nb.t == 'Plain') then return false end
  local prefix = (acfg.keyword_prefix or ""):gsub("[%s　]+", "")
  if prefix == "" then return false end
  local txt = stringify(nb):gsub("[%s　]+", "")
  txt = txt:gsub("^%*%*(.-)%*%*", "%1")
  return txt:sub(1, #prefix) == prefix
end

-- 优化 #9: 职责拆分 - 步骤1
local function detect_keyword_prefix(text, expected_prefix)
  local clean_text = text:gsub("%s+", ""):lower()
  local clean_prefix = expected_prefix:gsub("%s+", ""):lower()
  
  if not clean_text:find(clean_prefix, 1, true) then return nil end
  
  local s_idx, e_idx = text:lower():find(expected_prefix:lower(), 1, true)
  if not s_idx then 
    s_idx, e_idx = text:find("[:：]")
  end
  
  return e_idx
end

-- 步骤2
local function split_keywords(content, separators)
  local clean_keywords = {}
  local temp_str = content:gsub(separators, "\0")
  
  for word in temp_str:gmatch("%z*([^%z]+)%z*") do
    word = Utils.trim(word):gsub("[%.。;；,，:：]+$", "")
    if #word > 0 then table.insert(clean_keywords, word) end
  end
  
  return clean_keywords
end

-- 步骤3
local function validate_keyword_count(keywords, range, prefix)
  if not range then return true end
  
  local min, max = range[1], range[2]
  local count = #keywords
  
  if min and count < min then
    Utils.debug_log(string.format("[Warning] Insufficient keywords for '%s': %d < %d", prefix, count, min))
    return false
  elseif max and count > max then
    Utils.debug_log(string.format("[Warning] Too many keywords for '%s': %d > %d", prefix, count, max))
    return false
  end
  
  return true
end

-- 步骤4
local function format_keywords(keywords, acfg, original_prefix)
  local separator = acfg.separator or "; "
  local final_prefix = original_prefix
  
  if acfg.bold_prefix then
    local p_trimmed = final_prefix:gsub("%s+$", "")
    final_prefix = "**" .. p_trimmed .. "** "
  end
  
  return final_prefix .. table.concat(keywords, separator)
end

-- 主函数（步骤5）
function Abstract.fix_keywords_format(block, acfg)
  if not block or not (block.t == 'Para' or block.t == 'Plain') then return block end
  
  local prefix = acfg.keyword_prefix or ""
  if prefix == "" then return block end
  
  local text = stringify(block)
  text = text:gsub("^%*%*(.-)%*%*", "%1")
  
  local end_idx = detect_keyword_prefix(text, prefix)
  if not end_idx then return block end
  
  local original_prefix = text:sub(1, end_idx)
  local raw_content = text:sub(end_idx + 1)
  
  local separators = acfg.dirty_separators or "[,，;；、|/.]"
  local keywords = split_keywords(raw_content, separators)
  
  if #keywords == 0 then
    Utils.debug_log("[Error] No keywords found after splitting")
    return block
  end
  
  validate_keyword_count(keywords, acfg.validate_range, prefix)
  
  local final_text = format_keywords(keywords, acfg, original_prefix)
  
  local success, new_doc = pcall(function() 
    return pandoc.read(final_text, 'markdown') 
  end)
  
  if success and new_doc and #new_doc.blocks > 0 then
    Utils.debug_log(string.format("[Keywords] Formatted: %d keywords", #keywords))
    if block.t == 'Para' then 
      return pandoc.Para(new_doc.blocks[1].content)
    else 
      return pandoc.Plain(new_doc.blocks[1].content) 
    end
  else
    Utils.debug_log("[Error] Failed to parse formatted keywords: " .. tostring(new_doc))
    return block
  end
end

---------------------------------------------------------
-- 模块: NOTES (图表注处理)
-- 优化: #5 错误处理增强
---------------------------------------------------------

local Notes = {}

function Notes.is_note_text(text)
  local s = Utils.ltrim(text or "")
  if s == "" then return false end
  
  local s_lower = s:lower()
  
  for _, prefix in ipairs(Config.note_detection.prefixes) do
    local p_lower = prefix:lower()
    if #p_lower > 0 and s_lower:sub(1, #p_lower) == p_lower then
      return true
    end
  end
  return false
end

function Notes.is_figure_or_table(block)
  if not block then return false end
  if block.t == "Table" or block.t == "Figure" then return true end
  
  if block.t == "Div" then
    local id = block.identifier or (block.attr and block.attr.identifier) or ""
    if id:match("^fig:") or id:match("^tbl:") or id:match("^lst:") then return true end
  end

  if block.t == "Para" and #block.content == 1 and block.content[1].t == "Image" then
    return true
  end
  
  if block.t == "CodeBlock" then
    return true
  end
  
  return false
end

function Notes.wrap_notes(blocks)
  local out = {}
  local i = 1
  local style_name = Config.styles.figure_note
  local wrapped_count = 0

  while i <= #blocks do
    local b = blocks[i]
    
    if not b or not b.t then
      Utils.debug_log("[Warning] Invalid block at index " .. i)
      i = i + 1
      goto continue
    end
    
    if b.t == "Para" and i > 1 and Notes.is_figure_or_table(blocks[i-1]) and Notes.is_note_text(stringify(b)) then
      local grouped = { b }
      local j = i + 1
      
      while j <= #blocks and blocks[j].t == "Para" and Notes.is_note_text(stringify(blocks[j])) do
        table.insert(grouped, blocks[j])
        j = j + 1
      end
      
      local attr = pandoc.Attr("", {}, { ["custom-style"] = style_name })
      table.insert(out, pandoc.Div(grouped, attr))
      wrapped_count = wrapped_count + 1
      Utils.debug_log(string.format("[Notes] Wrapped %d note paragraphs", #grouped))
      i = j
    else
      table.insert(out, b)
      i = i + 1
    end
    
    ::continue::
  end
  
  if wrapped_count > 0 then
    Utils.debug_log(string.format("[Notes] Total wrapped groups: %d", wrapped_count))
  end
  
  return out
end

---------------------------------------------------------
-- 模块: LIST (列表处理)
---------------------------------------------------------

local List = {}

function List.style_list_items(list)
  if not Config.styles.list_paragraph then return list end
  
  local item_count = 0
  
  for i, item in ipairs(list.content) do
    for j, block in ipairs(item) do
      if block.t == "Para" then
        local div = pandoc.Div({ block }, { ["custom-style"] = Config.styles.list_paragraph })
        item[j] = div
        item_count = item_count + 1
      elseif block.t == "Plain" then
        local para = pandoc.Para(block.content)
        local div = pandoc.Div({ para }, { ["custom-style"] = Config.styles.list_paragraph })
        item[j] = div
        item_count = item_count + 1
      end
    end
  end
  
  if item_count > 0 then
    Utils.debug_log(string.format("[List] Styled %d list items", item_count))
  end
  
  return list
end

---------------------------------------------------------
-- 优化 #15: 进度反馈系统
---------------------------------------------------------

local Progress = {
  total = 0,
  current = 0,
  last_percent = 0
}

function Progress:init(total)
  self.total = total
  self.current = 0
  self.last_percent = 0
  Utils.debug_log(string.format("[Progress] Processing %d blocks", total))
end

function Progress:update(stage)
  self.current = self.current + 1
  local percent = math.floor((self.current / self.total) * 100)
  
  if percent >= self.last_percent + CONSTANTS.PROGRESS_UPDATE_INTERVAL or self.current == self.total then
    Utils.debug_log(string.format("[Progress] %d%% - %s", percent, stage))
    self.last_percent = percent
  end
end

---------------------------------------------------------
-- 全局过滤器（元素级别）
---------------------------------------------------------

function Para(elem)
  if not Config.cleaning.convert_softbreak then return nil end
  
  local has_sb = false
  for _, c in ipairs(elem.content) do
    if c.t == 'SoftBreak' then has_sb = true; break end
  end
  if not has_sb then return nil end

  local parts = {}
  local current = {}
  
  for _, c in ipairs(elem.content) do
    if c.t == 'SoftBreak' then
      if #current > 0 then
        table.insert(parts, pandoc.Para(current))
        current = {}
      end
    else
      table.insert(current, c)
    end
  end
  
  if #current > 0 then
    table.insert(parts, pandoc.Para(current))
  end
  
  if #parts > 1 then return parts end
  return nil
end

function CodeBlock(elem)
  if elem.classes and #elem.classes > 0 then
    Utils.debug_log("[CodeBlock] Removing language identifier: " .. table.concat(elem.classes, ", "))
    elem.classes = {}
  end
  return elem
end

---------------------------------------------------------
-- 优化 #3: 减少重复遍历 - 单次处理流水线
---------------------------------------------------------

local function single_pass_process(blocks)
  local new_blocks = {}
  local abstract_idx = 0
  local h1_idx = 0
  local is_after_ref = false
  
  local abs_cfg_list = Config.abstracts or {}
  
  Progress:init(#blocks)
  
  local i = 1
  while i <= #blocks do
    local b = blocks[i]
    
    if not b or not b.t then
      Utils.debug_log(string.format("[Warning] Invalid block at index %d", i))
      i = i + 1
      goto continue
    end
    
    -- A. 摘要处理
    if b.t == 'Header' and b.level == 2 and abstract_idx < #abs_cfg_list then
      Progress:update("Processing abstract")
      abstract_idx = abstract_idx + 1
      local acfg = abs_cfg_list[abstract_idx]
      
      local s_title = Config.styles[acfg.style_title] or "Heading 2"
      local s_body  = Config.styles[acfg.style_body]  or "Body Text"
      local s_kw    = Config.styles[acfg.style_kw]    or s_body

      table.insert(new_blocks, pandoc.Div({ pandoc.Para(b.content) }, { ["custom-style"] = s_title }))

      local abs_content = {}
      local kw_block = nil
      local j = i + 1
      while j <= #blocks do
        local nb = blocks[j]
        if nb.t == 'Header' then break
        elseif Abstract.is_keywords_of(nb, acfg) then
          kw_block = nb; j = j + 1; break
        else
          table.insert(abs_content, nb)
          j = j + 1
        end
      end
      
      table.insert(new_blocks, pandoc.Div(abs_content, { ["custom-style"] = s_body }))
      
      if kw_block then
        local fixed = Abstract.fix_keywords_format(kw_block, acfg)
        table.insert(new_blocks, pandoc.Div({ fixed }, { ["custom-style"] = s_kw }))
      end
      i = j

    -- B. H1 处理
    elseif b.t == 'Header' and b.level == 1 then
      Progress:update("Processing heading")
      h1_idx = h1_idx + 1
      local txt = stringify(b)
      
      if Heading.is_ref_trigger(txt) then
        is_after_ref = true
        Utils.debug_log("[SZCU] Reference section detected (for style selection)")
      end
      
      local target_cfg = nil
      if is_after_ref then
        target_cfg = { style_key = "h1_no_num", pagebreak = true }
      elseif Config.first and h1_idx <= #Config.first then
        target_cfg = Config.first[h1_idx]
      else
        target_cfg = Config.middle
      end

      local out = Heading.apply_h1_config(target_cfg, b)
      for _, ob in ipairs(out) do table.insert(new_blocks, ob) end
      i = i + 1

    -- C. 普通块
    else
      b = pandoc.walk_block(b, {
        Table = function(t)
          if Utils.block_has_image(t) then
            t.attr.attributes["custom-style"] = Config.styles.figure_table
            return t
          end
        end
      })
      table.insert(new_blocks, b)
      i = i + 1
    end
    
    ::continue::
  end
  
  Utils.debug_log("[Pipeline] Single-pass processing completed")
  return new_blocks
end

---------------------------------------------------------
-- 主处理函数
---------------------------------------------------------

function Pandoc(doc)
  local start_time = os.clock()
  Utils.debug_log(string.rep("=", 50))
  Utils.debug_log("[SZCU] SZCU Thesis Filter v2.1 (Style Application Layer)")
  Utils.debug_log(string.rep("=", 50))
  
  Utils.load_prefixes(doc.meta)
  
  -- 优化 #4: 构建哈希表
  Config.note_detection.prefixes_set = Utils.build_prefix_set(Config.note_detection.prefixes)
  Config.ref_trigger_set = Utils.build_prefix_set(Config.ref_trigger_titles)
  Utils.debug_log("[SZCU] Hash tables initialized for O(1) lookup")
  
  -- 注：标题编号清理已移至 heading_preprocess_filter.lua
  -- 本过滤器仅处理样式应用和业务逻辑
  
  -- 主处理流水线
  Utils.debug_log("[SZCU] Stage 1/3: Main processing pipeline")
  local new_blocks = single_pass_process(doc.blocks)
  
  -- 后处理: 包裹图表注
  Utils.debug_log("[SZCU] Stage 2/3: Wrapping figure/table notes")
  new_blocks = Notes.wrap_notes(new_blocks)
  
  -- 后处理: 列表样式映射
  Utils.debug_log("[SZCU] Stage 3/3: Styling lists")
  local temp_div = pandoc.Div(new_blocks)
  temp_div = pandoc.walk_block(temp_div, {
    BulletList = List.style_list_items,
    OrderedList = List.style_list_items
  })
  new_blocks = temp_div.content
  
  -- 优化 #15: 处理完成反馈
  local elapsed = os.clock() - start_time
  Utils.debug_log(string.rep("=", 50))
  Utils.debug_log(string.format("[Complete] Processed in %.3f seconds", elapsed))
  Utils.debug_log(string.format("[Stats] Blocks: %d → %d", #doc.blocks, #new_blocks))
  Utils.debug_log(string.rep("=", 50))
  
  return pandoc.Pandoc(new_blocks, doc.meta)
end
