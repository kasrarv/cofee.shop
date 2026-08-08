#!/usr/bin/env python3
"""Search and install Claude Code skills from the claude-skill-registry index.

Data source: https://github.com/majiayu000/claude-skill-registry
JSON API:    https://majiayu000.github.io/claude-skill-registry-core/

Stdlib only. Network access to *.github.io / raw.githubusercontent.com / github.com
is required; downloaded indices are cached under ~/.cache/claude-skill-registry.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://majiayu000.github.io/claude-skill-registry-core"
RAW = "https://raw.githubusercontent.com"
CACHE_DIR = Path(os.environ.get("SKILL_REGISTRY_CACHE", Path.home() / ".cache" / "claude-skill-registry"))
CACHE_TTL = int(os.environ.get("SKILL_REGISTRY_TTL", 24 * 3600))
TIMEOUT = 120

# Category short codes used by the sharded index -> canonical slugs in the lite index.
CODE_ALIASES = {
    "dev": "development",
    "ops": "devops",
    "sec": "security",
    "doc": "documentation",
    "test": "testing",
    "data": "data",
    "ai": "ai-llm",
}


# ---------------------------------------------------------------- fetching


def _fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "claude-skill-registry-skill"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def fetch_cached(path: str, ttl: int = CACHE_TTL) -> bytes:
    """GET {BASE}/{path} with an on-disk cache."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = CACHE_DIR / re.sub(r"[^A-Za-z0-9._-]", "_", path)
    if cache_file.exists() and time.time() - cache_file.stat().st_mtime < ttl:
        return cache_file.read_bytes()
    try:
        data = _fetch(f"{BASE}/{path}")
    except (urllib.error.URLError, TimeoutError) as exc:
        if cache_file.exists():
            print(f"warning: fetch failed ({exc}); using stale cache for {path}", file=sys.stderr)
            return cache_file.read_bytes()
        raise SystemExit(f"error: could not fetch {BASE}/{path}: {exc}")
    cache_file.write_bytes(data)
    return data


def load_json(path: str, ttl: int = CACHE_TTL):
    data = fetch_cached(path, ttl)
    if path.endswith(".gz"):
        data = gzip.decompress(data)
    return json.loads(data)


# ---------------------------------------------------------------- index loading


def normalize_install(install: str) -> str:
    install = install.strip().strip("/")
    if install.endswith("/SKILL.md"):
        install = install[: -len("/SKILL.md")]
    return install


def _record_from_lite(s: dict) -> dict:
    return {
        "name": s.get("name", ""),
        "description": s.get("description", ""),
        "category": s.get("category", ""),
        "tags": s.get("tags") or [],
        "stars": s.get("stars") or 0,
        "install": normalize_install(s.get("install") or ""),
        "branch": s.get("branch") or "main",
        "quality": s.get("quality_grade") or "",
        "security": s.get("security_status") or "",
        "install_status": s.get("install_status") or "",
    }


def _record_from_shard(s: dict) -> dict:
    code = s.get("c", "")
    return {
        "name": s.get("n", ""),
        "description": s.get("d", ""),
        "category": CODE_ALIASES.get(code, code),
        "tags": s.get("g") or [],
        "stars": s.get("r") or 0,
        "install": normalize_install(s.get("i") or ""),
        "branch": s.get("b") or "main",
        "quality": "",
        "security": "",
        "install_status": "",
    }


def load_skills(full: bool = False) -> list[dict]:
    """Load index records. Default is the curated lite index (~3.5 MB, 5k skills);
    full=True pulls every gzipped shard (~10 MB, 160k+ skills)."""
    if not full:
        return [_record_from_lite(s) for s in load_json("search-index-lite.json").get("skills", [])]

    manifest = load_json("search-index-manifest.json")
    out: list[dict] = []
    for shard in manifest.get("shards", []):
        path = shard.get("gzip_path") or shard.get("path")
        part = load_json(path)
        out.extend(_record_from_shard(s) for s in part.get("s", []))
    return out


# ---------------------------------------------------------------- search


