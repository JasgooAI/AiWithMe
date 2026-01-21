# AiWithMe - AI 情报收集助手

一个自动化的 AI 信息源聚合系统，从多个渠道抓取最新 AI/科技资讯，使用 AI 进行智能处理（翻译、摘要、分类），并集成到 Obsidian 笔记库中。

## ✨ 核心功能

- **📰 多源聚合**：支持 RSS、Hacker News、HuggingFace Papers、网页抓取等多种信息源
- **🤖 AI 智能处理**：自动翻译标题、生成中文摘要、提取关键词、智能分类
- **📝 Obsidian 集成**：生成带 frontmatter 的 Markdown 文件，支持 Dataview 查询
- **🔄 智能去重**：SQLite 数据库记录已抓取文章，自动去重
- **⏰ 定时运行**：支持 macOS launchd 定时任务
- **🔔 系统通知**：抓取完成后自动发送 macOS 通知

## 📂 项目结构

```
AiWithMe/
└── 优质信息源/                     # 信息聚合系统
    ├── .archive/                   # 核心程序
    │   ├── src/                   # 源代码
    │   │   ├── main.py           # 主程序入口
    │   │   ├── fetchers/         # 抓取器模块
    │   │   ├── processors/       # AI 处理模块
    │   │   ├── storage/          # 存储模块
    │   │   └── utils/            # 工具模块
    │   ├── .system/
    │   │   ├── config/           # 配置文件
    │   │   │   ├── config.yaml.example
    │   │   │   └── sources.yaml
    │   │   ├── data/             # SQLite 数据库（运行时生成）
    │   │   └── logs/             # 日志文件（运行时生成）
    │   ├── scripts/              # 安装/卸载脚本
    │   └── requirements.txt      # Python 依赖
    ├── 文章/                      # 文章输出目录（运行时生成）
    ├── 来源/                      # 信息源索引（运行时生成）
    ├── 每日汇总/                  # 每日汇总（运行时生成）
    └── README.md                 # 详细文档
```

## 🚀 快速开始

### 1. 环境要求

- Python 3.10+
- macOS（定时任务和通知功能）
- Obsidian（可选，用于查看笔记）

### 2. 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/AiWithMe.git
cd AiWithMe/优质信息源

# 创建虚拟环境
python3 -m venv .archive/.venv
source .archive/.venv/bin/activate

# 安装依赖
pip install -r .archive/requirements.txt
```

### 3. 配置

复制配置模板并填写：

```bash
cp .archive/.system/config/config.yaml.example .archive/.system/config/config.yaml
```

编辑 `config.yaml`，填入你的 API 配置：

```yaml
api:
  base_url: "https://api.openai.com/v1"
  api_key: "your-api-key-here"
  model: "gpt-4o-mini"
```

支持任何 OpenAI 兼容的 API：OpenAI、智谱 GLM、DeepSeek、Moonshot、Ollama 等。

### 4. 运行

```bash
# 进入虚拟环境
cd 优质信息源
source .archive/.venv/bin/activate

# 手动运行（抓取所有配置的信息源）
.archive/.venv/bin/python .archive/src/main.py

# 指定信息源
.archive/.venv/bin/python .archive/src/main.py -s hackernews bensbites

# 查看统计
.archive/.venv/bin/python .archive/src/main.py --stats

# 调试模式
.archive/.venv/bin/python .archive/src/main.py -d
```

### 5. 设置定时任务（macOS）

```bash
# 安装定时任务（每天 20:00 自动运行）
bash .archive/scripts/install.sh

# 手动触发
launchctl start com.intel-collector

# 查看状态
launchctl list | grep intel

