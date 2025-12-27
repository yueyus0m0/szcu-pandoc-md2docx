--[[
================================================================================
文件名: heading_preprocess_filter.lua
版本: 2.0 (重构自 h1_unnumbered_filter.lua + szcu_thesis_filter_v2_merged.lua)
================================================================================

【功能概述】
标题预处理过滤器，负责在 pandoc-crossref 之前完成所有标题相关的预处理工作。

【核心功能】
1. 清理标题中的手动编号（如 "第1章 绪论" → "绪论"）
2. 为前 N 个 H1 标题自动添加 unnumbered 属性
3. 为"参考文献"及其后的所有 H1 添加 unnumbered 属性

【工作原理】
- 采用单次遍历算法，同时完成编号清理和属性标记
- 使用哈希表实现 O(1) 参考文献触发词检测
- 状态机模式跟踪文档结构（前置章节 → 主体章节 → 参考文献区域）

【配置选项】
- unnumbered_h1_count: 前几个 H1 不编号（默认 3）
- auto_clean_numbering: 是否自动清理标题编号（默认 true）
- ref_trigger_titles: 参考文献触发词列表
- debug: 调试日志开关

【执行位置】
必须在过滤器链中位于 pandoc-crossref 之前：
  Markdown → heading_preprocess_filter.lua → pandoc-crossref → szcu_thesis_filter_v2_merged.lua

【与 szcu_thesis_filter_v2_merged.lua 的职责边界】
本过滤器: 标题内容和属性预处理（清理、标记）
SZCU 过滤器: 样式应用、分页符、业务逻辑（摘要、图表、列表）

【版本历史】
v2.0 (2025-12-27): 重构自原有过滤器，采用模块化架构
- 合并 h1_unnumbered_filter.lua 的 unnumbered 属性逻辑
- 迁移 szcu_thesis_filter_v2_merged.lua 的编号清理逻辑
- 统一代码风格和架构设计

================================================================================
]]

local utils = require 'pandoc.utils'
local stringify = utils.stringify

---------------------------------------------------------
-- 模块: CONFIG (配置中心)
---------------------------------------------------------

local Config = {
  debug = true,
  auto_clean_numbering = true,
  
  -- 前 N 个 H1 自动设为 unnumbered（通常为：中文题目、英文题目、目录）
  unnumbered_h1_count = 3,
  
  -- 参考文献触发词（检测到后，该标题及其后所有 H1 都设为 unnumbered）
  ref_trigger_titles = {
    "参考文献", "References", "Reference", "Bibliography", "参考资料"
  }
}

---------------------------------------------------------
-- 模块: UTILS (工具函数)
---------------------------------------------------------

local Utils = {}

-- 文本标准化（去除空格，转小写）
function Utils.normalize_text(text)
  return (text or ""):gsub("[%s　]+", ""):lower()
end

-- 检测是否为纯编号文本
-- 原理：移除所有编号相关字符后，如果字符串为空，则认为是纯编号
-- 示例: "第1章" "1.2节" "第一章" → true
--      "第1章 绪论" "绪论" → false
function Utils.is_pure_numbering(text)
  if not text or text == "" then return false end
  
  local check = text
  check = check:gsub("^第", "")                          -- 移除前缀 "第"
  check = check:gsub("章$", ""):gsub("节$", "")          -- 移除后缀 "章" "节"
  check = check:gsub("[0-9%.]", "")                      -- 移除阿拉伯数字和点号
  check = check:gsub("[一二三四五六七八九十百]+", "")      -- 移除中文数字
  check = check:gsub("、", "")                           -- 移除顿号
  
  return check == ""
end

-- 构建哈希表（用于 O(1) 快速查找）
function Utils.build_prefix_set(prefixes)
  if not prefixes then return {} end
  
  local set = {}
  for _, prefix in ipairs(prefixes) do
    local key = Utils.normalize_text(prefix)
    if key ~= "" then
      set[key] = true
    end
  end
  return set
end

-- 调试日志输出
function Utils.debug_log(msg)
  if Config.debug then
    io.stderr:write(msg .. "\n")
  end
end

---------------------------------------------------------
-- 模块: HEADING (标题处理)
---------------------------------------------------------

local Heading = {}

