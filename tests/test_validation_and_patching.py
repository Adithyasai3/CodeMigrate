import ast

from codemigrate.patching.fixer import apply_patch_text, make_patch
from codemigrate.patching.updater import add_todo_comments, apply_safe_patches
from codemigrate.pipeline import Pipeline, SystemConfig
from codemigrate.schemas import CodeRef, Evidence, Finding, FindingStatus, RefKind, ScoredEntry
from codemigrate.validation.citation_validator import CitationValidator
from codemigrate.validation.matching import symbol_matches

UTC_DEP = "django-4.1-deprecated-django_utils_timezone_utc"
UTC_REM = "django-5.0-removed-django_utils_timezone_utc"
QS_EQ = "django-4.2-deprecated-django_test_testcases_transactiontestcase_assertquerysetequa"


def by_id(kb, i):
    return next(e for e in kb if e.id == i)


def evidence(kb, line, symbol, ids):
    ref = CodeRef(file="a.py", line=line, col=0, symbol=symbol, raw_text="", kind=RefKind.ATTRIBUTE)
    entries = [ScoredEntry(entry=by_id(kb, i), score=1, retriever="exact") for i in ids]
    return Evidence(ref=ref, entries=entries)


def finding(line=3, symbol="django.utils.timezone.utc", cited=(UTC_REM,)):
    return Finding(file="a.py", line=line, symbol=symbol, cited_ids=list(cited))


def test_symbol_matching(kb):
    e = by_id(kb, UTC_REM)
    assert symbol_matches("django.utils.timezone.utc", e)
    assert symbol_matches("django.utils.timezone.utc.tzname", e)
    assert not symbol_matches("django.utils.timezone.now", e)
    qs = by_id(kb, QS_EQ)
    assert symbol_matches("django.test.TestCase.assertQuerysetEqual", qs)
    assert symbol_matches("*.assertQuerysetEqual", qs)


def test_validator_verifies_grounded_claim(kb):
    v = CitationValidator(kb, "4.0", "5.1")
    vf = v.validate(finding(), [evidence(kb, 3, "django.utils.timezone.utc", [UTC_DEP, UTC_REM])])
    assert vf.status is FindingStatus.VERIFIED and vf.cited_ids == [UTC_REM]
    assert vf.source_urls[0].startswith("https://docs.djangoproject.com/")


def test_validator_rejections(kb, tmp_path):
    log = tmp_path / "rej.jsonl"
    v = CitationValidator(kb, "4.0", "5.1", rejected_log=log)
    ev = [evidence(kb, 3, "django.utils.timezone.utc", [UTC_REM])]
    for f in [finding(cited=()), finding(cited=("django-9.9-removed-made_up",)), finding(line=4)]:
        assert v.validate(f, ev).status is FindingStatus.UNSUPPORTED_CLAIM
    wrong_symbol = v.validate(finding(symbol="django.utils.timezone.now"), ev)
    assert wrong_symbol.status is FindingStatus.UNVERIFIED
    assert len(log.read_text().splitlines()) == 4
    out_of_range = CitationValidator(kb, "5.0", "5.1").validate(
        finding(cited=(UTC_DEP,)), [evidence(kb, 3, "django.utils.timezone.utc", [UTC_DEP])]
    )
    assert out_of_range.status is FindingStatus.UNVERIFIED


def test_validator_requires_code_reference_to_match(kb):
    v = CitationValidator(kb, "4.0", "5.1")
    ev = [evidence(kb, 3, "django.utils.timezone.now", [UTC_REM])]  # retrieved, wrong code
    assert v.validate(finding(), ev).status is FindingStatus.UNVERIFIED


def _verified(kb, line, symbol, entry_id):
    v = CitationValidator(kb, "4.0", "5.1")
    vf = v.validate(
        Finding(file="a.py", line=line, symbol=symbol, cited_ids=[entry_id]),
        [evidence(kb, line, symbol, [entry_id])],
    )
    assert vf.status is FindingStatus.VERIFIED
    return vf


