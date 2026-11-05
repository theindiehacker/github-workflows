"""composite action の Python スクリプトで共通に使う、GitHub Actions のヘルパー。

スクリプトは `python3 -I -u` で動かす。
  -I: 対象 repo のモジュールや PYTHON* の環境変数を読み込まない。スクリプトのディレクトリも import 先から外れるため、
      各スクリプトが sys.path にこのディレクトリを足して import する
  -u: print の出力を貯めず、子プロセスの出力と順番が入れ替わらないようにする
"""

import contextlib
import json
import os
import subprocess
from collections.abc import Iterator, Sequence
from typing import Any


def run(args: Sequence[str], *, check: bool = True, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    """コマンドを実行する。引数はリストで渡し、シェルは通さない（出力は UTF-8 の文字列で受ける）"""
    return subprocess.run(args, check=check, text=True, encoding="utf-8", **kwargs)


def tee(args: Sequence[str]) -> tuple[int, str]:
    """コマンドを実行し、標準出力と標準エラーをログに流しながら受け取る（シェルの 2>&1 | tee と同じ）"""
    with subprocess.Popen(
        args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace"
    ) as proc:
        assert proc.stdout is not None
        lines = []
        for line in proc.stdout:
            print(line, end="")
            lines.append(line)
    # シグナルで止まったときは、シェルと同じく 128 + シグナル番号にする
    status = proc.returncode if proc.returncode >= 0 else 128 - proc.returncode
    return status, "".join(lines)


def git_z(command: str, *args: str) -> list[str]:
    """git ls-files / git grep -l を -z で実行し、パスのリストにする（改行や非 ASCII を含むパスも壊さない）。
    git grep の「該当なし」（終了コード 1）は空のリストにする
    """
    proc = run(["git", command, "-z", *args], check=False, stdout=subprocess.PIPE)
    if proc.returncode != 0 and not (command == "grep" and proc.returncode == 1):
        raise subprocess.CalledProcessError(proc.returncode, proc.args)
    return [path for path in proc.stdout.split("\0") if path]


def to_json(value: object) -> str:
    """jq -c と同じ形（空白なし・非 ASCII はそのまま）の JSON にする"""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def set_output(name: str, value: object) -> None:
    """出力 name に書く。文字列以外は 1 行の JSON にする"""
    text = value if isinstance(value, str) else to_json(value)
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
        f.write(f"{name}={text}\n")


def escape(value: str) -> str:
    """ワークフローコマンドのメッセージのエスケープ。対象 repo 由来の文字列で行を分けられ、コマンドを偽装されるのを防ぐ"""
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def escape_property(value: str) -> str:
    """ワークフローコマンドのプロパティ（file= など）のエスケープ"""
    return escape(value).replace(":", "%3A").replace(",", "%2C")


def command(name: str, message: str, file: str | None = None) -> None:
    """::error / ::warning / ::notice を出す。message は呼び出し側でエスケープしておく"""
    prop = f" file={escape_property(file)}" if file else ""
    print(f"::{name}{prop}::{message}")


def error(message: str, file: str | None = None) -> None:
    command("error", message, file)


def warning(message: str, file: str | None = None) -> None:
    command("warning", message, file)


@contextlib.contextmanager
def group(title: str) -> Iterator[None]:
    """ログを折りたたむ。title はエスケープして出す"""
    print(f"::group::{escape(title)}")
    try:
        yield
    finally:
        print("::endgroup::")
