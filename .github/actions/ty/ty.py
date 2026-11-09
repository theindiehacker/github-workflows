"""プロジェクト（カレントディレクトリ）の環境で ty を実行する。

検査対象と厳しさは、このプロジェクトの ty.toml / [tool.ty] に委ねる
（位置引数を渡すと設定の include が無視される。workspace のメンバーの設定は読まれない）。
ty は、このディレクトリに設定が無ければ親ディレクトリの ty.toml / [tool.ty] を使うため、設定を書き出す。

ty は action.yml の前の step で導入する。ランナーの Python（3.11 以上）で、
python3 -I（カレントディレクトリにある対象 repo のモジュールを import しない）で動かす。
"""

import glob
import json
import os
import re
import subprocess
import sys
import tomllib
from pathlib import Path

DOCS = "https://docs.astral.sh/ty/reference/configuration/"
# 0 件・知らないルール名・入れ子の判定は ty の出力の文言に頼るため、ty の版を上げたら文言が変わっていないか確かめる
NO_FILES = "No python files found under the given path(s)"
UNKNOWN_RULE = "warning[unknown-rule]"


def annotate(level: str, message: str) -> None:
    """注釈を出す。対象 repo 由来のパスが入るため、ワークフローコマンドとしてエスケープする"""
    message = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"::{level}::ty: {message}", flush=True)


def load_config() -> tuple[str, dict | None]:
    """ty が読む設定の場所（案内に使う）と中身を返す。設定が無ければ中身は None。

    ty.toml が pyproject.toml の [tool.ty] より優先される。
    [tool.ty] は TOML として読んで探す（サブテーブル・ドット付きのキーなど、どの書き方でも拾う）。
    """
    if Path("ty.toml").exists():
        where, path = "ty.toml", Path("ty.toml")
    else:
        where, path = "pyproject.toml の [tool.ty]", Path("pyproject.toml")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        # 利用者の設定を上書きしないよう、設定があるものとして扱う
        annotate(
            "warning",
            f"{path} を読めませんでした。設定を確かめられないため、そのまま検査します",
        )
        return where, {}
    if path.name == "ty.toml":
        return where, data
    tool = data.get("tool")
    return where, tool.get("ty") if isinstance(tool, dict) else None


def exclude_pattern(path: str) -> str:
    """入れ子のプロジェクトを除く src.exclude のパターン。パスはこのディレクトリが基準で、./ で始める。

    英数字と / . _ - 以外は \\ でエスケープする
    （ty はグロブの文字のほか、{ ! , などもそのままでは受け付けない。\\ を含む名前は ty が受け付けない）。
    """
    return "./" + re.sub(r"([^A-Za-z0-9/._-])", r"\\\1", path) + "/"


def toml_string(text: str) -> str:
    """TOML の basic string。" と \\ と制御文字（タブを除く）は \\uXXXX にする"""
    escaped = "".join(
        f"\\u{ord(c):04x}"
        if c in '"\\' or (ord(c) < 0x20 and c != "\t") or ord(c) == 0x7F
        else c
        for c in text
    )
    return f'"{escaped}"'


def unmatched_include(config: dict) -> list[str]:
    """src.include のうち、どのパスにも当てはまらない項目（ty は何も出さず 0 で終わる）。

    グロブの項目も Python の glob で確かめる（パスはこのディレクトリが基準。エスケープの \\ を含む項目は見ない）。
    """
    include = config.get("src", {}).get("include", [])
    return [
        p
        for p in include
        if "\\" not in p
        and not glob.glob(
            p.removeprefix("./") or ".", recursive=True, include_hidden=True
        )
    ]


def run_ty() -> tuple[int, list[str]]:
    """ty を実行し、出力をログに流しつつ、終了コードと出力の行を返す。

    ty は、このディレクトリの .venv（uv sync が作る）を見つけ、import をプロジェクトの依存で解決する。
    uv run は使わない（プロジェクトの依存に ty があると、PATH の先頭に入るそちらの版が使われるため）。
    0 件の警告は標準エラーに出るため、標準出力にまとめる。--no-progress: 進捗の表示をログに残さない。
    --output-format full: 入れ子の判定が読む「 --> パス」の行を、利用者の terminal.output-format に関わらず出させる。
    知らない設定・不正な値は ty が exit 2 で落とす。
    """
    # 引数は固定の文字列だけにし、action.yml で導入した ty を PATH の先頭から起動する
    # （Semgrep の r/all は、固定の文字列でない引数の subprocess を ERROR にする）。
    # S607 は CI の --select S でだけ有効になり、既定の ruff check はその noqa を不要 (RUF100) とするため、RUF100 も並べる
    where_bin = subprocess.run(
        ["uv", "tool", "dir", "--bin"],  # noqa: S607, RUF100
        check=True,
        capture_output=True,
        text=True,
    )
    env = {
        **os.environ,
        "PATH": where_bin.stdout.strip() + os.pathsep + os.environ.get("PATH", ""),
    }
    lines = []
    # 出力はバイトのまま流し、判定用に UTF-8 として読む（Semgrep が Popen の encoding / errors を ERROR にするため）
    with subprocess.Popen(
        ["ty", "check", "--no-progress", "--output-format", "full"],  # noqa: S607, RUF100
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
    ) as proc:
        assert proc.stdout is not None  # stdout=PIPE のため常にある
        for raw in proc.stdout:
            sys.stdout.buffer.write(raw)
            sys.stdout.buffer.flush()
            lines.append(raw.decode("utf-8", "replace").rstrip("\n"))
    return proc.returncode, lines


