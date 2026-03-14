#!/usr/bin/env python3
"""GitHub Trending 抓取器 - 每天获取热门项目并生成报告"""

import re
import json
from datetime import datetime
from urllib.request import urlopen, Request

LANGUAGES = ["", "python", "javascript", "go", "rust", "typescript"]  # "" = 全部
BASE_URL = "https://github.com/trending"


def fetch_trending(language=""):
    """抓取某个语言的 Trending 页面"""
    url = f"{BASE_URL}/{language}" if language else BASE_URL
    req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def parse_trending(html):
    """解析 Trending HTML，提取项目信息"""
    projects = []

    # 匹配每个项目块
    pattern = r'<article class="Box-row">.*?</article>'
    articles = re.findall(pattern, html, re.DOTALL)

    for article in articles[:10]:  # 只取前10个
        # 项目名 - 从 h2 > a 标签中提取
        name_match = re.search(r'<h2[^>]*>.*?<a[^>]*href="/([^/]+/[^"]+)"', article, re.DOTALL)
        if not name_match:
            # 备用: 找第一个看起来像 owner/repo 的链接
            name_match = re.search(r'href="/([a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+)"[^>]*>\s*\n?\s*<span', article)
        if not name_match:
            name_match = re.search(r'href="/([a-zA-Z0-9_-]+/[a-zA-Z0-9_.-]+)"', article)
        name = name_match.group(1).strip() if name_match else "unknown"

        # 过滤掉非仓库链接
        if name.startswith("login") or name.startswith("sponsors") or "/" not in name:
            continue

        # 描述
        desc_match = re.search(r'<p class="[^"]*col-9[^"]*"[^>]*>\s*(.+?)\s*</p>', article, re.DOTALL)
        desc = desc_match.group(1).strip() if desc_match else ""
        desc = re.sub(r'<[^>]+>', '', desc).strip()

        # 语言
        lang_match = re.search(r'itemprop="programmingLanguage">([^<]+)</span>', article)
        lang = lang_match.group(1).strip() if lang_match else ""

        # 总 Star 数
        star_match = re.search(r'/stargazers"[^>]*>[\s\n]*([0-9,]+)', article)
        stars = star_match.group(1).replace(",", "").strip() if star_match else "0"

        # 今日 Star
        today_match = re.search(r'([\d,]+)\s+stars?\s+today', article)
        today = today_match.group(1).replace(",", "") if today_match else "0"

        projects.append({
            "name": name,
            "url": f"https://github.com/{name}",
            "description": desc[:100] + "..." if len(desc) > 100 else desc,
            "language": lang,
            "stars": int(stars) if stars.isdigit() else 0,
            "stars_today": int(today) if today.isdigit() else 0,
        })

    return projects


def generate_markdown(all_trending):
    """生成 Markdown 报告"""
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"# GitHub Trending - {today}",
        "",
        f"> 自动更新于 {datetime.now().strftime('%Y-%m-%d %H:%M')} UTC",
        "",
    ]

    for lang, projects in all_trending.items():
        lang_name = lang.upper() if lang else "All Languages"
        lines.append(f"## {lang_name}")
        lines.append("")
        lines.append("| # | 项目 | 描述 | 语言 | Stars | 今日 |")
        lines.append("|---|------|------|------|-------|------|")

        for i, p in enumerate(projects, 1):
            name_link = f"[{p['name']}]({p['url']})"
            desc = p['description'].replace("|", "/")
            lines.append(f"| {i} | {name_link} | {desc} | {p['language']} | {p['stars']:,} | +{p['stars_today']} |")

        lines.append("")

    return "\n".join(lines)


def generate_issue_body(all_trending):
    """生成 Issue 内容（用于邮件通知）"""
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"## GitHub Trending 日报 - {today}", ""]

    # 只放全语言的 Top 10
    projects = all_trending.get("", [])
    for i, p in enumerate(projects[:10], 1):
        lines.append(f"**{i}. [{p['name']}]({p['url']})** ⭐ {p['stars']:,} (+{p['stars_today']} today)")
        if p['description']:
            lines.append(f"   > {p['description']}")
        lines.append("")

    return "\n".join(lines)


def main():
    print("Fetching GitHub Trending...")
    all_trending = {}

    for lang in LANGUAGES:
        lang_name = lang if lang else "all"
        print(f"  - {lang_name}...")
        try:
            html = fetch_trending(lang)
            projects = parse_trending(html)
            all_trending[lang] = projects
            print(f"    Found {len(projects)} projects")
        except Exception as e:
            print(f"    Error: {e}")
            all_trending[lang] = []

    # 生成 README
    readme = generate_markdown(all_trending)
    with open("README.md", "w") as f:
        f.write(readme)
    print("\nREADME.md updated!")

    # 生成 Issue 内容
    issue_body = generate_issue_body(all_trending)
    with open("issue_body.md", "w") as f:
        f.write(issue_body)
    print("issue_body.md generated!")

    # 保存 JSON（可选，方便后续处理）
    with open("trending.json", "w") as f:
        json.dump(all_trending, f, ensure_ascii=False, indent=2)
    print("trending.json saved!")


if __name__ == "__main__":
    main()
