"""プロジェクト（カレントディレクトリ）の環境で Pyright を実行する。

検査対象と厳しさは、このプロジェクトの [tool.pyright] / pyrightconfig.json に委ねる
（位置引数を渡すと設定の include が無視される。mypy と同じく、workspace のメンバーの設定は読まれない）。
-p .: このディレクトリに設定があればそれを使う（無ければ親の pyrightconfig.json が使われるため、書き出す）。
Pyright の wheel は本体を同梱しており、Node.js はランナーのものを使う（実行時に npm から取得しない）。

ログの判定は Pyright の出力の文言に頼るため、PYRIGHT_VERSION を上げたら文言が変わっていないか確かめる
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_lib"))
import gha

DOCS = "（https://microsoft.github.io/pyright/#/configuration）"


def has_tool(name: str) -> bool | None:
    """pyproject.toml に [tool.<name>] があるか（サブテーブル・ドット付きのキーなど、どの書き方でも拾う）。読めなければ None"""
    if not Path("pyproject.toml").exists():
        return False
    try:
        # tomllib は Python 3.11 から。import できないランナーでも、旧 .sh と同じく「読めない」として Pyright は動かす
        import tomllib

        with open("pyproject.toml", "rb") as f:
            return name in tomllib.load(f).get("tool", {})
    # 旧 .sh と同じく、どんな失敗でも「読めない」として Pyright は動かす（RecursionError なども）
    except Exception:  # noqa: BLE001
        return None


def has_mypy_cfg() -> bool:
    """setup.cfg に [mypy] / [mypy-xxx] があるか。configparser が読めない書き方（見出しの前の行など）でも拾えるよう、見出しの行を探す"""
    try:
        with open("setup.cfg", encoding="utf-8", errors="replace") as f:
            return any(re.match(r"\s*\[mypy(-[^]]*)?\]", line) for line in f)
    except OSError:
        return False


def prepare_config(nested: list[str]) -> tuple[str, bool]:
    """利用者の設定が無ければ、入れ子のプロジェクトを除いた設定を書き出す。案内に使う設定の場所と、書き出したかを返す"""
    if Path("pyrightconfig.json").exists():
        return "pyrightconfig.json", False
    # pyrightconfig.json が無ければ [tool.pyright] が読まれる。案内もそこを指す
    config = "pyproject.toml の [tool.pyright]"
    has_pyright = has_tool("pyright")
    if has_pyright is None:
        # 読めないときは、利用者の [tool.pyright] を上書きしないよう設定を書き出さない
        gha.warning(
            "Pyright: pyproject.toml を読めませんでした。[tool.pyright] があるか判定できないため、そのまま検査します"
        )
    if has_pyright is not False:
        return config, False
    if Path("mypy.ini").exists() or Path(".mypy.ini").exists() or has_tool("mypy") or has_mypy_cfg():
        gha.warning(
            f"Pyright: mypy の設定は使われません。検査対象や厳しさは pyproject.toml の [tool.pyright] に移してください{DOCS}"
        )
    # 設定が無いと、-p . でも親ディレクトリの pyrightconfig.json が使われ、ディレクトリ全体が検査される。
    # このプロジェクトの設定を書き出し、入れ子のプロジェクトを除く（既定の除外 node_modules・隠しディレクトリなどは残る）
    Path("pyrightconfig.json").write_text(
        json.dumps({"exclude": nested}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return config, True


def config_errors(log: str) -> list[str]:
    """設定の打ち間違い（知らない設定・不正な値・executionEnvironments の中の誤り）の行。
    "$schema"（エディタの補完に使う JSON Schema のキー）は Pyright が知らない設定として出すが、正しい設定なので除く
    """
    pattern = re.compile(r'^Config (contains unrecognized setting|"|executionEnvironments index [0-9]+: )')
    return [line for line in log.splitlines() if pattern.match(line) and 'unrecognized setting "$schema"' not in line]


def unchecked(nested: list[str], log: str, cwd: str) -> list[str]:
    """入れ子のプロジェクトのうち、このプロジェクトの環境で検査された（指摘が出た）もの"""
    lines = [line for line in log.splitlines() if re.search(r" - (error|warning): ", line)]
    return [d for d in nested if any(f"{cwd}/{d}/" in line for line in lines)]


def check(status: int, log: str, *, config: str, generated: bool, nested: list[str], cwd: str) -> int:
    """Pyright の終了コードとログから、結果を判定する。案内を出して、action の終了コードを返す"""
    # Pyright は include のパスが無くても 0 で終わる。何も検査しないまま通らないよう落とす（mypy も落ちていた）
    if status == 0 and re.search(r" does not exist\.$", log, re.MULTILINE):
        gha.error(
            f"Pyright: {config} の include に存在しないパスがあります。検査されないファイルが出ないよう直してください{DOCS}"
        )
        return 1
    # 設定の打ち間違いも、Pyright はその設定を無視して検査し、型エラーが無ければ 0 で終わる
    if config_errors(log):
        gha.error(
            f"Pyright: {config} に、知らない設定か不正な値があります。上の Config の行を確かめて直してください{DOCS}"
        )
        if status == 0:
            return 1
    # 利用者の設定で検査するファイルが 1 つも無いときも 0 で終わる（mypy は落ちていた）。
    # 書き出した設定では、コードがすべて入れ子のプロジェクトにあり 0 件のことがあるため落とさない。
    # include の項目ごとの 0 件（ほかの項目にファイルがある）は、項目ごとの一覧が要るため見ない
    if status == 0 and not generated and re.search(r"^No source files found\.$", log, re.MULTILINE):
        gha.error(
            f"Pyright: {config} の include / exclude に当てはまる Python ファイルがありません。検査されないファイルが出ないよう直してください{DOCS}"
        )
        return 1
    # ラッパー（pyright-python）が Pyright を起動できないときも 1 で終わる。Pyright は必ず集計の行を出すため、無ければ実行時のエラーとして扱う
    summary = r"^[0-9]+ errors?, [0-9]+ warnings?, [0-9]+ informations?$"
    if status == 1 and not re.search(summary, log, re.MULTILINE):
        status = 2

    if status == 1:
        keep = ""
        if generated and nested:
            # 書き出した設定にしか入れ子のプロジェクトの除外が無いため、利用者が設定を書くときに残すよう伝える
            keep = f"（設定を書くときは、入れ子のプロジェクト {', '.join(nested)} も exclude に入れてください）"
        gha.error(
            f"Pyright: 型エラーを直してください。検査から外すディレクトリ（scripts/ など）は {config} の include / exclude で絞れます{keep}{DOCS}"
        )
        # 入れ子のプロジェクトのファイルに指摘があれば、このプロジェクトの環境で検査されている（除外できていない）
        if found := unchecked(nested, log, cwd):
            gha.error(
                f"Pyright: 入れ子のプロジェクト（{', '.join(found)}）が、このプロジェクトの環境で検査されています。"
                f"{config} の exclude に入れてください（それぞれ自分の環境で検査されます）"
            )
    elif status != 0:
        gha.error(
            f"Pyright: 型チェックを実行できませんでした（exit {status}）。上のエラーと、{config} の書き方を確かめてください{DOCS}"
        )
    return status


def main() -> None:
    # 別の uv.lock を持つ入れ子のプロジェクト（自分の matrix で検査される）。どれがどの uv.lock に属するかは detect が決める
    nested = json.loads(os.environ["NESTED"]).get(os.environ["PROJECT"], [])
    config, generated = prepare_config(nested)

    # 一度だけ導入し、導入の失敗を型エラー（exit 1）と取り違えないようにする
    version = os.environ["PYRIGHT_VERSION"]
    if gha.run(["uv", "tool", "install", "--quiet", f"pyright=={version}"], check=False).returncode != 0:
        gha.error(f"Pyright: pyright {version} を導入できませんでした。上の uv のエラーを確かめてください")
        sys.exit(1)
    pyright = Path(gha.run(["uv", "tool", "dir", "--bin"], stdout=subprocess.PIPE).stdout.strip(), "pyright")

    # 実行はプロジェクトの環境（uv run）で行い、import をプロジェクトの依存で解決させる。
    # 存在しないパスの警告などは標準エラーに出るため、ログに入れる。--stats: 検査したファイルの数を出させる（0 件の判定に使う）
    status, log = gha.tee(["uv", "run", "--no-sync", str(pyright), "-p", ".", "--stats"])
    sys.exit(check(status, log, config=config, generated=generated, nested=nested, cwd=os.getcwd()))


if __name__ == "__main__":
    main()
