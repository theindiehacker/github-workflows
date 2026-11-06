#!/usr/bin/env bash
# FILES（JSON 配列）のシェルスクリプトを、導入済みの shellcheck で lint する
set -euo pipefail

# プロセス置換では jq の失敗が伝わらないため、いったんファイルに受ける
list="${RUNNER_TEMP}/shellcheck-targets.txt"
jq -r '.[]' <<< "${FILES}" > "${list}"
mapfile -t targets < "${list}"
# 出力には対象 repo のパスやソースが含まれるため、全行に "| " を付けてワークフローコマンドを防ぐ（runner は行頭の空白を除いて判定するため字下げでは防げない）
shellcheck --severity=warning --external-sources "${targets[@]}" 2>&1 | sed 's/\r/\\r/g; s/^/| /'
