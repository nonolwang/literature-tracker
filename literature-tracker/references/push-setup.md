# 定时推送与邮箱配置

## 邮箱 SMTP 配置

授权码**不是邮箱登录密码**，需在邮箱网页端单独生成，并写入环境变量（不要写进任何文件）：

| 邮箱 | smtp_host | 端口 | use_ssl | 授权码获取 |
|---|---|---|---|---|
| QQ 邮箱 | smtp.qq.com | 465 | true | 设置 → 账号 → POP3/SMTP 服务 → 生成授权码 |
| 163 邮箱 | smtp.163.com | 465 | true | 设置 → POP3/SMTP/IMAP → 开启并获取授权码 |
| Gmail | smtp.gmail.com | 587 | false（STARTTLS）| 需开启两步验证后创建"应用专用密码" |

`tracker_config.json` 中 `password_env` 指定环境变量名（默认 `QQ_SMTP_AUTH_CODE`），发送前在 shell 中导出：

```bash
export QQ_SMTP_AUTH_CODE='你的授权码'
```

## 定时推送（无人值守）

定时版本只做"抓取 → 分类 → 元数据简报推送"，不含 AI 导读。先确认手动跑通，再挂定时。

封装一条命令（以项目目录 `/path/to/lit-project`、技能目录 `/path/to/skills/literature-tracker` 为例）：

```bash
#!/bin/bash
# daily_digest.sh —— 抓取、分类、推送三连
set -e
PROJ=/path/to/lit-project
SKILL=/path/to/skills/literature-tracker
export QQ_SMTP_AUTH_CODE='你的授权码'   # 或从钥匙串读取
python3 "$SKILL/scripts/fetch_papers.py" --config "$PROJ/tracker_config.json" \
    --state "$PROJ/tracker_state.json" --output "$PROJ/new_papers.jsonl"
python3 "$SKILL/scripts/classify_papers.py" --input "$PROJ/new_papers.jsonl" \
    --topics "$PROJ/topics.json" --require-match --output "$PROJ/new_classified.jsonl"
# 没有匹配条目时 classify 输出为空文件，发送前检查
if [ -s "$PROJ/new_classified.jsonl" ]; then
  python3 "$SKILL/scripts/send_digest.py" --config "$PROJ/tracker_config.json" \
      --input "$PROJ/new_classified.jsonl" --subject "文献简报 $(date +%F)"
fi
```

### macOS launchd（推荐）

新建 `~/Library/LaunchAgents/com.user.literature-tracker.plist`，下面示例为每 3 天上午 8:00 运行（Interval 259200 秒）：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.user.literature-tracker</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>/path/to/daily_digest.sh</string></array>
  <key>StartInterval</key><integer>259200</integer>
  <key>StandardOutPath</key><string>/tmp/literature-tracker.log</string>
  <key>StandardErrorPath</key><string>/tmp/literature-tracker.err</string>
</dict>
</plist>
```

加载：`launchctl load ~/Library/LaunchAgents/com.user.literature-tracker.plist`

### cron（备选）

`crontab -e` 添加（每天 8:00，脚本内部按 state 去重，频率可调）：

```cron
0 8 * * * /bin/bash /path/to/daily_digest.sh >> /tmp/literature-tracker.log 2>&1
```

## 注意事项

- 定时推送与对话内推送共用 `tracker_state.json` 的 last_fetch，二者不会重复推送同一批文献；但对话内精读过的条目建议在 `reading_list.jsonl` 里补 `note` 字段，避免定时简报里显得生硬。
- RSS 源偶有失效（出版商下线 feed），脚本会跳过并记日志，不影响其他来源；定期查看日志确认来源健康。
- 想改成"定时抓取 + 对话内讲解后再推"：把 daily_digest.sh 里的 send_digest 行去掉，定时只更新清单；推送在对话中触发。
