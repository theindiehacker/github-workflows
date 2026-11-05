#!/usr/bin/env bash
# PATHS（JSON 配列）を対象に terraform の COMMAND（fmt / init / test）をディレクトリごとに実行する。
# 1 つ失敗しても残りは続け、最後に失敗を返す
set -euo pipefail
shopt -s nullglob

# 対象 repo 由来のパスで ::group:: の行を分けられないようエスケープする
escape() { local value=${1//%/%25}; value=${value//$'\r'/%0D}; printf '%s' "${value//$'\n'/%0A}"; }

list=$(mktemp)
case "${COMMAND}" in
  fmt)
    # fmt は -recursive を付けなければ指定ディレクトリ直下だけを見るため、変更ファイルを
    # ディレクトリに集約する。repo 全体を -recursive で検査すると、その PR が触っていない
    # ディレクトリに元からある崩れでも fail してしまう。
    # .terraform はキャッシュ・vendored モジュール置き場のため検査対象外
    jq -r '.[]' <<< "${PATHS}" | { grep -Ev '(^|/)\.terraform/' || true; } \
      | while IFS= read -r f; do dirname "${f}"; done | sort -u > "${list}"
    ;;
  init)
    jq -r '.[]' <<< "${PATHS}" > "${list}"
    if [ -z "${TF_PLUGIN_CACHE_DIR:-}" ]; then echo "::error::init では TF_PLUGIN_CACHE_DIR を env で渡してください"; exit 1; fi
    mkdir -p "${TF_PLUGIN_CACHE_DIR}"
    initialized="${RUNNER_TEMP}/terraform-initialized.txt"
    : > "${initialized}"
    ;;
  test)
    jq -r '.[]' <<< "${PATHS}" > "${list}"
    ;;
  *)
    echo "::error::実行できないコマンドです: ${COMMAND}"
    exit 1
    ;;
esac

status=0
while IFS= read -r dir; do
  if [ "${COMMAND}" = "test" ]; then
    # terraform test はモジュールのディレクトリで実行する。テストはその直下か tests/ に置かれる（terraform の既定）
    tests=("${dir}"/{,tests/}*.tftest.{hcl,json})
    if [ "${#tests[@]}" -eq 0 ]; then continue; fi
  fi

  echo "::group::$(escape "${dir}")"
  # terraform（provider・external data source を含む）が stdin を読んでディレクトリ一覧を消費しないよう、< /dev/null で切り離す
  case "${COMMAND}" in
    fmt)
      # 結果は annotation にせず log に出す（書式が一致しないファイルと差分を出し、どう直すかを読めるようにする）
      # 差分の文脈行は PR のファイルの内容そのままなので、行頭に "│ " を付けてワークフローコマンドとして解釈されないようにする
      terraform fmt -check -no-color -diff "${dir}" | sed 's/^/│ /'
      ;;
    init)
      # lock ファイルがあれば読み取り専用で使い、required_providers と合わなければ失敗させる
      args=(-backend=false)
      if [ -f "${dir}/.terraform.lock.hcl" ]; then args+=(-lockfile=readonly); fi
      # init に失敗したディレクトリは validate / test しない（module・provider が未導入なことによる二次的なエラーしか出ない）。
      # lock ファイルに無いハッシュ（多くは linux_amd64 のもの）を readonly のため追記できなかったときは、
      # init は警告だけで成功するが provider を検証できないため失敗とする
      terraform -chdir="${dir}" init "${args[@]}" 2>&1 | tee "${RUNNER_TEMP}/init.log" \
        && ! grep -q 'Provider lock file not updated' "${RUNNER_TEMP}/init.log" \
        && printf '%s\n' "${dir}" >> "${initialized}"
      ;;
    test)
      # クラウドの認証情報は渡さないため、command = plan と mock_provider で完結するテストだけが通る
      terraform -chdir="${dir}" test
      ;;
  esac < /dev/null || status=1
  echo "::endgroup::"
done < "${list}"

if [ "${COMMAND}" = "init" ]; then
  echo "initialized=$(jq -Rsc 'split("\n")[:-1]' "${initialized}")" >> "${GITHUB_OUTPUT}"
fi
exit "${status}"
