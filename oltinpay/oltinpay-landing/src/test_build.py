"""Tests for the landing generator.

Run with:
    python3 -m unittest discover -s src -p 'test_*.py'

`unittest` rather than pytest on purpose: the generator itself is standard
library only, and the landing has no test harness of its own. Adding one for
four pages would be a bigger change than the thing being tested.

What these cover is the generator's *refusals*. A silent failure here does not
crash anything — it publishes a page with a hole in it, or an orphan page nobody
edits any more. That is exactly the class of defect nobody notices in review.
"""

from __future__ import annotations

import json
import unicodedata
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import build


class TestRender(unittest.TestCase):
    """Substitution and its refusal."""

    def test_should_substitute_every_placeholder(self) -> None:
        result = build.render(
            "<h1>{{title}}</h1><p>{{body}}</p>",
            {"title": "Заголовок", "body": "Текст"},
            where="test",
        )
        self.assertEqual(result, "<h1>Заголовок</h1><p>Текст</p>")

    def test_should_raise_when_dictionary_lacks_a_key(self) -> None:
        with self.assertRaises(build.BuildError) as caught:
            build.render("<h1>{{title}}</h1>", {}, where="ru.json → index.html")

        message = str(caught.exception)
        self.assertIn("title", message)
        self.assertIn("index.html", message, "the error must say which page broke")

    def test_should_not_raise_when_every_key_is_present(self) -> None:
        """The other side of the refusal: it must stay quiet when it should."""
        result = build.render("{{a}}-{{b}}", {"a": "1", "b": "2"}, where="test")
        self.assertEqual(result, "1-2")

    def test_should_report_all_missing_keys_at_once(self) -> None:
        with self.assertRaises(build.BuildError) as caught:
            build.render("{{one}} {{two}}", {}, where="test")

        message = str(caught.exception)
        self.assertIn("one", message)
        self.assertIn("two", message, "reporting one key at a time wastes a round")

    def test_should_leave_text_that_only_looks_like_a_placeholder(self) -> None:
        """CSS braces and JS objects must survive untouched."""
        css = "body{margin:0} .x{color:red}"
        self.assertEqual(build.render(css, {}, where="test"), css)


class TestUnusedKeys(unittest.TestCase):
    """A key nobody uses is a typo or a leftover; both rot quietly."""

    def test_should_find_a_key_no_template_uses(self) -> None:
        unused = build.unused_keys({"a.html": "{{used}}"}, {"used": "x", "stale": "y"})
        self.assertEqual(unused, ["stale"])

    def test_should_ignore_service_keys(self) -> None:
        unused = build.unused_keys({"a.html": "{{used}}"}, {"used": "x", "_out": "ru"})
        self.assertEqual(unused, [], "_out configures the printer, no template uses it")

    def test_should_return_empty_when_every_key_is_used(self) -> None:
        self.assertEqual(build.unused_keys({"a.html": "{{k}}"}, {"k": "v"}), [])


class TestLoadStrings(unittest.TestCase):
    """The dictionary is hand-edited, so it is an untrusted input."""

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def write(self, content: str) -> Path:
        path = self.tmp / "ru.json"
        path.write_text(content, encoding="utf-8")
        return path

    def test_should_read_a_valid_dictionary(self) -> None:
        path = self.write(json.dumps({"k": "v"}, ensure_ascii=False))
        self.assertEqual(build.load_strings(path), {"k": "v"})

    def test_should_raise_on_invalid_json(self) -> None:
        path = self.write("{ not json")
        with self.assertRaises(build.BuildError):
            build.load_strings(path)

    def test_should_raise_when_a_value_is_not_a_string(self) -> None:
        """A number here would render as `405` in one language and break another."""
        path = self.write(json.dumps({"tests": 405}))
        with self.assertRaises(build.BuildError) as caught:
            build.load_strings(path)
        self.assertIn("tests", str(caught.exception))

    def test_should_raise_when_the_file_is_not_an_object(self) -> None:
        path = self.write(json.dumps(["a", "b"]))
        with self.assertRaises(build.BuildError):
            build.load_strings(path)


