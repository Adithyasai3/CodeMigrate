import json

import pytest
from pydantic import ValidationError

from codemigrate.config import get_settings
from codemigrate.kb.build_kb import extract_symbols, parse_sections, strip_rst
from codemigrate.kb.schema import KBEntry, load_kb
from codemigrate.kb.versions import in_range

KB = get_settings().kb_path


def test_kb_has_enough_valid_entries():
    entries = load_kb(KB)
    assert len(entries) >= 150
    assert len({e.id for e in entries}) == len(entries)
    for e in entries:
        assert str(e.source_url).startswith("https://docs.djangoproject.com/")
        assert "#" in str(e.source_url)


def test_build_report_has_no_invalid_urls():
    report = json.loads((KB.parent / "build_report.json").read_text(encoding="utf-8"))
    assert report["source_urls_invalid"] == []
    assert report["auto_parsed_entries"] > 0


def test_schema_rejects_bad_entries():
    good = load_kb(KB)[0].model_dump(mode="json")
    for field, bad in [
        ("change_type", "exploded"),
        ("version_introduced", "five"),
        ("source_url", "not a url"),
        ("description", "short"),
    ]:
        with pytest.raises(ValidationError):
            KBEntry.model_validate({**good, field: bad})


def test_in_range_is_exclusive_from_inclusive_to():
    assert in_range("5.0", "4.0", "5.1")
    assert in_range("5.1", "4.0", "5.1")
    assert not in_range("4.0", "4.0", "5.1")
    assert not in_range("5.2", "4.0", "5.1")


def test_parser_handles_lead_in_lists_and_roles():
    text = """Features removed in 9.9
=======================

* The ``django.utils.foo`` module is removed.

The ``x`` argument is removed from:

* :func:`django.db.models.functions.Trunc`
* :meth:`~django.db.models.query.QuerySet.datetimes`
"""
    items = parse_sections("9.9", text)
    assert len(items) == 3
    assert items[1].lead.endswith("removed from:")
    assert [s.name for s in extract_symbols(items[2].text)] == [
        "django.db.models.query.QuerySet.datetimes"
    ]


def test_strip_rst():
    assert strip_rst(":class:`~django.a.B` and ``c()``") == "django.a.B and c()"


def test_known_entries_present():
    names = {e.affected_api for e in load_kb(KB)}
    for api in [
        "django.utils.timezone.utc",
        "settings.USE_L10N",
        "Meta.index_together",
        "django.contrib.postgres.fields.CICharField",
        "django.utils.encoding.force_text",
    ]:
        assert api in names
