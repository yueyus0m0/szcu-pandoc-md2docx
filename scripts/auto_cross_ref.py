#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_cross_ref.py - 双花括号占位符自动处理脚本

功能：
1. 自动为图片、表格、代码块生成唯一ID（基于名称+序号）
2. 替换用户友好的占位符 {{type:名称}} 为标准Pandoc引用 @type:名称_N

用户语法：
  图片：![图名](path)         → 添加 {#fig:图名_1}
  表格：Table: 表名            → 添加 {#tbl:表名_1}
  代码：{caption="代码名"}    → 添加 #lst:代码名_1
  
  引用：{{fig:图名}}          → @fig:图名_1
  引用：{{tbl:表名}}          → @tbl:表名_1
  引用：{{lst:代码名}}        → @lst:代码名_1
  
  注：引用语法支持全角花括号 ｛｛ ｝｝ 和半角花括号 {{ }}

用法：
    python auto_cross_ref.py <markdown文件> [选项]
    
选项：
    -o, --output FILE    输出文件（默认覆盖原文件）
    -v, --verbose        显示详细处理过程
    --dry-run           只检查不修改
    -h, --help          显示帮助信息

示例：
    python auto_cross_ref.py main.md
    python auto_cross_ref.py main.md -o output.md --verbose
"""

import re
import sys
import argparse
from collections import defaultdict
from typing import List, Dict, Tuple


def sanitize_id_name(name: str) -> str:
    """
    清理ID名称，确保ID兼容性
    
    规则：
    - 保留：数字(0-9)、英文字母(a-z A-Z)、汉字(U+4E00-U+9FFF)
    - 替换：所有其他字符 → 下划线 _
    - 清理：连续下划线 → 单个下划线
    - 去除：首尾的下划线
    - 统一：所有ID都添加 id_ 前缀
    
    示例：
        "系统架构图" → "id_系统架构图"
        "用户（管理）界面" → "id_用户_管理_界面"
        "Test-v2.0" → "id_Test_v2_0"
        "数据 流程 图" → "id_数据_流程_图"
        "100%完成" → "id_100_完成"
        "API-v2" → "id_API_v2"
    """
    # 1. 只保留数字、英文字母、汉字，其他字符替换为下划线
    # 数字：0-9
    # 英文字母：a-zA-Z
    # 汉字范围：\u4e00-\u9fff
    cleaned = re.sub(r'[^0-9a-zA-Z\u4e00-\u9fff]', '_', name)
    
    # 2. 清理连续的下划线为单个
    cleaned = re.sub(r'_+', '_', cleaned)
    
    # 3. 去除首尾的下划线
    cleaned = cleaned.strip('_')
    
    # 4. 处理边缘情况
    if not cleaned:
        # 如果清理后为空，使用默认名称
        cleaned = "unnamed"
    
    # 5. 统一添加 id_ 前缀
    return "id_" + cleaned


class CrossRefProcessor:
    """交叉引用处理器"""
    
    def __init__(self, verbose=False, dry_run=False):
        self.verbose = verbose
        self.dry_run = dry_run
        
        # 定义记录：{type: {cleaned_name: [def1, def2, ...]}}
        # 每个def是字典：{'line_num': int, 'seq': int, 'id_str': str}
        self.definitions = {
            'fig': {},  # 图片定义
            'tbl': {},  # 表格定义
            'lst': {}   # 代码块定义
        }
        
        # 统计信息
        self.stats = {
            'figures': 0,
            'tables': 0,
            'listings': 0,
            'refs_replaced': 0,
            'warnings': []
        }
    
    # ==================== 辅助方法 ====================
    
    def _has_id_marker(self, line: str, id_type: str) -> bool:
        """
        检查行中是否已有指定类型的ID标记
        
        Args:
            line: 要检查的行
            id_type: ID类型 ('fig', 'tbl', 'lst')
        
        Returns:
            如果已有ID标记返回True，否则False
        """
        return f'#{id_type}:' in line
    
    def _generate_id(self, name: str, elem_type: str, line_num: int) -> Tuple[str, str, int]:
        """
        生成ID并记录到definitions
        
        Args:
            name: 原始名称
            elem_type: 元素类型 ('fig', 'tbl', 'lst')
            line_num: 定义所在行号
        
        Returns:
            (完整ID字符串, 清理后的名称, 序号)
            例如: ('fig:id_系统架构图_1', 'id_系统架构图', 1)
        """
        cleaned_name = sanitize_id_name(name)
        
        # 初始化该名称的定义列表
        if cleaned_name not in self.definitions[elem_type]:
            self.definitions[elem_type][cleaned_name] = []
        
        # 序号 = 已有定义数 + 1
        seq = len(self.definitions[elem_type][cleaned_name]) + 1
        id_str = f"{elem_type}:{cleaned_name}_{seq}"
        
        # 记录定义
        self.definitions[elem_type][cleaned_name].append({
            'line_num': line_num,
            'seq': seq,
            'id_str': id_str
        })
        
        return id_str, cleaned_name, seq
    
    def _log_element_processed(self, line_num: int, elem_type: str, 
                               name: str, id_str: str = '', skipped: bool = False):
        """
        记录元素处理日志
        
        Args:
            line_num: 行号
            elem_type: 元素类型 ('fig', 'tbl', 'lst')
            name: 元素名称
            id_str: 生成的ID（仅在skipped=False时需要）
            skipped: 是否跳过处理
        """
        type_labels = {'fig': '图片', 'tbl': '表格', 'lst': '代码'}
        label = type_labels.get(elem_type, elem_type)
        
        if skipped:
            self.log(f"  Line {line_num}: {label} '{name}' 已有ID，跳过")
        else:
            self.log(f"  Line {line_num}: ✅ {label} '{name}' → {id_str}")
    
    def _find_nearest(self, definitions: list, ref_line_num: int) -> dict:
        """
        找到最近的定义（支持向前和向后引用）
        
        Args:
            definitions: 同名定义列表 [{'line_num': 15, 'seq': 1, ...}, ...]
            ref_line_num: 引用所在行号
        
        Returns:
            最近的定义字典
        
        匹配策略：
        1. 优先向前找（引用前面最近的定义）
        2. 如果没有向前的，找向后最近的（向后引用）
        """
        # 向前找（引用前面的定义）
        before = [d for d in definitions if d['line_num'] < ref_line_num]
        if before:
            # 返回距离最近的（行号最大的）
            return max(before, key=lambda d: d['line_num'])
        
        # 向后找（引用后面的定义）
        after = [d for d in definitions if d['line_num'] > ref_line_num]
        if after:
            # 返回距离最近的（行号最小的）
            return min(after, key=lambda d: d['line_num'])
        
        # 理论上不应该到这里（definitions不应为空）
        return definitions[0] if definitions else None
    
    # ==================== 主要处理方法 ====================
    
    def _preprocess_multiline_attrs(self, lines: List[str]) -> List[str]:
        """预处理：合并跨行的属性块
        
        将类似这样的跨行属性：
            ![图名](path){width="..."
            height="..."}
        合并为单行：
            ![图名](path){width="..." height="..."}
        """
        processed = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # 检查是否是图片行且属性块未闭合
            # 匹配：![...](...){... 但没有闭合的 }
            if re.search(r'!\[([^\]]+)\]\([^)]+\)\{[^}]*$', line.rstrip()):
                # 找到未闭合的属性块，需要合并后续行
                combined = line.rstrip()
                i += 1
                
                # 继续读取直到找到闭合的 }
                while i < len(lines):
                    next_line = lines[i].strip()
                    combined += ' ' + next_line
                    
                    # 检查是否已闭合
                    if '}' in next_line:
                        break
                    i += 1
                
                processed.append(combined + '\n')
                i += 1
            else:
                # 普通行，直接添加
                processed.append(line)
                i += 1
        
        return processed
    
    def process_file(self, input_path: str, output_path: str = None):
        """处理文件主函数"""
        self.log(f"📂 读取文件: {input_path}")
        
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except FileNotFoundError:
            print(f"❌ 错误：文件 '{input_path}' 不存在")
            sys.exit(1)
        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
            sys.exit(1)
        
        self.log(f"📊 总行数: {len(lines)}")
        
        # 预处理：合并跨行属性块
        self.log("\n🔧 预处理：合并跨行属性块...")
        lines = self._preprocess_multiline_attrs(lines)
        self.log(f"   处理后行数: {len(lines)}")
        
        # 第一遍：收集所有定义并添加ID
        self.log("\n🔍 第一遍：收集定义并生成ID...")
        lines_with_ids = self._collect_and_add_ids(lines)
        
        # 第二遍：替换所有引用
        self.log("\n✏️  第二遍：替换引用...")
        final_lines = self._replace_all_references(lines_with_ids)
        
        # 保存结果
        if not self.dry_run:
            output_path = output_path or input_path
            with open(output_path, 'w', encoding='utf-8') as f:
                f.writelines(final_lines)
            self.log(f"\n💾 已保存到: {output_path}")
        else:
            self.log("\n🔍 [Dry Run] 未保存任何更改")
        
        # 打印报告
        self._print_report()
    
    def _collect_and_add_ids(self, lines: List[str]) -> List[str]:
        """第一遍：收集所有定义并生成ID"""
        new_lines = []
        
        for i, line in enumerate(lines, 1):
            new_line = line
            
            # 处理图片
            new_line, added = self._add_id_to_figure(new_line, i)
            if added:
                new_lines.append(new_line)
                continue
            
            # 处理表格
            new_line, added = self._add_id_to_table(new_line, i)
            if added:
                new_lines.append(new_line)
                continue
            
            # 处理代码块
            new_line, added = self._add_id_to_listing(new_line, i)
            if added:
                new_lines.append(new_line)
                continue
            
            # 没有添加ID，保持原样
            new_lines.append(line)
        
        return new_lines
    
    def _replace_all_references(self, lines: List[str]) -> List[str]:
        """第二遍：替换所有引用占位符 {{type:name}}"""
        new_lines = []
        
        for i, line in enumerate(lines, 1):
            new_line = self._replace_placeholders(line, i)
            new_lines.append(new_line)
        
        return new_lines
    
    def _add_id_to_figure(self, line: str, line_num: int) -> Tuple[str, bool]:
        """为图片添加ID，支持带属性块的图片"""
        # 匹配图片语法：![name](path) 或 ![name](path){...}
        # 分两种情况：
        # 1. ![name](path){existing attrs}  - 已有属性块
        # 2. ![name](path)                  - 无属性块
        
        # 先尝试匹配带属性块的情况
        pattern_with_attrs = r'(!\[([^\]]+)\]\([^)]+\))(\{([^}]+)\})'
        match = re.search(pattern_with_attrs, line)
        
        if match:
            # 情况1: 已有属性块
            img_part = match.group(1)  # ![name](path)
            name = match.group(2).strip()
            full_attrs_block = match.group(3)  # {attrs}
            attrs_content = match.group(4)  # attrs内容
            
            # 检查是否已有ID
            if self._has_id_marker(attrs_content, 'fig'):
                self._log_element_processed(line_num, 'fig', name, skipped=True)
                return line, False
            
            # 生成ID
            id_str, cleaned_name, seq = self._generate_id(name, 'fig', line_num)
            
            # 将ID添加到属性块内部的最前面
            new_attrs = f"{{#{id_str} {attrs_content}}}"
            new_line = line.replace(
                f"{img_part}{full_attrs_block}",
                f"{img_part}{new_attrs}"
            )
            
            # 更新统计和日志
            self.stats['figures'] += 1
            self._log_element_processed(line_num, 'fig', name, id_str)
            
            return new_line, True
        
        # 尝试匹配无属性块的情况
        pattern_no_attrs = r'(!\[([^\]]+)\]\([^)]+\))(?!\{)'
        match = re.search(pattern_no_attrs, line)
        
        if match:
            # 情况2: 无属性块
            full_match = match.group(1)
            name = match.group(2).strip()
            
            # 检查是否已有ID（虽然理论上不应该有）
            if self._has_id_marker(line, 'fig'):
                self._log_element_processed(line_num, 'fig', name, skipped=True)
                return line, False
            
            # 生成ID
            id_str, cleaned_name, seq = self._generate_id(name, 'fig', line_num)
            
            # 添加新的属性块
            new_line = line.replace(full_match, f"{full_match}{{#{id_str}}}")
            
            # 更新统计和日志
            self.stats['figures'] += 1
            self._log_element_processed(line_num, 'fig', name, id_str)
            
            return new_line, True
        
        return line, False
    
    def _add_id_to_table(self, line: str, line_num: int) -> Tuple[str, bool]:
        """为表格添加ID"""
        # 匹配表格语法：Table: name
        if match := re.search(r'(Table:\s*)([^\{]+)', line):
            prefix = match.group(1)
            name = match.group(2).strip()
            
            # 检查是否已有ID
            if self._has_id_marker(line, 'tbl'):
                self._log_element_processed(line_num, 'tbl', name, skipped=True)
                return line, False
            
            # 生成ID
            id_str, cleaned_name, seq = self._generate_id(name, 'tbl', line_num)
            
            # 添加ID：Table: name → Table: name {#tbl:id_name_1}
            new_line = line.replace(
                f"{prefix}{name}",
                f"{prefix}{name} {{#{id_str}}}"
            )
            
            # 更新统计和日志
            self.stats['tables'] += 1
            self._log_element_processed(line_num, 'tbl', name, id_str)
            
            return new_line, True
        
        return line, False
    
    def _add_id_to_listing(self, line: str, line_num: int) -> Tuple[str, bool]:
        """为代码块添加ID，支持带/不带空格的属性块"""
        # 匹配代码块：```lang {caption="name"} 或 ```{caption="name"} 或 ```lang{caption="name"}
        # 关键：空格是可选的（\s*）
        if match := re.search(
            r'(```([^\n{]*?))(\s*)(\{([^}]*caption=["\']([^"\'}]+)["\'][^}]*)\})',
            line
        ):
            code_fence = match.group(1).rstrip()  # ``` 或 ```python（去除尾部空格）
            lang = match.group(2).strip()  # 语言标识符（可能为空）
            spacing = match.group(3)  # 中间的空格（可能为空）
            full_attrs_block = match.group(4)  # {attrs} 整个属性块（不含括号）
            attrs = match.group(5)  # 属性块内容（不含括号）
            name = match.group(6).strip()  # caption的值
            
            # 检查是否已有ID
            if self._has_id_marker(attrs, 'lst'):
                self._log_element_processed(line_num, 'lst', name, skipped=True)
                return line, False
            
            # 生成ID
            id_str, cleaned_name, seq = self._generate_id(name, 'lst', line_num)
            
            # 重构属性：ID必须在最前面
            # {caption="..."} → {#lst:id_name_1 caption="..."}
            new_attrs = f"#{id_str} {attrs}"
            new_code_fence = f"{code_fence}{{{new_attrs}}}"
            
            new_line = line.replace(match.group(0), new_code_fence)
            
            # 更新统计和日志
            self.stats['listings'] += 1
            self._log_element_processed(line_num, 'lst', name, id_str)
            
            return new_line, True
        
        return line, False
    
    def _replace_placeholders(self, line: str, line_num: int) -> str:
        """
        替换占位符 {{type:name}} 为 @type:name_N
        
        支持向前和向后引用，智能匹配最近的定义
        """
        
        def replace_match(match):
            ref_type = match.group(1).lower()  # 统一转换为小写：fig, tbl, lst
            name = match.group(2).strip()
            
            # 清理名称
            cleaned_name = sanitize_id_name(name)
            
            # 查找定义
            if cleaned_name not in self.definitions[ref_type]:
                # ❌ 未找到定义
                type_labels = {'fig': '图片', 'tbl': '表格', 'lst': '代码'}
                label = type_labels.get(ref_type, ref_type)
                
                # 简短警告（用于最终报告）
                short_warning = f"Line {line_num}: ❌ 找不到{label}引用 '{name}'"
                
                # 详细警告（用于详细日志）
                detailed_warning = (
                    f"{short_warning} 的定义\n"
                    f"           引用: {{{{{ref_type}:{name}}}}}\n"
                    f"           清理后名称: '{cleaned_name}'\n"
                    f"           请检查是否拼写错误或缺少定义"
                )
                
                self.stats['warnings'].append(short_warning)
                self.log(f"  ⚠️  {detailed_warning}")
                return match.group(0)  # 保持原样，不替换
            
            defs = self.definitions[ref_type][cleaned_name]
            
            # 判断唯一性
            if len(defs) == 1:
                # ✅ 唯一定义，直接使用
                matched = defs[0]
                id_str = matched['id_str']
                self.log(f"  Line {line_num}: 引用 {{{{{ref_type}:{name}}}}} → @{id_str} (唯一)")
            else:
                # 🔍 多个定义，找最近的
                matched = self._find_nearest(defs, line_num)
                if matched is None:
                    # 理论上不应该发生
                    warning = f"Line {line_num}: 内部错误 - 找不到匹配的定义"
                    self.stats['warnings'].append(warning)
                    self.log(f"  ⚠️  {warning}")
                    return match.group(0)
                
                id_str = matched['id_str']
                direction = "向前" if matched['line_num'] < line_num else "向后"
                self.log(
                    f"  Line {line_num}: 引用 {{{{{ref_type}:{name}}}}} → @{id_str} "
                    f"({direction}匹配，从{len(defs)}个中选择，距离: {abs(matched['line_num'] - line_num)}行)"
                )
            
            # 生成标准引用，前后保证有空格
            ref = f" @{id_str} "
            
            self.stats['refs_replaced'] += 1
            
            return ref
        
        # 匹配 {{fig:名称}}, {{tbl:名称}}, {{lst:名称}}
        # 支持全角花括号 ｛｝ 和半角花括号 {}
        # 支持大小写不敏感的类型名称和全角半角冒号
        pattern = r'[{｛][{｛](fig|tbl|lst)[:：]([^}｝]+)[}｝][}｝]'
        
        return re.sub(pattern, replace_match, line, flags=re.IGNORECASE)
    
    def _print_report(self):
        """打印处理报告"""
        print("\n" + "="*60)
        print("📊 处理报告")
        print("="*60)
        
        print(f"\n✅ 已处理元素:")
        print(f"  📷 图片 (Figure):  {self.stats['figures']} 个")
        print(f"  📋 表格 (Table):   {self.stats['tables']} 个")
        print(f"  💻 代码 (Listing): {self.stats['listings']} 个")
        print(f"  ──────────────────────────")
        print(f"  📌 总计:           {sum([self.stats['figures'], self.stats['tables'], self.stats['listings']])} 个")
        
        print(f"\n🔗 引用替换:")
        print(f"  替换数量: {self.stats['refs_replaced']} 个")
        
        # 显示重名统计（从definitions获取）
        duplicates = {}
        for type_name, names_dict in self.definitions.items():
            duplicates[type_name] = {
                name: len(defs) 
                for name, defs in names_dict.items() 
                if len(defs) > 1
            }
        
        has_duplicates = any(duplicates.values())
        if has_duplicates:
            print(f"\n⚠️  检测到重名:")
            for type_name, names in duplicates.items():
                if names:
                    type_label = {'fig': '图片', 'tbl': '表格', 'lst': '代码'}[type_name]
                    for name, count in names.items():
                        print(f"  {type_label} \"{name}\": {count} 次")
                        print(f"    → 已生成: {type_name}:{name}_1, _{2}, ... _{count}")
        
        # 显示警告
        if self.stats['warnings']:
            print(f"\n⚠️  警告 ({len(self.stats['warnings'])} 个):")
            for warning in self.stats['warnings']:
                print(f"  {warning}")
        
        print("\n" + "="*60)
        if self.dry_run:
            print("🔍 [Dry Run] 未保存任何更改")
        else:
            print("✅ 处理完成！")
        print("="*60)
    
    def log(self, message: str):
        """输出日志"""
        if self.verbose:
            print(message)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='自动处理Markdown文件中的交叉引用占位符',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s main.md
  %(prog)s main.md -o output.md
  %(prog)s main.md --verbose
  %(prog)s main.md --dry-run
        """
    )
    
    parser.add_argument(
        'input',
        help='输入的Markdown文件'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='输出文件（默认覆盖输入文件）'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细处理过程'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='只检查不修改文件'
    )
    
    args = parser.parse_args()
    
    # 创建处理器
    processor = CrossRefProcessor(
        verbose=args.verbose,
        dry_run=args.dry_run
    )
    
    # 处理文件
    processor.process_file(args.input, args.output)


if __name__ == '__main__':
    main()
