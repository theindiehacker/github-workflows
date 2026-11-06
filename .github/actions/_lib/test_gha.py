import os
import subprocess
import sys

import gha
import pytest


def test_escape():
    assert gha.escape("a%b\r\nc") == "a%25b%0D%0Ac"
    assert gha.escape_property("a:b,c%") == "a%3Ab%2Cc%25"


def test_command_escapes_message_and_file(capsys):
    # 対象 repo 由来の値をそのまま渡しても、改行で次の行をワークフローコマンドにされない
    gha.error("bad path: a%b\n::warning::injected", file="x,y:z\n")
    assert capsys.readouterr().out == "::error file=x%2Cy%3Az%0A::bad path: a%25b%0A::warning::injected\n"


def test_tee(capsys):
    # 標準エラーもログに入り、UTF-8 でない出力は置き換えて読む。終了コードはそのまま返す
    code = "import sys; print('out', flush=True); sys.stderr.buffer.write(b'err \\xff\\n'); sys.exit(3)"
    status, log = gha.tee([sys.executable, "-c", code])
    assert (status, log) == (3, "out\nerr �\n")
    assert capsys.readouterr().out == log


def test_tee_signal():
    status, _ = gha.tee([sys.executable, "-c", "import os, signal; os.kill(os.getpid(), signal.SIGTERM)"])
    assert status == 128 + 15


def test_run_command_not_found(capsys):
    # コマンドが無ければ、シェルと同じく 127 にする（check=False の呼び出し側が失敗の経路に入れる）
    assert gha.run(["no-such-command-xyz"], check=False).returncode == 127
    with pytest.raises(subprocess.CalledProcessError) as exc_info:
        gha.run(["no-such-command-xyz"])
    assert exc_info.value.returncode == 127
    assert "no-such-command-xyz: command not found" in capsys.readouterr().err


def test_tee_command_not_found():
    assert gha.tee(["no-such-command-xyz"]) == (127, "")


def test_git_z_non_utf8_path(repo):
    # UTF-8 でないパスは U+FFFD に置き換えて読む（jq -R と同じ。traceback で止めない）
    root = repo({})
    os.makedirs(os.path.join(os.fsencode(root), b"a\xff"))
    (root / os.fsdecode(b"a\xff") / "uv.lock").write_text("")
    gha.run(["git", "add", "-A"])
    assert gha.git_z("ls-files") == ["a�/uv.lock"]


def test_set_output_rejects_line_break(tmp_path, monkeypatch):
    # 改行で GITHUB_OUTPUT の行を分け、ほかの出力を差し込めないようにする
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "output"))
    with pytest.raises(ValueError):
        gha.set_output("x", "true\nimages=[]")
    gha.set_output("x", ["a\nb"])  # JSON は改行を \\n にするので書ける
    assert (tmp_path / "output").read_text() == 'x=["a\\nb"]\n'
