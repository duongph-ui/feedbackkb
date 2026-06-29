"""Step 3 — adapter factory + default impls + interface contract."""

import pytest

from feedbackkb_server import adapters
from feedbackkb_server.adapters import (
    AuthAdapter,
    Identity,
    KnowledgeStore,
    Lesson,
    SearchAdapter,
    StorageAdapter,
)


def test_factory_returns_default_impls():
    assert isinstance(adapters.get_storage("local"), StorageAdapter)
    assert isinstance(adapters.get_search("keyword"), SearchAdapter)
    assert isinstance(adapters.get_auth("none"), AuthAdapter)
    assert isinstance(adapters.get_knowledge("pg"), KnowledgeStore)


@pytest.mark.parametrize(
    "fn,bad",
    [(adapters.get_storage, "ftp"), (adapters.get_search, "elasticsearch"),
     (adapters.get_auth, "oauth"), (adapters.get_knowledge, "redis")],
)
def test_unknown_adapter_raises(fn, bad):
    # genuinely-unknown names -> loud failure, not silent default
    with pytest.raises(ValueError):
        fn(bad)


def test_interfaces_have_required_methods():
    assert hasattr(StorageAdapter, "put") and hasattr(StorageAdapter, "get_signed_url")
    assert hasattr(SearchAdapter, "search")
    assert hasattr(AuthAdapter, "verify")
    for m in ("put", "get", "search"):
        assert hasattr(KnowledgeStore, m)


def test_local_storage_roundtrip_and_signing():
    s = adapters.get_storage("local")
    key = s.put(b"hello", "text/plain")
    assert key and "hello" not in key  # opaque, no original content/name
    url = s.get_signed_url(key, ttl=60)
    assert key in url and "sig=" in url


def test_local_storage_persists_across_instances(tmp_path):
    # regression: in-memory store lost bytes on every new instance/restart. Disk
    # backing must survive a fresh LocalStorage pointed at the same dir.
    from feedbackkb_server.adapters.storage import LocalStorage

    a = LocalStorage(str(tmp_path))
    key = a.put(b"\x89PNG", "image/png")
    b = LocalStorage(str(tmp_path))  # simulate restart / per-request instance
    data, mime = b.get_bytes(key)
    assert data == b"\x89PNG" and mime == "image/png"
    with pytest.raises(KeyError):
        b.get_bytes("../escape")  # path-traversal guard


def test_get_storage_is_singleton():
    assert adapters.get_storage("local") is adapters.get_storage("local")


def test_none_auth_is_anonymous():
    ident = adapters.get_auth("none").verify({})
    assert isinstance(ident, Identity)
    assert ident.user == "anonymous"


def test_knowledge_store_put_get_search():
    ks = adapters.get_knowledge("pg")
    ref = ks.put(Lesson(system="FPS", title="dup ca_number", content="lock the row"))
    assert ks.get(ref).system == "FPS"
    assert ks.search("lock", system="FPS")
    assert ks.search("lock", system="FPA") == []  # tenant-scoped
