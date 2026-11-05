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
import sys
from collections.abc import Iterator, Sequence
from typing import Any

# シェルと同じく、コマンドが見つからないときの終了コード
COMMAND_NOT_FOUND = 127


def not_found(args: Sequence[str]) -> None:
    print(f"{args[0]}: command not found", file=sys.stderr)


def run(args: Sequence[str], *, check: bool = True, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    """コマンドを実行する。引数はリストで渡し、シェルは通さない。
    出力は UTF-8 の文字列で受け、読めないバイトは U+FFFD に置き換える（jq -R と同じ。UTF-8 でないパスがあっても止まらない）。
    コマンドが無ければ、シェルと同じく終了コード 127 にする（check=False の呼び出し側が失敗の経路に入れるように）
    """
    try:
        return subprocess.run(args, check=check, text=True, encoding="utf-8", errors="replace", **kwargs)
    except FileNotFoundError:
        not_found(args)
        if check:
            raise subprocess.CalledProcessError(COMMAND_NOT_FOUND, args) from None
        return subprocess.CompletedProcess(args, COMMAND_NOT_FOUND, stdout="", stderr="")


def tee(args: Sequence[str]) -> tuple[int, str]:
    """コマンドを実行し、標準出力と標準エラーをログに流しながら受け取る（シェルの 2>&1 | tee と同じ）"""
    try:
        proc = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except FileNotFoundError:
        not_found(args)
        return COMMAND_NOT_FOUND, ""
    # バイト列で受けて 1 行ずつデコードする（UTF-8 でない出力があっても止まらないよう、読めない文字は置き換える）
    with proc:
        assert proc.stdout is not None
        lines = []
        for raw in proc.stdout:
            line = raw.decode("utf-8", errors="replace")
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
