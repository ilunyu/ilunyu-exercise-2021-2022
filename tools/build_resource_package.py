#!/usr/bin/env python3
"""Build an Android-installable exercise resource package from this repository."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from validate_exercises import validate_exercise


ROOT = Path(__file__).resolve().parents[1]
YEAR_RE = re.compile(r"^(\d{4})-(\d{4})$")
PACKAGE_ID_RE = re.compile(r"^exercise\.\d{4}-\d{4}$")


class PackageError(ValueError):
    """The source repository cannot be converted into a resource package."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PackageError(f"{path}: invalid JSON: {error}") from error
    if not isinstance(value, dict):
        raise PackageError(f"{path}: root must be a JSON object")
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def exercise_summary(exercise: dict[str, Any]) -> dict[str, Any]:
    return {
        key: exercise[key]
        for key in ("id", "title", "year", "source", "type", "grade", "number", "score", "month")
    }


def resource_config(root: Path) -> dict[str, Any]:
    config = read_json(root / "resource.json")
    required_strings = ("packageId", "kind", "year", "name", "versionName", "license")
    for field in required_strings:
        if not isinstance(config.get(field), str) or not config[field].strip():
            raise PackageError(f"resource.json.{field} must be a non-empty string")
    if config["kind"] != "exercise":
        raise PackageError("resource.json.kind must be exercise")
    if not PACKAGE_ID_RE.fullmatch(config["packageId"]):
        raise PackageError("resource.json.packageId must be exercise.YYYY-YYYY")
    year_match = YEAR_RE.fullmatch(config["year"])
    if year_match is None or int(year_match.group(2)) != int(year_match.group(1)) + 1:
        raise PackageError("resource.json.year must be consecutive YYYY-YYYY")
    package_year = config["packageId"].removeprefix("exercise.")
    if package_year != config["year"]:
        raise PackageError("resource.json.packageId must use resource.json.year")
    for field in ("versionCode", "minAppVersionCode"):
        value = config.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise PackageError(f"resource.json.{field} must be a positive integer")
    source = config.get("sourceRepository", "")
    if not isinstance(source, str):
        raise PackageError("resource.json.sourceRepository must be a string")
    return config


def source_exercises(root: Path, expected_year: str) -> list[dict[str, Any]]:
    paths = sorted(path for path in root.glob("*.json") if path.name != "resource.json")
    if not paths:
        raise PackageError("the repository root has no exercise JSON files")

    errors = [error for path in paths for error in validate_exercise(path)]
    if errors:
        raise PackageError("exercise validation failed:\n- " + "\n- ".join(errors))

    exercises = [read_json(path) for path in paths]
    identifiers = [exercise["id"] for exercise in exercises]
    if len(identifiers) != len(set(identifiers)):
        raise PackageError("exercise IDs must be unique within a resource package")
    mismatched = [exercise["id"] for exercise in exercises if exercise["year"] != expected_year]
    if mismatched:
        raise PackageError(
            f"exercise year must match resource.json.year ({expected_year}): {', '.join(mismatched)}"
        )
    return sorted(exercises, key=lambda item: item["id"])


def created_at() -> str:
    source_date_epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if source_date_epoch:
        return datetime.fromtimestamp(int(source_date_epoch), tz=timezone.utc).isoformat().replace("+00:00", "Z")
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def deterministic_zip(source: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(source.rglob("*")):
            if not path.is_file():
                continue
            info = zipfile.ZipInfo(path.relative_to(source).as_posix(), date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def build(root: Path, output: Path, source_repository: str | None) -> dict[str, Any]:
    config = resource_config(root)
    if source_repository is not None:
        config["sourceRepository"] = source_repository
    exercises = source_exercises(root, config["year"])

    with tempfile.TemporaryDirectory(prefix="ilunyu-resource-") as temporary:
        package_root = Path(temporary)
        content = package_root / "content"
        summaries = [exercise_summary(exercise) for exercise in exercises]
        write_json(content / "index.json", {"formatVersion": 2, "exercises": summaries})
        write_json(content / "search.json", {"formatVersion": 2, "exercises": summaries})
        for exercise in exercises:
            write_json(content / "items" / f"{exercise['id']}.json", exercise)

        files = {
            path.relative_to(package_root).as_posix(): sha256(path)
            for path in sorted(content.rglob("*.json"))
        }
        manifest = {
            "packageFormat": 1,
            "contentSchema": 1,
            "packageId": config["packageId"],
            "kind": config["kind"],
            "name": config["name"],
            "versionName": config["versionName"],
            "versionCode": config["versionCode"],
            "minAppVersionCode": config["minAppVersionCode"],
            "sourceRepository": config["sourceRepository"],
            "license": config["license"],
            "createdAt": created_at(),
            "files": files,
        }
        write_json(package_root / "manifest.json", manifest)
        deterministic_zip(package_root, output)

    metadata = {
        "packageId": manifest["packageId"],
        "kind": manifest["kind"],
        "name": manifest["name"],
        "versionName": manifest["versionName"],
        "versionCode": manifest["versionCode"],
        "minAppVersionCode": manifest["minAppVersionCode"],
        "sourceRepository": manifest["sourceRepository"],
        "size": output.stat().st_size,
        "sha256": sha256(output),
    }
    write_json(output.with_name("release.json"), metadata)
    output.with_name(f"{output.name}.sha256").write_text(
        f"{metadata['sha256']}  {output.name}\n", encoding="utf-8"
    )
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Exercise repository root")
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "resource.ilunyupack", help="Package output path")
    parser.add_argument("--source-repository", help="GitHub repository URL recorded in the resource manifest")
    args = parser.parse_args()
    try:
        metadata = build(args.root.resolve(), args.output.resolve(), args.source_repository)
    except PackageError as error:
        print(f"Resource package build failed: {error}", file=sys.stderr)
        return 1
    print(
        f"Built {args.output}: {metadata['packageId']} {metadata['versionName']} "
        f"({metadata['size']} bytes, SHA-256 {metadata['sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
