# literature-tracker

面向所有学科的**个人文献追踪助手（Skill）**：给它一份参考文献清单，或者只说一个研究方向，就能帮你搭建文献库、追踪最新论文、精读讲解，并把新文献简报定期推送到邮箱。

## 适用人群

- 需要持续跟踪某个研究领域最新进展的研究生、青年教师和科研人员
- 不想写代码、不想部署服务器，希望"说一句话就能用"的用户
- 需要定期向自己（或课题组）邮箱投递文献简报的人
- 任何学科：检索关键词、主题词表、追踪来源都根据你的方向现场生成

## 使用场景

- **开题/进入新方向**：给出研究方向（如"土壤碳汇""大模型对齐"），自动搭建第一版文献库
- **已有参考文献**：粘贴文献清单或 BibTeX，逐条核实元数据后整理成结构化文献库
- **日常追踪**：一句"看看最近有什么新文献"，自动抓取、归类、排序并并入文献库
- **精读文献**：指定任意一篇，得到一页纸讲解（研究问题、方法、核心结果、局限、与你方向的相关性）
- **定期推送**：配置一次后，新文献简报按天/按周自动发到邮箱，无需值守
- **研究讨论**：围绕文献库讨论选题、方法差异与研究空白，结论可回写为条目笔记

## 对应产出

| 你做的事 | 得到的产出 |
|---|---|
| 提供研究方向或参考文献 | `reading_list.jsonl` 结构化文献库（标题、作者、期刊、日期、DOI、摘要齐全）+ 主题分布概览 |
| 说"更新文献" | 距上次更新以来的新论文清单，按主题归类、按相关性排序、去重合并 |
| 说"讲讲这篇" | 一页纸精读笔记，可直接存档 |
| 说"发本周简报到邮箱" | HTML 格式的文献简报邮件（含每篇 2–3 句中文导读） |
| 配置定时任务（可选） | 定期自动到达的邮件简报 |

## 上手流程

```
1. 初始化（一次性，约 2 分钟）   告诉它研究方向或粘贴参考文献（+ 邮箱和 SMTP 授权码，可选）
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

- **学科无关**：不绑定任何特定领域，词表和来源按你的方向定制
- **零依赖**：脚本只用 Python 标准库，无需 `pip install`，无需付费 API key（检索走 OpenAlex / arXiv 免费接口）
- **数据在你手里**：文献清单是项目目录下的纯文本 JSONL，可 git 管理、可手动编辑
- **凭据安全**：邮箱 SMTP 授权码（不是登录密码）只走环境变量，不写入任何文件
- **结果可核实**：清单中每条文献都来自检索接口返回，不凭模型记忆生成

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
│   └── examples/                     # 词表与期刊源的格式示例
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

## 致谢

本技能的设计与开发在**玻尔（Bohrium）科研平台**的 SciMaster 智能体辅助下完成：由其将作者自建的文献追踪网站的工作流提炼、泛化并封装为可复用的 Skill。感谢玻尔平台提供的智能体开发与技能运行环境。

## 原创声明

本项目为 **100% 原创**作品：全部代码、技能说明与文档均由项目作者（在玻尔 SciMaster 智能体辅助下）原创完成，未复制任何第三方项目的代码或文档。
