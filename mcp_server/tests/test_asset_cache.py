from mcp_blender.assets.cache import cache_dir, find_cached_file


def test_cache_dir_creates_nested_path(tmp_path):
    path = cache_dir("polyhaven", "victorian_chair", home=tmp_path)
    assert path.exists()
    assert path == tmp_path / ".mcp-blender" / "assets" / "polyhaven" / "victorian_chair"


def test_cache_dir_sanitizes_asset_id(tmp_path):
    path = cache_dir("sketchfab", "weird/id:1", home=tmp_path)
    assert path.exists()
    assert "/" not in path.name
    assert ":" not in path.name


def test_find_cached_file_returns_none_when_empty(tmp_path):
    assert find_cached_file("polyhaven", "victorian_chair", home=tmp_path) is None


def test_find_cached_file_returns_downloaded_file(tmp_path):
    path = cache_dir("polyhaven", "victorian_chair", home=tmp_path)
    (path / "model.glb").write_bytes(b"data")

    found = find_cached_file("polyhaven", "victorian_chair", home=tmp_path)

    assert found is not None
    assert found.name == "model.glb"


def test_find_cached_file_ignores_metadata_json(tmp_path):
    path = cache_dir("polyhaven", "victorian_chair", home=tmp_path)
    (path / "meta.json").write_text("{}")

    assert find_cached_file("polyhaven", "victorian_chair", home=tmp_path) is None