def score(rec: dict, terms: list[str]) -> float:
    name = rec["name"].lower()
    desc = rec["description"].lower()
    tags = [t.lower() for t in rec["tags"]]
    cat = rec["category"].lower()
    name_words = set(re.split(r"[^a-z0-9]+", name))
    query = " ".join(terms)

    total = 0.0
    if name == query:
        total += 200
    elif query and query in name:
        total += 90

    for term in terms:
        if term == name:
            total += 120
        elif term in name_words:
            total += 60
        elif term in name:
            total += 35
        if term in tags:
            total += 25
        if term in cat:
            total += 15
        if term in desc:
            total += 12

    if total == 0:
        return 0.0

    # Popularity and curation nudges — never enough to outrank a real name match.
    total += min(math.log10(rec["stars"] + 1) * 4, 20)
    total += {"S": 8, "A": 6, "B": 4, "C": 2}.get(rec["quality"], 0)
    if rec["security"] == "passed":
        total += 3
    if rec["install_status"] == "known_good":
        total += 3
    return total


def cmd_search(args) -> int:
    terms = [t.lower() for t in re.split(r"\s+", args.query.strip()) if t]
    if not terms:
        raise SystemExit("error: empty query")

    skills = load_skills(full=args.all)
    hits = []
    for rec in skills:
        if args.category and rec["category"].lower() != args.category.lower():
            continue
        if rec["stars"] < args.min_stars:
            continue
        s = score(rec, terms)
        if s > 0:
            hits.append((s, rec))
    hits.sort(key=lambda x: (-x[0], -x[1]["stars"], x[1]["name"]))
    hits = hits[: args.limit]

    if args.json:
        print(json.dumps([r for _, r in hits], indent=2))
        return 0

    if not hits:
        scope = "full index" if args.all else "curated index (retry with --all for all 160k+ skills)"
        print(f"No matches for {args.query!r} in the {scope}.")
        return 1

    print(f"{len(hits)} match(es) for {args.query!r}"
          f"{'' if args.all else '  [curated index; use --all to search everything]'}\n")
    for i, (s, r) in enumerate(hits, 1):
        flags = " ".join(
            x for x in (
                f"quality:{r['quality']}" if r["quality"] else "",
                f"security:{r['security']}" if r["security"] else "",
            ) if x
        )
        print(f"{i}. {r['name']}  ({r['stars']:,}★  {r['category'] or 'uncategorized'}"
              f"{'  ' + flags if flags else ''})")
        print(f"   {r['description'][:160]}")
        print(f"   install: {r['install']}  [branch: {r['branch']}]")
        print()
    print("Next: registry.py show <install>   |   registry.py install <install>")
    return 0


# ---------------------------------------------------------------- show / install


def split_install(install: str) -> tuple[str, str, str]:
    install = normalize_install(install)
    parts = install.split("/")
    if len(parts) < 3:
        raise SystemExit(
            f"error: {install!r} is not a valid install path — expected owner/repo/path/to/skill"
        )
    return parts[0], parts[1], "/".join(parts[2:])


def lookup_branch(install: str, given: str | None) -> list[str]:
    if given:
        return [given]
    target = normalize_install(install)
    try:
        for rec in load_skills(full=False):
            if rec["install"] == target:
                return [rec["branch"], "main", "master"]
    except SystemExit:
        pass
    return ["main", "master"]


def fetch_skill_md(owner: str, repo: str, path: str, branches: list[str]) -> tuple[str, str]:
    errors = []
    seen = []
    for branch in branches:
        if branch in seen:
            continue
        seen.append(branch)
        url = f"{RAW}/{owner}/{repo}/{branch}/{path}/SKILL.md"
        try:
            return _fetch(url).decode("utf-8", "replace"), branch
        except urllib.error.HTTPError as exc:
            errors.append(f"{branch}: HTTP {exc.code}")
        except (urllib.error.URLError, TimeoutError) as exc:
            errors.append(f"{branch}: {exc}")
    raise SystemExit(f"error: could not fetch SKILL.md for {owner}/{repo}/{path} ({'; '.join(errors)})")


def cmd_show(args) -> int:
    owner, repo, path = split_install(args.install)
    body, branch = fetch_skill_md(owner, repo, path, lookup_branch(args.install, args.branch))
    print(f"# source: https://github.com/{owner}/{repo}/blob/{branch}/{path}/SKILL.md\n")
    if args.full:
        print(body)
    else:
        lines = body.splitlines()
        print("\n".join(lines[:120]))
        if len(lines) > 120:
            print(f"\n... [{len(lines) - 120} more lines — rerun with --full]")
    return 0