class TestResolveOutputDir(unittest.TestCase):
    """`_out` is the one hand-edited value that becomes a filesystem write."""

    def setUp(self) -> None:
        self._tmp = TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.addCleanup(self._tmp.cleanup)

    def test_should_return_the_root_when_no_subdirectory(self) -> None:
        self.assertEqual(
            build.resolve_output_dir(self.root, "", source="en.json"), self.root
        )

    def test_should_return_the_subdirectory_when_ordinary(self) -> None:
        resolved = build.resolve_output_dir(self.root, "ru", source="ru.json")
        self.assertEqual(resolved, (self.root / "ru").resolve())

    def test_should_refuse_to_escape_the_output_tree(self) -> None:
        with self.assertRaises(build.BuildError) as caught:
            build.resolve_output_dir(self.root, "../escaped", source="ru.json")
        self.assertIn("ru.json", str(caught.exception))

    def test_should_refuse_an_absolute_path(self) -> None:
        with self.assertRaises(build.BuildError):
            build.resolve_output_dir(self.root, "/etc", source="ru.json")


class TestDifferencesAgainstPublic(unittest.TestCase):
    """The guard that makes `public/` generated rather than hand-edited."""

    def setUp(self) -> None:
        self._fresh = TemporaryDirectory()
        self._public = TemporaryDirectory()
        self.fresh = Path(self._fresh.name)
        self.public = Path(self._public.name)
        self.addCleanup(self._fresh.cleanup)
        self.addCleanup(self._public.cleanup)
        patcher = mock.patch.object(build, "PUBLIC_DIR", self.public)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_should_report_nothing_when_trees_match(self) -> None:
        (self.fresh / "index.html").write_text("same", encoding="utf-8")
        (self.public / "index.html").write_text("same", encoding="utf-8")

        problems = build.differences_against_public(self.fresh, [Path("index.html")])

        self.assertEqual(problems, [])

    def test_should_catch_a_page_edited_by_hand(self) -> None:
        (self.fresh / "index.html").write_text("generated", encoding="utf-8")
        (self.public / "index.html").write_text("edited by hand", encoding="utf-8")

        problems = build.differences_against_public(self.fresh, [Path("index.html")])

        self.assertEqual(len(problems), 1)
        self.assertIn("differs", problems[0])

    def test_should_catch_a_page_missing_from_public(self) -> None:
        (self.fresh / "index.html").write_text("generated", encoding="utf-8")

        problems = build.differences_against_public(self.fresh, [Path("index.html")])

        self.assertEqual(len(problems), 1)
        self.assertIn("missing", problems[0])

    def test_should_catch_an_orphan_no_template_prints(self) -> None:
        """A page still served from a source nobody edits is just as broken."""
        (self.fresh / "index.html").write_text("same", encoding="utf-8")
        (self.public / "index.html").write_text("same", encoding="utf-8")
        (self.public / "orphan.html").write_text("left behind", encoding="utf-8")

        problems = build.differences_against_public(self.fresh, [Path("index.html")])

        self.assertEqual(len(problems), 1)
        self.assertIn("orphan.html", problems[0])

    def test_should_compare_nested_language_directories(self) -> None:
        """Languages print into subdirectories; the guard must follow them."""
        (self.fresh / "ru").mkdir()
        (self.public / "ru").mkdir()
        (self.fresh / "ru" / "index.html").write_text("generated", encoding="utf-8")
        (self.public / "ru" / "index.html").write_text("stale", encoding="utf-8")

        problems = build.differences_against_public(
            self.fresh, [Path("ru") / "index.html"]
        )

        self.assertEqual(len(problems), 1)
        self.assertIn("ru/index.html", problems[0])


class TestScript(unittest.TestCase):
    """Homoglyphs: a Cyrillic «а» inside a Latin word is invisible to a reader.

    This is not a hypothetical. Review found exactly one — `tegа` in the Uzbek
    dictionary — and no human eye would have caught it, in review or in proof-
    reading. A machine catches the whole class in milliseconds.
    """

    #: Which alphabet each language is written in. Uzbek is Latin script here,
    #: matching the Mini App.
    LATIN = ("en", "uz")
    CYRILLIC = ("ru",)

    @staticmethod
    def cyrillic_in(strings: dict[str, str]) -> list[tuple[str, str]]:
        return [
            (key, char)
            for key, value in strings.items()
            for char in value
            if "CYRILLIC" in unicodedata.name(char, "")
        ]

    def test_should_find_no_cyrillic_in_latin_script_languages(self) -> None:
        for lang in self.LATIN:
            with self.subTest(language=lang):
                strings = build.load_strings(build.STRINGS_DIR / f"{lang}.json")
                offenders = self.cyrillic_in(strings)
                self.assertEqual(
                    offenders,
                    [],
                    f"Cyrillic look-alike inside {lang}.json: {offenders}",
                )

    def test_should_still_find_cyrillic_where_it_belongs(self) -> None:
        """Positive control: without this, the check above could be blind."""
        for lang in self.CYRILLIC:
            with self.subTest(language=lang):
                strings = build.load_strings(build.STRINGS_DIR / f"{lang}.json")
                self.assertTrue(
                    self.cyrillic_in(strings),
                    f"{lang}.json has no Cyrillic at all — the detector is broken",
                )


