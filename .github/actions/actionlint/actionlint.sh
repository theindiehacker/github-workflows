#!/usr/bin/env bash
# GitHub Actions のワークフロー定義を actionlint で構文チェックする
set -euo pipefail

# workflow command 形式で出力し、検出箇所を PR に annotation 表示する
# shellcheck disable=SC2016 # $err は actionlint のテンプレートの変数
actionlint -format $'{{range $err := .}}::error file={{$err.Filepath}},line={{$err.Line}},col={{$err.Column}}::{{$err.Message}}\n{{end}}'