def sparse_clone(owner: str, repo: str, path: str, branch: str, workdir: Path) -> Path:
    """Blobless sparse clone so huge monorepos stay cheap. Returns the skill dir."""
    clone = workdir / "repo"
    subprocess.run(
        ["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse",
         "--branch", branch, f"https://github.com/{owner}/{repo}.git", str(clone)],
        check=True, capture_output=True, text=True,
    )
    subprocess.run(["git", "-C", str(clone), "sparse-checkout", "set", "--no-cone", path],
                   check=True, capture_output=True, text=True)
    src = clone / path
    if not src.is_dir():
        raise FileNotFoundError(path)
    return src


def cmd_install(args) -> int:
    owner, repo, path = split_install(args.install)
    branches = lookup_branch(args.install, args.branch)

    dest_root = Path(args.dest) if args.dest else (
        Path.cwd() / ".claude" / "skills" if args.project else Path.home() / ".claude" / "skills"
    )
    name = args.name or path.rstrip("/").split("/")[-1]
    target = dest_root / name

    if target.exists() and not args.force:
        raise SystemExit(f"error: {target} already exists — pass --force to overwrite")

    installed_via = None
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        for branch in branches:
            try:
                src = sparse_clone(owner, repo, path, branch, work)
            except (subprocess.CalledProcessError, FileNotFoundError):
                shutil.rmtree(work / "repo", ignore_errors=True)
                continue
            if target.exists():
                shutil.rmtree(target)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, target, ignore=shutil.ignore_patterns(".git"))
            installed_via = f"git sparse clone ({branch})"
            break

        if installed_via is None:
            # Fallback: the repo may be unclonable here (network policy, huge, gone).
            # A skill is still usable with SKILL.md alone, minus any bundled assets.
            body, branch = fetch_skill_md(owner, repo, path, branches)
            target.mkdir(parents=True, exist_ok=True)
            (target / "SKILL.md").write_text(body)
            installed_via = f"raw SKILL.md only ({branch}) — bundled scripts/references were NOT fetched"

    print(f"Installed {name} -> {target}")
    print(f"  method: {installed_via}")
    print(f"  source: https://github.com/{owner}/{repo}/tree/{branches[0]}/{path}")
    print("\nReview SKILL.md before using it — a skill is instructions this agent will follow,")
    print("and community skills are third-party code. Restart Claude Code to pick it up.")
    return 0


# ---------------------------------------------------------------- misc


def cmd_categories(args) -> int:
    data = load_json("categories/index.json")
    cats = sorted(data.get("categories", []), key=lambda c: -c.get("count", 0))
    print(f"{data.get('category_count', len(cats))} categories, "
          f"{data.get('total_count', 0):,} skills indexed\n")
    for c in cats:
        print(f"  {c['name']:<24} {c.get('count', 0):>7,}")
    return 0


def cmd_stats(args) -> int:
    d = load_json("stats.json", ttl=3600)
    print(f"updated_at:        {d.get('updated_at')}")
    print(f"skills (dedup):    {d.get('registry_skill_count_dedup', 0):,}")
    print(f"SKILL.md files:    {d.get('archive_skill_md_count_raw', 0):,}")
    print(f"categories:        {d.get('categories')}")
    print(f"plugins:           {d.get('total_plugins')}")
    return 0


def main() -> int:
    # Piping into `head` should not raise.
    try:
        import signal

        signal.signal(signal.SIGPIPE, signal.SIG_DFL)
    except (ImportError, AttributeError, ValueError):
        pass

    p = argparse.ArgumentParser(prog="registry.py", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="search the registry")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=10)
    s.add_argument("--category")
    s.add_argument("--min-stars", type=int, default=0)
    s.add_argument("--all", action="store_true", help="search all 160k+ skills (~10 MB download, cached)")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_search)

    s = sub.add_parser("show", help="print a skill's SKILL.md")
    s.add_argument("install", help="owner/repo/path/to/skill")
    s.add_argument("--branch")
    s.add_argument("--full", action="store_true")
    s.set_defaults(func=cmd_show)

    s = sub.add_parser("install", help="download a skill into a skills directory")
    s.add_argument("install", help="owner/repo/path/to/skill")
    s.add_argument("--branch")
    s.add_argument("--name", help="install under a different directory name")
    s.add_argument("--dest", help="explicit destination directory")
    s.add_argument("--project", action="store_true", help="install to ./.claude/skills instead of ~/.claude/skills")
    s.add_argument("--force", action="store_true")
    s.set_defaults(func=cmd_install)

    sub.add_parser("categories", help="list categories and counts").set_defaults(func=cmd_categories)
    sub.add_parser("stats", help="registry size and freshness").set_defaults(func=cmd_stats)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
