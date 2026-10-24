import zipfile

from codemigrate.analysis.ast_analyzer import analyze_source, analyze_template
from codemigrate.analysis.repo_scanner import scan_path, scan_sources
from codemigrate.schemas import RefKind

SRC = """import django.utils.timezone as tz
from django.utils.timezone import utc as UTC
from django.contrib.auth.views import LogoutView
from django.conf import settings
from django.test import TestCase

x = tz.utc
y = UTC
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware"]


class V(LogoutView):
    def get_next_page(self):
        return self.get_next_page()


class T(TestCase):
    def test_a(self):
        self.assertFormsetError(None)
        if settings.USE_L10N:
            pass


class M:
    class Meta:
        index_together = [["a"]]


def f(obj):
    return obj.assertQuerysetEqual(1, 2)
"""


def refs_by_line():
    refs = analyze_source(
        SRC, "a.py", {"get_next_page", "assertFormsetError", "assertQuerysetEqual"}
    )
    out = {}
    for r in refs:
        out.setdefault(r.line, set()).add((r.kind, r.symbol))
    return out


def test_import_alias_and_attribute_chain():
    lines = refs_by_line()
    assert (RefKind.ATTRIBUTE, "django.utils.timezone.utc") in lines[7]
    assert (RefKind.ATTRIBUTE, "django.utils.timezone.utc") in lines[8]
    assert (RefKind.IMPORT, "django.utils.timezone.utc") in lines[2]


def test_strings_settings_meta():
    lines = refs_by_line()
    assert (RefKind.STRING, "django.middleware.security.SecurityMiddleware") in lines[9]
    assert (RefKind.SETTING, "settings.USE_L10N") in lines[20]
    assert (RefKind.META, "Meta.index_together") in lines[26]


def test_self_resolution_through_library_base():
    lines = refs_by_line()
    assert (RefKind.METHOD, "django.contrib.auth.views.LogoutView.get_next_page") in lines[13]
    assert (RefKind.CALL, "django.contrib.auth.views.LogoutView.get_next_page") in lines[14]
    assert (RefKind.CALL, "django.test.TestCase.assertFormsetError") in lines[19]


def test_unknown_receiver_distinctive_method():
    lines = refs_by_line()
    assert (RefKind.METHOD, "*.assertQuerysetEqual") in lines[30]


def test_dunder_methods_are_not_distinctive():
    src = (
        "from django.contrib.sitemaps.views import SitemapIndexItem\n"
        "class Plain:\n    def __str__(self):\n        return ''\n"
        "class Item(SitemapIndexItem):\n    def __str__(self):\n        return ''\n"
    )
    refs = {(r.line, r.symbol) for r in analyze_source(src, method_names={"__str__"})}
    assert not any(line == 3 for line, _ in refs)
    assert (6, "django.contrib.sitemaps.views.SitemapIndexItem.__str__") in refs


def test_columns_are_exact():
    ref = next(
        r
        for r in analyze_source(
            "import os\nv = os.x\nfrom django.utils import timezone\nw = timezone.utc\n"
        )
        if r.line == 4
    )
    assert ref.col == 4 and ref.symbol == "django.utils.timezone.utc"


def test_relative_imports_ignored():
    assert analyze_source("from . import models\nx = models.utc\n") == []


def test_template_filters():
    refs = analyze_template(
        "{% if a|length_is:2 %}x{% endif %}\n{{ b|upper }}", "t.html", {"length_is"}
    )
    assert [(r.line, r.symbol) for r in refs] == [(1, "template:length_is")]


def test_scanner_skips_venv_and_survives_syntax_errors(tmp_path):
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "ok.py").write_text("from django.utils import timezone\nx = timezone.utc\n")
    (tmp_path / "app" / "bad.py").write_text("def broken(:\n")
    (tmp_path / ".venv" / "lib").mkdir(parents=True)
    (tmp_path / ".venv" / "lib" / "x.py").write_text("import django\n")
    files = {f.path: f for f in scan_path(tmp_path, set(), set())}
    assert set(files) == {"app/ok.py", "app/bad.py"}
    assert files["app/bad.py"].error.startswith("SyntaxError")
    assert any(r.symbol == "django.utils.timezone.utc" for r in files["app/ok.py"].refs)


def test_scanner_accepts_utf8_bom():
    [f] = scan_sources(iter([("a.py", "﻿import os\n")]), set(), set())
    assert f.error is None and f.source == "import os\n"


def test_scanner_reads_zip(tmp_path):
    z = tmp_path / "proj.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("proj/views.py", "from django.conf.urls import url\n")
        zf.writestr("proj/node_modules/x.py", "import django\n")
    files = scan_path(z, set(), set())
    assert [f.path for f in files] == ["proj/views.py"]