# 卸载定时任务
bash .archive/scripts/uninstall.sh
```

## 🎯 支持的信息源类型

| 类型 | 说明 | 配置参数 |
|------|------|----------|
| `rss` | RSS/Atom Feed | `feed_url` |
| `webpage` | 网页抓取 | `selectors` (CSS) |
| `hackernews` | Hacker News | `story_type`, `min_score` |
| `huggingface` | HF Daily Papers | - |
| `beehiiv` | Beehiiv 平台 | - |
| `every` | Every.to | - |

## 📝 配置信息源

编辑 `.archive/.system/config/sources.yaml` 添加信息源：

```yaml
sources:
  # RSS 源示例
  - id: example-rss
    name: Example RSS
    type: rss
    url: https://example.com
    feed_url: https://example.com/feed
    description: 示例 RSS 源
    limit: 10

  # 网页抓取示例
  - id: example-webpage
    name: Example Page
    type: webpage
    url: https://example.com/articles
    selectors:
      item: "article"
      title: "h2 a"
      link: "a"
      summary: "p"
    limit: 20

  # Hacker News 示例
  - id: hackernews
    name: Hacker News
    type: hackernews
    story_type: top  # top/new/best
    min_score: 100
    limit: 30
```

## 🤖 AI 处理流程

系统使用 AI 自动处理每篇文章：

1. **标题翻译**：将英文标题翻译为中文
2. **摘要生成**：生成 50-100 字中文摘要
3. **智能分类**：AI/技术/产品/商业/研究/工具/教程/新闻/其他
4. **关键词提取**：提取 2-3 个关键词

## 📄 Obsidian 文件格式

生成的文章 Markdown 文件格式：

```markdown
---
title: "中文标题"
title_original: "English Title"
url: https://example.com/article
source: source-id
source_name: Source Name
category: AI
date: 2026-01-21
---

# 中文标题

**原标题**: English Title
**来源**: [[source-id]]
**链接**: [https://example.com/article](https://example.com/article)

## AI 摘要

> 文章摘要内容...

## 关键词

#关键词1 #关键词2

- [ ] 加入精选

## 阅读笔记

（此处记录你的笔记）
```

### Dataview 查询示例

```dataview
TABLE title, source_name, date
FROM "优质信息源/文章"
WHERE category = "AI"
SORT date DESC
LIMIT 20
```

## 🔧 扩展开发

### 添加新的抓取器

1. 创建 `.archive/src/fetchers/xxx_fetcher.py`：

```python
from fetchers.base import BaseFetcher, Article

class XXXFetcher(BaseFetcher):
    def fetch(self) -> list[Article]:
        # 实现抓取逻辑
        articles = []
        # ...
        return articles
```

2. 在 `main.py` 注册：

```python
from fetchers.xxx_fetcher import XXXFetcher

FETCHER_MAP = {
    ...
    'xxx': XXXFetcher,
}
```

3. 在 `sources.yaml` 配置：

```yaml
- id: xxx-source
  type: xxx
  # 其他配置...
```

## 💡 使用技巧

### 精选文章功能

在文章中勾选「✅ 加入精选」复选框，文章会自动出现在「精华汇总.md」中（通过 Dataview 动态查询）。

### 反爬虫处理

系统内置了多种应对策略：
- 完整的浏览器 User-Agent
- curl 备用方案
- 请求间延迟
- 自动重试机制

### API 调用失败处理

- 自动重试（最多 3 次）
- 备用模型切换
- 优雅降级（跳过 AI 处理）

## 📦 依赖项

```
feedparser>=6.0.10      # RSS 解析
beautifulsoup4>=4.12.0  # HTML 解析
requests>=2.31.0        # HTTP 请求
lxml>=5.0.0            # XML/HTML 解析
openai>=1.0.0          # AI API
pyyaml>=6.0.1          # 配置解析
python-dateutil>=2.8.2 # 日期处理
```

## 📄 许可证

MIT License

## 🙏 致谢

- [feedparser](https://github.com/kurtmckee/feedparser) - RSS 解析
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) - HTML 解析
- [Obsidian](https://obsidian.md/) - 知识管理工具
- [Dataview](https://github.com/blacksmithgu/obsidian-dataview) - Obsidian 插件

## 📧 问题反馈

如有问题或建议，欢迎提交 Issue 或 Pull Request。
