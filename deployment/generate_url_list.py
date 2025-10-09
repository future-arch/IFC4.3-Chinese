#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成所有需要爬取的 URL 列表

从源数据文件中提取所有实体、类型、属性集等，生成完整的 URL 列表
"""

import json
import sys
from pathlib import Path

# 源数据目录
SOURCE_DIR = Path("/Users/weilai/Documents/devs/IFC4-3-x-development/code_zh")
BASE_URL = "http://127.0.0.1:5050"

def generate_urls():
    """生成所有URL"""
    urls = set()

    # 基础页面
    basic_pages = [
        "/",
        "/IFC/RELEASE/IFC4x3/HTML/index.htm",
        "/IFC/RELEASE/IFC4x3/HTML/toc.html",
        "/IFC/RELEASE/IFC4x3/HTML/annex-a.html",
        "/IFC/RELEASE/IFC4x3/HTML/annex-b.html",
        "/IFC/RELEASE/IFC4x3/HTML/annex-c.html",
        "/IFC/RELEASE/IFC4x3/HTML/annex-d.html",
        "/IFC/RELEASE/IFC4x3/HTML/annex-e.html",
        "/IFC/RELEASE/IFC4x3/HTML/content/foreword.htm",
        "/IFC/RELEASE/IFC4x3/HTML/content/introduction.htm",
        "/IFC/RELEASE/IFC4x3/HTML/content/scope.htm",
        "/IFC/RELEASE/IFC4x3/HTML/content/normative_references.htm",
        "/IFC/RELEASE/IFC4x3/HTML/content/terms_and_definitions.htm",
        "/IFC/RELEASE/IFC4x3/HTML/content/bibliography.htm",
    ]

    for page in basic_pages:
        urls.add(f"{BASE_URL}{page}")

    # 章节页面
    for i in range(1, 9):
        urls.add(f"{BASE_URL}/IFC/RELEASE/IFC4x3/HTML/chapter-{i}/")

    # 从 entity_definitions.json 读取所有实体
    entity_file = SOURCE_DIR / "entity_definitions.json"
    if entity_file.exists():
        with open(entity_file, 'r', encoding='utf-8') as f:
            entities = json.load(f)
            for entity_name in entities.keys():
                urls.add(f"{BASE_URL}/IFC/RELEASE/IFC4x3/HTML/lexical/{entity_name}.htm")

    # 从 pset_definitions.json 读取所有属性集
    pset_file = SOURCE_DIR / "pset_definitions.json"
    if pset_file.exists():
        with open(pset_file, 'r', encoding='utf-8') as f:
            psets = json.load(f)
            for pset_name in psets.keys():
                urls.add(f"{BASE_URL}/IFC/RELEASE/IFC4x3/HTML/lexical/{pset_name}.htm")

    # 从 type_values.json 读取所有类型枚举
    type_file = SOURCE_DIR / "type_values.json"
    if type_file.exists():
        with open(type_file, 'r', encoding='utf-8') as f:
            types = json.load(f)
            for type_name in types.keys():
                urls.add(f"{BASE_URL}/IFC/RELEASE/IFC4x3/HTML/lexical/{type_name}.htm")

    # Schema 模块页面 - 完整列表
    schema_modules = [
        # Core schemas
        "ifckernel", "ifccontrolextension", "ifcprocessextension", "ifcproductextension",

        # Resource schemas
        "ifcactorresource", "ifcapprovalresource", "ifcconstraintresource",
        "ifccostresource", "ifcdatetimeresource", "ifcexternalreferenceresource",
        "ifcgeometricconstraintresource", "ifcgeometricmodelresource", "ifcgeometryresource",
        "ifcmaterialresource", "ifcmeasureresource", "ifcpresentationappearanceresource",
        "ifcpresentationdefinitionresource", "ifcpresentationorganizationresource",
        "ifcprofileresource", "ifcpropertyresource", "ifcquantityresource",
        "ifcrepresentationresource", "ifcstructuralloadresource", "ifctopologyresource",
        "ifcutilityresource",

        # Shared schemas
        "ifcsharedbldgelements", "ifcsharedbldgserviceelements", "ifcsharedcomponentelements",
        "ifcsharedfacilitieselements", "ifcsharedinfrastructureelements", "ifcsharedmgmtelements",

        # Domain schemas (建筑相关)
        "ifcarchitecturedomain", "ifcbuildingelementdomain", "ifcbuildingcontrolsdomain",

        # Domain schemas (设施服务)
        "ifcelectricaldomain", "ifchvacdomain", "ifcplumbingfiredomain",

        # Domain schemas (结构)
        "ifcstructuralelementsdomain", "ifcstructuralanalysisdomain",

        # Domain schemas (施工)
        "ifcconstructionmgmtdomain",

        # Domain schemas (港口与水路)
        "ifcportandwaterwaydomain",

        # Domain schemas (铁路)
        "ifcraildomain",

        # Domain schemas (道路)
        "ifcroaddomain",
    ]

    for module in schema_modules:
        urls.add(f"{BASE_URL}/IFC/RELEASE/IFC4x3/HTML/{module}/content.html")

    # Concepts 页面
    urls.add(f"{BASE_URL}/IFC/RELEASE/IFC4x3/HTML/concepts/content.html")

    return sorted(urls)


def main():
    """主函数"""
    print("生成 URL 列表...")

    urls = generate_urls()

    # 保存到文件
    output_file = Path("/Users/weilai/Documents/devs/IFC-4-3-Chinese/deployment/urls.txt")
    with open(output_file, 'w', encoding='utf-8') as f:
        for url in urls:
            f.write(f"{url}\n")

    print(f"✅ 生成完成")
    print(f"   总URL数: {len(urls)}")
    print(f"   保存到: {output_file}")

    return len(urls)


if __name__ == "__main__":
    count = main()
    sys.exit(0 if count > 0 else 1)
