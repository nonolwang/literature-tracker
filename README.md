# literature-tracker

面向所有学科的**个人文献追踪助手（Skill）**：给它一份参考文献清单，或者只说一个研究方向，就能帮你搭建文献库、追踪最新论文、精读讲解，并把新文献简报定期推送到邮箱。

## 它能帮你做什么

| 能力 | 你说 | 你得到 |
|---|---|---|
| 📚 建文献库 | "帮我搭建*土壤碳汇*方向的文献库" 或粘贴一份参考文献清单 | `reading_list.jsonl`：标题、作者、期刊、日期、DOI、摘要齐全的结构化清单 + 主题分布概览 |
| 🔍 追新文献 | "看看最近有什么新文献" | 距上次更新以来的新论文，按主题归类、按相关性排序，去重后并入清单 |
| 📖 精读讲解 | "讲讲清单里第 3 篇" | 一页纸讲解：研究问题、方法、核心结果、局限、和你研究方向的关系 |
| 📮 邮箱推送 | "把本周新文献发我邮箱" | HTML 文献简报邮件；也可配置定时任务自动推送 |
| 💬 研究讨论 | "这几篇的方法有什么区别，还有什么空白" | 围绕库中文献的讨论，结论可写回清单长期积累 |

## 上手流程

```
1. 初始化（一次性，约 2 分钟）   告诉它研究方向或粘贴参考文献（+ 邮箱，可选）
2. 建库                        确认它整理出的第一版文献清单
3. 日常使用                    一句话指令：更新 / 精读 / 推送
4. 自动化（可选）              配一次 launchd/cron，之后简报定期自动到达
```

## 安装

把 `literature-tracker/` 目录复制到技能扫描根目录：

```bash
git clone https://github.com/nonolwang/literature-tracker.git
cp -R literature-tracker/literature-tracker ~/.bohrium/skills/literature-tracker
```

新开对话后说"帮我搭建 XX 方向的文献追踪"即可触发，首次使用会引导你完成初始化。

## 特点

- **学科无关**：检索关键词、主题词表、追踪来源都根据你的研究方向现场生成，不绑定任何特定领域
- **零依赖**：脚本只用 Python 标准库，无需 `pip install`，无需付费 API key（检索走 OpenAlex / arXiv 免费接口）
- **数据在你手里**：文献清单是项目目录下的纯文本 JSONL，可 git 管理、可手动编辑
- **凭据安全**：邮箱授权码只走环境变量，不写入任何文件

## 目录结构

```
literature-tracker/
├── SKILL.md                          # 技能主说明：能力、上手流程、五大工作模式
├── scripts/
│   ├── fetch_papers.py               # 增量抓取：OpenAlex / arXiv / 期刊 RSS → JSONL
│   ├── classify_papers.py            # 按主题词表做关键词分类
│   └── send_digest.py                # HTML 简报邮件推送（--dry-run 预览）
├── assets/
│   ├── tracker_config.template.json  # 用户配置模板
│   └── examples/                     # 词表与期刊源的格式示例（农经领域，仅供参考）
├── references/
│   ├── push-setup.md                 # 邮箱 SMTP 与 launchd/cron 定时推送配置
│   └── paper-explainer.md            # 文献精读讲解模板
```

## 手动使用脚本（不经过智能体也可以）

```bash
# 抓取近 7 天文献（关键词换成你的方向）
python3 literature-tracker/scripts/fetch_papers.py \
    --config tracker_config.json --state tracker_state.json --output new.jsonl

# 按你的主题词表分类
python3 literature-tracker/scripts/classify_papers.py \
    --input new.jsonl --topics topics.json --require-match --output classified.jsonl

# 预览并发送邮件简报
python3 literature-tracker/scripts/send_digest.py \
    --config tracker_config.json --input classified.jsonl --subject "文献简报" --dry-run
```

## 已知限制

- 部分出版商 RSS 源会失效或反爬（脚本会跳过并记日志）；OpenAlex 和 arXiv 是可靠主力
- 中文文献（知网/万方）无公开 API，需通过检索工具补充或手动录入
- OpenAlex 在共享出口 IP 上可能触发限流（429），脚本会自动重试，配置邮箱 `mailto` 可进入礼貌池
