#!/usr/bin/env bash
# プロジェクト（カレントディレクトリ）の環境で ty を実行する。
# 検査対象と厳しさは、このプロジェクトの ty.toml / [tool.ty] に委ねる
# （位置引数を渡すと設定の include が無視される。mypy と同じく、workspace のメンバーの設定は読まれない）。
# ty は、このディレクトリに設定が無ければ親ディレクトリの ty.toml / [tool.ty] を使うため、下で書き出す
set -euo pipefail

docs="https://docs.astral.sh/ty/reference/configuration/"
# 別の uv.lock を持つ入れ子のプロジェクト（自分の matrix で検査される）。どれがどの uv.lock に属するかは python-targets が決める
nested=$(jq -c --arg project "${PROJECT}" '.[$project] // []' <<< "${NESTED}")
# 設定の有無は、pyproject.toml を TOML として読み（サブテーブル・ドット付きのキーなど、どの書き方でも拾う）、setup.cfg は見出しの行を探して判定する。
# ランナーの Python（3.11 以上）で読む。-I: カレントディレクトリ（対象 repo）のモジュールを import しない。
# 終了コード: 0 = ある、10 = 無い、それ以外 = 読めなかった
has_tool() { # <pyproject.toml の [tool] の下の名前>
  [ -e pyproject.toml ] || return 10
  python3 -I -c 'import sys, tomllib; sys.exit(0 if sys.argv[1] in tomllib.load(open("pyproject.toml", "rb")).get("tool", {}) else 10)' "$1"
}
has_mypy_cfg() { # setup.cfg の [mypy] / [mypy-xxx]。configparser が読めない書き方（見出しの前の行など）でも拾えるよう、見出しの行を探す
  [ -e setup.cfg ] || return 10
  python3 -I -c 'import re, sys; sys.exit(0 if any(re.match(r"\s*\[mypy(-[^]]*)?\]", line) for line in open("setup.cfg", encoding="utf-8", errors="replace")) else 10)'
}
# 利用者の設定の src.include のうち、グロブ（* ? [ \ と否定の !）を含まない項目で、存在しないパスを JSON の配列で出す
missing_include() {
  python3 -I -c '
import json, os, tomllib
if os.path.exists("ty.toml"):
    src = tomllib.load(open("ty.toml", "rb")).get("src", {})
else:
    src = tomllib.load(open("pyproject.toml", "rb")).get("tool", {}).get("ty", {}).get("src", {})
print(json.dumps([p for p in src.get("include", []) if not p.startswith("!") and not any(c in p for c in "*?[\\") and not os.path.exists(p.removeprefix("./").rstrip("/") or ".")]))
'
}
# 対象 repo 由来のパスの一覧を、ワークフローコマンドに埋め込めるようエスケープして , でつなぐ
join_escaped() { # <JSON の文字列の配列>
  jq -r 'join(", ") | gsub("%"; "%25") | gsub("\r"; "%0D") | gsub("\n"; "%0A")' <<< "$1"
}
# 利用者の設定があれば書き換えない（入れ子のプロジェクトを除くかも利用者に任せ、落ちたときに案内する）
generated=false
if [ -e ty.toml ]; then
  config="ty.toml"
else
  # ty.toml が無ければ [tool.ty] が読まれる。案内もそこを指す
  config="pyproject.toml の [tool.ty]"
  ty_config=0
  has_tool ty || ty_config=$?
  if [ "${ty_config}" -ne 0 ] && [ "${ty_config}" -ne 10 ]; then
    # 読めないときは、利用者の [tool.ty] を上書きしないよう設定を書き出さない
    echo "::warning::ty: pyproject.toml を読めませんでした。[tool.ty] があるか判定できないため、そのまま検査します"
  fi
  if [ "${ty_config}" -eq 10 ]; then
    if [ -e pyrightconfig.json ] || has_tool pyright; then
      echo "::warning::ty: Pyright の設定は使われません。検査対象や厳しさは pyproject.toml の [tool.ty] に移してください（${docs}）"
    fi
    if [ -e mypy.ini ] || [ -e .mypy.ini ] || has_tool mypy || has_mypy_cfg; then
      echo "::warning::ty: mypy の設定は使われません。検査対象や厳しさは pyproject.toml の [tool.ty] に移してください（${docs}）"
    fi
    # このプロジェクトの設定を書き出し、入れ子のプロジェクトを除く。パスはこのディレクトリが基準で、./ で始めてグロブの否定（!）と取り違えないようにする。
    # 既定の除外（.venv・node_modules など）と .gitignore の除外は残る。jq の JSON の文字列の配列は、TOML の配列としても読める
    jq -rn --argjson nested "${nested}" '"[src]\nexclude = " + ($nested | map("./" + . + "/") | tojson)' > ty.toml
    generated=true
  fi
