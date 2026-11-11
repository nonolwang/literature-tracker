#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文献主题分类：按 topics.json 的中英文关键词表做确定性匹配。

用法：
  python3 classify_papers.py --input new.jsonl --topics topics.json --output classified.jsonl
  python3 classify_papers.py --input new.jsonl --topics topics.json --require-match --output classified.jsonl

退出码：0 = 成功；1 = 输入错误。
"""
import argparse
import json
import sys
from collections import Counter


def load_jsonl(path):
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                print("第 %d 行 JSON 解析失败: %s" % (i, e), file=sys.stderr)
                return None
    return records


def main():
    ap = argparse.ArgumentParser(description="文献关键词主题分类")
    ap.add_argument("--input", required=True, help="输入 JSONL")
    ap.add_argument("--output", required=True, help="输出 JSONL")
    ap.add_argument("--topics", required=True, help="topics.json 主题词表")
    ap.add_argument("--require-match", action="store_true", help="只保留至少匹配一个主题的条目")
    args = ap.parse_args()

    try:
        with open(args.topics, "r", encoding="utf-8") as f:
            topics = json.load(f)
    except Exception as e:
        print("topics 文件读取失败: %s" % e, file=sys.stderr)
        return 1

    records = load_jsonl(args.input)
    if records is None:
        return 1

    kept, dropped, counts = [], 0, Counter()
    for r in records:
        text = ("%s %s" % (r.get("title", ""), r.get("abstract", ""))).lower()
        matched = []
        for tid, info in topics.items():
            kws = info.get("keywords_en", []) + info.get("keywords_cn", [])
            if any(kw.lower() in text for kw in kws):
                matched.append(tid)
        if args.require_match and not matched:
            dropped += 1
            continue
        r["topics"] = matched
        r["topic_names"] = [topics[t].get("name_cn", t) for t in matched]
        for t in matched:
            counts[t] += 1
        kept.append(r)

    with open(args.output, "w", encoding="utf-8") as f:
        for r in kept:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    print("保留 %d 条，过滤 %d 条" % (len(kept), dropped), file=sys.stderr)
    for tid, n in counts.most_common():
        print("  %s (%s): %d" % (tid, topics.get(tid, {}).get("name_cn", tid), n), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
