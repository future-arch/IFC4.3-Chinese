#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复 annex-d.html - 保留中文版框架，插入完整的图表列表
"""

import requests
import re
from pathlib import Path

# 文件路径
CHINESE_ANNEX_D = Path("/Users/weilai/Documents/devs/IFC-4-3-Chinese/IFC/RELEASE/IFC4x3/HTML/annex-d.html")
GITHUB_URL = "https://raw.githubusercontent.com/buildingSMART/IFC4.3-html/main/IFC/RELEASE/IFC4x3/HTML/annex-d.html"

def main():
    print("1. 读取中文版 annex-d.html...")
    with open(CHINESE_ANNEX_D, 'r', encoding='utf-8') as f:
        chinese_content = f.read()

    print("2. 下载 GitHub 版本...")
    response = requests.get(GITHUB_URL, timeout=30)
    response.raise_for_status()
    github_content = response.text

    print("3. 提取图表列表...")
    # 提取 GitHub 版本中的 <ol class="referenced-list">...</ol> 内容
    match = re.search(r'<ol class="referenced-list">(.*?)</ol>', github_content, re.DOTALL)
    if not match:
        print("❌ 无法从 GitHub 版本提取图表列表")
        return 1

    diagram_list = match.group(1).strip()
    print(f"   找到 {diagram_list.count('<li')} 个图表链接")

    print("4. 替换中文版中的空列表...")
    # 替换中文版中的空 <ol class="referenced-list"></ol>
    new_content = re.sub(
        r'<ol class="referenced-list">\s*</ol>',
        f'<ol class="referenced-list">\n{diagram_list}\n</ol>',
        chinese_content
    )

    if new_content == chinese_content:
        print("❌ 未找到要替换的空列表")
        return 1

    print("5. 保存更新后的文件...")
    with open(CHINESE_ANNEX_D, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print("✅ annex-d.html 已成功更新！")
    print(f"   文件大小: {CHINESE_ANNEX_D.stat().st_size / 1024:.1f} KB")

    return 0

if __name__ == "__main__":
    exit(main())
