import pytest

from codemigrate.retrieval import build_retriever
from codemigrate.retrieval.exact import ExactRetriever
from codemigrate.retrieval.hybrid import HybridRetriever
from codemigrate.schemas import CodeRef, RefKind


def ref(symbol, raw=""):
    return CodeRef(
        file="a.py", line=1, col=0, symbol=symbol, raw_text=raw or symbol, kind=RefKind.ATTRIBUTE
    )


def test_exact_full_path_and_version_filter(kb):
    r = ExactRetriever(kb)
    ids = [s.entry.id for s in r.search(ref("django.utils.timezone.utc"), k=10)]
    assert {
        "django-4.1-deprecated-django_utils_timezone_utc",
        "django-5.0-removed-django_utils_timezone_utc",
    } <= set(ids)
    only_52 = r.search(ref("django.utils.timezone.utc"), k=10, from_version="5.1", to_version="5.2")
    assert only_52 == []


def test_exact_prefix_and_member_fallback(kb):
    r = ExactRetriever(kb)
    hits = r.search(ref("django.utils.timezone.utc.tzname"))
    assert hits and hits[0].score == 0.8
    hits = r.search(ref("django.test.TestCase.assertFormsetError"))
    assert any("assertformseterror" in h.entry.id for h in hits)


def test_exact_no_match(kb):
    assert ExactRetriever(kb).search(ref("django.shortcuts.render")) == []


def test_bm25_finds_by_tokens(kb):
    r = build_retriever("bm25", kb)
    top = r.search(ref("django.utils.encoding.force_text", "force_text(value)"), k=3)
    assert "force_text" in top[0].entry.affected_api


def test_tfidf_dense_variant(kb):
    r = build_retriever("tfidf", kb)
    top = r.search(ref("PickleSerializer", "SESSION_SERIALIZER = PickleSerializer"), k=3)
    assert any("pickleserializer" in s.entry.id for s in top)


@pytest.mark.slow
def test_sentence_transformer_dense(kb):
    r = build_retriever("dense", kb)
    top = r.search(ref("django.contrib.postgres.fields.CICharField"), k=5)
    assert any("cicharfield" in s.entry.id for s in top)


def test_hybrid_rrf_fuses_and_filters(kb):
    r = HybridRetriever(kb, [ExactRetriever(kb), build_retriever("bm25", kb)])
    top = r.search(ref("django.utils.timezone.utc"), k=3, from_version="4.0", to_version="5.1")
    assert top and all(s.entry.version_introduced in {"4.1", "4.2", "5.0", "5.1"} for s in top)
    assert "utc" in top[0].entry.affected_api


def test_unknown_retriever_name(kb):
    with pytest.raises(ValueError):
        build_retriever("magic", kb)