def main() -> int:
    # 別の uv.lock を持つ入れ子のプロジェクト（自分の matrix で検査される）。どれがどの uv.lock に属するかは python-targets が決める
    nested: list[str] = json.loads(os.environ["NESTED"]).get(os.environ["PROJECT"], [])
    where, config = load_config()
    # 利用者の設定があれば書き換えない（入れ子のプロジェクトを除くかも利用者に任せ、落ちたときに案内する）
    generated = config is None
    if generated:
        # 既定の除外（.venv・node_modules など）と .gitignore の除外は残る。
        # CLI の --exclude では親ディレクトリの設定が使われたままになるため、ファイルに書く
        patterns = ", ".join(toml_string(exclude_pattern(d)) for d in nested)
        Path("ty.toml").write_text(f"[src]\nexclude = [{patterns}]\n", encoding="utf-8")

    status, log = run_ty()

    # 以降の判定は、利用者の設定で何も検査しないまま通らないようにする。
    # 書き出した設定では、コードがすべて入れ子のプロジェクトにあり 0 件のことがあるため落とさない
    if status == 0 and config is not None:
        if missing := unmatched_include(config):
            annotate(
                "error",
                f"{where} の src.include に、どのパスにも当てはまらない項目（{', '.join(missing)}）があります。"
                f"検査されないファイルが出ないよう直してください（{DOCS}）",
            )
            return 1
        # include の項目ごとの 0 件（ほかの項目にファイルがある）は、項目ごとの一覧が要るため見ない
        if any(NO_FILES in line for line in log):
            annotate(
                "error",
                f"{where} の src.include / src.exclude に当てはまる Python ファイルがありません。"
                f"検査されないファイルが出ないよう直してください（{DOCS}）",
            )
            return 1
        # 知らないルール名は警告になり、terminal.error-on-warning = false では 0 で終わる
        if any(line.startswith(UNKNOWN_RULE) for line in log):
            annotate(
                "error",
                f"{where} の rules に知らないルール名があります。上の unknown-rule の警告を確かめて直してください（{DOCS}）",
            )
            return 1

    if status == 1:
        keep = ""
        if generated and nested:
            # 書き出した設定にしか入れ子のプロジェクトの除外が無いため、利用者が設定を書くときに残すよう伝える
            keep = f"（設定を書くときは、入れ子のプロジェクト {', '.join(nested)} も src.exclude に入れてください）"
        annotate(
            "error",
            f"型エラーと警告を直してください。検査から外すディレクトリ（scripts/ など）は {where} の src.include / src.exclude で、"
            f"ルールの厳しさは rules で変えられます{keep}（{DOCS}）",
        )
    elif status != 0:
        annotate(
            "error",
            f"型チェックを実行できませんでした（exit {status}）。上のエラーと、{where} の書き方を確かめてください（{DOCS}）",
        )
        # シグナルで止まったとき（負の値）も失敗で終える
        return status if status > 0 else 1

    # 入れ子のプロジェクトのファイルに指摘があれば、このプロジェクトの環境で検査されている（除外できていない）。
    # error-on-warning = false で警告だけのとき（exit 0）も見る。
    # 指摘の場所は「 --> <カレントディレクトリからのパス>:<行>:<列>」の行に出る（行番号の桁数で字下げが変わる）
    if unchecked := [
        d
        for d in nested
        if any(line.lstrip(" ").startswith(f"--> {d}/") for line in log)
    ]:
        annotate(
            "error",
            f"入れ子のプロジェクト（{', '.join(unchecked)}）が、このプロジェクトの環境で検査されています。"
            f"{where} の src.exclude に入れてください（それぞれ自分の環境で検査されます）",
        )
        return 1
    return status


if __name__ == "__main__":
    sys.exit(main())
