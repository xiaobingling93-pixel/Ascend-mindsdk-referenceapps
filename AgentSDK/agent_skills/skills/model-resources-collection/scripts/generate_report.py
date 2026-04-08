#!/usr/bin/env python3
"""
模型资源收集报告生成器
从JSON文件读取页面总结数据，按照output-template模板生成Markdown文档。
"""

import json
import argparse
import os
import sys
import logging
import re
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def load_template(template_path):
    """
    加载output-template模板文件

    Args:
        template_path: 模板文件路径

    Returns:
        模板文件内容字符串

    Raises:
        FileNotFoundError: 模板文件不存在时抛出
    """
    if not os.path.exists(template_path):
        raise FileNotFoundError(f"模板文件不存在: {template_path}")
    with open(template_path, 'r', encoding='utf-8') as f:
        return f.read()


def load_data(input_path):
    """加载JSON数据文件"""
    with open(input_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_item_section(items):
    """生成项目列表部分（通用函数）"""
    if not items:
        return ""

    lines = []
    for i, item in enumerate(items, 1):
        lines.append(f"### {i}. [{item.get('name', '未知')}]")
        lines.append(f"- **价格**: {item.get('price', '暂无信息')}")
        lines.append(f"- **支持的模型**: {item.get('models', '暂无信息')}")
        lines.append(f"- **套餐说明**: {item.get('description', '暂无信息')}")
        lines.append(f"- **用量限制**: {item.get('limit', '暂无信息')}")
        lines.append(f"- **额度恢复机制**: {item.get('recovery', '暂无信息')}")
        lines.append(f"- **支持的工具**: {item.get('tools', '暂无信息')}")
        lines.append(f"- **注意事项**: {item.get('notes', '暂无信息')}")
        lines.append(f"- **推荐指数**: {item.get('rating', '暂无信息')}")
        lines.append(f"- **直达链接**: {item.get('link', '#')}")
        lines.append("")

    return "\n".join(lines)


def generate_cost_effective_section(items):
    """生成性价比之选部分"""
    return generate_item_section(items)


def generate_discount_section(items):
    """生成优惠套餐部分"""
    return generate_item_section(items)


def generate_free_models_section(items):
    """生成免费模型部分"""
    if not items:
        return ""

    lines = []
    for i, item in enumerate(items, 1):
        lines.append(f"### {i}. [{item.get('name', '未知')}]")
        lines.append(f"- **提供商**: {item.get('provider', '暂无信息')}")
        lines.append(f"- **价格**: {item.get('price', '暂无信息')}")
        features = item.get('features', [])
        if features:
            lines.append(f"- **特点**: ")
            for feature in features:
                lines.append(f"  - {feature}")
        else:
            lines.append(f"- **特点**: 暂无信息")
        lines.append(f"- **使用限制**: {item.get('limits', '暂无信息')}")
        lines.append(f"- **官网**: {item.get('link', '#')}")
        lines.append("")

    return "\n".join(lines)


def generate_free_plans_section(items):
    """
    生成免费计划部分

    Args:
        items: 免费计划列表

    Returns:
        生成的Markdown格式字符串
    """
    if not items:
        return ""

    lines = []
    for i, item in enumerate(items, 1):
        lines.append(f"### {i}. {item.get('name', '未知')}")
        lines.append(f"- **免费条件**: {item.get('free_condition', '暂无信息')}")
        features = item.get('features', [])
        if features:
            lines.append("- **功能**:")
            for feature in features:
                lines.append(f"  - {feature}")
        else:
            lines.append(f"- **功能**: 暂无信息")
        lines.append(f"- **申请链接**: {item.get('link', '#')}")
        lines.append("")

    return "\n".join(lines)


def generate_verification_table(items):
    """生成信源核对表"""
    if not items:
        return "暂无信源信息"

    lines = []
    lines.append("| 序号 | 信源类别 | 信源名称 | URL | 状态 | 获取信息摘要 |")
    lines.append("|------|----------|----------|-----|------|--------------|")
    for i, item in enumerate(items, 1):
        category = item.get('category', '待确认')
        name = item.get('name', '待确认')
        url = item.get('url', '待确认')
        status = item.get('status', '⚠️')
        summary = item.get('summary', '待确认')
        lines.append(f"| {i} | {category} | {name} | {url} | {status} | {summary} |")

    return "\n".join(lines)


def generate_recommendations_section(data):
    """
    生成快速选择建议部分

    Args:
        data: 包含推荐信息的字典

    Returns:
        生成的Markdown格式字符串
    """
    recommendations = data.get('recommendations', {})

    budget_first = recommendations.get('budget_first', {})
    value_first = recommendations.get('value_first', {})
    feature_first = recommendations.get('feature_first', {})
    free_first = recommendations.get('free_first', {})

    lines = []
    lines.append("### 预算优先（最便宜）")
    lines.append(f"- **首选**: {budget_first.get('primary', '暂无')}")
    lines.append(f"- **次选**: {budget_first.get('secondary', '暂无')}")
    lines.append("")
    lines.append("### 性价比优先")
    lines.append(f"- **首选**: {value_first.get('primary', '暂无')}")
    lines.append(f"- **次选**: {value_first.get('secondary', '暂无')}")
    lines.append("")
    lines.append("### 功能全面")
    lines.append(f"- **首选**: {feature_first.get('primary', '暂无')}")
    lines.append(f"- **次选**: {feature_first.get('secondary', '暂无')}")
    lines.append("")
    lines.append("### 免费方案")
    lines.append(f"- **首选**: {free_first.get('primary', '暂无')}")
    lines.append(f"- **特定人群**: {free_first.get('specific', '暂无')}")

    return "\n".join(lines)


def generate_report(data, template_path=None):
    """
    根据数据和模板生成报告

    Args:
        data: 包含页面总结数据的字典
        template_path: 模板文件路径（可选）

    Returns:
        生成的Markdown文档内容
    """
    # 获取当前日期
    date = data.get('date', datetime.now(timezone.utc).strftime('%Y-%m-%d'))

    # 生成各部分内容
    cost_effective = generate_cost_effective_section(data.get('cost_effective', []))
    discount_plans = generate_discount_section(data.get('discount_plans', []))
    free_models = generate_free_models_section(data.get('free_models', []))
    free_plans = generate_free_plans_section(data.get('free_plans', []))
    verification_table = generate_verification_table(data.get('verification_table', []))
    recommendations = generate_recommendations_section(data)

    # 如果提供了模板路径，从模板加载
    if template_path:
        template = load_template(template_path)

        # 替换模板中的占位符
        replacements = {
            '{{date}}': date,
            '{{cost_effective}}': cost_effective if cost_effective else "暂无相关信息",
            '{{discount_plans}}': discount_plans if discount_plans else "暂无相关信息",
            '{{free_models}}': free_models if free_models else "暂无相关信息",
            '{{free_plans}}': free_plans if free_plans else "暂无相关信息",
            '{{verification_table}}': verification_table,
            '{{recommendations}}': recommendations,
        }

        report = template
        for placeholder, value in replacements.items():
            report = report.replace(placeholder, value)

        # 清理未替换的占位符
        report = re.sub(r'\{\{[^}]+\}\}', '待确认', report)
    else:
        # 使用默认内嵌格式（兼容旧版本）
        report = f"""# 模型资源收集指南

> 生成日期: {date}

> **注意**: 以下信息基于公开资料整理，具体优惠以各平台官方最新公告为准。

## 一、性价比之选

{cost_effective if cost_effective else "暂无相关信息"}

## 二、优惠套餐

{discount_plans if discount_plans else "暂无相关信息"}

## 三、免费模型

{free_models if free_models else "暂无相关信息"}

## 四、免费计划

{free_plans if free_plans else "暂无相关信息"}

## 五、快速选择建议

{recommendations}

## 六、信源核对表

{verification_table}

## 七、注意事项

1. 免费额度可能有变化，请以官方最新公告为准
2. 某些服务可能有地区限制
3. 使用前请仔细阅读服务条款
4. 建议优先使用免费额度测试后再充值
5. Coding Plan仅限在编程工具中使用，禁止API调用
6. 套餐为订阅人专享使用，禁止共享
7. Coding Plan不支持退款
8. 使用期间模型输入输出用于服务改进
9. 特惠活动名额有限，先到先得

---
"""

    return report


def main():
    parser = argparse.ArgumentParser(description='模型资源收集报告生成器')
    parser.add_argument('--input', '-i', required=True, help='输入的JSON数据文件路径')
    parser.add_argument('--output', '-o', required=True, help='输出的Markdown文件路径')
    parser.add_argument('--template', '-t', help='模板文件路径（可选）')

    args = parser.parse_args()

    # 检查输入文件是否存在
    if not os.path.exists(args.input):
        logger.error(f"输入文件不存在: {args.input}")
        sys.exit(1)

    # 加载数据
    try:
        data = load_data(args.input)
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"读取输入文件失败: {e}")
        sys.exit(1)

    # 生成报告
    report = generate_report(data, args.template)

    # 确保输出目录存在
    output_dir = os.path.dirname(args.output)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    # 写入文件
    try:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(report)
        logger.info(f"报告已生成: {args.output}")
    except Exception as e:
        logger.error(f"写入输出文件失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()