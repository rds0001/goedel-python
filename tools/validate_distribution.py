#!/usr/bin/env python3
"""Fail-closed template for wheel and source-distribution validation."""

from __future__ import annotations

import argparse
import json
import sys
import tarfile
import zipfile
from email.parser import BytesParser
from email.policy import default
from hashlib import sha256
from pathlib import Path, PurePosixPath

DISTRIBUTION_NAME = "goedel"
IMPORT_PACKAGE = "goedel"
VERSION = "0.2.0"
LICENSE_EXPRESSION = "Apache-2.0"
AUTHOR_EMAIL = "riskdatascience@web.de"
FORBIDDEN_SUFFIXES = {".pdf", ".doc", ".docx", ".odt", ".zip"}
FORBIDDEN_PARTS = {
    "goedel-scaffold",
    "transformation",
    "scaffold",
    "unterlagen",
    "intern",
    "archiv",
    ".git",
    "build",
    "dist",
    "downloaded-documents",
    "downloads",
    ".venv",
    "__pycache__",
}


def fail_unresolved_placeholders() -> None:
    values = (
        DISTRIBUTION_NAME,
        IMPORT_PACKAGE,
        VERSION,
        LICENSE_EXPRESSION,
        AUTHOR_EMAIL,
    )
    if any(value.startswith("__") and value.endswith("__") for value in values):
        raise AssertionError("distribution validator still contains scaffold placeholders")


def forbidden(names: set[str]) -> list[str]:
    failures = []
    for name in names:
        path = PurePosixPath(name.lower())
        if path.is_absolute() or ".." in path.parts or path.suffix in FORBIDDEN_SUFFIXES or any(part in FORBIDDEN_PARTS for part in path.parts):
            failures.append(name)
    return sorted(failures)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def check_resources(entries: dict[str, bytes]) -> None:
    manifests = [name for name in entries if name.endswith("/resources/resource_manifest.json")]
    require(len(manifests) == 1, "Missing/duplicate resource manifest")
    prefix = manifests[0].rsplit("/", 1)[0] + "/"
    manifest = json.loads(entries[manifests[0]])
    actual = {name[len(prefix):] for name in entries if name.startswith(prefix)}
    require(actual == set(manifest["files"]) | {"resource_manifest.json"}, "Unapproved archive resources")
    def scan(value):
        if isinstance(value, dict):
            require(not set(value) & {"private_locator", "never_publish", "current_authorization", "scaffold_version"}, "Private resource metadata")
            for item in value.values():
                scan(item)
        elif isinstance(value, list):
            for item in value:
                scan(item)
    for name, digest in manifest["files"].items():
        require(sha256(entries[prefix + name]).hexdigest() == digest, "Archive resource hash mismatch")
        scan(json.loads(entries[prefix + name]))


def validate_wheel(path: Path) -> dict[str, int]:
    require(path.stat().st_size < 100 * 1024 * 1024, "wheel exceeds project archive-size limit (verify service limits separately)")
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        check_resources({name: archive.read(name) for name in names if not name.endswith("/")})
        require(not forbidden(names), f"forbidden wheel content: {forbidden(names)[:5]}")
        metadata_names = [name for name in names if name.endswith(".dist-info/METADATA")]
        require(len(metadata_names) == 1, "wheel must contain exactly one METADATA file")
        metadata = BytesParser(policy=default).parsebytes(archive.read(metadata_names[0]))
        require(metadata["Name"] == DISTRIBUTION_NAME, "unexpected distribution name")
        require(metadata["Version"] == VERSION, "unexpected distribution version")
        require(metadata["License-Expression"] == LICENSE_EXPRESSION or metadata["License"] == LICENSE_EXPRESSION, "license missing")
        require(AUTHOR_EMAIL in str(metadata["Maintainer-email"]), "author email missing")
        require(f"{IMPORT_PACKAGE}/__init__.py" in names, "import package missing")
        require(f"{IMPORT_PACKAGE}/py.typed" in names, "typed-package marker missing")
    return {"files": len(names)}


def check_reproduction(entries: dict[str, bytes]) -> None:
    manifests = [name for name in entries if name.endswith("/tools/reproduction/manifest.json")]
    require(len(manifests) == 1, "Missing reproduction manifest from source distribution")
    prefix = manifests[0].rsplit("/", 1)[0] + "/"
    manifest = json.loads(entries[manifests[0]])
    observed = {name[len(prefix):] for name in entries if name.startswith(prefix)}
    require(observed == set(manifest["files_sha256"]) | {"manifest.json"}, "Incomplete reproduction source archive")
    for name, digest in manifest["files_sha256"].items():
        require(PurePosixPath(name).name == name and sha256(entries[prefix + name]).hexdigest() == digest,
                "Reproduction source hash mismatch")


def validate_sdist(path: Path) -> dict[str, int]:
    with tarfile.open(path, "r:gz") as archive:
        require(all(member.isfile() or member.isdir() for member in archive.getmembers()), "Unsupported archive member type")
        names = {member.name for member in archive.getmembers() if member.isfile()}
        entries = {name: archive.extractfile(name).read() for name in names}
        check_resources(entries)
        check_reproduction(entries)
    require(not forbidden(names), f"forbidden sdist content: {forbidden(names)[:5]}")
    for ending in ("/LICENSE", "/README.md", "/pyproject.toml", "/CHANGELOG.md"):
        require(any(name.endswith(ending) for name in names), f"sdist member missing: {ending}")
    return {"files": len(names)}


def main(argv: list[str] | None = None) -> int:
    fail_unresolved_placeholders()
    parser = argparse.ArgumentParser()
    parser.add_argument("dist", type=Path, nargs="?", default=Path("dist"))
    args = parser.parse_args(argv)
    wheels = sorted(args.dist.glob("*.whl"))
    sdists = sorted(args.dist.glob("*.tar.gz"))
    require(len(wheels) == 1, f"expected one wheel, found {len(wheels)}")
    require(len(sdists) == 1, f"expected one sdist, found {len(sdists)}")
    print({"wheel": validate_wheel(wheels[0]), "sdist": validate_sdist(sdists[0])})
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
