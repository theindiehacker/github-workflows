import sys

import gha


def test_escape():
    assert gha.escape("a%b\r\nc") == "a%25b%0D%0Ac"
    assert gha.escape_property("a:b,c%") == "a%3Ab%2Cc%25"


def test_tee(capsys):
    # 標準エラーもログに入り、UTF-8 でない出力は置き換えて読む。終了コードはそのまま返す
    code = "import sys; print('out', flush=True); sys.stderr.buffer.write(b'err \\xff\\n'); sys.exit(3)"
    status, log = gha.tee([sys.executable, "-c", code])
    assert (status, log) == (3, "out\nerr �\n")
    assert capsys.readouterr().out == log


def test_tee_signal():
    status, _ = gha.tee([sys.executable, "-c", "import os, signal; os.kill(os.getpid(), signal.SIGTERM)"])
    assert status == 128 + 15