fi
# 一度だけ導入し、導入の失敗を型エラー（exit 1）と取り違えないようにする。
# 実行はプロジェクトの環境（uv run が VIRTUAL_ENV を設定する）で行い、import をプロジェクトの依存で解決させる
if ! uv tool install --quiet "ty==${TY_VERSION}"; then
  echo "::error::ty: ty ${TY_VERSION} を導入できませんでした。上の uv のエラーを確かめてください"
  exit 1
fi
ty="$(uv tool dir --bin)/ty"
log=$(mktemp)
status=0
# 0 件の警告は標準エラーに出るため、ログに入れる。--no-progress: 進捗の表示をログに残さない。
# --output-format full: 入れ子の判定が読む「 --> パス」の行を、利用者の terminal.output-format に関わらず出させる。
# 知らない設定・不正な値は ty が exit 2 で、知らないルール名は警告（既定で exit 1）で落とす
uv run --no-sync "${ty}" check --no-progress --output-format full 2>&1 | tee "${log}" || status=$?
# 以降の判定は、利用者の設定で何も検査しないまま通らないようにする（mypy も落ちていた）。
# 書き出した設定では、コードがすべて入れ子のプロジェクトにあり 0 件のことがあるため落とさない
if [ "${status}" -eq 0 ] && [ "${generated}" = false ]; then
  # ty は include のパスが無くても何も出さず 0 で終わる
  missing=$(missing_include) || { echo "::warning::ty: ${config} を読めず、include のパスがあるか確かめられませんでした"; missing="[]"; }
  if [ "${missing}" != "[]" ]; then
    echo "::error::ty: ${config} の src.include に存在しないパス（$(join_escaped "${missing}")）があります。検査されないファイルが出ないよう直してください（${docs}）"
    exit 1
  fi
  # include の項目ごとの 0 件（ほかの項目にファイルがある）は、項目ごとの一覧が要るため見ない。
  # この判定と入れ子の判定は ty の出力の文言に頼るため、TY_VERSION を上げたら文言が変わっていないか確かめる
  if grep -qF 'No python files found under the given path(s)' "${log}"; then
    echo "::error::ty: ${config} の src.include / src.exclude に当てはまる Python ファイルがありません。検査されないファイルが出ないよう直してください（${docs}）"
    exit 1
  fi
fi
case "${status}" in
  0) ;;
  1)
    keep=""
    if [ "${generated}" = true ] && [ "${nested}" != "[]" ]; then
      # 書き出した設定にしか入れ子のプロジェクトの除外が無いため、利用者が設定を書くときに残すよう伝える
      keep="（設定を書くときは、入れ子のプロジェクト $(join_escaped "${nested}") も src.exclude に入れてください）"
    fi
    echo "::error::ty: 型エラーと警告を直してください。検査から外すディレクトリ（scripts/ など）は ${config} の src.include / src.exclude で、ルールの厳しさは rules で変えられます${keep}（${docs}）"
    # 入れ子のプロジェクトのファイルに指摘があれば、このプロジェクトの環境で検査されている（除外できていない）。
    # 指摘の場所は「 --> <カレントディレクトリからのパス>:<行>:<列>」の行に出る（行番号の桁数で字下げが変わる）
    unchecked=$(jq -c --rawfile log "${log}" '[.[] | select(. as $dir | $log | split("\n") | any(sub("^ +"; "") | startswith("--> " + $dir + "/")))]' <<< "${nested}")
    if [ "${unchecked}" != "[]" ]; then
      echo "::error::ty: 入れ子のプロジェクト（$(join_escaped "${unchecked}")）が、このプロジェクトの環境で検査されています。${config} の src.exclude に入れてください（それぞれ自分の環境で検査されます）"
    fi
    ;;
  *) echo "::error::ty: 型チェックを実行できませんでした（exit ${status}）。上のエラーと、${config} の書き方を確かめてください（${docs}）" ;;
esac
exit "${status}"
