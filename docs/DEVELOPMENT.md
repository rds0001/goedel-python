# Development and local verification

Run from the Python package root:

```bash
python -m pip install -e '.[dev]'
python -m ruff check src tests tools examples
python -m pytest --capture=sys
python tools/api_audit.py
python tools/verify_source_tree.py
python -m build
python -m twine check dist/*
python tools/validate_distribution.py dist
```

`--capture=sys` avoids a filesystem-specific temporary-file issue seen with file
descriptor capture on WSL/NTFS. Source-boundary validation deliberately runs before
building. Build outputs are not source inputs. When an offline build environment
already supplies the declared backend requirements, `python -m build --no-isolation`
uses that environment; it does not claim a successful online isolated build.

Install the wheel and source distribution into separate fresh virtual environments,
change into a separate directory and run a copy of `tools/smoke_installed.py` with
`python -I`, without PYTHONPATH. The smoke test checks substitution, coding,
proof search, actual checking and a missing-premise guard.

The package contains independent literal reference cases and property tests.
Cross-language agreement supplements mathematical examples and independent oracles;
it cannot by itself show that either implementation is correct.

The CI workflow checks Python 3.10–3.14 on Linux and Python 3.14 on Windows/macOS;
this prepared matrix must actually run before a public release. Action commits
were checked against their official release pages on 2026-11-05. The publication
workflow is additionally disabled unless the repository variable
`RELEASE_AUTHORIZED` is set to the exact string `true`; setting it and creating a
release are explicit publication actions. Configure a matching PyPI Trusted
Publisher and protected pypi environment only as part of that release preparation.
No registry publication or remote CI result is implied by local tests.

License metadata uses the supported PEP 621 text field so an existing setuptools
61+ backend can build offline. Newer backends may emit PEP 639 license metadata;
the archive validator accepts either exact Apache-2.0 representation. No unverified
repository URLs are invented while publication destinations remain undecided.


The source distribution includes `tools/reproduction/` with all mathematical source
programs, compilers, specifications and their hash manifest. Run its `build.py`
with an explicit output directory to reproduce the six program/formula hashes.
The resulting graphs remain labelled `UNREVIEWED_REBUILD`. Six narrowly scoped
Ruff exceptions preserve the separately reviewed input bytes: delayed local imports
in the builder, original import ordering in two compilers, and cross-file helper
names in three numerical DSL files that are compiled together. Runtime package code
has no such exemptions. Source and archive validation check every reproduction
manifest entry and reject missing or altered files.
