# 🧠 Claude レビューワークフロー

PR のコメントで Claude Code にレビューさせる reusable workflow。各リポジトリには呼び出し側ファイルだけを置く。

| ワークフロー | コマンド |
|:--|:--|
| `.github/workflows/claude-code-review.yml` | `/code-review` / `/code-review fable` |
| `.github/workflows/claude-security-review.yml` | `/security-review` |

セットアップは [SETUP.md](./SETUP.md) 4. を参照。

## ⚠️ 前提

> 本リポジトリは private のため、reusable workflow を呼べるのは同じ org の private リポジトリだけ(public リポジトリや他 org からは呼び出せない)。[SETUP.md](./SETUP.md) 3. の Access 設定が前提。
>
> 進捗コメントを出すため tag mode(`track_progress`)で動かしており、action が許可ツールを自動で足す。そのためレビュー中の Claude は、作業ディレクトリ外を含むファイルを読め(`.git/config` の App トークン、`/proc/self/environ` の Anthropic 認証情報)、PR ブランチへのコミット・push もできる。PR の本文・コメント・差分に仕込まれた指示で、これらがコメントに書き出されたり PR ブランチに push されたりしうる。org の fork 禁止([SETUP.md](./SETUP.md) 0.)により PR を作れるのは write 権限者に限られ、書き出し先も private リポジトリのコメントなので、このリスクは許容している

## 🧠 使い方

open な PR に以下をコメントする(OWNER / MEMBER / COLLABORATOR のみ。Bot のコメントは無視される)。コメント本文がコマンドと完全一致したときだけ起動する(前後の空白・改行や補足の追記があると起動しない):

| コメント | 動作 |
|:--------|:----|
| `/code-review` | コードレビュー |
| `/code-review fable` | コードレビュー(モデルを fable に切り替え) |
| `/security-review` | セキュリティレビュー |

実行中の状況と完了・失敗は進捗コメントに、指摘は該当行へのインラインコメントに残る。

## 📥 呼び出し側ファイル

呼び出し側ワークフロー `.github/workflows/claude.yml` は [claude-plugins](https://github.com/theindiehacker/claude-plugins) で配布する。呼び出し元は org 内の private リポジトリに限る(「⚠️ 前提」)。仕様は以下のとおり(claude-plugins 側の参照仕様):

```yaml
name: "🧠 Claude"

on:
  issue_comment:
    types: [created]

# write は reusable workflow 側の job にのみ与える(ここで与えた permissions が上限になる)
permissions: {}

jobs:
  code-review:
    # 無関係な issue_comment で run を作らないよう呼び出し側でも絞る(reusable 側の条件を緩めるものではなく、狭めるだけ)
    if: github.event.issue.pull_request && (github.event.comment.body == '/code-review' || github.event.comment.body == '/code-review fable') && github.event.comment.user.type != 'Bot'
    # 本リポジトリの Release の SHA に固定する(タグ参照のままだと zizmor / ghalint の必須ワークフローで落ちる)
    uses: theindiehacker/github-workflows/.github/workflows/claude-code-review.yml@<sha>  # vX.Y.Z
    permissions:
      contents: read
      pull-requests: write
      issues: write
      id-token: write
    # secrets: inherit は使わない(ghalint deny_inherit_secrets)。組織シークレットをこの名前で登録する
    secrets:
      CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}

  security-review:
    if: github.event.issue.pull_request && github.event.comment.body == '/security-review' && github.event.comment.user.type != 'Bot'
    uses: theindiehacker/github-workflows/.github/workflows/claude-security-review.yml@<sha>  # vX.Y.Z
    permissions:
      contents: read
      pull-requests: write
      issues: write
      id-token: write
    secrets:
      CLAUDE_CODE_OAUTH_TOKEN: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

- 呼び出し側の PR も通常どおり必須ワークフローの対象になる

## 🔄 更新の流れ

1. 本リポジトリの `.github/workflows/claude-*.yml` を PR で変更する(`.github/workflows/**` は [SETUP.md](./SETUP.md) 2.6 のルールセットで security チームの承認が必須)
2. `main` にマージ後、GitHub Releases で `vX.Y.Z` タグを作成する
3. Renovate が各リポジトリの `.github/workflows/claude.yml` の `uses:` を新しい SHA に更新する PR を作るので、承認してマージする

呼び出し側は SHA 固定のため、Renovate の PR をマージするまで各リポジトリには反映されない。

> 必須ワークフロー(`.github/workflows/gitleaks.yml` 等)はルールセットが `main` を直接参照するため、この Release の流れは Claude の reusable workflow だけに関係する。
