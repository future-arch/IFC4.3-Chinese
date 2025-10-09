# IFC 4.3 中文版 - 部署工具集

这个文件夹存储上线部署的驱动代码和工具。

- 所有与部署相关的html静态页面、自动化程序、脚本、说明、报告全部放在这个文件夹，不许放在其他地方。

---

## 📁 文件说明

### 主要脚本

| 文件 | 功能 | 使用频率 |
|------|------|---------|
| `sync_from_source.py` | **自动同步系统** - 从源仓库同步更新的文档 | ⭐⭐⭐ 高频 |
| `crawl_complete.py` | 完整网站爬取工具 - 爬取所有页面到静态文件 | ⭐ 低频 |
| `download_pages.py` | 批量页面下载工具 - 从 Flask 服务器下载页面 | ⭐⭐ 中频 |
| `download_images.py` | 图片下载工具 - 从 GitHub 下载所有图片资源 | ⭐ 低频 |
| `fix_annex_d.py` | 修复 Annex D 页面 - 补全图表列表 | ⭐ 一次性 |
| `fix_annex_e.py` | 修复 Annex E 页面 - 补全示例列表 | ⭐ 一次性 |

### 辅助文件

| 文件 | 说明 |
|------|------|
| `SYNC_GUIDE.md` | **同步系统使用指南** - 详细的使用文档 |
| `README.md` | 本文件 - 部署工具集总览 |
| `urls.txt` | URL 列表 - 用于批量下载 |

---

## 🚀 快速开始

### 最常用的功能：同步源仓库更新

```bash
# 方式 1: 使用快捷命令（推荐）
cd /Users/weilai/Documents/devs/IFC-4-3-Chinese
./sync                    # 检查更改
./sync auto               # 自动同步+提交+推送

# 方式 2: 直接调用 Python 脚本
python3 deployment/sync_from_source.py --check
python3 deployment/sync_from_source.py --auto
```

**详细文档**: 查看 [SYNC_GUIDE.md](./SYNC_GUIDE.md)

---

## 部署方案 Github+Vercel

### Github 情况：
- 用户名：future-arch
- 邮箱：weilai@19650.net
- 仓库： https://github.com/future-arch/IFC4.3-Chinese
- 状态：已推送并正常运行

### Vercel 情况：
- 账户与Github一致
- 已在本地机安装了 Vercel Cli
- 已经建立了与Github仓库的同步
- Deployment: ifc-4-3-chinese-6aff4ru6u-wei-lais-projects-281252dc.vercel.app
- Domains: ifc-4-3-chinese.vercel.app

---

## 🔧 部署流程

### 初次部署（从零开始）

```bash
# 1. 下载所有图片资源
python3 deployment/download_images.py

# 2. 爬取所有页面
python3 deployment/crawl_complete.py

# 3. 修复特殊页面（如果需要）
python3 deployment/fix_annex_d.py
python3 deployment/fix_annex_e.py

# 4. 提交到 Git
git add .
git commit -m "feat: 初始部署完整静态站点"
git push origin main
```

### 日常更新（源仓库有更改）

```bash
# 使用同步系统（推荐）
./sync auto

# 或手动控制
./sync check              # 检查更改
./sync file /path/to/file.md   # 同步单个文件
git push origin main      # 推送到 GitHub
```

---

## 其他说明

- LLM 为上线部署提供最大化执行能力，无需人类做太多事情
- 如需人类提供信息，可提出问题，让人类操作
- Credential 的信息，如果产生和存放，需告诉人类如何保管

---

**最后更新**: 2025-10-09
**维护者**: Wei Lai