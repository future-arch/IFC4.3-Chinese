#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 buildingSMART GitHub 仓库下载缺失的页面

下载 annex_d、concepts 和其他缺失的页面
"""

import os
import sys
import time
import requests
from pathlib import Path
from urllib.parse import quote

# 配置
GITHUB_RAW_BASE = "https://raw.githubusercontent.com/buildingSMART/IFC4.3-html/main"
OUTPUT_DIR = Path("/Users/weilai/Documents/devs/IFC-4-3-Chinese")
BATCH_SIZE = 50
DELAY_BETWEEN_BATCHES = 2  # 秒

class GitHubDownloader:
    """从 GitHub 下载文件"""

    def __init__(self):
        self.session = requests.Session()
        self.downloaded = 0
        self.skipped = 0
        self.failed = []
        self.start_time = time.time()

    def download_file(self, github_path: str) -> bool:
        """
        从 GitHub 下载单个文件

        Args:
            github_path: GitHub 中的文件路径

        Returns:
            是否下载成功
        """
        # 确定本地保存路径
        local_path = OUTPUT_DIR / github_path

        # 如果文件已存在且大小合理，跳过
        if local_path.exists() and local_path.stat().st_size > 100:
            self.skipped += 1
            return True

        # 构建 GitHub raw URL
        github_url = f"{GITHUB_RAW_BASE}/{github_path}"

        try:
            # 下载文件
            response = self.session.get(github_url, timeout=30)
            response.raise_for_status()

            # 创建目录
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # 保存文件
            with open(local_path, 'wb') as f:
                f.write(response.content)

            self.downloaded += 1
            return True

        except Exception as e:
            print(f"  ❌ 下载失败: {github_path}")
            print(f"     错误: {e}")
            self.failed.append((github_path, str(e)))
            return False

    def download_batch(self, file_paths: list):
        """
        批量下载文件

        Args:
            file_paths: GitHub 文件路径列表
        """
        total = len(file_paths)
        print(f"开始下载 {total} 个文件...")

        for i, path in enumerate(file_paths, 1):
            self.download_file(path)

            # 每 BATCH_SIZE 个文件报告进度并休息
            if i % BATCH_SIZE == 0:
                elapsed = time.time() - self.start_time
                speed = i / elapsed if elapsed > 0 else 0
                eta = (total - i) / speed if speed > 0 else 0

                print(f"\n进度: {i}/{total} ({i/total*100:.1f}%)")
                print(f"  ✅ 已下载: {self.downloaded}")
                print(f"  ⏭️  已跳过: {self.skipped}")
                print(f"  ❌ 失败: {len(self.failed)}")
                print(f"  🚀 速度: {speed:.1f} 文件/秒")
                print(f"  ⏰ 预计剩余: {eta:.0f} 秒\n")

                # 避免请求过快
                time.sleep(DELAY_BETWEEN_BATCHES)

        # 最终报告
        elapsed = time.time() - self.start_time
        print(f"\n{'='*80}")
        print(f"下载完成！")
        print(f"{'='*80}")
        print(f"  ✅ 成功下载: {self.downloaded} 个文件")
        print(f"  ⏭️  跳过: {self.skipped} 个文件 (已存在)")
        print(f"  ❌ 失败: {len(self.failed)} 个文件")
        print(f"  ⏱️  总耗时: {elapsed:.1f} 秒")
        print(f"{'='*80}\n")

        # 保存失败列表
        if self.failed:
            failed_file = OUTPUT_DIR / "deployment" / "github_download_failed.txt"
            with open(failed_file, 'w', encoding='utf-8') as f:
                f.write(f"从 GitHub 下载失败的文件 ({len(self.failed)} 个)\n")
                f.write("="*80 + "\n\n")
                for path, error in self.failed:
                    f.write(f"文件: {path}\n")
                    f.write(f"错误: {error}\n\n")
            print(f"❌ 失败列表已保存: {failed_file}")


def get_missing_files() -> list:
    """
    从 GitHub API 获取缺失的文件列表

    Returns:
        缺失文件的路径列表
    """
    print("正在从 GitHub API 获取文件列表...")

    url = "https://api.github.com/repos/buildingSMART/IFC4.3-html/git/trees/main?recursive=1"
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    data = response.json()
    all_paths = [item['path'] for item in data['tree']
                 if item['path'].endswith(('.htm', '.html'))]

    # 筛选缺失的文件
    missing = []
    for path in all_paths:
        local_path = OUTPUT_DIR / path
        # 如果本地不存在或文件太小（可能损坏）
        if not local_path.exists() or local_path.stat().st_size < 100:
            # 只下载特定目录
            if any(x in path for x in ['annex_d/', 'concepts/', 'annex_e/', 'examples/']):
                missing.append(path)
            elif '/lexical/' not in path and '/property/' not in path:
                # 其他顶层或特殊文件
                missing.append(path)

    print(f"找到 {len(missing)} 个缺失文件\n")
    return missing


def main():
    """主函数"""
    print("="*80)
    print("从 buildingSMART GitHub 下载缺失页面")
    print("="*80)
    print(f"源: {GITHUB_RAW_BASE}")
    print(f"目标: {OUTPUT_DIR}")
    print("="*80 + "\n")

    try:
        # 获取缺失文件列表
        missing_files = get_missing_files()

        if not missing_files:
            print("✅ 没有缺失文件，所有页面已完整！")
            return 0

        # 下载缺失文件
        downloader = GitHubDownloader()
        downloader.download_batch(missing_files)

        return 0 if not downloader.failed else 1

    except Exception as e:
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
