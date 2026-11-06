import json
import sys

import pyright_check
import pytest

SUMMARY = "1 error, 0 warnings, 0 informations"
CONFIG = "pyproject.toml の [tool.pyright]"


def annotations(capsys) -> list[str]:
    return [line for line in capsys.readouterr().out.splitlines() if line.startswith("::")]


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_prepare_config_generates_exclude(project, capsys):
    assert pyright_check.prepare_config(["sub", "日本語"]) == (CONFIG, True)
    assert json.loads((project / "pyrightconfig.json").read_text()) == {"exclude": ["sub", "日本語"]}
    assert annotations(capsys) == []


def test_prepare_config_keeps_user_config(project):
    (project / "pyrightconfig.json").write_text("{}")
    assert pyright_check.prepare_config(["sub"]) == ("pyrightconfig.json", False)
    (project / "pyrightconfig.json").unlink()
    (project / "pyproject.toml").write_text("[tool.pyright.defineConstant]\nDEBUG = true\n")
    assert pyright_check.prepare_config(["sub"]) == (CONFIG, False)
    assert not (project / "pyrightconfig.json").exists()


def test_prepare_config_unreadable_pyproject(project, capsys):
    (project / "pyproject.toml").write_text("[[[\n")
    assert pyright_check.prepare_config([]) == (CONFIG, False)
    assert annotations(capsys)[0].startswith("::warning::Pyright: pyproject.toml を読めませんでした。")
    assert not (project / "pyrightconfig.json").exists()


@pytest.mark.parametrize(
    ("name", "content"), [("pyproject.toml", "[tool.mypy]\n"), ("setup.cfg", "x = 1\n[mypy-foo.*]\n"), ("mypy.ini", "")]
)
def test_prepare_config_warns_mypy(project, capsys, name, content):
    (project / name).write_text(content)
    assert pyright_check.prepare_config([]) == (CONFIG, True)
    assert annotations(capsys)[0].startswith("::warning::Pyright: mypy の設定は使われません。")


def test_config_errors():
    log = (
        'Config contains unrecognized setting "$schema".\n'
        'Config contains unrecognized setting "typeCheckMode2".\n'
        'Config "include" entry must contain a string.\n'
        "Config executionEnvironments index 0: unrecognized setting.\n"
        "Config file not found.\n"
    )
    assert pyright_check.config_errors(log) == log.splitlines()[1:4]


def test_unchecked():
    log = (
        "/work/app/sub/a.py:1:10 - error: Type is not assignable\n"
        "/work/app/other/b.py:1:1 - information: note\n"
        "/work/app/subdir/c.py:1:1 - warning: unused\n"
    )
    assert pyright_check.unchecked(["sub", "other", "subdir", "none"], log, "/work/app") == ["sub", "subdir"]


def check(status, log, *, generated=False, nested=(), config=CONFIG):
    return pyright_check.check(status, log, config=config, generated=generated, nested=list(nested), cwd="/w")


def test_check_passes(capsys):
    assert check(0, "0 errors, 0 warnings, 0 informations") == 0
    assert annotations(capsys) == []


def test_check_missing_include(capsys):
    assert check(0, 'File or directory "/w/nope" does not exist.\n0 errors, 0 warnings, 0 informations') == 1
    assert "include に存在しないパスがあります" in annotations(capsys)[0]


def test_check_config_error_keeps_type_error_status(capsys):
    log = f'Config contains unrecognized setting "foo".\n{SUMMARY}'
    assert check(0, log) == 1
    assert check(1, log) == 1
    messages = annotations(capsys)
    assert "知らない設定か不正な値があります" in messages[0]
    assert "型エラーを直してください" in messages[2]


def test_check_no_source_files(capsys):
    log = "No source files found.\n0 errors, 0 warnings, 0 informations"
    assert check(0, log) == 1
    assert check(0, log, generated=True) == 0  # 書き出した設定では、コードがすべて入れ子のプロジェクトにあり得る
    assert len(annotations(capsys)) == 1


def test_check_type_errors_with_nested(capsys):
    log = f"/w/sub/a.py:1:1 - error: bad\n{SUMMARY}"
    assert check(1, log, generated=True, nested=["sub", "a%b"]) == 1
    type_error, nested_error = annotations(capsys)
    assert "（設定を書くときは、入れ子のプロジェクト sub, a%25b も exclude に入れてください）" in type_error
    assert nested_error.startswith(
        "::error::Pyright: 入れ子のプロジェクト（sub）が、このプロジェクトの環境で検査されています。"
    )


def test_check_runtime_error(capsys):
    assert check(1, "Error: pyright could not start") == 2
    assert "型チェックを実行できませんでした（exit 2）" in annotations(capsys)[0]


def test_has_tool_without_tomllib(project, monkeypatch):
    # tomllib の無い Python（3.10 以前）でも落とさず、「読めない」として扱う
    (project / "pyproject.toml").write_text("[tool.pyright]\n")
    monkeypatch.setitem(sys.modules, "tomllib", None)
    assert pyright_check.has_tool("pyright") is None


def test_has_tool_unexpected_error(project, monkeypatch):
    # 旧 .sh と同じく、どんな失敗でも「読めない」として扱う（深い入れ子の RecursionError など）
    (project / "pyproject.toml").write_text("[tool.pyright]\n")

    class BrokenToml:
        @staticmethod
        def load(_):
            raise RecursionError("maximum recursion depth exceeded")

    monkeypatch.setitem(sys.modules, "tomllib", BrokenToml)
    assert pyright_check.has_tool("pyright") is None
