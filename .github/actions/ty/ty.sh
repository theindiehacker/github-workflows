#!/usr/bin/env bash
# プロジェクト（カレントディレクトリ）の環境で ty を実行する。
# 検査対象と厳しさは、このプロジェクトの [tool.ty] / ty.toml に委ねる
# （位置引数を渡すと設定の include が無視される。workspace のメンバーの設定は読まれない）。
set -euo pipefail

docs="https://docs.astral.sh/ty/reference/configuration/"

# 別の uv.lock を持つ入れ子のプロジェクト（自分の matrix で検査される）。どれがどの uv.lock に属するかは python-targets が決める。
# --exclude は利用者の設定の exclude に足されるため、設定の有無によらず除ける。
# ./: このプロジェクトの直下からのパスに限る（付けないと、同じ名前のディレクトリがどの階層でも除かれる）。
# ty は glob として読み、空白や % などがあると止まるため、英数字と . _ - / のほかはエスケープする
nested=$(jq -c --arg project "${PROJECT}" '.[$project] // []' <<< "${NESTED}")
excludes=()
while IFS= read -r -d '' dir; do
  excludes+=("--exclude=./${dir}")
done < <(jq -j '.[] | gsub("(?<c>[^A-Za-z0-9_./-])"; "\\\(.c)") + "\u0000"' <<< "${nested}")

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
# 利用者の設定があれば書き換えない
generated=false
if [ -e ty.toml ]; then
  config="ty.toml"
else
  # ty.toml が無ければ [tool.ty] が読まれる。案内もそこを指す
  config="pyproject.toml の [tool.ty]"
  ty_config=0
  has_tool ty || ty_config=$?
  if [ "${ty_config}" -ne 0 ] && [ "${ty_config}" -ne 10 ]; then
    # 読めないときは、利用者の [tool.ty] を隠さないよう ty.toml を書き出さない
    echo "::warning::ty: pyproject.toml を読めませんでした。[tool.ty] があるか判定できないため、そのまま検査します"
  fi
  if [ "${ty_config}" -eq 10 ]; then
    if [ -e pyrightconfig.json ] || [ -e mypy.ini ] || [ -e .mypy.ini ] || has_tool pyright || has_tool mypy || has_mypy_cfg; then
      echo "::warning::ty: Pyright / mypy の設定は使われません。検査対象や厳しさは pyproject.toml の [tool.ty] に移してください（${docs}）"
    fi
    # 設定が無いと、親のディレクトリの [tool.ty] / ty.toml まで遡り、親のプロジェクトを検査してしまう。
    # 空の ty.toml を置いて、このディレクトリをプロジェクトにする（requires-python は pyproject.toml から読まれる）
    : > ty.toml
    generated=true
  fi
fi
# 一度だけ導入し、導入の失敗を型エラー（exit 1）と取り違えないようにする。
# 実行はプロジェクトの環境（uv run）で行い、import をプロジェクトの依存で解決させる
if ! uv tool install --quiet "ty==${TY_VERSION}"; then
  echo "::error::ty: ty ${TY_VERSION} を導入できませんでした。上の uv のエラーを確かめてください"
  exit 1
fi
ty="$(uv tool dir --bin)/ty"
log=$(mktemp)
status=0
# 検査するファイルが無いときの警告は標準エラーに出るため、ログに入れる
uv run --no-sync "${ty}" check "${excludes[@]}" 2>&1 | tee "${log}" || status=$?
# ty は include のパスが無くても 0 で終わる。何も検査しないまま通らないよう落とす。
# ty が 0 で終わったので設定は TOML として読める。ty.toml があれば [tool.ty] は読まれない。glob とエスケープは存在を確かめられないため見ない
if [ "${status}" -eq 0 ] && [ "${generated}" = false ]; then
  missing=$(python3 -I -c '
import json, os, tomllib
path = "ty.toml" if os.path.exists("ty.toml") else "pyproject.toml"
data = tomllib.load(open(path, "rb"))
ty = data if path == "ty.toml" else data.get("tool", {}).get("ty", {})
print(json.dumps([p for p in ty.get("src", {}).get("include", []) if not set(p) & set("*?[!\\") and not os.path.exists(p.lstrip("/"))]))
')
  if [ "${missing}" != "[]" ]; then
    # パスは対象 repo 由来のため、ワークフローコマンドとしてエスケープする
    echo "::error::ty: ${config} の include に存在しないパス（$(jq -r 'join(", ") | gsub("%"; "%25") | gsub("\r"; "%0D") | gsub("\n"; "%0A")' <<< "${missing}")）があります。検査されないファイルが出ないよう直してください（${docs}）"
    exit 1
  fi
fi
# 利用者の設定で検査するファイルが 1 つも無いときも 0 で終わる。
# 設定が無いプロジェクトでは、コードがすべて入れ子のプロジェクトにあり 0 件のことがあるため落とさない。
# この判定は ty の出力の文言に頼るため、TY_VERSION を上げたら文言が変わっていないか確かめる
if [ "${status}" -eq 0 ] && [ "${generated}" = false ] && grep -q 'No python files found' "${log}"; then
  echo "::error::ty: ${config} の include / exclude に当てはまる Python ファイルがありません。検査されないファイルが出ないよう直してください（${docs}）"
  exit 1
fi
# uv run が ty を起動できないときも 1 で終わる。ty は指摘があれば必ず件数の行を出すため、無ければ実行時のエラーとして扱う
if [ "${status}" -eq 1 ] && ! grep -qE '^Found [0-9]+ diagnostics?$' "${log}"; then
  status=2
fi
case "${status}" in
  0) ;;
  1) echo "::error::ty: 型エラー（warning を含む）を直してください。検査から外すディレクトリ（scripts/ など）は ${config} の include / exclude で絞れます（${docs}）" ;;
  *) echo "::error::ty: 型チェックを実行できませんでした（exit ${status}）。上のエラーと、${config} の書き方を確かめてください（${docs}）" ;;
esac
exit "${status}"
