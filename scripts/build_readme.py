#!/usr/bin/env python3
"""Refresh the numbers in README.md from GitHub.

    GITHUB_TOKEN=... python3 scripts/build_readme.py

Updates the merged-PR line in the whoami block, the "N merged" link on each Open Source line,
and the ★ count on each Featured Work line. All prose is hand-written.
"""
import json
import os
import re
import urllib.parse
import urllib.request

LOGIN = "alanhuangyoo"
EXCLUDE_OWNERS = ["alanhuangyoo", "ArtClaw1"]  # own account and own org don't count as upstream

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def api(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": LOGIN + "-readme"}
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    with urllib.request.urlopen(urllib.request.Request("https://api.github.com" + path, headers=headers), timeout=30) as resp:
        return json.load(resp)


def merged_counts():
    query = "author:%s type:pr is:merged %s" % (LOGIN, " ".join("-user:" + o for o in EXCLUDE_OWNERS))
    counts, seen, page = {}, 0, 1
    while True:
        res = api("/search/issues?" + urllib.parse.urlencode({"q": query, "per_page": 100, "page": page}))
        for item in res["items"]:
            repo = item["repository_url"].split("/repos/", 1)[1].lower()
            counts[repo] = counts.get(repo, 0) + 1
        seen += len(res["items"])
        if not res["items"] or seen >= res["total_count"] or page == 10:
            return counts
        page += 1


def human(n):
    return str(n) if n < 1000 else ("%.1fk" % (n / 1000.0)).replace(".0k", "k")


def main():
    path = os.path.join(ROOT, "README.md")
    content = open(path, encoding="utf-8").read()
    counts = merged_counts()

    content = re.sub(r"^\d+ merged upstream PRs · \d+ repos$",
                     "%d merged upstream PRs · %d repos" % (sum(counts.values()), len(counts)), content, flags=re.MULTILINE)

    def merged_link(m):
        return "%s%d%s" % (m.group(1), counts.get(m.group(2).lower(), 0), m.group(3))
    content = re.sub(r"(^- \*\*\[([\w.-]+/[\w.-]+)\].*· \[)\d+( merged\])", merged_link, content, flags=re.MULTILINE)

    def stars(m):
        return m.group(1) + human(api("/repos/" + m.group(2))["stargazers_count"])
    content = re.sub(r"(^- \*\*\[([\w.-]+/[\w.-]+)\].*★)[\d.]+k?$", stars, content, flags=re.MULTILINE)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("%d merged upstream PRs across %d repos" % (sum(counts.values()), len(counts)))


if __name__ == "__main__":
    main()
