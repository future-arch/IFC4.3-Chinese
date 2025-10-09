# IFC 4.3 中文版

> Industry Foundation Classes (IFC) 4.3 中文文档静态网站

[![部署状态](https://img.shields.io/badge/Vercel-已部署-success)](https://ifc-4-3-chinese.vercel.app)
[![许可证](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## 📖 项目简介

本项目是 IFC 4.3 标准规范的中文版静态文档网站，包含完整的实体定义、属性集、类型枚举等技术文档。

## 🌐 在线访问

**主站地址**: [https://ifc-4-3-chinese.vercel.app](https://ifc-4-3-chinese.vercel.app)

## 📊 内容统计

- **HTML 页面**: 235+ 个
- **静态资源**: CSS, JavaScript, 图片等
- **文档类型**:
  - 实体定义 (Entities)
  - 属性集 (Property Sets)
  - 类型枚举 (Enumerations)
  - 章节文档 (Chapters)
  - 附录 (Annexes)

## 🏗️ 技术架构

- **内容来源**: 从 Flask 应用爬取生成的静态 HTML
- **部署平台**: Vercel (自动 CDN 加速)
- **版本控制**: Git + GitHub
- **自动化部署**: GitHub Push → Vercel 自动构建

## 📁 项目结构

```
IFC-4-3-Chinese/
├── IFC/RELEASE/IFC4x3/HTML/
│   ├── assets/           # 静态资源 (CSS, JS, 图片)
│   ├── lexical/          # 词汇表页面 (实体、类型等)
│   ├── content/          # 内容页面 (前言、介绍等)
│   ├── chapter-*/        # 章节页面
│   ├── annex-*.html      # 附录页面
│   └── index.htm         # 主页
├── deployment/           # 部署脚本和文档
│   ├── README.md         # 部署说明
│   ├── DEPLOYMENT_SUMMARY.md  # 部署摘要
│   └── crawl_static_pages.py  # 爬取脚本
├── index.html            # 网站首页
└── README.md             # 本文件
```

## 🚀 本地开发

### 查看静态网站

```bash
# 克隆仓库
git clone https://github.com/future-arch/IFC4.3-Chinese.git
cd IFC-4-3-Chinese

# 启动本地服务器 (Python 3)
python3 -m http.server 8000

# 访问
open http://localhost:8000
```

### 更新内容

如需从源仓库更新内容，请参考 `deployment/README.md` 中的说明。

## 📝 许可证

本项目内容基于 IFC 4.3 标准规范，遵循 [MIT License](LICENSE)。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进中文翻译和文档结构。

## 📧 联系方式

- **维护者**: future-arch
- **邮箱**: weilai@19650.net
- **GitHub**: [https://github.com/future-arch](https://github.com/future-arch)

## 🔗 相关链接

- [IFC 官方网站](https://www.buildingsmart.org/standards/bsi-standards/industry-foundation-classes/)
- [buildingSMART International](https://www.buildingsmart.org/)

---

**最后更新**: 2025-10-09
**部署平台**: Vercel
**构建状态**: ✅ 自动部署
