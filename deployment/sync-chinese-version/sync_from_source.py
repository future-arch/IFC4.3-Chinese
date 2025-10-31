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
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import List, Tuple, Dict, Optional
import argparse


# ============================================================================
# 配置参数
# ============================================================================

# 源仓库路径
SOURCE_REPO = Path("/Users/weilai/Library/CloudStorage/GoogleDrive-weilai0811@gmail.com/My Drive/devs/IFC4-3-x-development")
SOURCE_DOCS = SOURCE_REPO / "docs_zh"
SOURCE_CODE = SOURCE_REPO / "code_zh"

# 目标仓库路径（当前仓库）
TARGET_REPO = Path("/Users/weilai/Library/CloudStorage/GoogleDrive-weilai0811@gmail.com/My Drive/devs/IFC-4-3-Chinese")
TARGET_HTML = TARGET_REPO / "IFC/RELEASE/IFC4x3/HTML"

# Flask 渲染服务器配置
FLASK_SERVER_URL = "http://127.0.0.1:5050"
FLASK_START_SCRIPT = SOURCE_CODE / "start_zh_server.sh"

# 进度记录文件
PROGRESS_FILE = Path(__file__).parent / "sync_progress.json"

# Markdown 到 HTML 路径映射规则
# schemas/Entities:             docs_zh/schemas/resource/IfcGeometryResource/Entities/IfcTrimmedCurve.md
#                               -> IFC/RELEASE/IFC4x3/HTML/lexical/IfcTrimmedCurve.htm
# schemas/Types:                docs_zh/schemas/resource/IfcGeometryResource/Types/IfcDirection.md
#                               -> IFC/RELEASE/IFC4x3/HTML/lexical/IfcDirection.htm
# schemas/Functions:            docs_zh/schemas/resource/IfcGeometryResource/Functions/IfcBuildAxis2Placement.md
#                               -> IFC/RELEASE/IFC4x3/HTML/lexical/IfcBuildAxis2Placement.htm
# schemas/PropertySets:         docs_zh/schemas/domain/IfcHvacDomain/PropertySets/Pset_DuctFittingOccurrence.md
#                               -> IFC/RELEASE/IFC4x3/HTML/lexical/Pset_DuctFittingOccurrence.htm
# schemas/QuantitySets:         docs_zh/schemas/core/IfcProductExtension/QuantitySets/Qto_BuildingBaseQuantities.md
#                               -> IFC/RELEASE/IFC4x3/HTML/lexical/Qto_BuildingBaseQuantities.htm
# schemas/PropertyEnumerations: docs_zh/schemas/domain/IfcArchitectureDomain/PropertyEnumerations/PEnum_WindowPanelOperationEnum.md
#                               -> IFC/RELEASE/IFC4x3/HTML/lexical/PEnum_WindowPanelOperationEnum.htm
# properties:                   docs_zh/properties/c/CounterSlope.md
#                               -> IFC/RELEASE/IFC4x3/HTML/property/CounterSlope.htm


# ============================================================================
# 进度记录管理
# ============================================================================

