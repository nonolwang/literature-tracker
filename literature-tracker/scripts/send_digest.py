#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文献简报邮件推送：JSONL 文献列表或 Markdown 简报 → HTML 邮件（SMTP）。

仅依赖标准库。用法：
  python3 send_digest.py --config tracker_config.json --input classified.jsonl --subject "文献简报" --dry-run
  python3 send_digest.py --config tracker_config.json --input digest.md --subject "文献简报"

邮箱授权码从环境变量读取（config 的 password_env 指定变量名，默认 QQ_SMTP_AUTH_CODE）。
退出码：0 = 成功/预览；1 = 参数或输入错误；2 = 凭据缺失或发送失败。
"""
import argparse
import json
import os
import re
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from html import escape


def md_to_html(md):
    """极简 Markdown → HTML（标题/加粗/斜体/链接/列表/段落）。"""
    lines, html_parts, in_list = md.split("\n"), [], False
    def inline(t):
        t = escape(t)
        t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
        t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
        t = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', t)
        return t
    for line in lines:
        s = line.strip()
        if s.startswith("- "):
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            html_parts.append("<li>%s</li>" % inline(s[2:]))
            continue
        if in_list:
            html_parts.append("</ul>")
            in_list = False
        if not s:
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", s)
        if m:
            level = len(m.group(1)) + 1  # h2 起，避免与邮件主标题冲突
            html_parts.append("<h%d>%s</h%d>" % (level, inline(m.group(2)), level))
        else:
            html_parts.append("<p>%s</p>" % inline(s))
    if in_list:
        html_parts.append("</ul>")
    return "\n".join(html_parts)


def papers_to_html(records, top_n):
    groups = {}
    for r in records[:top_n]:
        names = r.get("topic_names") or ["未分类"]
        groups.setdefault(" / ".join(names), []).append(r)
    parts = []
    for topic, papers in groups.items():
        parts.append('<h2 style="color:#4a7c3a;font-size:18px;">%s（%d 篇）</h2>' % (escape(topic), len(papers)))
        for p in papers:
            link = escape(p.get("url") or "#")
            parts.append(
                '<div style="margin-bottom:14px;padding:10px;border-left:3px solid #4a7c3a;background:#f9f9f9;">'
                '<h3 style="margin:0 0 4px 0;font-size:15px;"><a href="%s" style="color:#2d5a27;text-decoration:none;">%s</a></h3>'
                '<p style="margin:0;color:#666;font-size:13px;">%s ｜ %s ｜ %s</p>'
                "%s</div>"
                % (
                    link, escape(p.get("title", "")),
                    escape(p.get("authors", "")[:120]), escape(p.get("journal", "")),
                    escape(p.get("published_date", "")),
                    ('<p style="margin:6px 0 0 0;color:#555;font-size:13px;">%s</p>'
                     % escape(p["note"])) if p.get("note") else "",
                )
            )
    return "\n".join(parts)


def wrap_html(title, body_html):
    return (
        '<!DOCTYPE html><html><head><meta charset="UTF-8"></head>'
        '<body style="font-family:&quot;Microsoft YaHei&quot;,Arial,sans-serif;margin:0;padding:20px;background:#f5f5f5;">'
        '<div style="max-width:800px;margin:0 auto;background:#fff;padding:28px;border-radius:5px;">'
        '<h1 style="color:#2d5a27;border-bottom:3px solid #4a7c3a;padding-bottom:10px;">%s</h1>'
        "%s"
        '<div style="margin-top:24px;padding-top:16px;border-top:1px solid #ddd;color:#999;font-size:12px;">'
        "由 literature-tracker 技能生成的文献简报</div></div></body></html>"
    ) % (escape(title), body_html)


def main():
    ap = argparse.ArgumentParser(description="文献简报邮件推送")
    ap.add_argument("--config", required=True, help="tracker_config.json 路径")
    ap.add_argument("--input", required=True, help=".jsonl 文献列表或 .md 简报")
    ap.add_argument("--subject", required=True, help="邮件主题")
    ap.add_argument("--to", help="覆盖收件人（逗号分隔，默认取 config email.to）")
    ap.add_argument("--top", type=int, default=15, help="JSONL 输入时最多推送条数（默认 15）")
    ap.add_argument("--dry-run", action="store_true", help="只预览不发送")
    args = ap.parse_args()

    try:
        with open(args.config, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception as e:
        print("config 读取失败: %s" % e, file=sys.stderr)
        return 1
    email_cfg = cfg.get("email", {})

    if args.input.endswith(".jsonl"):
        records = []
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
        except Exception as e:
            print("输入读取失败: %s" % e, file=sys.stderr)
            return 1
        if not records:
            print("输入为空，没有可推送的条目", file=sys.stderr)
            return 1
        body = papers_to_html(records, args.top)
        plain = "\n".join("%s | %s | %s" % (r.get("title", ""), r.get("journal", ""), r.get("url", ""))
                          for r in records[:args.top])
    else:
        try:
            with open(args.input, "r", encoding="utf-8") as f:
                md = f.read()
        except Exception as e:
            print("输入读取失败: %s" % e, file=sys.stderr)
            return 1
        body = md_to_html(md)
        plain = md

    html = wrap_html(args.subject, body)
    recipients = [r.strip() for r in args.to.split(",")] if args.to else email_cfg.get("to", [])
    recipients = [r for r in recipients if r]

    if args.dry_run:
        print("=== DRY RUN ===")
        print("主题: %s" % args.subject)
        print("收件人: %s" % (", ".join(recipients) or "（未配置）"))
        print("HTML 长度: %d 字符" % len(html))
        print("--- 内容预览（前 600 字符） ---")
        print(re.sub(r"<[^>]+>", " ", html)[:600])
        return 0

    if not recipients:
        print("错误：未配置收件人（config email.to 或 --to）", file=sys.stderr)
        return 1

    username = email_cfg.get("username", "")
    password = os.environ.get(email_cfg.get("password_env", "QQ_SMTP_AUTH_CODE"), "")
    if not username or not password:
        print("错误：缺少 SMTP 凭据。", file=sys.stderr)
        print("注意：QQ/163 等邮箱不允许用登录密码走 SMTP，必须使用网页端单独生成的【授权码】。", file=sys.stderr)
        print("  QQ 邮箱：设置 → 账号 → POP3/SMTP 服务 → 生成授权码", file=sys.stderr)
        print("  163 邮箱：设置 → POP3/SMTP/IMAP → 开启并获取授权码", file=sys.stderr)
        print("然后：在 config 的 email.username 填入邮箱地址，并执行 export %s='你的授权码'"
              % email_cfg.get("password_env", "QQ_SMTP_AUTH_CODE"), file=sys.stderr)
        return 2

    msg = MIMEMultipart("alternative")
    msg["Subject"] = args.subject
    msg["From"] = formataddr(("文献追踪", email_cfg.get("from_addr") or username))
    msg["To"] = ", ".join(recipients)
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))

    host = email_cfg.get("smtp_host", "smtp.qq.com")
    port = int(email_cfg.get("smtp_port", 465))
    try:
        if email_cfg.get("use_ssl", True):
            with smtplib.SMTP_SSL(host, port, timeout=30) as server:
                server.login(username, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=30) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(msg)
    except Exception as e:
        print("发送失败: %s" % e, file=sys.stderr)
        return 2

    print("已发送给 %s" % ", ".join(recipients))
    return 0


if __name__ == "__main__":
    sys.exit(main())
