from __future__ import annotations

import app


def test_cleanup_startup_caches_removes_tool_and_python_caches(tmp_path):
    pycache = tmp_path / "src" / "__pycache__"
    pytest_cache = tmp_path / ".pytest_cache"
    ruff_cache = tmp_path / ".ruff_cache"
    data_cache = tmp_path / "data" / "raw"

    for path in [pycache, pytest_cache, ruff_cache, data_cache]:
        path.mkdir(parents=True)
        (path / "marker.txt").write_text("cache", encoding="utf-8")

    removed = app._cleanup_startup_caches(tmp_path)

    assert pycache in removed
    assert pytest_cache in removed
    assert ruff_cache in removed
    assert not pycache.exists()
    assert not pytest_cache.exists()
    assert not ruff_cache.exists()
    assert data_cache.exists()
    assert (data_cache / "marker.txt").exists()
