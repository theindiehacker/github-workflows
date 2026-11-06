"""pytest の設定。各スクリプトと同じく _lib/gha.py を import できるようにし、テスト用の git repo を作る fixture を置く"""

import sys
from collections.abc import Callable
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent / "_lib"))
import gha


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Callable[[dict[str, str]], Path]:
    """{パス: 内容} のファイルをコミットした git repo を作り、カレントディレクトリにする"""

    def create(files: dict[str, str]) -> Path:
        for name, content in files.items():
            path = tmp_path / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        git = ["git", "-C", str(tmp_path), "-c", "user.name=test", "-c", "user.email=test@example.com"]
        gha.run([*git, "init", "-q"])
        gha.run([*git, "add", "-A"])
        gha.run([*git, "commit", "-q", "--allow-empty", "-m", "init"])
        monkeypatch.chdir(tmp_path)
        return tmp_path

    return create


@pytest.fixture
def outputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Callable[[], dict[str, str]]:
    """GITHUB_OUTPUT を一時ファイルにし、書かれた出力を {名前: 値} で返す関数を渡す"""
    path = tmp_path.parent / f"{tmp_path.name}-output"
    path.write_text("")
    monkeypatch.setenv("GITHUB_OUTPUT", str(path))
    return lambda: dict(line.split("=", 1) for line in path.read_text(encoding="utf-8").splitlines())