class SyncProgress:
    """
    同步进度管理器

    记录每个文件的同步状态，避免重复同步
    """

    def __init__(self, progress_file: Path = PROGRESS_FILE):
        """
        初始化进度管理器

        Args:
            progress_file: 进度记录文件路径
        """
        self.progress_file = progress_file
        self.data = self._load()

    def _load(self) -> Dict:
        """
        加载进度记录

        Returns:
            进度数据字典
        """
        if not self.progress_file.exists():
            return {
                "version": "1.0",
                "last_sync": None,
                "files": {}
            }

        try:
            with open(self.progress_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"⚠️  进度文件损坏，重新初始化: {e}")
            return {
                "version": "1.0",
                "last_sync": None,
                "files": {}
            }

    def _save(self):
        """
        保存进度记录
        """
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.progress_file, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    @staticmethod
    def _file_hash(file_path: Path) -> str:
        """
        计算文件的 MD5 哈希值

        Args:
            file_path: 文件路径

        Returns:
            MD5 哈希值
        """
        md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5.update(chunk)
        return md5.hexdigest()

    def is_synced(self, md_file: Path) -> bool:
        """
        检查文件是否已同步且未修改

        Args:
            md_file: Markdown 文件路径

        Returns:
            True 如果已同步且未修改
        """
        if not md_file.exists():
            return False

        file_key = str(md_file.relative_to(SOURCE_REPO))

        if file_key not in self.data["files"]:
            return False

        record = self.data["files"][file_key]

        # 检查文件修改时间
        current_mtime = md_file.stat().st_mtime
        if current_mtime != record.get("mtime"):
            return False

        # 检查文件哈希值（更可靠）
        current_hash = self._file_hash(md_file)
        if current_hash != record.get("hash"):
            return False

        return True

    def mark_synced(self, md_file: Path, html_file: Path, success: bool = True):
        """
        标记文件已同步

        Args:
            md_file: 源 Markdown 文件
            html_file: 目标 HTML 文件
            success: 是否成功同步
        """
        file_key = str(md_file.relative_to(SOURCE_REPO))

        self.data["files"][file_key] = {
            "source": str(md_file),
            "target": str(html_file),
            "mtime": md_file.stat().st_mtime,
            "hash": self._file_hash(md_file),
            "synced_at": datetime.now().isoformat(),
            "success": success
        }

        self.data["last_sync"] = datetime.now().isoformat()
        self._save()

    def get_stats(self) -> Dict:
        """
        获取同步统计信息

        Returns:
            统计信息字典
        """
        total = len(self.data["files"])
        success = sum(1 for f in self.data["files"].values() if f.get("success", False))

        return {
            "total_synced": total,
            "success": success,
            "failed": total - success,
            "last_sync": self.data.get("last_sync")
        }

    def reset(self):
        """
        重置所有进度记录
        """
        self.data = {
            "version": "1.0",
            "last_sync": None,
            "files": {}
        }
        self._save()
        print("✅ 进度记录已重置")

    def show_progress(self):
        """
        显示进度信息
        """
        stats = self.get_stats()

        print("=" * 80)
        print("📊 同步进度统计")
        print("=" * 80)
        print(f"总同步文件数: {stats['total_synced']}")
        print(f"  - 成功: {stats['success']}")
        print(f"  - 失败: {stats['failed']}")

        if stats['last_sync']:
            last_sync_time = datetime.fromisoformat(stats['last_sync'])
            print(f"上次同步: {last_sync_time.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("上次同步: 从未同步")

        print("\n最近同步的文件 (最多显示 10 个):")

        # 按同步时间排序
        sorted_files = sorted(
            self.data["files"].items(),
            key=lambda x: x[1].get("synced_at", ""),
            reverse=True
        )

        for file_key, record in sorted_files[:10]:
            status = "✅" if record.get("success", False) else "❌"
            sync_time = datetime.fromisoformat(record["synced_at"]).strftime('%m-%d %H:%M')
            print(f"  {status} {file_key} ({sync_time})")

        if len(self.data["files"]) > 10:
            print(f"  ... 还有 {len(self.data['files']) - 10} 个文件")

        print("=" * 80)


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
        md_file: docs_zh 或 content_zh 中的 Markdown 文件路径

    Returns:
        HTML 文件的 URL 路径（相对于 Flask 服务器根目录）

    示例:
        docs_zh/schemas/resource/IfcGeometryResource/Entities/IfcTrimmedCurve.md
        -> /IFC/RELEASE/IFC4x3/HTML/lexical/IfcTrimmedCurve.htm

        docs_zh/templates/Object Definition/README.md
        -> /IFC/RELEASE/IFC4x3/HTML/concepts/Object_Definition/content.html

        content_zh/introduction.md
        -> /IFC/RELEASE/IFC4x3/HTML/content/introduction.htm
    """
    # 转换为相对于 SOURCE_DOCS 的路径
    try:
        rel_path = md_file.relative_to(SOURCE_DOCS)
        base_dir = "docs_zh"
    except ValueError:
        # 尝试相对于 SOURCE_REPO/content_zh
        try:
            rel_path = md_file.relative_to(SOURCE_REPO / "content_zh")
            base_dir = "content_zh"
        except ValueError:
            print(f"⚠️  文件不在 docs_zh 或 content_zh 目录下: {md_file}")
            return None

    # 提取文件名（不含扩展名）
    entity_name = md_file.stem

    # 根据路径结构判断类型
    path_str = str(rel_path)

    # === 处理 docs_zh 目录下的文件 ===
    if base_dir == "docs_zh":
        # schemas/ 下的所有子类型 -> lexical/
        if path_str.startswith("schemas/"):
            # 处理 GlobalRules
            if "/GlobalRules/" in path_str:
                # GlobalRules 暂时跳过,这些是全局规则定义
                # 未来可能需要特殊处理
                print(f"ℹ️  跳过 GlobalRules: {rel_path}")
                return None

            # 处理 README.md - 映射到对应目录的索引页
            if md_file.name == "README.md":
                # schemas/core/IfcKernel/README.md -> ifckernel/content.html
                # 提取 schema 名称（目录名）
                schema_dir = md_file.parent.name.lower()
                return f"/IFC/RELEASE/IFC4x3/HTML/{schema_dir}/content.html"

            # 标准实体/类型/函数/属性集等
            keywords = ["/Entities/", "/Types/", "/Functions/", "/PropertySets/",
                       "/QuantitySets/", "/PropertyEnumerations/"]
            if any(keyword in path_str for keyword in keywords):
                return f"/IFC/RELEASE/IFC4x3/HTML/lexical/{entity_name}.htm"

        # properties/ 下的属性 -> property/
        elif path_str.startswith("properties/"):
            return f"/IFC/RELEASE/IFC4x3/HTML/property/{entity_name}.htm"

        # templates/ 下的模板 -> concepts/
        elif path_str.startswith("templates/"):
            # templates/Object Definition/Property Sets/README.md
            # -> concepts/Object_Definition/Property_Sets/content.html

            # 移除 templates/ 前缀
            template_path = rel_path.relative_to("templates")

            # 空格替换为下划线
            parts = []
            for part in template_path.parts[:-1]:  # 排除文件名
                parts.append(part.replace(" ", "_"))

            # 构建目标路径
            if parts:
                html_path = "/".join(parts) + "/content.html"
            else:
                # templates/README.md -> concepts/content.html
                html_path = "content.html"

            return f"/IFC/RELEASE/IFC4x3/HTML/concepts/{html_path}"

        # concepts/ 下的概念 -> concepts/
        elif path_str.startswith("concepts/"):
            # 保留目录结构
            html_path = str(rel_path.parent / "content.html")
            return f"/IFC/RELEASE/IFC4x3/HTML/{html_path}"

        # examples/ 下的示例 -> examples/
        elif path_str.startswith("examples/"):
            # 暂不处理，示例页面结构不同
            return None

    # === 处理 content_zh 目录下的文件 ===
    elif base_dir == "content_zh":
        # content_zh/introduction.md -> content/introduction.htm
        return f"/IFC/RELEASE/IFC4x3/HTML/content/{entity_name}.htm"

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
        -> /Users/weilai/Library/CloudStorage/GoogleDrive-weilai0811@gmail.com/My Drive/devs/IFC-4-3-Chinese/IFC/RELEASE/IFC4x3/HTML/lexical/IfcTrimmedCurve.htm
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

    modified_files = []

    # 检查 docs_zh/ 目录的 Git 状态
    returncode, stdout, stderr = run_command(
        "git status --porcelain docs_zh/",
        cwd=SOURCE_REPO,
        check=False
    )

    if returncode == 0:
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

    # 检查 content_zh/ 目录的 Git 状态
    returncode, stdout, stderr = run_command(
        "git status --porcelain content_zh/",
        cwd=SOURCE_REPO,
        check=False
    )

    if returncode == 0:
        for line in stdout.strip().split("\n"):
            if not line.strip():
                continue

            status = line[:2]
            file_path = line[3:].strip()

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

    # 扫描 docs_zh/ 目录
    for md_file in SOURCE_DOCS.rglob("*.md"):
        if md_file.stat().st_mtime > cutoff_time:
            modified_files.append(md_file)

    # 扫描 content_zh/ 目录
    content_zh_dir = SOURCE_REPO / "content_zh"
    if content_zh_dir.exists():
        for md_file in content_zh_dir.rglob("*.md"):
            if md_file.stat().st_mtime > cutoff_time:
                modified_files.append(md_file)

    return modified_files


# ============================================================================
# 渲染和同步
# ============================================================================

def render_and_sync_file(md_file: Path, auto_commit: bool = False, progress: Optional[SyncProgress] = None, force: bool = False) -> str:
    """
    渲染并同步单个文件

    Args:
        md_file: 源 Markdown 文件路径
        auto_commit: 是否自动提交到 Git
        progress: 进度管理器
        force: 是否强制同步（忽略进度记录）

    Returns:
        "success" - 渲染成功
        "skip" - 跳过（已同步或无法映射）
        "fail" - 失败
    """
    print(f"\n📄 处理: {md_file.relative_to(SOURCE_REPO)}")

    # 0. 检查是否已同步
    if not force and progress and progress.is_synced(md_file):
        print("   ⏭️  跳过（已同步且未修改）")
        return "skip"

    # 1. 转换路径
    html_url = md_to_html_path(md_file)
    if not html_url:
        print("   ⏭️  跳过（无法映射路径）")
        return "skip"

    print(f"   URL: {html_url}")

    # 2. 确保服务器运行
    if not ensure_flask_server():
        if progress:
            target_file = html_url_to_file_path(html_url)
            progress.mark_synced(md_file, target_file, success=False)
        return "fail"

    # 3. 请求渲染
    full_url = FLASK_SERVER_URL + html_url
    print(f"   🌐 请求渲染: {full_url}")

    try:
        response = requests.get(full_url, timeout=30)
        if response.status_code != 200:
            print(f"   ❌ 渲染失败 (HTTP {response.status_code})")
            if progress:
                target_file = html_url_to_file_path(html_url)
                progress.mark_synced(md_file, target_file, success=False)
            return "fail"
    except requests.exceptions.RequestException as e:
        print(f"   ❌ 请求失败: {e}")
        if progress:
            target_file = html_url_to_file_path(html_url)
            progress.mark_synced(md_file, target_file, success=False)
        return "fail"

    # 4. 保存到目标位置
    target_file = html_url_to_file_path(html_url)
    target_file.parent.mkdir(parents=True, exist_ok=True)

    with open(target_file, "wb") as f:
        f.write(response.content)

    file_size = target_file.stat().st_size
    print(f"   ✅ 已保存: {target_file.relative_to(TARGET_REPO)} ({file_size/1024:.1f} KB)")

    # 5. 记录进度
    if progress:
        progress.mark_synced(md_file, target_file, success=True)

    # 6. 自动提交（如果启用）
    if auto_commit:
        commit_file(target_file, md_file)

    return "success"


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
渲染时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

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

    # 初始化进度管理器
    progress = SyncProgress()

    # 检查 Git 未提交的更改
    git_modified = get_modified_files_in_source()

    # 过滤出真正需要同步的文件（未同步或已修改）
    need_sync = []
    already_synced = []

    for f in git_modified:
        if progress.is_synced(f):
            already_synced.append(f)
        else:
            need_sync.append(f)

    if need_sync:
        print(f"\n📝 需要同步的文件 ({len(need_sync)} 个):")
        for f in need_sync[:10]:
            print(f"   - {f.relative_to(SOURCE_REPO)}")
        if len(need_sync) > 10:
            print(f"   ... 还有 {len(need_sync) - 10} 个文件")
    else:
        print("\n✅ 没有需要同步的文件")

    if already_synced:
        print(f"\n✓ 已同步（未修改）({len(already_synced)} 个):")
        for f in already_synced[:5]:
            print(f"   - {f.relative_to(SOURCE_REPO)}")
        if len(already_synced) > 5:
            print(f"   ... 还有 {len(already_synced) - 5} 个文件")

    # 检查最近修改的文件
    recent_modified = get_recently_modified_files(hours=24)
    if recent_modified:
        print(f"\n🕒 最近 24 小时修改的文件 ({len(recent_modified)} 个文件):")
        for f in recent_modified[:10]:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            synced_mark = "✓" if progress.is_synced(f) else "✗"
            print(f"   {synced_mark} {f.relative_to(SOURCE_REPO)} ({mtime.strftime('%Y-%m-%d %H:%M')})")
        if len(recent_modified) > 10:
            print(f"   ... 还有 {len(recent_modified) - 10} 个文件")

    # 显示进度统计
    print("\n" + "-" * 80)
    stats = progress.get_stats()
    print(f"📊 同步统计: 总计 {stats['total_synced']} 个文件已同步（成功 {stats['success']} 个）")

    print("\n" + "=" * 80)


def sync_changes(files: Optional[List[Path]] = None, auto_commit: bool = False, force: bool = False):
    """
    同步更改

    Args:
        files: 要同步的文件列表（None 表示同步所有检测到的更改）
        auto_commit: 是否自动提交
        force: 是否强制同步（忽略进度记录）
    """
    print("=" * 80)
    print("🔄 同步更改到静态站点")
    print("=" * 80)

    # 初始化进度管理器
    progress = SyncProgress()

    if files is None:
        # 自动检测更改
        all_files = get_modified_files_in_source()

        # 过滤出需要同步的文件
        if not force:
            files = [f for f in all_files if not progress.is_synced(f)]
        else:
            files = all_files

        if not files:
            print("\n✅ 没有待同步的更改")
            if all_files:
                print(f"   （{len(all_files)} 个文件已同步且未修改）")
            return

    print(f"\n📦 共 {len(files)} 个文件待处理")
    if force:
        print("   （强制模式：忽略进度记录）")
    print()

    success_count = 0
    fail_count = 0
    skip_count = 0

    for md_file in files:
        result = render_and_sync_file(md_file, auto_commit=auto_commit, progress=progress, force=force)
        # render_and_sync_file 返回 "success", "skip", 或 "fail"
        if result == "success":
            success_count += 1
        elif result == "skip":
            skip_count += 1
        else:  # result == "fail"
            fail_count += 1

    print("\n" + "=" * 80)
    print(f"📊 同步完成: 成功 {success_count} 个，失败 {fail_count} 个，跳过 {skip_count} 个")
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
  python sync_from_source.py --progress
  python sync_from_source.py --reset-progress
        """
    )

    parser.add_argument("--check", action="store_true", help="检查待同步的更改")
    parser.add_argument("--sync", action="store_true", help="同步所有检测到的更改")
    parser.add_argument("--file", type=str, help="同步指定的单个文件")
    parser.add_argument("--auto", action="store_true", help="自动模式（检测+同步+提交+推送）")
    parser.add_argument("--no-commit", action="store_true", help="不自动提交（与 --sync 配合使用）")
    parser.add_argument("--force", action="store_true", help="强制同步所有文件（忽略进度记录）")
    parser.add_argument("--progress", action="store_true", help="查看同步进度统计")
    parser.add_argument("--reset-progress", action="store_true", help="重置同步进度记录")

    args = parser.parse_args()

    # 如果没有任何参数，显示帮助
    if not any([args.check, args.sync, args.file, args.auto, args.progress, args.reset_progress]):
        parser.print_help()
        return

    # 进度管理命令
    if args.reset_progress:
        progress = SyncProgress()
        confirm = input("⚠️  确认要重置所有进度记录吗？(yes/no): ")
        if confirm.lower() in ['yes', 'y']:
            progress.reset()
        else:
            print("❌ 已取消")
        return

    if args.progress:
        progress = SyncProgress()
        progress.show_progress()
        return

    # 执行相应的操作
    if args.check:
        check_changes()

    if args.sync:
        sync_changes(auto_commit=not args.no_commit, force=args.force)

    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ 文件不存在: {file_path}")
            return
        sync_changes([file_path], auto_commit=not args.no_commit, force=args.force)

    if args.auto:
        auto_mode()


if __name__ == "__main__":
    main()
