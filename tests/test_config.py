from pathlib import Path

from voxtral_studio.config import AppPaths, DEFAULT_SERVER_VOICES, organize_voices_by_language


def test_organize_voices_by_language_keeps_english_first() -> None:
    grouped = organize_voices_by_language(list(DEFAULT_SERVER_VOICES))
    assert list(grouped.keys())[0] == "English"
    assert "French" in grouped
    assert "neutral_male" in grouped["English"]


def test_app_paths_point_inside_workspace(tmp_path: Path) -> None:
    paths = AppPaths(root=tmp_path)
    paths.ensure()
    assert paths.data_dir.exists()
    assert paths.voice_dir.parent == paths.data_dir

