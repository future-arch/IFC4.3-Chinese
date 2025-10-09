#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
IFC 4.3 中文版 - 自动同步和渲染系统

功能：
1. 检测源仓库 (IFC4-3-x-development/docs_zh) 中的更改
2. 自动调用渲染引擎 (code_zh/server.py) 重新渲染
3. 拉取渲染结果到静态站点目录
4. 自动提交并推送到 GitHub

使用方法：
  python sync_from_source.py --check             # 检查待同步的更改
  python sync_from_source.py --sync              # 同步所有更改
  python sync_from_source.py --file <path>       # 同步单个文件
  python sync_from_source.py --auto              # 自动模式（检测+同步+提交）
"""

import os
import sys
import re
import subprocess
import requests
import time
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict, Optional
import argparse


# ============================================================================
# 配置参数
# ============================================================================

# 源仓库路径
SOURCE_REPO = Path("/Users/weilai/Documents/devs/IFC4-3-x-development")
SOURCE_DOCS = SOURCE_REPO / "docs_zh"
SOURCE_CODE = SOURCE_REPO / "code_zh"

# 目标仓库路径（当前仓库）
TARGET_REPO = Path("/Users/weilai/Documents/devs/IFC-4-3-Chinese")
TARGET_HTML = TARGET_REPO / "IFC/RELEASE/IFC4x3/HTML"

# Flask 渲染服务器配置
FLASK_SERVER_URL = "http://127.0.0.1:5050"
FLASK_START_SCRIPT = SOURCE_CODE / "start_zh_server.sh"

# Markdown 到 HTML 路径映射规则
# docs_zh/schemas/resource/IfcGeometryResource/Entities/IfcTrimmedCurve.md
# -> IFC/RELEASE/IFC4x3/HTML/lexical/IfcTrimmedCurve.htm


# ============================================================================
# 工具函数
# ============================================================================

def run_command(cmd: str, cwd: Optional[Path] = None, check: bool = True) -> Tuple[int, str, str]:
    """
    执行 shell 命令

    Args:
        cmd: 要执行的命令
        cwd: 工作目录
        check: 是否检查返回码

    Returns:
        (返回码, stdout, stderr)
    """
    result = subprocess.run(
        cmd,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False
    )

    if check and result.returncode != 0:
        print(f"❌ 命令执行失败: {cmd}")
        print(f"   错误: {result.stderr}")

    return result.returncode, result.stdout, result.stderr


def check_flask_server() -> bool:
    """
    检查 Flask 服务器是否运行

    Returns:
        True 如果服务器在运行
    """
    try:
        response = requests.get(FLASK_SERVER_URL, timeout=2)
        return response.status_code in [200, 404]  # 404 也说明服务器在运行
    except requests.exceptions.RequestException:
        return False


def start_flask_server() -> bool:
    """
    启动 Flask 渲染服务器

    Returns:
        True 如果成功启动
    """
    print("🚀 启动 Flask 渲染服务器...")

    if not FLASK_START_SCRIPT.exists():
        print(f"❌ 启动脚本不存在: {FLASK_START_SCRIPT}")
        return False

    # 在后台启动服务器
    subprocess.Popen(
        [str(FLASK_START_SCRIPT)],
        cwd=SOURCE_CODE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # 等待服务器启动
    for i in range(10):
        time.sleep(1)
        if check_flask_server():
            print("✅ Flask 服务器已启动")
            return True
        print(f"   等待服务器启动... ({i+1}/10)")

    print("❌ Flask 服务器启动失败")
    return False


def ensure_flask_server() -> bool:
    """
    确保 Flask 服务器运行

    Returns:
        True 如果服务器在运行或成功启动
    """
    if check_flask_server():
        print("✅ Flask 服务器已在运行")
        return True

    return start_flask_server()


# ============================================================================
# 文件路径映射
# ============================================================================

def md_to_html_path(md_file: Path) -> Optional[str]:
    """
    将 Markdown 文件路径转换为 HTML URL 路径

    Args:
        md_file: docs_zh 中的 Markdown 文件路径

    Returns:
        HTML 文件的 URL 路径（相对于 Flask 服务器根目录）

    示例:
        docs_zh/schemas/resource/IfcGeometryResource/Entities/IfcTrimmedCurve.md
        -> /IFC/RELEASE/IFC4x3/HTML/lexical/IfcTrimmedCurve.htm
    """
    # 转换为相对于 SOURCE_DOCS 的路径
    try:
        rel_path = md_file.relative_to(SOURCE_DOCS)
    except ValueError:
        print(f"⚠️  文件不在 docs_zh 目录下: {md_file}")
        return None

    # 提取文件名（不含扩展名）
    entity_name = md_file.stem

    # 根据路径结构判断类型
    path_str = str(rel_path)

    # schemas/ 下的实体、类型、函数 -> lexical/
    if path_str.startswith("schemas/"):
        if "/Entities/" in path_str or "/Types/" in path_str or "/Functions/" in path_str:
            return f"/IFC/RELEASE/IFC4x3/HTML/lexical/{entity_name}.htm"

    # concepts/ 下的概念 -> concepts/
    if path_str.startswith("concepts/"):
        # 保留目录结构
        html_path = str(rel_path.parent / "content.html")
        return f"/IFC/RELEASE/IFC4x3/HTML/{html_path}"

    # examples/ 下的示例 -> examples/
    if path_str.startswith("examples/"):
        # 暂不处理，示例页面结构不同
        return None

    print(f"⚠️  未知的文件类型: {rel_path}")
    return None


def html_url_to_file_path(html_url: str) -> Path:
    """
    将 HTML URL 路径转换为本地文件系统路径

    Args:
        html_url: HTML 文件的 URL 路径

    Returns:
        本地文件系统中的完整路径

    示例:
        /IFC/RELEASE/IFC4x3/HTML/lexical/IfcTrimmedCurve.htm
        -> /Users/weilai/Documents/devs/IFC-4-3-Chinese/IFC/RELEASE/IFC4x3/HTML/lexical/IfcTrimmedCurve.htm
    """
    # 移除开头的斜杠
    relative_path = html_url.lstrip("/")
    return TARGET_REPO / relative_path


# ============================================================================
# 变更检测
# ============================================================================

def get_modified_files_in_source() -> List[Path]:
    """
    获取源仓库中已修改但未提交的文件列表

    Returns:
        已修改的 Markdown 文件路径列表
    """
    print("🔍 检测源仓库中的更改...")

    # 检查 Git 状态
    returncode, stdout, stderr = run_command(
        "git status --porcelain docs_zh/",
        cwd=SOURCE_REPO,
        check=False
    )

    if returncode != 0:
        print(f"❌ 无法检查 Git 状态: {stderr}")
        return []

    modified_files = []
    for line in stdout.strip().split("\n"):
        if not line.strip():
            continue

        # Git status 格式: " M file.md" 或 "M  file.md"
        status = line[:2]
        file_path = line[3:].strip()

        # 只处理修改的文件（M）和新增的文件（A）
        if "M" in status or "A" in status:
            full_path = SOURCE_REPO / file_path
            if full_path.suffix == ".md" and full_path.exists():
                modified_files.append(full_path)

    return modified_files


def get_recently_modified_files(hours: int = 24) -> List[Path]:
    """
    获取最近修改的文件（基于文件系统修改时间）

    Args:
        hours: 最近多少小时内修改的文件

    Returns:
        最近修改的 Markdown 文件路径列表
    """
    print(f"🔍 检测最近 {hours} 小时内修改的文件...")

    current_time = time.time()
    cutoff_time = current_time - (hours * 3600)

    modified_files = []
    for md_file in SOURCE_DOCS.rglob("*.md"):
        if md_file.stat().st_mtime > cutoff_time:
            modified_files.append(md_file)

    return modified_files


# ============================================================================
# 渲染和同步
# ============================================================================

def render_and_sync_file(md_file: Path, auto_commit: bool = False) -> bool:
    """
    渲染并同步单个文件

    Args:
        md_file: 源 Markdown 文件路径
        auto_commit: 是否自动提交到 Git

    Returns:
        True 如果成功
    """
    print(f"\n📄 处理: {md_file.relative_to(SOURCE_REPO)}")

    # 1. 转换路径
    html_url = md_to_html_path(md_file)
    if not html_url:
        print("   ⏭️  跳过（无法映射路径）")
        return False

    print(f"   URL: {html_url}")

    # 2. 确保服务器运行
    if not ensure_flask_server():
        return False

    # 3. 请求渲染
    full_url = FLASK_SERVER_URL + html_url
    print(f"   🌐 请求渲染: {full_url}")

    try:
        response = requests.get(full_url, timeout=30)
        if response.status_code != 200:
            print(f"   ❌ 渲染失败 (HTTP {response.status_code})")
            return False
    except requests.exceptions.RequestException as e:
        print(f"   ❌ 请求失败: {e}")
        return False

    # 4. 保存到目标位置
    target_file = html_url_to_file_path(html_url)
    target_file.parent.mkdir(parents=True, exist_ok=True)

    with open(target_file, "wb") as f:
        f.write(response.content)

    file_size = target_file.stat().st_size
    print(f"   ✅ 已保存: {target_file.relative_to(TARGET_REPO)} ({file_size/1024:.1f} KB)")

    # 5. 自动提交（如果启用）
    if auto_commit:
        commit_file(target_file, md_file)

    return True


def commit_file(html_file: Path, source_md: Path):
    """
    提交单个文件到 Git

    Args:
        html_file: 目标 HTML 文件
        source_md: 源 Markdown 文件
    """
    rel_html = html_file.relative_to(TARGET_REPO)
    rel_md = source_md.relative_to(SOURCE_REPO)

    # Git add
    run_command(f"git add {rel_html}", cwd=TARGET_REPO, check=False)

    # Git commit
    commit_message = f"""feat: 同步渲染 {html_file.stem}

