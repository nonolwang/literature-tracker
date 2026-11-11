#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""文献增量抓取：OpenAlex / arXiv / 期刊 RSS → 统一 JSONL。

仅依赖 Python 标准库。用法：
  python3 fetch_papers.py --config tracker_config.json --state tracker_state.json --output new.jsonl
  python3 fetch_papers.py --keywords "cultivated land quality,green agriculture" --days 30 --output new.jsonl

退出码：0 = 至少一个来源成功；1 = 参数或输入错误；2 = 所有来源均失败。
"""
import argparse
import email.utils
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36 literature-tracker/1.0"}
ATOM_NS = {"a": "http://www.w3.org/2005/Atom"}
SKILL_DIR = None  # 由调用方通过 --config 相对路径或默认 assets 定位

DEFAULT_ARXIV_CATEGORIES = ["econ.GN", "econ.EM", "econ.TH"]


def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def log(msg):
    print("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg), file=sys.stderr)


# ---------- OpenAlex ----------

def reconstruct_abstract(inv_index):
    if not inv_index:
        return ""
    pos = {}
    for word, idxs in inv_index.items():
        for i in idxs:
            pos[i] = word
    return " ".join(pos[i] for i in sorted(pos))


def fetch_openalex(keywords, since, per_kw_limit, mailto=""):
    records, ok = [], False
    for kw in keywords:
        params = {
            "search": kw,
            "filter": "from_publication_date:%s" % since,
            "per-page": min(per_kw_limit, 50),
            "sort": "publication_date:desc",
            "select": "id,doi,title,publication_date,authorships,primary_location,abstract_inverted_index,cited_by_count",
        }
        if mailto:
            params["mailto"] = mailto
        url = "https://api.openalex.org/works?" + urllib.parse.urlencode(params)
        data = None
        for attempt in range(4):
            try:
                data = json.loads(http_get(url).decode("utf-8"))
                ok = True
                break
            except Exception as e:
                wait = 5 * (attempt + 1)
                log("openalex 第 %d 次尝试失败 [%s]: %s（%ds 后重试）" % (attempt + 1, kw, e, wait))
                time.sleep(wait)
        if data is None:
            log("openalex FAIL [%s]: 多次重试后仍失败" % kw)
            continue
        for w in data.get("results", []):
            loc = w.get("primary_location") or {}
            src = loc.get("source") or {}
            records.append({
                "title": (w.get("title") or "").strip(),
                "authors": "; ".join((a.get("author") or {}).get("display_name", "")
                                     for a in w.get("authorships", [])),
                "journal": src.get("display_name") or "",
                "published_date": w.get("publication_date") or "",
                "doi": (w.get("doi") or "").replace("https://doi.org/", ""),
                "url": loc.get("landing_page_url") or w.get("id") or "",
                "abstract": reconstruct_abstract(w.get("abstract_inverted_index")),
                "cited_by_count": w.get("cited_by_count", 0),
                "source": "openalex",
                "matched_query": kw,
            })
        log("openalex [%s]: %d 条" % (kw, len(data.get("results", []))))
        time.sleep(0.3)
    return records, ok


# ---------- arXiv ----------

def fetch_arxiv(keywords, since, categories, per_kw_limit):
    records, ok = [], False
    cat_q = " OR ".join("cat:%s" % c for c in categories)
    for kw in keywords:
        q = '(%s) AND all:"%s"' % (cat_q, kw)
        params = {
            "search_query": q, "start": 0, "max_results": min(per_kw_limit, 50),
            "sortBy": "submittedDate", "sortOrder": "descending",
        }
        url = "http://export.arxiv.org/api/query?" + urllib.parse.urlencode(params)
        try:
            root = ET.fromstring(http_get(url))
            ok = True
        except Exception as e:
            log("arxiv FAIL [%s]: %s" % (kw, e))
            continue
        n = 0
        for entry in root.findall("a:entry", ATOM_NS):
            published = (entry.findtext("a:published", default="", namespaces=ATOM_NS) or "")[:10]
            if published and published < since:
                continue
            authors = "; ".join((a.findtext("a:name", default="", namespaces=ATOM_NS) or "")
                                for a in entry.findall("a:author", ATOM_NS))
            records.append({
                "title": re.sub(r"\s+", " ", entry.findtext("a:title", default="", namespaces=ATOM_NS)).strip(),
                "authors": authors,
                "journal": "arXiv (preprint)",
                "published_date": published,
                "doi": "",
                "url": (entry.findtext("a:id", default="", namespaces=ATOM_NS) or "").strip(),
                "abstract": re.sub(r"\s+", " ", entry.findtext("a:summary", default="", namespaces=ATOM_NS)).strip(),
                "cited_by_count": 0,
                "source": "arxiv",
                "matched_query": kw,
            })
            n += 1
        log("arxiv [%s]: %d 条" % (kw, n))
        time.sleep(3)  # arXiv API 限速
    return records, ok


# ---------- 期刊 RSS ----------

def parse_rss_date(entry, tag_candidates):
    for tag in tag_candidates:
        text = entry.findtext(tag)
        if text:
            try:
                return email.utils.parsedate_to_datetime(text).strftime("%Y-%m-%d")
            except Exception:
                m = re.search(r"(\d{4}-\d{2}-\d{2})", text)
                if m:
                    return m.group(1)
    return ""


def fetch_rss(journal_name, rss_url, since, max_items=50):
    records, ok = [], False
    try:
        content = http_get(rss_url)
        root = ET.fromstring(content)
        ok = True
    except Exception as e:
        log("rss FAIL [%s]: %s" % (journal_name, e))
        return records, ok

    def clean(html_text):
        return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html_text or "")).strip()

    if root.tag.endswith("feed"):  # Atom
        for e in root.findall("a:entry", ATOM_NS)[:max_items]:
            published = (e.findtext("a:published", namespaces=ATOM_NS)
                         or e.findtext("a:updated", default="", namespaces=ATOM_NS) or "")[:10]
            if published and published < since:
                continue
            link = ""
            for l in e.findall("a:link", ATOM_NS):
                if l.get("rel") in (None, "alternate"):
                    link = l.get("href", "")
                    break
            records.append({
                "title": clean(e.findtext("a:title", default="", namespaces=ATOM_NS)),
                "authors": "; ".join((a.findtext("a:name", default="", namespaces=ATOM_NS) or "")
                                     for a in e.findall("a:author", ATOM_NS)),
                "journal": journal_name,
                "published_date": published,
                "doi": "",
                "url": link,
                "abstract": clean(e.findtext("a:summary", default="", namespaces=ATOM_NS))[:2000],
                "cited_by_count": 0,
                "source": "rss",
                "matched_query": "",
            })
    else:  # RSS 2.0
        months = {m: i + 1 for i, m in enumerate(
            ["january", "february", "march", "april", "may", "june", "july",
             "august", "september", "october", "november", "december"])}
        for it in list(root.iter("item"))[:max_items]:
            desc = clean(it.findtext("description"))
            published = parse_rss_date(it, ["pubDate", "date", "{http://purl.org/dc/elements/1.1/}date"])
            if not published:
                # ScienceDirect 等 feed 把日期放在 description 里："Publication date: December 2026"
                m = re.search(r"Publication date:\s*([A-Za-z]+)\s+(\d{4})", desc)
                if m and m.group(1).lower() in months:
                    published = "%04d-%02d-01" % (int(m.group(2)), months[m.group(1).lower()])
            if published and published < since:
                continue
            authors = clean(it.findtext("author") or it.findtext("{http://purl.org/dc/elements/1.1/}creator"))
            if not authors:
                m = re.search(r"Author\(s\):\s*(.+)$", desc)
                if m:
                    authors = m.group(1).strip()
            records.append({
                "title": clean(it.findtext("title")),
                "authors": authors,
                "journal": journal_name,
                "published_date": published,
                "doi": "",
                "url": (it.findtext("link") or "").strip(),
                "abstract": desc[:2000],
                "cited_by_count": 0,
                "source": "rss",
                "matched_query": "",
            })
    log("rss [%s]: %d 条" % (journal_name, len(records)))
    return records, ok


# ---------- 主流程 ----------

def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def dedupe(records):
    seen, out = set(), []
    for r in records:
        key = r.get("doi") or r.get("url") or re.sub(r"\W+", "", (r.get("title") or "").lower())
        if key and key not in seen:
            seen.add(key)
            out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser(description="文献增量抓取 → JSONL")
    ap.add_argument("--config", help="tracker_config.json 路径（提供 keywords/RSS 期刊源/arXiv 分类）")
    ap.add_argument("--keywords", help="逗号分隔的检索词（无 config 时必填）")
    ap.add_argument("--since", help="起始日期 YYYY-MM-DD（优先于 --days 和 state）")
    ap.add_argument("--days", type=int, default=7, help="回溯天数（默认 7）")
    ap.add_argument("--state", help="状态文件路径：读取 last_fetch 作为起始日期，成功后回写")
    ap.add_argument("--limit", type=int, default=25, help="每个关键词每个来源的最大条数（默认 25）")
    ap.add_argument("--sources", default="openalex,arxiv,rss", help="启用来源，逗号分隔")
    ap.add_argument("--journals", help="journal_sources.json 路径（覆盖 config 中的路径）")
    ap.add_argument("--output", required=True, help="输出 JSONL 路径")
    args = ap.parse_args()

    keywords, rss_journals, arxiv_cats, mailto = [], [], DEFAULT_ARXIV_CATEGORIES, ""
    if args.config:
        try:
            cfg = load_json(args.config)
        except Exception as e:
            log("无法读取 config: %s" % e)
            return 1
        interests = cfg.get("interests", {})
        keywords = interests.get("keywords", [])
        arxiv_cats = interests.get("arxiv_categories", DEFAULT_ARXIV_CATEGORIES)
        mailto = cfg.get("email", {}).get("from_addr", "")
        js_path = args.journals or interests.get("journal_sources_file")
        if js_path and interests.get("use_journal_rss", True):
            try:
                tiers_wanted = set(interests.get("journal_tiers", ["A+", "A", "B+", "B", "WP"]))
                js = load_json(js_path)
                for tier, journals in js.items():
                    if tier in tiers_wanted:
                        rss_journals.extend(journals)
            except Exception as e:
                log("期刊源文件读取失败（跳过 RSS）: %s" % e)
    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(",") if k.strip()]
    if not keywords and not rss_journals:
        log("错误：没有检索关键词也没有 RSS 期刊源")
        return 1

    since = args.since
    state = {}
    if not since and args.state:
        try:
            state = load_json(args.state)
            since = state.get("last_fetch")
        except Exception:
            state = {}
    if not since:
        since = (datetime.now() - timedelta(days=args.days)).strftime("%Y-%m-%d")
    log("抓取起始日期: %s" % since)

    enabled = {s.strip() for s in args.sources.split(",")}
    all_records, any_ok = [], False

    if "openalex" in enabled and keywords:
        recs, ok = fetch_openalex(keywords, since, args.limit, mailto)
        all_records.extend(recs)
        any_ok = any_ok or ok
    if "arxiv" in enabled and keywords:
        recs, ok = fetch_arxiv(keywords, since, arxiv_cats, args.limit)
        all_records.extend(recs)
        any_ok = any_ok or ok
    if "rss" in enabled:
        for j in rss_journals:
            recs, ok = fetch_rss(j["name"], j["rss"], since)
            for r in recs:
                r["journal_tier"] = j.get("tier", "")
            all_records.extend(recs)
            any_ok = any_ok or ok
            time.sleep(1)

    all_records = dedupe([r for r in all_records if r.get("title")])
    all_records.sort(key=lambda r: r.get("published_date") or "", reverse=True)

    with open(args.output, "w", encoding="utf-8") as f:
        for r in all_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    log("共 %d 条（去重后），写入 %s" % (len(all_records), args.output))

    if any_ok and args.state:
        state["last_fetch"] = datetime.now().strftime("%Y-%m-%d")
        state["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        state["last_count"] = len(all_records)
        with open(args.state, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    return 0 if any_ok else 2


if __name__ == "__main__":
    sys.exit(main())
