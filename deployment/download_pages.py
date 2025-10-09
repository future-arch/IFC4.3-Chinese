#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
使用 curl 批量下载静态页面

从 urls.txt 读取所有 URL，使用 curl 下载并保存为静态 HTML 文件
支持断点续传、进度报告、错误重试
"""

import os
import sys
import time
import subprocess
from pathlib import Path
from urllib.parse import urlparse, unquote
from datetime import datetime

# 配置
BASE_URL = "http://127.0.0.1:5050"
OUTPUT_DIR = Path("/Users/weilai/Documents/devs/IFC-4-3-Chinese")
URL_LIST = Path("/Users/weilai/Documents/devs/IFC-4-3-Chinese/deployment/urls.txt")
MAX_RETRIES = 3
REPORT_INTERVAL = 50  # 每下载50个页面报告一次


class CurlDownloader:
    """基于 curl 的页面下载器"""

    def __init__(self):
        self.total_urls = 0
        self.downloaded = 0
        self.failed = []
        self.skipped = 0
        self.start_time = time.time()

    def get_file_path(self, url: str) -> Path:
        """
        根据 URL 确定文件保存路径

        Args:
            url: 页面 URL

        Returns:
            文件保存路径
        """
        parsed = urlparse(url)
        url_path = parsed.path

        # 根目录
        if url_path == "/" or url_path == "":
            return OUTPUT_DIR / "index.html"

        # 移除前导斜杠
        url_path = url_path.lstrip("/")
        # URL 解码
        url_path = unquote(url_path)

        # 如果以 .htm 或 .html 结尾，直接使用
        if url_path.endswith((".htm", ".html")):
            return OUTPUT_DIR / url_path
        else:
            # 否则创建目录并保存为 index.html
            return OUTPUT_DIR / url_path / "index.html"

    def should_skip(self, file_path: Path) -> bool:
        """
        检查文件是否已存在且有效（支持断点续传）

        Args:
            file_path: 文件路径

        Returns:
            是否应跳过下载
        """
        if not file_path.exists():
            return False

        # 检查文件大小（太小可能是错误页面）
        if file_path.stat().st_size < 100:
            return False

        return True

    def download_url(self, url: str, retry: int = 0) -> bool:
        """
        使用 curl 下载单个 URL

        Args:
            url: 页面 URL
            retry: 重试次数

        Returns:
            是否下载成功
        """
        file_path = self.get_file_path(url)

        # 检查是否已存在
        if self.should_skip(file_path):
            self.skipped += 1
            return True

        # 创建目录
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # 使用 curl 下载
            result = subprocess.run(
                [
                    "curl",
                    "-s",  # 静默模式
                    "-f",  # 失败时返回错误
                    "-L",  # 跟随重定向
                    "--max-time", "30",  # 超时 30 秒
                    "-o", str(file_path),  # 输出文件
                    url
                ],
                capture_output=True,
                text=True,
                timeout=35
            )

            if result.returncode == 0:
                # 验证文件大小
                if file_path.stat().st_size < 100:
                    raise ValueError("下载的文件太小，可能是错误页面")

                self.downloaded += 1
                return True
            else:
                raise subprocess.CalledProcessError(
                    result.returncode,
                    "curl",
                    stderr=result.stderr
                )

        except Exception as e:
            if retry < MAX_RETRIES:
                time.sleep(2 ** retry)  # 指数退避
                return self.download_url(url, retry + 1)
            else:
                print(f"  ❌ 失败: {url}")
                print(f"     错误: {e}")
                self.failed.append((url, str(e)))
                return False

    def print_progress(self):
        """打印下载进度"""
        elapsed = time.time() - self.start_time
        processed = self.downloaded + self.skipped + len(self.failed)

        if processed > 0:
            speed = processed / elapsed if elapsed > 0 else 0
            eta = (self.total_urls - processed) / speed if speed > 0 else 0
        else:
            speed = 0
            eta = 0

        print(f"\n{'='*80}")
        print(f"📊 进度报告 [{datetime.now().strftime('%H:%M:%S')}]")
        print(f"{'='*80}")
        print(f"  总 URL 数: {self.total_urls}")
        print(f"  ✅ 已下载: {self.downloaded}")
        print(f"  ⏭️  已跳过: {self.skipped} (文件已存在)")
        print(f"  ❌ 失败: {len(self.failed)}")
        print(f"  📈 已处理: {processed}/{self.total_urls} ({processed/self.total_urls*100:.1f}%)")
        print(f"  ⏱️  已用时: {elapsed:.1f} 秒")
        print(f"  🚀 速度: {speed:.1f} 页/秒")
        print(f"  ⏰ 预计剩余: {eta:.0f} 秒")
        print(f"{'='*80}\n")

    def download_all(self, url_list_file: Path):
        """
        下载所有 URL

        Args:
            url_list_file: URL 列表文件路径
        """
        # 读取 URL 列表
        with open(url_list_file, 'r', encoding='utf-8') as f:
            urls = [line.strip() for line in f if line.strip()]

        self.total_urls = len(urls)

        print(f"{'='*80}")
        print(f"开始批量下载页面")
        print(f"{'='*80}")
        print(f"  总 URL 数: {self.total_urls}")
        print(f"  输出目录: {OUTPUT_DIR}")
        print(f"  断点续传: 已启用（跳过已存在文件）")
        print(f"{'='*80}\n")

        # 逐个下载
        for i, url in enumerate(urls, 1):
            self.download_url(url)

            # 每隔一定数量报告进度
            if i % REPORT_INTERVAL == 0:
                self.print_progress()

        # 最终报告
        self.print_progress()

        # 生成失败报告
        if self.failed:
            report_path = OUTPUT_DIR / "deployment" / "download_failed.txt"
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(f"下载失败的 URL ({len(self.failed)} 个)\n")
                f.write("="*80 + "\n\n")
                for url, error in self.failed:
                    f.write(f"URL: {url}\n")
                    f.write(f"错误: {error}\n\n")
            print(f"❌ 失败报告已保存: {report_path}")


def check_server_running() -> bool:
    """检查 Flask 服务器是否运行"""
    try:
        result = subprocess.run(
            ["curl", "-s", "-f", BASE_URL],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except:
        return False


def main():
    """主函数"""
    print("="*80)
    print("IFC 4.3 中文版 - 批量页面下载工具")
    print("="*80)

    # 检查服务器
    if not check_server_running():
        print(f"❌ Flask 服务器未运行: {BASE_URL}")
        print("   请先启动服务器")
        sys.exit(1)

    print(f"✅ 服务器正在运行: {BASE_URL}\n")

    # 检查 URL 列表
    if not URL_LIST.exists():
        print(f"❌ URL 列表文件不存在: {URL_LIST}")
        sys.exit(1)

    # 开始下载
    downloader = CurlDownloader()
    downloader.download_all(URL_LIST)

    # 总结
    print("\n" + "="*80)
    print("下载完成！")
    print("="*80)
    print(f"  ✅ 成功下载: {downloader.downloaded} 个页面")
    print(f"  ⏭️  跳过: {downloader.skipped} 个页面 (已存在)")
    print(f"  ❌ 失败: {len(downloader.failed)} 个页面")
    print(f"  ⏱️  总耗时: {time.time() - downloader.start_time:.1f} 秒")
    print(f"  📁 输出目录: {OUTPUT_DIR}")
    print("="*80)


if __name__ == "__main__":
    main()