源文件: {rel_md}
渲染时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"""

    returncode, stdout, stderr = run_command(
        f'git commit -m "{commit_message}"',
        cwd=TARGET_REPO,
        check=False
    )

    if returncode == 0:
        print(f"   ✅ 已提交到 Git")
    else:
        print(f"   ⚠️  提交失败或无更改")


# ============================================================================
# 主要功能
# ============================================================================

def check_changes():
    """
    检查待同步的更改
    """
    print("=" * 80)
    print("🔍 检查待同步的更改")
    print("=" * 80)

    # 检查 Git 未提交的更改
    git_modified = get_modified_files_in_source()
    if git_modified:
        print(f"\n📝 Git 未提交的更改 ({len(git_modified)} 个文件):")
        for f in git_modified[:10]:  # 只显示前 10 个
            print(f"   - {f.relative_to(SOURCE_REPO)}")
        if len(git_modified) > 10:
            print(f"   ... 还有 {len(git_modified) - 10} 个文件")
    else:
        print("\n✅ 源仓库没有未提交的更改")

    # 检查最近修改的文件
    recent_modified = get_recently_modified_files(hours=24)
    if recent_modified:
        print(f"\n🕒 最近 24 小时修改的文件 ({len(recent_modified)} 个文件):")
        for f in recent_modified[:10]:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            print(f"   - {f.relative_to(SOURCE_REPO)} ({mtime.strftime('%Y-%m-%d %H:%M')})")
        if len(recent_modified) > 10:
            print(f"   ... 还有 {len(recent_modified) - 10} 个文件")
    else:
        print("\n✅ 没有最近修改的文件")

    print("\n" + "=" * 80)


def sync_changes(files: Optional[List[Path]] = None, auto_commit: bool = False):
    """
    同步更改

    Args:
        files: 要同步的文件列表（None 表示同步所有检测到的更改）
        auto_commit: 是否自动提交
    """
    print("=" * 80)
    print("🔄 同步更改到静态站点")
    print("=" * 80)

    if files is None:
        # 自动检测更改
        files = get_modified_files_in_source()
        if not files:
            print("\n✅ 没有待同步的更改")
            return

    print(f"\n📦 共 {len(files)} 个文件待处理\n")

    success_count = 0
    fail_count = 0

    for md_file in files:
        if render_and_sync_file(md_file, auto_commit=auto_commit):
            success_count += 1
        else:
            fail_count += 1

    print("\n" + "=" * 80)
    print(f"📊 同步完成: 成功 {success_count} 个，失败 {fail_count} 个")
    print("=" * 80)


def auto_mode():
    """
    自动模式：检测 -> 同步 -> 提交 -> 推送
    """
    print("=" * 80)
    print("🤖 自动模式")
    print("=" * 80)

    # 1. 检测更改
    files = get_modified_files_in_source()
    if not files:
        print("\n✅ 没有待同步的更改")
        return

    print(f"\n📦 检测到 {len(files)} 个修改的文件")

    # 2. 同步（自动提交每个文件）
    sync_changes(files, auto_commit=True)

    # 3. 推送到 GitHub
    print("\n🚀 推送到 GitHub...")
    returncode, stdout, stderr = run_command(
        "git push origin main",
        cwd=TARGET_REPO,
        check=False
    )

    if returncode == 0:
        print("✅ 已推送到 GitHub")
    else:
        print(f"❌ 推送失败: {stderr}")


# ============================================================================
# CLI 接口
# ============================================================================

def main():
    """
    主函数
    """
    parser = argparse.ArgumentParser(
        description="IFC 4.3 中文版 - 自动同步和渲染系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python sync_from_source.py --check
  python sync_from_source.py --sync
  python sync_from_source.py --file /path/to/file.md
  python sync_from_source.py --auto
        """
    )

    parser.add_argument("--check", action="store_true", help="检查待同步的更改")
    parser.add_argument("--sync", action="store_true", help="同步所有检测到的更改")
    parser.add_argument("--file", type=str, help="同步指定的单个文件")
    parser.add_argument("--auto", action="store_true", help="自动模式（检测+同步+提交+推送）")
    parser.add_argument("--no-commit", action="store_true", help="不自动提交（与 --sync 配合使用）")

    args = parser.parse_args()

    # 如果没有任何参数，显示帮助
    if not any([args.check, args.sync, args.file, args.auto]):
        parser.print_help()
        return

    # 执行相应的操作
    if args.check:
        check_changes()

    if args.sync:
        sync_changes(auto_commit=not args.no_commit)

    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ 文件不存在: {file_path}")
            return
        sync_changes([file_path], auto_commit=not args.no_commit)

    if args.auto:
        auto_mode()


if __name__ == "__main__":
    main()
