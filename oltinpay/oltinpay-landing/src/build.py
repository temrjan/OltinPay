#!/usr/bin/env python3
"""Print the OltinPay landing pages from one template set and per-language strings.

The landing is plain static HTML that Caddy serves straight off disk. Nothing here
runs in production: this is a build-time printer whose output — `public/` — is
committed and deployed exactly as it is today.

Design constraints, agreed at plan review and deliberately narrow:

  * standard library only. No dependencies, no template engine;
  * substitution is dumb: ``{{key}}`` becomes a string from the dictionary. No
    conditionals, no loops, no pluralisation. If a page ever needs one, that is a
    decision to escalate, not a feature to grow here;
  * service values (output subdirectory, language code, sibling page paths) are
    ordinary dictionary keys, so no logic sneaks in through the back door.

This is a CLI tool: it reports through stdout/stderr and an exit code, which is
why it prints rather than logs.

Usage:
    python3 src/build.py            # print pages into public/
    python3 src/build.py --check    # print into a temp dir, diff against public/
"""

from __future__ import annotations

import argparse
import filecmp
import json
import re
import sys
import tempfile
from pathlib import Path

LANDING_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = LANDING_ROOT / "src" / "templates"
STRINGS_DIR = LANDING_ROOT / "src" / "strings"
PUBLIC_DIR = LANDING_ROOT / "public"

PLACEHOLDER = re.compile(r"\{\{([a-zA-Z0-9_]+)\}\}")

#: Keys with this prefix configure the printer and are never substituted into a
#: template. Only ``_out`` exists today: the subdirectory a language prints into.
SERVICE_PREFIX = "_"


class BuildError(Exception):
    """Raised when templates and dictionaries disagree."""


