#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
静态网页爬取工具

功能：
1. 启动 Flask 开发服务器
2. 爬取所有页面并保存为静态 HTML
3. 下载所有静态资源（CSS, JS, 图片等）

使用方法：
    python3 crawl_static_pages.py
"""

import os
import sys
import time
import subprocess
import requests
import shutil
from pathlib import Path
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import re

# 配置
SERVER_HOST = "127.0.0.1"
SERVER_PORT = 5050
BASE_URL = f"http://{SERVER_HOST}:{SERVER_PORT}"
SOURCE_DIR = Path("/Users/weilai/Documents/devs/IFC4-3-x-development/code_zh")
OUTPUT_DIR = Path("/Users/weilai/Documents/devs/IFC-4-3-Chinese")
MAX_RETRIES = 3
TIMEOUT = 30

# 需要爬取的页面列表（根据实际路由配置）
PAGES_TO_CRAWL = [
    "/",
    "/content/foreword.htm",
    "/content/introduction.htm",
    "/content/scope.htm",
    "/content/normative_references.htm",
    "/content/terms_and_definitions.htm",
    "/content/abbreviated_terms.htm",
    "/content/schema_definition.htm",
]

class StaticSiteCrawler:
    """静态网站爬取器"""

    def __init__(self):
        self.session = requests.Session()
        self.crawled_urls = set()
        self.failed_urls = []

    def fetch_page(self, url: str, retry: int = 0) -> tuple[str, int]:
        """
        获取页面内容

        Args:
            url: 页面 URL
            retry: 重试次数

        Returns:
            (内容, 状态码) 元组
        """
        try:
            response = self.session.get(url, timeout=TIMEOUT)
            response.raise_for_status()
            return response.text, response.status_code
        except requests.RequestException as e:
            if retry < MAX_RETRIES:
                print(f"  ⚠️  重试 {retry + 1}/{MAX_RETRIES}: {url}")
                time.sleep(2 ** retry)  # 指数退避
                return self.fetch_page(url, retry + 1)
            else:
                print(f"  ❌ 失败: {url} - {e}")
                self.failed_urls.append((url, str(e)))
                return None, 0

    def save_page(self, url_path: str, content: str):
        """
        保存页面到本地文件

        Args:
            url_path: URL 路径
            content: 页面内容
        """
        # 确定文件路径
        if url_path == "/" or url_path == "":
            file_path = OUTPUT_DIR / "index.html"
        else:
            # 移除前导斜杠
            url_path = url_path.lstrip("/")

            # 如果路径以 .htm 或 .html 结尾，直接使用
            if url_path.endswith((".htm", ".html")):
                file_path = OUTPUT_DIR / url_path
            else:
                # 否则创建目录并保存为 index.html
                file_path = OUTPUT_DIR / url_path / "index.html"

        # 创建目录
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 保存文件
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"  ✅ 已保存: {file_path.relative_to(OUTPUT_DIR)}")

    def extract_links(self, html: str, base_url: str) -> list[str]:
        """
        从 HTML 中提取链接

        Args:
            html: HTML 内容
            base_url: 基础 URL

        Returns:
            链接列表
        """
        soup = BeautifulSoup(html, "html.parser")
        links = []

        # 提取所有 <a> 标签的 href
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]
            # 过滤掉锚点和外部链接
            if not href.startswith("#") and not href.startswith("http"):
                full_url = urljoin(base_url, href)
                # 只保留同域名的链接
                if urlparse(full_url).netloc == urlparse(base_url).netloc:
                    links.append(full_url)

        return links

    def crawl_recursive(self, start_url: str, max_depth: int = 5):
        """
        递归爬取页面

        Args:
            start_url: 起始 URL
            max_depth: 最大深度
        """
        queue = [(start_url, 0)]  # (URL, 深度)

        while queue:
            url, depth = queue.pop(0)

            # 检查是否已爬取或超过最大深度
            if url in self.crawled_urls or depth > max_depth:
                continue

            print(f"\n📄 爬取 (深度 {depth}): {url}")

            # 获取页面
            content, status = self.fetch_page(url)
            if content is None:
                continue

            # 标记为已爬取
            self.crawled_urls.add(url)

            # 保存页面
            url_path = urlparse(url).path
            self.save_page(url_path, content)

            # 提取链接并加入队列
            links = self.extract_links(content, url)
            for link in links:
                if link not in self.crawled_urls:
                    queue.append((link, depth + 1))

    def generate_report(self):
        """生成爬取报告"""
        report_path = OUTPUT_DIR / "deployment" / "crawl_report.txt"
        report_path.parent.mkdir(parents=True, exist_ok=True)

        with open(report_path, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("静态网页爬取报告\n")
            f.write("=" * 60 + "\n\n")
            f.write(f"爬取时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"成功爬取: {len(self.crawled_urls)} 个页面\n")
            f.write(f"失败: {len(self.failed_urls)} 个页面\n\n")

            if self.failed_urls:
                f.write("失败的 URL:\n")
                for url, error in self.failed_urls:
                    f.write(f"  - {url}\n    错误: {error}\n")

        print(f"\n📊 报告已保存: {report_path}")


def check_server_running() -> bool:
    """检查服务器是否运行"""
    try:
        response = requests.get(BASE_URL, timeout=2)
        return response.status_code < 500
    except:
        return False


def start_server() -> subprocess.Popen:
    """启动 Flask 服务器"""
    print("🚀 启动 Flask 服务器...")

    env = os.environ.copy()
    env["IFC_LANG"] = "zh"
    env["FLASK_APP"] = "server.py"
    env["FLASK_ENV"] = "development"

    process = subprocess.Popen(
        ["python3", "-c", "from server import app; app.run(host='127.0.0.1', port=5050, debug=False)"],
        cwd=SOURCE_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # 等待服务器启动
    print("⏳ 等待服务器启动...")
    for i in range(30):  # 最多等待 30 秒
        time.sleep(1)
        if check_server_running():
            print(f"✅ 服务器已启动: {BASE_URL}")
            return process

    # 超时
    process.terminate()
    raise RuntimeError("服务器启动超时")


def main():
    """主函数"""
    print("=" * 60)
    print("IFC 4.3 中文版 - 静态网页爬取工具")
    print("=" * 60)

    # 检查服务器是否已运行
    server_process = None
    if check_server_running():
        print(f"✅ 服务器已在运行: {BASE_URL}")
    else:
        try:
            server_process = start_server()
        except Exception as e:
            print(f"❌ 无法启动服务器: {e}")
            sys.exit(1)

    try:
        # 创建爬虫
        crawler = StaticSiteCrawler()

        # 开始爬取
        print("\n" + "=" * 60)
        print("开始爬取页面...")
        print("=" * 60)

        crawler.crawl_recursive(BASE_URL, max_depth=10)

        # 生成报告
        crawler.generate_report()

        # 总结
        print("\n" + "=" * 60)
        print("爬取完成！")
        print("=" * 60)
        print(f"✅ 成功: {len(crawler.crawled_urls)} 个页面")
        print(f"❌ 失败: {len(crawler.failed_urls)} 个页面")
        print(f"📁 输出目录: {OUTPUT_DIR}")

    finally:
        # 停止服务器
        if server_process:
            print("\n🛑 停止服务器...")
            server_process.terminate()
            server_process.wait(timeout=5)
            print("✅ 服务器已停止")


if __name__ == "__main__":
    main()
