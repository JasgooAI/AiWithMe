# AI 信息源聚合系统（Intel Collector）

自动从 30+ 个 AI/技术信息源抓取文章，使用 AI 进行翻译、摘要和分类，输出到 Obsidian 笔记库。

## 功能特点

- **多源聚合**：支持 RSS、Hacker News、HuggingFace Papers、网页抓取等多种信息源
- **AI 处理**：自动翻译标题、生成中文摘要、提取关键词、智能分类
- **Obsidian 集成**：生成带 frontmatter 的 Markdown 文件，支持 Dataview 查询
- **智能去重**：SQLite 数据库记录已抓取文章，避免重复
- **定时运行**：支持 macOS launchd 定时任务
- **系统通知**：抓取完成后发送 macOS 通知

## 系统架构

```
信息源 (RSS/API/网页)
        ↓
   Fetchers (抓取器)
        ↓
   Article 数据对象
        ↓
   AI Processor (翻译/摘要/分类)
        ↓
   ┌─────────────────────┐
   │  SQLite Database    │ ← 去重、统计
   │  Obsidian Writer    │ ← Markdown 文件
   └─────────────────────┘
```

## 目录结构

```
intel-collector/
├── .archive/                      # 系统核心
│   ├── src/                       # 源代码
│   │   ├── main.py               # 主程序入口
│   │   ├── fetchers/             # 抓取器模块
│   │   ├── processors/           # AI 处理模块
│   │   ├── storage/              # 存储模块
│   │   └── utils/                # 工具模块
│   ├── .system/
│   │   ├── config/               # 配置文件
│   │   ├── data/                 # SQLite 数据库
│   │   └── logs/                 # 日志文件
│   ├── scripts/                  # 安装/卸载脚本
│   └── requirements.txt
├── 来源/                          # 信息源索引
├── 文章/                          # 文章详情
├── 每日汇总/                      # 每日汇总
├── 精华汇总.md                    # 精选文章
└── 看板.md                        # Obsidian 仪表盘
```

## 快速开始

### 1. 环境要求

- Python 3.10+
- macOS（定时任务和通知功能）
- Obsidian（可选，用于查看笔记）

### 2. 安装

```bash
# 克隆仓库
git clone https://github.com/yourusername/intel-collector.git
cd intel-collector

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

编辑 `config.yaml`：

```yaml
api:
  base_url: "https://your-api-endpoint"
  api_key: "your-api-key"
  model: "your-model-name"
```

### 4. 运行

```bash
# 手动运行
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
# 安装定时任务（每天 20:00 运行）
bash .archive/scripts/install.sh

# 手动触发
launchctl start com.intel-collector

# 查看状态
launchctl list | grep intel

# 卸载
bash .archive/scripts/uninstall.sh
```

## 信息源配置

编辑 `.archive/.system/config/sources.yaml` 添加或修改信息源：

```yaml
sources:
  # RSS 源
  - id: example-rss
    name: Example RSS
    type: rss
    url: https://example.com
    feed_url: https://example.com/feed
    description: 示例 RSS 源
    limit: 10

  # 网页抓取
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

  # Hacker News
  - id: hackernews
    name: Hacker News
    type: hackernews
    story_type: top  # top/new/best
    min_score: 100
    limit: 30
```

### 支持的信息源类型

| 类型 | 说明 | 配置参数 |
|------|------|----------|
| `rss` | RSS/Atom Feed | `feed_url` |
| `webpage` | 网页抓取 | `selectors` (CSS) |
| `hackernews` | Hacker News | `story_type`, `min_score` |
| `huggingface` | HF Daily Papers | - |
| `beehiiv` | Beehiiv 平台 | - |
| `every` | Every.to | - |

## 默认信息源

系统预配置了 30+ 个 AI/技术信息源：

**AI 新闻**
- Ben's Bites、TLDR AI、The AI Valley

**Substack**
- One Useful Thing、Import AI、SemiAnalysis、ChinaTalk 等

**大厂博客**
- OpenAI、DeepMind、Microsoft Research

**学术论文**
- arXiv (CS.AI, CS.CL, CS.LG)、HuggingFace Papers

**社区**
- Hacker News、Dev.to、HackerNoon

**科技媒体**
- TechCrunch、The Verge、Wired、MIT Tech Review

**中文源**
- 机器之心、InfoQ AI

## AI 处理

系统使用 OpenAI 兼容 API 处理文章：

1. **标题翻译**：将英文标题翻译为中文
2. **摘要生成**：生成 50 字中文摘要
3. **分类**：AI/技术/产品/商业/研究/工具/教程/新闻/其他
4. **关键词**：提取 2-3 个关键词

### 支持的 API

任何兼容 OpenAI API 格式的服务：
- OpenAI
- 智谱 GLM
- DeepSeek
- Moonshot
- 本地 LLM (Ollama, vLLM 等)

## Obsidian 集成

### 文章文件格式

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


```

### Dataview 查询

系统生成的文件支持 Dataview 查询：

```dataview
TABLE title, source_name, date
FROM "文章"
WHERE category = "AI"
SORT date DESC
LIMIT 20
```

### 精选功能

在文章中勾选「加入精选」复选框，文章会自动出现在精华汇总中。

## 扩展开发

### 添加新抓取器

1. 创建 `.archive/src/fetchers/xxx_fetcher.py`：

```python
from fetchers.base import BaseFetcher, Article

class XXXFetcher(BaseFetcher):
    def fetch(self) -> list[Article]:
        # 抓取逻辑
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
  ...
```

## 常见问题

### Q: 如何处理反爬虫？

系统内置了多种应对策略：
- 完整的浏览器 User-Agent
- curl 备用方案
- 请求间延迟

### Q: API 调用失败怎么办？

系统支持：
- 自动重试（3次）
- 备用模型切换
- 优雅降级（跳过 AI 处理）

### Q: 如何禁用某个信息源？

在 `sources.yaml` 中添加 `enabled: false`：

```yaml
- id: example
  enabled: false
  ...
```

## 依赖

```
feedparser>=6.0.10    # RSS 解析
beautifulsoup4>=4.12.0 # HTML 解析
requests>=2.31.0      # HTTP 请求
lxml>=5.0.0          # XML/HTML 解析
openai>=1.0.0        # AI API
pyyaml>=6.0.1        # 配置解析
python-dateutil>=2.8.2 # 日期处理
```

## 许可证

MIT License

## 致谢

- [feedparser](https://github.com/kurtmckee/feedparser)
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/)
- [Obsidian](https://obsidian.md/)
- [Dataview](https://github.com/blacksmithgu/obsidian-dataview)
