from pathlib import Path

from app.config import _REPO_ROOT, Settings


class TestStoragePathResolved:
    """Regression tests for the STORAGE_PATH working-directory bug: a relative
    path used to resolve against the process's cwd, so `uvicorn app.main:app`
    run from `backend/` (per the local dev instructions) wrote uploads to
    backend/storage/documents instead of the repo's storage/documents —
    silently splitting data across two locations depending on launch
    directory. storage_path_resolved must always land in the same place."""

    def test_relative_default_anchors_to_the_repo_root(self):
        settings = Settings(storage_path="./storage/documents")
        assert settings.storage_path_resolved == (_REPO_ROOT / "storage" / "documents").resolve()

    def test_resolution_is_independent_of_the_working_directory(self, monkeypatch, tmp_path):
        monkeypatch.chdir(tmp_path)
        from_unrelated_cwd = Settings(storage_path="./storage/documents").storage_path_resolved

        monkeypatch.chdir(Path(__file__).resolve().parent)  # backend/tests
        from_tests_dir = Settings(storage_path="./storage/documents").storage_path_resolved

        assert from_unrelated_cwd == from_tests_dir == (_REPO_ROOT / "storage" / "documents").resolve()

    def test_absolute_path_is_used_unchanged(self):
        settings = Settings(storage_path="/app/storage/documents")
        assert settings.storage_path_resolved == Path("/app/storage/documents")

    def test_resolved_path_is_always_absolute(self):
        assert Settings(storage_path="relative/dir").storage_path_resolved.is_absolute()
        assert Settings(storage_path="/already/absolute").storage_path_resolved.is_absolute()
