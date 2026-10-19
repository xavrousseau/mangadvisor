"""Mangadvisor tracked-repository contract audit (read-only, CI friendly).

Run with: python tools/audit_repository.py
No runtime network access, external Python dependency or Docker access needed.
All tracked files are enumerated; code files get UTF-8 and syntax checks,
source references are checked where the referenced path is explicit.
"""
from __future__ import annotations

import argparse
import ast
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BINARY = {".docx", ".xlsx", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".webp"}
SCANNED = {".py", ".js", ".mjs", ".css", ".html", ".sql", ".yml",
           ".yaml", ".ps1", ".cmd", ".md", ".txt", ".csv", ".toml", ".conf"}
EXPECTED_SERVICES = ("postgres:", "meilisearch:", "api:", "web:", "engine:")


def inventory():
    result = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT,
                            check=True, capture_output=True)
    return [Path(part.decode("utf-8")) for part in result.stdout.split(b"\0") if part]


def check():
    failures = []
    warnings = []
    examined = Counter()
    paths = inventory()
    all_paths = {p.as_posix() for p in paths}
    for relative in paths:
        target = ROOT / relative
        suffix = target.suffix.lower()
        if not target.is_file():
            failures.append(f"Missing Git-tracked file: {relative}")
            continue
        if suffix in BINARY:
            examined["binary assets"] += 1
            continue
        examined["text files"] += 1
        try:
            data = target.read_bytes()
            content = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            failures.append(f"Non UTF-8 tracked file: {relative}")
            continue
        if suffix == ".py":
            examined["Python syntax"] += 1
            try:
                ast.parse(content, filename=relative.as_posix())
            except SyntaxError as exc:
                failures.append(f"Python syntax error: {relative}: {exc}")
        elif suffix in (".js", ".mjs"):
            examined["JavaScript files"] += 1
            for reference in re.findall(r'''(?:from\s*|import\s*)["'](\./[^"']+\.js)["']''', content):
                dependency = (target.parent / reference).resolve()
                if not dependency.is_file() or ROOT not in dependency.parents:
                    failures.append(f"Broken JavaScript dependency {relative}: {reference}")
        elif suffix == ".md":
            examined["documentation files"] += 1
            # Historic V1 documents may contain obsolete conceptual links.
            # Flag such links for editorial review rather than deleting docs.
            for link in re.findall(r"\]\(([^)]+)\)", content):
                destination = link.split("#", 1)[0].replace("%20", " ")
                if not destination or ":" in destination or destination.startswith("#"):
                    continue
                if destination.startswith(("/", "mailto:")):
                    continue
                if not (target.parent / destination).exists():
                    warnings.append(f"Documentation link to review: {relative} -> {destination}")
        if relative.as_posix().startswith("cmd/") and suffix == ".ps1":
            if any(x >= 128 for x in data) and not data.startswith(b"\xef\xbb\xbf"):
                failures.append(f"Windows PowerShell 5.1 encoding: {relative}")
        if relative.as_posix() == "mangadvisor.cmd":
            for name in re.findall(r'%ROOT_DIR%cmd\\([\w-]+\.cmd)', content):
                if f"cmd/{name}" not in all_paths:
                    failures.append(f"Menu references missing cmd/{name}")
    nginx = (ROOT / "apps/web/nginx.conf").read_text(encoding="utf-8")
    compose = (ROOT / "infra/compose/docker-compose.yml").read_text(encoding="utf-8")
    for service in EXPECTED_SERVICES:
        if not re.search(r"(?m)^  " + re.escape(service), compose):
            failures.append(f"Missing Compose service: {service}")
    for contract, ok in {
        "Docker DNS refresh": "resolver 127.0.0.11" in nginx,
        "Web depends on healthy API": re.search(
            r"(?ms)^  web:.*?^    depends_on:\s*\n      api:\s*\n        condition: service_healthy",
            compose) is not None,
        "Legacy Streamlit opt in": 'profiles: ["legacy"]' in compose,
        "API has a healthcheck": "healthcheck:" in compose[compose.index("  api:"):compose.index("  ollama:")],
        "Pending entries never use manga FK": "CREATE TABLE IF NOT EXISTS user_manga_inventory_pending" in
            (ROOT / "apps/api/app/inventory_import.py").read_text(encoding="utf-8"),
        "No destructive legacy Jikan import": "TRUNCATE " not in
            (ROOT / "pipelines/engine/scripts/run_jikan_pipeline.py").read_text(encoding="utf-8"),
        "Backup checks pending inventory": "user_manga_inventory_pending" in
            (ROOT / "cmd/library-backup.ps1").read_text(encoding="utf-8"),
        "Only 8501 restored by backup": "up -d api web ui" not in
            (ROOT / "cmd/library-backup.ps1").read_text(encoding="utf-8"),
    }.items():
        if not ok:
            failures.append(f"Broken application contract: {contract}")
    for dockerfile in sorted((ROOT / "infra/docker").glob("*/Dockerfile")):
        for source in re.findall(r"(?m)^COPY\s+([^\s]+)", dockerfile.read_text("utf-8")):
            if source.startswith("--"):
                continue
            if not (ROOT / source).exists():
                failures.append(f"{dockerfile.relative_to(ROOT)}: missing COPY source {source}")
        examined["Dockerfiles"] += 1
    return paths, examined, failures, warnings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true",
                        help="Nonzero return code on broken code and deployment contracts")
    options = parser.parse_args()
    paths, scanned, failures, warnings = check()
    print(f"TRACKED FILES: {len(paths)}")
    for category, count in sorted(scanned.items()):
        print(f"  {category}: {count}")
    for item in failures:
        print("FAIL: " + item)
    for item in warnings[:30]:
        print("NOTE: " + item)
    if len(warnings) > 30:
        print(f"NOTE: {len(warnings)-30} additional legacy doc links to review")
    print(f"RESULT: {len(failures)} critical defects, {len(warnings)} documentation notices")
    return 1 if failures and options.strict else 0


if __name__ == "__main__":
    raise SystemExit(main())
