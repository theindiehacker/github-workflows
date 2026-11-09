#!/usr/bin/env bash
# アプリケーションコードを Semgrep CE（SAST, ルールセット r/all と rules/ の自作ルール・severity ERROR のみ）でスキャンする。
set -euo pipefail

# コンテナは root で動くため、runner が checkout した作業ツリーを git に信頼させる
# --disable-nosem: インライン nosemgrep コメントを無効化（repo 側の抑制は .semgrepignore に限定する）
docker run --rm \
  --volume "${GITHUB_WORKSPACE}:/src" --workdir /src \
  --volume "${GITHUB_ACTION_PATH}/rules:/rules:ro" \
  --env GIT_CONFIG_COUNT=1 --env GIT_CONFIG_KEY_0=safe.directory --env GIT_CONFIG_VALUE_0=/src \
  "${IMAGE}" \
  semgrep scan \
  --config r/all \
  --config /rules/nextjs.yml \
  --severity ERROR \
  --exclude-rule ajinabraham.njsscan.generic.hardcoded_secrets.node_api_key \
  --exclude-rule ajinabraham.njsscan.generic.hardcoded_secrets.node_secret \
  --exclude-rule dockerfile.correctness.multiple-entrypoint-instructions.multiple-entrypoint-instructions \
  --exclude-rule gitlab.nodejs_scan.javascript-ssrf-rule-node_ssrf \
  --exclude-rule python.lang.correctness.return-in-init.return-in-init \
  --exclude-rule python.lang.maintainability.useless-innerfunction.useless-inner-function \
  --error \
  --metrics off \
  --disable-version-check \
  --disable-nosem \
  .