def test_patch_rename_same_class(kb):
    src = "class T:\n    def test(self):\n        self.assertQuerysetEqual(1, 2)\n"
    vf = _verified(kb, 3, "django.test.TestCase.assertQuerysetEqual", QS_EQ)
    patched = apply_patch_text(src, vf)
    assert "assertQuerySetEqual(1, 2)" in patched
    ast.parse(patched)


def test_patch_cross_module_import_and_attribute(kb):
    src = "from django.utils.timezone import now, utc\n\nx = utc\n"
    vf = _verified(kb, 1, "django.utils.timezone.utc", UTC_DEP)
    patched = apply_patch_text(src, vf)
    assert patched.startswith(
        "from django.utils.timezone import now\nimport datetime\nutc = datetime.timezone.utc\n"
    )
    src2 = "from django.utils import timezone\n\nx = timezone.utc\n"
    vf2 = _verified(kb, 3, "django.utils.timezone.utc", UTC_DEP)
    patched2 = apply_patch_text(src2, vf2)
    assert "x = datetime.timezone.utc" in patched2 and "import datetime\n" in patched2
    assert make_patch(src2, vf2, "a.py").startswith("--- a/a.py")


def test_apply_safe_patches_tracks_shifted_lines(kb):
    # the utc fix inserts "import datetime" above the second finding; it must still be found
    src = (
        "from django.utils import timezone\n\nx = timezone.utc\n\n"
        "class T:\n    def test(self):\n        self.assertQuerysetEqual(1, 2)\n"
    )
    utc = _verified(kb, 3, "django.utils.timezone.utc", UTC_DEP)
    qs = _verified(kb, 7, "django.test.TestCase.assertQuerysetEqual", QS_EQ)
    new, fixed, remaining = apply_safe_patches(src, [qs, utc])
    assert len(fixed) == 2 and not remaining
    assert "x = datetime.timezone.utc" in new and "assertQuerySetEqual(1, 2)" in new
    ast.parse(new)


def test_todo_comments_never_change_the_code():
    src = 'def f():\n    s = """\n    text\n    """\n    return s\n'
    out, done = add_todo_comments(src, {2: "a note", 3: "inside a string"})
    assert done == [2]  # line 3 is inside the string literal: a comment there would change it
    assert "    # TODO(codemigrate): a note\n    s = " in out
    assert ast.dump(ast.parse(out)) == ast.dump(ast.parse(src))


def test_pipeline_builds_updated_files_offline(kb):
    src = (
        "from django.utils import timezone\n"
        "from django.utils.itercompat import is_iterable\n\n"
        "def f(x):\n    return is_iterable(x), timezone.utc\n"
    )
    p = Pipeline(SystemConfig(provider="offline", make_updated=True), kb=kb)
    [u] = p.scan_sources([("a.py", src)], "4.0", "5.1").updated_files
    assert "datetime.timezone.utc" in u.content and u.auto_fixed == [5]
    assert u.manual == [2, 5] and u.content.count("# TODO(codemigrate): is_iterable") == 2
    assert u.diff.startswith("--- a/a.py")
    ast.parse(u.content)


def test_fixed_import_resolves_later_uses_without_duplicate_import(kb):
    src = (
        "import datetime\n"
        "from django.utils.timezone import utc\n\n"
        "now = datetime.datetime.now(tz=utc)\n"
    )
    p = Pipeline(SystemConfig(provider="offline", make_updated=True), kb=kb)
    [u] = p.scan_sources([("a.py", src)], "4.0", "5.1").updated_files
    assert u.content == (
        "import datetime\nutc = datetime.timezone.utc\n\nnow = datetime.datetime.now(tz=utc)\n"
    )
    assert u.auto_fixed == [2, 4] and u.manual == []


def test_no_patch_without_mechanical_fix(kb):
    vf = _verified(kb, 1, "django.utils.baseconv", "django-5.0-removed-django_utils_baseconv")
    assert make_patch("from django.utils import baseconv\n", vf, "a.py") is None