-- 清理标题开头的纯编号部分
-- 支持格式: "第1章 绪论" "**第1章** 绪论" "1.2 背景" "3.1.1技术可行性"
-- 处理逻辑:
--   1. 检测第一个元素是否为纯编号
--   2. 如果在 Strong 标签内，移除 Strong 内的编号
--   3. 如果 Strong 标签变空，移除整个 Strong 元素
--   4. 清理标题开头的空格
function Heading.clean_heading_number(block)
  if block.t ~= "Header" or #block.content == 0 then return end
  
  local first_elem = block.content[1]
  local text_to_check = nil
  local is_bold = false
  
  -- 检测第一个元素是否为粗体包裹的文本
  if first_elem.t == "Strong" and #first_elem.content > 0 then
    local inner_first = first_elem.content[1]
    if inner_first.t == "Str" then
      text_to_check = inner_first.text
      is_bold = true
    end
  elseif first_elem.t == "Str" then
    text_to_check = first_elem.text
  end
  
  if not text_to_check then return end
  
  -- 如果是纯编号，则移除
  if Utils.is_pure_numbering(text_to_check) then
    Utils.debug_log(string.format("[Preprocess] Removing numbering: '%s'", text_to_check))
    
    if is_bold then
      -- 移除粗体内的编号文本
      table.remove(first_elem.content, 1)
      -- 移除紧随的空格
      while #first_elem.content > 0 and first_elem.content[1].t == "Space" do
        table.remove(first_elem.content, 1)
      end
      -- 如果粗体标签已空，移除整个 Strong 元素
      if #first_elem.content == 0 then
        table.remove(block.content, 1)
      end
    else
      -- 直接移除编号
      table.remove(block.content, 1)
    end
    
    -- 清理标题开头的空格
    while #block.content > 0 and block.content[1].t == "Space" do
      table.remove(block.content, 1)
    end
  end
end

-- 检测是否为参考文献触发词
function Heading.is_ref_trigger(header_text, trigger_set)
  if not header_text or not trigger_set then return false end
  local h_norm = Utils.normalize_text(header_text)
  return trigger_set[h_norm] == true
end

---------------------------------------------------------
-- 全局状态
---------------------------------------------------------

local h1_count = 0           -- H1 计数器
local is_after_ref = false   -- 是否已进入参考文献区域
local ref_trigger_set = {}   -- 参考文献触发词哈希表

---------------------------------------------------------
-- 主过滤函数
---------------------------------------------------------

function Header(el)
  -- 步骤 1: 清理标题编号（所有级别的标题）
  if Config.auto_clean_numbering then
    Heading.clean_heading_number(el)
  end
  
  -- 步骤 2: H1 特殊处理
  if el.level == 1 then
    h1_count = h1_count + 1
    local text = stringify(el)
    
    -- 检测是否为参考文献标题
    if Heading.is_ref_trigger(text, ref_trigger_set) then
      is_after_ref = true
      Utils.debug_log(string.format("[Preprocess] Reference section detected at H1 #%d: '%s'", h1_count, text))
    end
    
    -- 判断是否需要添加 unnumbered 属性
    local should_be_unnumbered = false
    local reason = nil
    
    if h1_count <= Config.unnumbered_h1_count then
      should_be_unnumbered = true
      reason = string.format("front matter (H1 #%d <= %d)", h1_count, Config.unnumbered_h1_count)
    elseif is_after_ref then
      should_be_unnumbered = true
      reason = "after references"
    end
    
    -- 添加 unnumbered 类（如果尚未存在）
    if should_be_unnumbered then
      local has_unnumbered = false
      for _, cls in ipairs(el.classes) do
        if cls == "unnumbered" then
          has_unnumbered = true
          break
        end
      end
      
      if not has_unnumbered then
        table.insert(el.classes, "unnumbered")
        Utils.debug_log(string.format("[Preprocess] H1 #%d marked unnumbered (%s): '%s'", h1_count, reason, text))
      end
    else
      Utils.debug_log(string.format("[Preprocess] H1 #%d will be numbered: '%s'", h1_count, text))
    end
  end
  
  return el
end

---------------------------------------------------------
-- 文档初始化
---------------------------------------------------------

function Pandoc(doc)
  Utils.debug_log(string.rep("=", 60))
  Utils.debug_log("[Preprocess] Heading Preprocess Filter v2.0")
  Utils.debug_log(string.rep("=", 60))
  
  -- 构建参考文献触发词哈希表（O(1) 查找性能）
  ref_trigger_set = Utils.build_prefix_set(Config.ref_trigger_titles)
  Utils.debug_log(string.format("[Preprocess] Reference triggers: %s", table.concat(Config.ref_trigger_titles, ", ")))
  Utils.debug_log(string.format("[Preprocess] Unnumbered H1 count: %d", Config.unnumbered_h1_count))
  Utils.debug_log(string.format("[Preprocess] Auto clean numbering: %s", tostring(Config.auto_clean_numbering)))
  
  -- 返回 nil 表示使用默认的 Header 过滤器处理
  return nil
end