def load_strings(path: Path) -> dict[str, str]:
    """Read one language dictionary.

    Args:
        path: Path to a ``<lang>.json`` file.

    Returns:
        Mapping of key to string, service keys included.

    Raises:
        BuildError: If the file is not valid JSON, is not an object, or holds a
            value that is not a string.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BuildError(f"{path.name}: invalid JSON — {exc}") from exc

    if not isinstance(data, dict):
        raise BuildError(f"{path.name}: expected an object, got {type(data).__name__}")

    non_strings = sorted(k for k, v in data.items() if not isinstance(v, str))
    if non_strings:
        raise BuildError(f"{path.name}: values must be strings: {non_strings}")
    return data


def render(template: str, strings: dict[str, str], *, where: str) -> str:
    """Substitute every ``{{key}}`` in one template.

    Args:
        template: Raw template text.
        strings: Language dictionary.
        where: Human-readable origin, used in the error message.

    Returns:
        The rendered page.

    Raises:
        BuildError: If the template asks for a key the dictionary lacks. Failing
            here is the point: a silently empty placeholder would ship a page with
            a hole in it.
    """
    missing: set[str] = set()

    def substitute(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in strings:
            missing.add(key)
            return match.group(0)
        return strings[key]

    rendered = PLACEHOLDER.sub(substitute, template)
    if missing:
        raise BuildError(f"{where}: no string for {sorted(missing)}")
    return rendered


def unused_keys(templates: dict[str, str], strings: dict[str, str]) -> list[str]:
    """Return dictionary keys no template refers to.

    A key nobody uses is either a typo or a leftover from a deleted block; both
    rot quietly, so the build refuses them.
    """
    used: set[str] = set()
    for text in templates.values():
        used.update(PLACEHOLDER.findall(text))
    return sorted(
        key for key in strings if not key.startswith(SERVICE_PREFIX) and key not in used
    )


def read_templates() -> dict[str, str]:
    """Load every template, keyed by file name.

    Raises:
        BuildError: If the template directory holds nothing.
    """
    templates = {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted(TEMPLATES_DIR.glob("*.html"))
    }
    if not templates:
        raise BuildError(f"no templates in {TEMPLATES_DIR}")
    return templates


def resolve_output_dir(destination: Path, subdir: str, *, source: str) -> Path:
    """Resolve a language's output directory, refusing to escape `destination`.

    `_out` is hand-edited, and this function is the one place where its value
    turns into a filesystem write. A stray `..` would put generated pages on top
    of the repository instead of inside `public/`, and the mistake would look
    like a successful build.

    Args:
        destination: Root the generated tree must stay inside.
        subdir: Value of `_out`, possibly empty.
        source: Dictionary file name, for the error message.

    Returns:
        The directory to print into.

    Raises:
        BuildError: If `subdir` is absolute or points outside `destination`.
    """
    if not subdir:
        return destination

    candidate = (destination / subdir).resolve()
    if not candidate.is_relative_to(destination.resolve()):
        raise BuildError(f"{source}: _out must stay inside the output tree: {subdir!r}")
    return candidate


def build(destination: Path) -> list[Path]:
    """Print every language into ``destination``.

    Args:
        destination: Directory that receives the generated tree.

    Returns:
        Written paths, relative to ``destination``, in a stable order.

    Raises:
        BuildError: On any template/dictionary mismatch.
    """
    templates = read_templates()

    dictionaries = sorted(STRINGS_DIR.glob("*.json"))
    if not dictionaries:
        raise BuildError(f"no string files in {STRINGS_DIR}")

    written: list[Path] = []
    for dictionary in dictionaries:
        strings = load_strings(dictionary)

        stale = unused_keys(templates, strings)
        if stale:
            raise BuildError(f"{dictionary.name}: keys no template uses: {stale}")

        subdir = strings.get("_out", "")
        out_dir = resolve_output_dir(destination, subdir, source=dictionary.name)
        out_dir.mkdir(parents=True, exist_ok=True)

        for name, template in templates.items():
            page = render(template, strings, where=f"{dictionary.name} → {name}")
            target = out_dir / name
            target.write_text(page, encoding="utf-8")
            written.append(target.relative_to(destination))

    return written


def differences_against_public(expected_root: Path, expected: list[Path]) -> list[str]:
    """Compare a freshly printed tree with the committed ``public/``.

    Both directions are checked. A page that templates no longer print but which
    still sits in ``public/`` is just as broken as a stale one: it keeps serving
    from a source nobody edits any more.
    """
    problems: list[str] = []

    for relative in expected:
        committed = PUBLIC_DIR / relative
        if not committed.exists():
            problems.append(f"missing from public/: {relative}")
        elif not filecmp.cmp(expected_root / relative, committed, shallow=False):
            problems.append(f"differs from templates: {relative}")

    printed = {str(path) for path in expected}
    for committed in sorted(PUBLIC_DIR.rglob("*.html")):
        relative = committed.relative_to(PUBLIC_DIR)
        if str(relative) not in printed:
            problems.append(f"in public/ but no template prints it: {relative}")

    return problems


def check() -> int:
    """Print into a temp directory and diff against the committed ``public/``.

    Returns:
        0 when ``public/`` is exactly what the templates produce, 1 otherwise.
    """
    with tempfile.TemporaryDirectory() as tmp:
        expected_root = Path(tmp)
        expected = build(expected_root)
        problems = differences_against_public(expected_root, expected)

    if problems:
        print("public/ is out of step with src/:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print("\nRun `python3 src/build.py` and commit the result.", file=sys.stderr)
        return 1

    print(f"public/ matches src/ ({len(expected)} pages)")
    return 0


def main() -> int:
    """Entry point. Returns the process exit code."""
    parser = argparse.ArgumentParser(
        description="Print the OltinPay landing pages from templates and strings."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="verify public/ matches the templates instead of writing it",
    )
    args = parser.parse_args()

    try:
        if args.check:
            return check()
        written = build(PUBLIC_DIR)
    except BuildError as exc:
        print(f"build failed: {exc}", file=sys.stderr)
        return 1

    for relative in written:
        print(f"  {relative}")
    print(f"printed {len(written)} pages into {PUBLIC_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
