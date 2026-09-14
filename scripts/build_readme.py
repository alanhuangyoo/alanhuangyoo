#!/usr/bin/env python3
"""Refresh the auto-updated parts of README.md from GitHub.

    GITHUB_TOKEN=... python3 scripts/build_readme.py

Rewrites the <!-- recent_merged --> and <!-- upstream --> blocks, the merged-PR line in the
whoami block, and the ★ count on each Featured Work line. Everything else is hand-written.
"""
import json
import os
import re
import urllib.parse
import urllib.request

LOGIN = "alanhuangyoo"
EXCLUDE_OWNERS = ["alanhuangyoo", "ArtClaw1"]  # own account and own org don't count as upstream
RECENT = 8
TITLE_MAX = 34

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def api(path):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": LOGIN + "-readme"}
    if TOKEN:
        headers["Authorization"] = "Bearer " + TOKEN
    with urllib.request.urlopen(urllib.request.Request("https://api.github.com" + path, headers=headers), timeout=30) as resp:
        return json.load(resp)


def merged_prs():
    query = "author:%s type:pr is:merged %s" % (LOGIN, " ".join("-user:" + o for o in EXCLUDE_OWNERS))
    items, page = [], 1
    while True:
        res = api("/search/issues?" + urllib.parse.urlencode({"q": query, "per_page": 100, "page": page}))
        items += res["items"]
        if not res["items"] or len(items) >= res["total_count"] or page == 10:
            break
        page += 1
    prs = [{"repo": it["repository_url"].split("/repos/", 1)[1], "title": it["title"], "url": it["html_url"],
            "merged_at": it["pull_request"]["merged_at"]} for it in items]
    return sorted(prs, key=lambda pr: pr["merged_at"], reverse=True)


def human(n):
    if n < 1000:
        return str(n)
    return ("%.1fk" % (n / 1000.0)).replace(".0k", "k")


def link_text(s):
    return s.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]").replace("<", "&lt;").replace(">", "&gt;")


def shorten(s, limit):
    return s if len(s) <= limit else s[:limit - 1].rstrip() + "…"


def replace_block(content, marker, body):
    pattern = re.compile(r"<!-- %s starts -->.*?<!-- %s ends -->" % (marker, marker), re.DOTALL)
    return pattern.sub(lambda _: "<!-- %s starts -->\n%s\n<!-- %s ends -->" % (marker, body, marker), content)


def main():
    path = os.path.join(ROOT, "README.md")
    content = open(path, encoding="utf-8").read()

    prs = merged_prs()
    counts = {}
    for pr in prs:
        counts[pr["repo"]] = counts.get(pr["repo"], 0) + 1
    featured = re.findall(r"^- \*\*\[([\w.-]+/[\w.-]+)\]", content, re.MULTILINE)
    stars = {repo: api("/repos/" + repo)["stargazers_count"] for repo in sorted(set(counts) | set(featured))}

    recent = "<br>".join(
        "• [%s](%s) - %s" % (link_text(pr["repo"].split("/")[1] + " · " + shorten(pr["title"], TITLE_MAX)), pr["url"], pr["merged_at"][:10])
        for pr in prs[:RECENT])
    more = "https://github.com/search?" + urllib.parse.urlencode(
        {"q": "author:%s is:pr is:merged %s" % (LOGIN, " ".join("-user:" + o for o in EXCLUDE_OWNERS)), "type": "pullrequests"})
    content = replace_block(content, "recent_merged", recent + "<br>→ [all merged PRs](%s)" % more)

    upstream = "<br>".join(
        "• [%s](https://github.com/%s/pulls?%s) — **%d** merged · ★%s" % (
            repo.split("/")[1], repo, urllib.parse.urlencode({"q": "is:pr author:" + LOGIN}), n, human(stars[repo]))
        for repo, n in sorted(counts.items(), key=lambda kv: (-kv[1], -stars[kv[0]])))
    content = replace_block(content, "upstream", upstream)

    content = re.sub(r"^\d+ merged upstream PRs · \d+ repos$",
                     "%d merged upstream PRs · %d repos" % (len(prs), len(counts)), content, flags=re.MULTILINE)
    for repo in featured:
        line = re.compile(r"^(- \*\*\[%s\].*★)[\d.]+k?$" % re.escape(repo), re.MULTILINE)
        content = line.sub(lambda m: m.group(1) + human(stars[repo]), content)

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("%d merged upstream PRs across %d repos" % (len(prs), len(counts)))


if __name__ == "__main__":
    main()
