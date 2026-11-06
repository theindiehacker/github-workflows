#!/usr/bin/env bash
# PR のコミット範囲 (LOG_OPTS) を gitleaks でスキャンする
set -euo pipefail

# --ignore-gitleaks-allow: インライン allow コメントを無効化（抑制は .gitleaksignore に限定する）
# --max-archive-depth: zip / tar.gz などの圧縮ファイルを展開して中身も検査する（入れ子は 5 階層まで）
gitleaks git . --redact --verbose --exit-code 1 --ignore-gitleaks-allow --max-archive-depth 5 --log-opts="${LOG_OPTS}"
