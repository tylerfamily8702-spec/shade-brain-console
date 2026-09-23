#!/usr/bin/env python3
"""List Obsidian capture notes by their long or short feedback loop.

The script reads Markdown files with YAML frontmatter, never edits the vault,
and has no required third-party dependency. If PyYAML is installed it is used
for full YAML parsing; otherwise a deliberately small parser handles the
simple scalar and tag-list frontmatter used by this capture kit.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Any

try:  # Prefer a full YAML parser when a vault already has more complex metadata.
    import yaml  # type: ignore
except ImportError:  # Keep the utility usable in a plain Python install.
    yaml = None

SKIP_DIRECTORIES = {".obsidian", ".trash", ".git", "node_modules"}
FRONTMATTER_BOUNDARY = re.compile(r"^---\s*$")
KEY_VALUE = re.compile(r"^([A-Za-z0-9_-]+):(?:\s*(.*))?$")
LIST_VALUE = re.compile(r"^\s*-\s+(.*)$")
VALID_LOOPS = {"long", "short"}


def fallback_yaml_load(text: str) -> dict[str, Any]:
    """Parse the simple YAML subset used by the template without dependencies."""
    data: dict[str, Any] = {}
    lines = text.splitlines()
    index = 0

    while index < len(lines):
        line = lines[index]
        if not line.strip() or line.lstrip().startswith("#"):
            index += 1
            continue
        match = KEY_VALUE.match(line)
        if not match:
            raise ValueError(f"unsupported frontmatter line: {line!r}")

        key, raw_value = match.groups()
        raw_value = (raw_value or "").strip()
        if raw_value:
            data[key] = parse_scalar(raw_value)
            index += 1
            continue

        values: list[Any] = []
        index += 1
        while index < len(lines):
            child = lines[index]
            list_match = LIST_VALUE.match(child)
            if not list_match:
                break
            values.append(parse_scalar(list_match.group(1).strip()))
            index += 1
        data[key] = values if values else None

    return data


def parse_scalar(value: str) -> Any:
    if value.startswith("[") and value.endswith("]"):
        inner = value[1:-1].strip()
        return [] if not inner else [parse_scalar(item.strip()) for item in inner.split(",")]
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        try:
            return ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return value[1:-1]
    lower = value.lower()
    if lower in {"true", "false"}:
        return lower == "true"
    if lower in {"null", "~"}:
        return None
    return value


def read_frontmatter(path: Path) -> dict[str, Any] | None:
    """Return YAML frontmatter from a Markdown file, or None when absent."""
    try:
        with path.open("r", encoding="utf-8") as handle:
            first_line = handle.readline()
            if not FRONTMATTER_BOUNDARY.match(first_line.rstrip("\n\r")):
                return None
            frontmatter_lines: list[str] = []
            for line in handle:
                if FRONTMATTER_BOUNDARY.match(line.rstrip("\n\r")):
                    break
                frontmatter_lines.append(line)
            else:
                raise ValueError("opening frontmatter boundary has no closing boundary")
    except UnicodeDecodeError as exc:
        raise ValueError("file is not UTF-8 text") from exc

    frontmatter = "".join(frontmatter_lines)
    try:
        parsed = yaml.safe_load(frontmatter) if yaml else fallback_yaml_load(frontmatter)
    except Exception as exc:  # PyYAML exposes several parser exception classes.
        raise ValueError(f"invalid YAML frontmatter: {exc}") from exc

    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise ValueError("frontmatter must be a YAML mapping")
    return {str(key): value for key, value in parsed.items()}


def created_sort_key(value: Any) -> tuple[int, datetime]:
    """Sort dated notes newest first; undated or invalid dates always come last."""
    if isinstance(value, datetime):
        return (0, value)
    if isinstance(value, date):
        return (0, datetime.combine(value, datetime.min.time()))
    if value is not None:
        text = str(value).strip()
        for parser in (datetime.fromisoformat, lambda item: datetime.strptime(item, "%Y-%m-%d")):
            try:
                return (0, parser(text))
            except ValueError:
                pass
    return (1, datetime.min)


def normalise_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(tag).lstrip("#") for tag in value]
    return [str(value).lstrip("#")]


def scan_vault(vault: Path) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    loops: dict[str, list[dict[str, Any]]] = {"long": [], "short": []}
    warnings: list[str] = []

    for path in vault.rglob("*.md"):
        if any(part in SKIP_DIRECTORIES for part in path.relative_to(vault).parts):
            continue
        try:
            metadata = read_frontmatter(path)
        except ValueError as exc:
            warnings.append(f"{path.relative_to(vault)}: {exc}")
            continue
        if metadata is None:
            continue

        loop_cycle = str(metadata.get("loop_cycle", "")).strip().lower()
        if loop_cycle not in VALID_LOOPS:
            continue

        loops[loop_cycle].append(
            {
                "path": path.relative_to(vault).as_posix(),
                "title": path.stem,
                "created": str(metadata.get("created", "")),
                "status": str(metadata.get("status", "")),
                "source": str(metadata.get("source", "")),
                "significance": str(metadata.get("significance", "")),
                "tags": normalise_tags(metadata.get("tags")),
            }
        )

    for entries in loops.values():
        entries.sort(key=lambda item: created_sort_key(item["created"]), reverse=True)
    return loops, warnings


def text_report(loops: dict[str, list[dict[str, Any]]], warnings: list[str]) -> str:
    sections: list[str] = []
    for cycle, cadence in (("short", "daily / every 2-3 days"), ("long", "weekly Sunday audit")):
        entries = loops[cycle]
        sections.append(f"{cycle.upper()} LOOP - {cadence} ({len(entries)} items)")
        if entries:
            for item in entries:
                tags = ", ".join(f"#{tag}" for tag in item["tags"]) or "no tags"
                details = " | ".join(part for part in (item["created"], item["status"], item["significance"]) if part)
                sections.append(f"- {item['title']} [{details or 'no metadata'}] - {item['path']} ({tags})")
        else:
            sections.append("- none")
        sections.append("")

    if warnings:
        sections.append(f"WARNINGS ({len(warnings)})")
        sections.extend(f"- {warning}" for warning in warnings)
    return "\n".join(sections).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Surface Obsidian captures on long and short feedback loops.")
    parser.add_argument("vault", type=Path, help="Path to the root of the Obsidian vault")
    parser.add_argument("--format", choices=("text", "json"), default="text", help="Report format (default: text)")
    parser.add_argument("--output", type=Path, help="Write the report to this file instead of stdout")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    vault = args.vault.expanduser().resolve()
    if not vault.is_dir():
        print(f"Vault directory not found: {vault}", file=sys.stderr)
        return 2

    loops, warnings = scan_vault(vault)
    if args.format == "json":
        report = json.dumps({"long_loop": loops["long"], "short_loop": loops["short"], "warnings": warnings}, indent=2) + "\n"
    else:
        report = text_report(loops, warnings)

    if args.output:
        args.output.expanduser().write_text(report, encoding="utf-8")
    else:
        print(report, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
