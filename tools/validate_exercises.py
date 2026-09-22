#!/usr/bin/env python3
"""Validate the current exercise JSON format without external dependencies."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
YEAR_RE = re.compile(r"^(\d{4})-(\d{4})$")
MONTH_RE = re.compile(r"^(\d{4})(\d{2})$")
BLOCK_TYPES = {"regular", "material", "note"}
INDENT_KINDS = {"hanging", "firstLine", "paragraph"}
MARK_KINDS = {"underline", "emphasis"}


def utf16_length(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_format(
    value: Any, text: str, location: str, errors: list[str]
) -> None:
    require(isinstance(value, dict), f"{location}.format must be an object", errors)
    if not isinstance(value, dict):
        return
    indent = value.get("indent")
    if indent is not None:
        require(isinstance(indent, dict), f"{location}.format.indent must be an object", errors)
        if isinstance(indent, dict):
            require(
                indent.get("kind") in INDENT_KINDS,
                f"{location}.format.indent.kind must be one of {sorted(INDENT_KINDS)}",
                errors,
            )
            level = indent.get("level")
            require(
                isinstance(level, int) and not isinstance(level, bool) and 1 <= level <= 8,
                f"{location}.format.indent.level must be an integer from 1 to 8",
                errors,
            )

    marks = value.get("marks")
    if marks is None:
        return
    require(isinstance(marks, dict), f"{location}.format.marks must be an object", errors)
    if not isinstance(marks, dict):
        return
    length = utf16_length(text)
    for kind, ranges in marks.items():
        require(kind in MARK_KINDS, f"{location}.format.marks.{kind} is not supported", errors)
        require(isinstance(ranges, list), f"{location}.format.marks.{kind} must be a list", errors)
        if not isinstance(ranges, list):
            continue
        for index, item in enumerate(ranges):
            item_location = f"{location}.format.marks.{kind}[{index}]"
            require(isinstance(item, dict), f"{item_location} must be an object", errors)
            if not isinstance(item, dict):
                continue
            start, end = item.get("start"), item.get("end")
            valid = (
                isinstance(start, int)
                and not isinstance(start, bool)
                and isinstance(end, int)
                and not isinstance(end, bool)
                and 0 <= start < end <= length
            )
            require(
                valid,
                f"{item_location} must be a UTF-16 range within text (0 <= start < end <= {length})",
                errors,
            )


def validate_block(value: Any, location: str, errors: list[str]) -> None:
    require(isinstance(value, dict), f"{location} must be an object", errors)
    if not isinstance(value, dict):
        return
    kind = value.get("type")
    require(kind in BLOCK_TYPES, f"{location}.type must be one of {sorted(BLOCK_TYPES)}", errors)
    if kind in {"regular", "note"}:
        text = value.get("text")
        require(isinstance(text, str), f"{location}.text must be a string", errors)
        if isinstance(text, str):
            validate_format(value.get("format"), text, location, errors)
    elif kind == "material":
        source_id = value.get("sourceid")
        require(
            isinstance(source_id, int)
            and not isinstance(source_id, bool)
            and (source_id == -1 or source_id > 0),
            f"{location}.sourceid must be -1 or a positive integer",
            errors,
        )
        paragraphs = value.get("paragraphs")
        require(isinstance(paragraphs, list) and paragraphs, f"{location}.paragraphs must be a non-empty list", errors)
        if not isinstance(paragraphs, list):
            return
        for index, paragraph in enumerate(paragraphs):
            paragraph_location = f"{location}.paragraphs[{index}]"
            require(isinstance(paragraph, dict), f"{paragraph_location} must be an object", errors)
            if not isinstance(paragraph, dict):
                continue
            text = paragraph.get("text")
            require(isinstance(text, str), f"{paragraph_location}.text must be a string", errors)
            if isinstance(text, str):
                validate_format(paragraph.get("format"), text, paragraph_location, errors)


def validate_exercise(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        return [f"{path.name}: invalid JSON: {error}"]
    require(isinstance(value, dict), f"{path.name}: root must be an object", errors)
    if not isinstance(value, dict):
        return errors

    def text_field(name: str) -> str | None:
        field = value.get(name)
        require(isinstance(field, str) and field.strip(), f"{path.name}.{name} must be a non-empty string", errors)
        return field if isinstance(field, str) else None

    identifier = text_field("id")
    text_field("title")
    text_field("source")
    text_field("type")
    require(identifier == path.stem, f"{path.name}.id must match the filename", errors)

    year = text_field("year")
    year_match = YEAR_RE.fullmatch(year or "")
    require(year_match is not None, f"{path.name}.year must be YYYY-YYYY", errors)
    if year_match:
        require(
            int(year_match.group(2)) == int(year_match.group(1)) + 1,
            f"{path.name}.year must span consecutive years",
            errors,
        )

    month = value.get("month")
    month_match = (
        MONTH_RE.fullmatch(str(month))
        if isinstance(month, int) and not isinstance(month, bool)
        else None
    )
    valid_month = month_match is not None and 1 <= int(month_match.group(2)) <= 12
    require(valid_month, f"{path.name}.month must be YYYYMM", errors)

    grade, number, score = value.get("grade"), value.get("number"), value.get("score")
    require(isinstance(grade, int) and not isinstance(grade, bool) and 1 <= grade <= 3, f"{path.name}.grade must be an integer from 1 to 3", errors)
    require(isinstance(number, int) and not isinstance(number, bool) and number > 0, f"{path.name}.number must be a positive integer", errors)
    require(isinstance(score, (int, float)) and not isinstance(score, bool) and score >= 0, f"{path.name}.score must be a non-negative number", errors)

    for name in ("question", "answer"):
        blocks = value.get(name)
        require(isinstance(blocks, list), f"{path.name}.{name} must be a list", errors)
        if isinstance(blocks, list):
            for index, block in enumerate(blocks):
                validate_block(block, f"{path.name}.{name}[{index}]", errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=ROOT,
        help="Directory containing exercise JSON files (default: repository root).",
    )
    root = parser.parse_args().root.resolve()
    paths = sorted(
        path
        for path in root.glob("*.json")
        if path.is_file() and path.name != "resource.json"
    )
    errors = [error for path in paths for error in validate_exercise(path)]
    if errors:
        print("Exercise validation failed:", file=sys.stderr)
        print("\n".join(f"- {error}" for error in errors), file=sys.stderr)
        return 1
    print(f"Validated {len(paths)} exercise file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
