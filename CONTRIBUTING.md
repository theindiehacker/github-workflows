# Contributing

`theindiehacker/github-workflows` は、組織全体で使う reusable workflow・Taskfile・lefthook の設定を管理するリポジトリです。このドキュメントでは、このリポジトリへの変更の入れ方を説明します。

Claude Code プラグイン（マーケットプレイス `fastship`）は [theindiehacker/fastship-plugin](https://github.com/theindiehacker/fastship-plugin) に移しました。プラグインの変更は同リポジトリで行ってください。

## PR 作成・マージ

PR の作成・更新・CI 監視・レビュー対応は `dev:push-pr` スキル（`/dev:push-pr`）に従ってください。主な流れ:

1. `main` から `<種別>/<内容>` 形式のブランチを作成する（例: `feat/`, `fix/`, `docs/`, `chore/`, `refactor/`）
2. 変更をコミットし、PR テンプレートに従って PR を作成する
3. CI（`.github/workflows/` のスキャン各種）が通過することを確認する
4. 必要に応じてレビューを受け、マージする

## リリース

呼び出し側の挙動が変わる変更をマージしたら、🏷️ Release ワークフローでリリースタグを付けます。手順とバージョンの上げ方は [docs/SETUP.md](./docs/SETUP.md) の「5. 🏷️ リリースタグ」を参照してください。

ドキュメントだけの変更ではリリースしないでください（全リポジトリに Renovate の参照更新 PR が届くため）。
