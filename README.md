# literature-tracker

面向科研工作流的**文献追踪与推送技能（Skill）**：根据你的参考文献清单或研究方向搭建文献库，持续追踪学界最新动态，支持文献精读讲解与邮箱定期推送。

本技能由网站项目 [Stardy Valley 农经学术追踪系统](https://github.com/nonolwang/stardy-valley) 转化而来：把原网站（Flask + SQLite + 定时任务）背后的工作流沉淀为一套可在对话中按需执行的 Skill，不再依赖服务器、数据库和付费 API。

## 功能

| 能力 | 实现方式 |
|---|---|
| 📥 文献抓取 | arXiv API + 89 个经管期刊 RSS（按 A+/A/B+/B 层级裁剪）+ OpenAlex（免 API key），增量抓取、自动去重 |
| 🗂️ 梳理归类 | 9 个研究方向的中英文关键词词表（可自定义），确定性分类 + 智能体相关性排序 |
| 📝 整理归纳 | 智能体按精读模板输出：研究问题、识别策略、核心结果、局限、与个人方向的相关性 |
| 📮 更新推送 | QQ/163/Gmail SMTP 发送 HTML 简报，支持 launchd/cron 定时无人值守推送 |
| 💬 研究讨论 | 围绕文献库的选题、方法、研究空白讨论，结论可回写为条目笔记 |

## 特点

- **零依赖**：三个脚本只用 Python 标准库，无需 `pip install`
- **数据在你手里**：文献清单是项目目录下的 `reading_list.jsonl`，纯文本、可版本管理
- **凭据安全**：邮箱授权码只走环境变量，不写入任何文件

## 安装

把 `literature-tracker/` 目录复制到技能扫描根目录即可：

```bash
cp -R literature-tracker ~/.bohrium/skills/literature-tracker
```

新开对话后，对智能体说"帮我搭建 XX 方向的文献追踪"即可触发，首次使用会引导你完成初始化（研究方向、期刊范围、邮箱）。

## 目录结构

```
literature-tracker/
├── SKILL.md                        # 技能主说明：五大工作模式与纪律
├── scripts/
│   ├── fetch_papers.py             # 增量抓取：OpenAlex / arXiv / 期刊 RSS → JSONL
│   ├── classify_papers.py          # 关键词主题分类（topics.json 可自定义词表）
│   └── send_digest.py              # HTML 简报邮件推送（--dry-run 预览）
├── assets/
│   ├── topics.json                 # 9 个研究方向的中英文关键词词表
│   ├── journal_sources.json        # 89 个经管期刊 RSS 源（按层级分组）
│   └── tracker_config.template.json # 用户配置模板
└── references/
    ├── push-setup.md               # 邮箱 SMTP 与 launchd/cron 定时推送配置
    └── paper-explainer.md          # 文献精读讲解模板
```

## 手动使用脚本（不经过智能体也可以）

```bash
# 抓取近 7 天文献
python3 literature-tracker/scripts/fetch_papers.py \
    --config tracker_config.json --state tracker_state.json --output new.jsonl

# 按主题词表分类
python3 literature-tracker/scripts/classify_papers.py \
    --input new.jsonl --topics topics.json --require-match --output classified.jsonl

# 预览并发送邮件简报
python3 literature-tracker/scripts/send_digest.py \
    --config tracker_config.json --input classified.jsonl --subject "文献简报" --dry-run
```

## 已知限制

- 部分出版商 RSS 源会失效或反爬（脚本会跳过并记日志）；arXiv 和 OpenAlex 是可靠主力
- 中文文献（知网/万方）无公开 API，需通过检索工具补充或手动录入
- OpenAlex 在共享出口 IP 上可能触发限流（429），配置 `mailto` 可进入礼貌池
