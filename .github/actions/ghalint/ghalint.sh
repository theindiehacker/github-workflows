#!/usr/bin/env bash
# ghalint で、permissions 未設定・アクションの SHA 未固定など、構文ではなくセキュリティ観点のポリシー違反を検出する
set -euo pipefail

# ghalint run は個別ファイル指定ができないため、.github/workflows/ 全体が対象になる
ghalint run
