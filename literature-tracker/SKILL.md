---
name: literature-tracker
description: 搭建并维护个人文献清单、追踪研究方向或目标期刊的最新论文动态、精读讲解文献，并将新文献简报推送到邮箱（支持定时自动推送）。当用户提到文献追踪、搭建文献清单/文献库、学界最新动态、新论文监控、定期推送文献、文献简报、晨读文献、tracking papers、literature digest 等需求时使用。单次的文献检索问答、论文写作与润色、引用格式整理不触发本技能。
---

# 文献追踪与推送助手

把"文献抓取 → 梳理归类 → 整理归纳 → 更新推送 → 研究讨论"沉淀为一套可复用的对话式工作流。技能内置确定性脚本完成抓取、分类、发信；智能体负责选题判断、归纳讲解和与用户的讨论。

## 原则（必须遵守）

- 绝不凭记忆编造文献。清单中每一条目的标题、作者、期刊、日期、DOI 必须来自脚本抓取结果或检索工具（paper_search / web 检索）的返回。
- 脚本、配置、模板都从本技能目录解析（用加载时的技能目录作为基准路径），不要依赖当前工作目录。
- 用户数据（配置、文献清单、状态文件）一律存放在用户指定的项目目录中，技能目录保持只读。
- 邮箱授权码等凭据只通过环境变量读取（如 `QQ_SMTP_AUTH_CODE`），不写进任何文件，不出现在对话输出中。
- 首次配置推送时，先 `--dry-run` 预览并给用户看样例，用户确认后才真实发送。
- 定时任务（launchd/cron）只做"抓取 + 分类 + 元数据简报推送"，不含 AI 讲解；带归纳讲解的推送由用户在对话中触发（见模式 D）。

## 首次初始化（只做一次）

1. 询问并确认四件事：研究方向（或一份种子参考文献清单）、关注的期刊范围（默认用 `assets/journal_sources.json` 中的经管期刊 RSS，可按层级 A+/A/B+/B 裁剪）、接收推送的邮箱、存放数据的项目目录。
2. 把 `assets/tracker_config.template.json` 复制到项目目录为 `tracker_config.json`，填入用户的 keywords、期刊层级和邮箱；把 `assets/topics.json` 复制过去供用户自定义主题词表。
3. 提醒用户设置邮箱授权码环境变量（QQ/163 邮箱需在网页端开启 SMTP 并生成授权码，见 `references/push-setup.md`）。

## 模式 A：搭建文献清单

- 用户给参考文献清单（粘贴文本 / BibTeX / PDF 列表）：逐条用 paper_search 或 Crossref 核实元数据，查不到的条目标记"未核实"并告知用户，然后写入 `reading_list.jsonl`（每行一条 JSON，字段：title, authors, journal, published_date, doi, url, abstract, source, topics）。
- 用户只给研究方向：把方向拆解为 3–8 组英文检索关键词（可参考 `assets/topics.json` 的 topics 体系），然后跑模式 B 的抓取做首次建库（`--days 30`）。
- 建库后向用户汇报：总量、主题分布、时间跨度，并询问是否需要精读其中某几篇。

## 模式 B：更新追踪（抓取 + 归类）

```bash
python3 <技能目录>/scripts/fetch_papers.py --config <项目目录>/tracker_config.json \
    --state <项目目录>/tracker_state.json --output <项目目录>/new_papers.jsonl
python3 <技能目录>/scripts/classify_papers.py --input <项目目录>/new_papers.jsonl \
    --topics <项目目录>/topics.json --output <项目目录>/new_classified.jsonl
```

- `--state` 让脚本自动从上次抓取日期增量抓取并回写状态；首次运行用 `--days 30`。
- 分类后由智能体读新增条目的标题与摘要，按与用户方向的相关性排序、剔除明显不相关的（给出理由），再追加合并进 `reading_list.jsonl`（按 doi/url/标题去重）。
- 中文文献：知网/万方无公开 API，用 paper_search 的中文语料（zh）按主题检索补充；用户在知网看到的文献可给题录让智能体按同一 JSONL 格式手动录入。

## 模式 C：精读讲解

用户指定清单中某篇（或给 DOI/标题）时，按 `references/paper-explainer.md` 的模板输出讲解：研究问题、数据与识别策略、核心结果、局限、与用户研究方向的相关性和可借用点。讲解只基于可获得的摘要/正文，明确标注哪些内容只是基于摘要的推断。

## 模式 D：邮箱推送

```bash
python3 <技能目录>/scripts/send_digest.py --config <项目目录>/tracker_config.json \
    --input <项目目录>/new_classified.jsonl --subject "文献简报 $(date +%F)" --dry-run
```

- 流程：模式 B 产出新条目 → 智能体为入选条目写 2–3 句中文导读（研究问题 + 方法 + 一个亮点），在对话中给用户预览 → 确认后去掉 `--dry-run` 真实发送。
- 用户确认过首次样例后，之后的推送可在用户一句话指令下直接执行（"发本周简报"）。
- 定时自动推送（每 N 天无人值守）：按 `references/push-setup.md` 配置 launchd 或 cron；定时版本推送的是元数据简报（无 AI 导读），需要讲解时用户在对话里发起。

## 模式 E：研究讨论

围绕清单内容讨论（选题价值、方法对比、文献间的矛盾、研究空白）时，先引用清单中的具体条目，再展开；讨论产出的结论可经用户同意后作为笔记字段追加到对应条目（`note` 字段），保持清单可积累。