class TestPublishedPages(unittest.TestCase):
    """Guards on the pages actually sitting in `public/`.

    These run against every language present, so they keep working unchanged as
    ru/uz/en appear. They exist because the whole point of this page is honesty
    about the testnet: losing one of those disclosures in translation would
    reproduce, in a new language, exactly the defect the rewrite was for.
    """

    #: The network name is not translated, which makes it a language-independent
    #: probe: a disclosure that stopped mentioning Sepolia stopped being one.
    NETWORK = "Sepolia"

    #: page → keys whose value must appear on it and must name the network.
    DISCLOSURES = {
        "index.html": ("foot_disclaimer", "idx_status1_p"),
        "how-it-works.html": ("foot_disclaimer", "hiw_limit1_p"),
        "license.html": ("foot_disclaimer", "lic_phase1_p"),
    }

    #: Ratified with the Captain: EN/UZ carry a short, careful legal note. It lives
    #: in a slot of its own rather than inside the surrounding paragraph, and that
    #: is the whole guarantee: the template demands the key, so a language that
    #: drops it cannot be printed at all. What the slot *says* is a human's job —
    #: the agreed proof-read — because no assertion can tell a real disclaimer from
    #: a plausible sentence.
    LEGAL_NOTE_KEY = "lic_no_legal_advice"

    def languages(self) -> list[tuple[str, dict[str, str]]]:
        """Return (output subdirectory, dictionary) for every language."""
        dictionaries = [
            build.load_strings(path)
            for path in sorted(build.STRINGS_DIR.glob("*.json"))
        ]
        return [(strings.get("_out", ""), strings) for strings in dictionaries]

    def page(self, subdir: str, name: str) -> str:
        directory = build.PUBLIC_DIR / subdir if subdir else build.PUBLIC_DIR
        return (directory / name).read_text(encoding="utf-8")

    def test_should_declare_the_language_of_every_version(self) -> None:
        for subdir, strings in self.languages():
            with self.subTest(language=strings["lang"]):
                markup = self.page(subdir, "index.html")
                self.assertIn(f'<html lang="{strings["lang"]}">', markup)

    def test_should_disclose_the_testnet_on_every_page_of_every_language(self) -> None:
        for subdir, strings in self.languages():
            for page, keys in self.DISCLOSURES.items():
                markup = self.page(subdir, page)
                for key in keys:
                    with self.subTest(language=strings["lang"], page=page, key=key):
                        self.assertIn(
                            self.NETWORK,
                            strings[key],
                            f"{key} no longer names the network it discloses",
                        )
                        self.assertIn(strings[key], markup)

    def test_should_mark_the_mockup_as_testnet(self) -> None:
        """The seventh disclosure: the phone mockup's own build label."""
        for subdir, strings in self.languages():
            with self.subTest(language=strings["lang"]):
                self.assertIn("Testnet", self.page(subdir, "index.html"))

    def test_should_keep_the_legal_note_in_every_language(self) -> None:
        for subdir, strings in self.languages():
            with self.subTest(language=strings["lang"]):
                self.assertTrue(strings[self.LEGAL_NOTE_KEY].strip())
                self.assertIn(
                    strings[self.LEGAL_NOTE_KEY], self.page(subdir, "license.html")
                )

    def test_should_leave_no_unsubstituted_placeholder(self) -> None:
        for page in sorted(build.PUBLIC_DIR.rglob("*.html")):
            with self.subTest(page=str(page.relative_to(build.PUBLIC_DIR))):
                leftovers = build.PLACEHOLDER.findall(page.read_text(encoding="utf-8"))
                self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
