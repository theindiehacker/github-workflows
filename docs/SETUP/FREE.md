# 🆓 セットアップ（Free プラン）

Organization を Free プランで運用する場合の手順。[TEAM.md](./TEAM.md) の「0.」「3.」「4.」「5.」はそのまま実施し、ルールセット（「2.」）の代わりに本書の「2.」「3.」を行う。

## 1. 👥 セキュリティチームを作成

TEAM.md の「1.」と同様にチームを作成し、`Security manager` ロールのみをアサインする（`All-repository write` のアサインは不要）。

---
## 2. 🛡️ 検知ワークフローを各リポジトリに導入

各リポジトリに caller ワークフローを 1 ファイル置き、本リポジトリのワークフローを reusable workflow として呼び出す。

### 2.1 本リポジトリの共有設定

`github-workflows` → Settings → Actions → General → **Access** を
`Accessible from repositories in the '<org>' organization` に設定する。

### 2.2 caller ワークフローを配置

各リポジトリに `.github/workflows/security.yml` を追加する（そのままコピペ可。`<org>` は自組織名に置換）:

```yaml
name: "🛡️ Security checks"

# github-workflows の検知ワークフロー（reusable）を呼び出す。導入手順は github-workflows の docs/SETUP/FREE.md を参照
on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions: {}

# 同一 PR に連投された run のみ束ねて追い越しキャンセル
concurrency:
  group: security-checks-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  gitleaks:
    permissions:
      contents: read
    uses: <org>/github-workflows/.github/workflows/gitleaks.yml@main
  trivy:
    permissions:
      contents: read
    uses: <org>/github-workflows/.github/workflows/trivy.yml@main
  semgrep:
    permissions:
      contents: read
    uses: <org>/github-workflows/.github/workflows/semgrep.yml@main
  zizmor:
    permissions:
      contents: read
      pull-requests: read
    uses: <org>/github-workflows/.github/workflows/zizmor.yml@main
  ghalint:
    permissions:
      contents: read
      pull-requests: read
    uses: <org>/github-workflows/.github/workflows/ghalint.yml@main
  actionlint:
    permissions:
      contents: read
      pull-requests: read
    uses: <org>/github-workflows/.github/workflows/actionlint.yml@main
  tflint:
    permissions:
      contents: read
      pull-requests: read
    uses: <org>/github-workflows/.github/workflows/tflint.yml@main
  terraform-fmt:
    permissions:
      contents: read
      pull-requests: read
    uses: <org>/github-workflows/.github/workflows/terraform-fmt.yml@main
  shellcheck:
    permissions:
      contents: read
      pull-requests: read
    uses: <org>/github-workflows/.github/workflows/shellcheck.yml@main
```

- 呼び出し先は `@main` 参照のままにする（SHA 固定にすると中央の検知強化・修正に追従しなくなる）
- Terraform を使わないリポジトリでも `tflint` / `terraform-fmt` の job は削除しない（Terraform 関連ファイルに変更がなければ skip され success になる）
- シェルスクリプトを持たないリポジトリでも `shellcheck` の job は削除しない（対象ファイルに変更がなければ skip され success になる）

### 2.3 zizmor / ghalint の許可設定を配置

caller の `@main` 参照は SHA 固定チェック（zizmor の `unpinned-uses` / ghalint の `action_ref_should_be_full_length_commit_sha`）で fail するため、caller と同じ PR で以下の 2 ファイルも追加する（既にファイルがある場合は追記）:

`.github/zizmor.yml`:

```yaml
rules:
  unpinned-uses:
    config:
      policies:
        "<org>/github-workflows/*": ref-pin  # 中央の検知ワークフローは @main 参照で即時反映させる
        "*": hash-pin
```

※ `/*` は省略不可（`<org>/github-workflows` だけではサブパス付きのワークフロー参照にマッチしない）。`"*": hash-pin` は zizmor デフォルトの再定義で、policies を書くとデフォルトが**置換**されるため省略すると他の action の SHA 固定チェックが消える

`ghalint.yml`（リポジトリ直下）:

```yaml
excludes:
  # 中央の検知ワークフローは @main 参照で即時反映させる（SHA 固定の対象外）
  - policy_name: action_ref_should_be_full_length_commit_sha
    action_name: <org>/github-workflows/.github/workflows/gitleaks.yml
  - policy_name: action_ref_should_be_full_length_commit_sha
    action_name: <org>/github-workflows/.github/workflows/trivy.yml
  - policy_name: action_ref_should_be_full_length_commit_sha
    action_name: <org>/github-workflows/.github/workflows/semgrep.yml
  - policy_name: action_ref_should_be_full_length_commit_sha
    action_name: <org>/github-workflows/.github/workflows/zizmor.yml
  - policy_name: action_ref_should_be_full_length_commit_sha
    action_name: <org>/github-workflows/.github/workflows/ghalint.yml
  - policy_name: action_ref_should_be_full_length_commit_sha
    action_name: <org>/github-workflows/.github/workflows/actionlint.yml
  - policy_name: action_ref_should_be_full_length_commit_sha
    action_name: <org>/github-workflows/.github/workflows/tflint.yml
  - policy_name: action_ref_should_be_full_length_commit_sha
    action_name: <org>/github-workflows/.github/workflows/terraform-fmt.yml
  - policy_name: action_ref_should_be_full_length_commit_sha
    action_name: <org>/github-workflows/.github/workflows/shellcheck.yml
```

※ `action_name` はサブパス込みの完全一致のため、リポジトリ名だけの指定（`<org>/github-workflows`）では効かない

### 2.4 監査ワークフローを有効化（読み取り専用 GitHub App）

2.2〜2.3 のファイルの配置はサーバー側で強制できないため、org の全リポジトリを毎日 09:00 (JST) に走査する監査ワークフローを本リポジトリに配置する。欠落・改変を検知すると本リポジトリに issue（`security-audit` ラベル）を起票する（解消されると次回実行時に自動 close）。

#### 2.4.1 監査ワークフローを配置

本リポジトリに `.github/workflows/security-audit.yml` を追加する（そのままコピペ可。org 名・リポジトリ名は実行時に解決されるため置換不要）:

```yaml
name: "🔍 Security audit"

# サーバー側で配置を強制できない caller・許可設定（docs/SETUP/FREE.md 2.2〜2.3 のファイル）の欠落・改変を、
# 読み取り専用の GitHub App トークンで日次走査して検知し、本リポジトリに issue を起票する。
# App 未設定（AUDIT_APP_CLIENT_ID が空）の間は job ごと skip される。
on:
  schedule:
    - cron: "0 0 * * *"  # 毎日 09:00 JST
  workflow_dispatch:

permissions: {}

# 手動実行と定期実行が同時に走った場合の issue 重複起票を防ぐ
concurrency:
  group: security-audit
  cancel-in-progress: false

jobs:
  audit:
    name: "検知ファイルの欠落・改変を監査"
    if: vars.AUDIT_APP_CLIENT_ID != ''
    runs-on: ubuntu-latest
    timeout-minutes: 15
    permissions:
      issues: write  # 監査結果 issue の起票・更新・close
    steps:
      - name: "App トークンを発行"
        id: app-token
        uses: actions/create-github-app-token@bcd2ba49218906704ab6c1aa796996da409d3eb1  # v3.2.0
        with:
          client-id: ${{ vars.AUDIT_APP_CLIENT_ID }}
          private-key: ${{ secrets.AUDIT_APP_PRIVATE_KEY }}
          owner: ${{ github.repository_owner }}
          permission-contents: read

      - name: "全リポジトリを走査"
        id: audit
        shell: bash
        env:
          GH_TOKEN: ${{ steps.app-token.outputs.token }}
          ORG: ${{ github.repository_owner }}
        run: |
          set -euo pipefail
          CENTRAL="${GITHUB_REPOSITORY#*/}"
          report="${RUNNER_TEMP}/report.md"
          target="${RUNNER_TEMP}/target.tmp"
          : > "${report}"

          # $1: リポジトリ名, $2: パス, $3: 保存先。0=取得, 1=404。その他の失敗（権限・rate limit 等）を
          # 「ファイルがない」と誤報しないよう、404 以外は run を fail させる
          fetch() {
            local err="${RUNNER_TEMP}/fetch-err.txt"
            if gh api -H "Accept: application/vnd.github.raw" "/repos/${ORG}/$1/contents/$2" > "$3" 2> "${err}"; then
              return 0
            elif grep -q "HTTP 404" "${err}"; then
              return 1
            else
              echo "::error::${ORG}/$1 の $2 の取得に失敗しました"
              cat "${err}"
              exit 1
            fi
          }

          repos=$(gh api --paginate "/installation/repositories?per_page=100" \
            --jq '.repositories[] | select(.archived | not) | .name' | sort)

          total=0
          flagged=0
          while IFS= read -r repo; do
            if [ -z "${repo}" ] || [ "${repo}" = "${CENTRAL}" ]; then continue; fi
            total=$((total + 1))
            problems=()

            # caller（2.2）: 存在・必須ワークフローの @main 呼び出し・pull_request トリガー
            if fetch "${repo}" ".github/workflows/security.yml" "${target}"; then
              if ! grep -q "pull_request" "${target}"; then
                problems+=("caller に \`pull_request\` トリガーがない")
              fi
              for wf in gitleaks trivy semgrep zizmor ghalint actionlint tflint terraform-fmt shellcheck; do
                if ! grep -Eq "uses:[[:space:]]*${ORG}/${CENTRAL}/\.github/workflows/${wf}\.yml@main" "${target}"; then
                  problems+=("caller が \`${wf}.yml@main\` を呼び出していない")
                fi
              done
            else
              problems+=("caller（\`.github/workflows/security.yml\`）がない")
            fi

            # 許可設定（2.3）: zizmor は .github/zizmor.yml に固定、ghalint は自動探索パスを順に確認
            if fetch "${repo}" ".github/zizmor.yml" "${target}"; then
              if ! grep -Eq "\"${ORG}/${CENTRAL}/\*\"[[:space:]]*:[[:space:]]*ref-pin" "${target}"; then
                problems+=("\`.github/zizmor.yml\` に \`\"${ORG}/${CENTRAL}/*\": ref-pin\` の policy がない")
              fi
              if ! grep -Eq "\"\*\"[[:space:]]*:[[:space:]]*hash-pin" "${target}"; then
                problems+=("\`.github/zizmor.yml\` に \`\"*\": hash-pin\` がない")
              fi
            else
              problems+=("\`.github/zizmor.yml\` がない")
            fi

            ghalint_cfg=""
            for path in ghalint.yml ghalint.yaml .ghalint.yml .ghalint.yaml .github/ghalint.yml .github/ghalint.yaml; do
              if fetch "${repo}" "${path}" "${target}"; then ghalint_cfg="${path}"; break; fi
            done
            if [ -n "${ghalint_cfg}" ]; then
              if ! grep -q "action_ref_should_be_full_length_commit_sha" "${target}" || ! grep -q "${ORG}/${CENTRAL}/" "${target}"; then
                problems+=("\`${ghalint_cfg}\` に caller 用の excludes がない")
              fi
            else
              problems+=("\`ghalint.yml\` がない")
            fi

            if [ "${#problems[@]}" -gt 0 ]; then
              flagged=$((flagged + 1))
              {
                echo "### ${repo}"
                printf -- '- %s\n' "${problems[@]}"
                echo
              } >> "${report}"
              echo "::warning::${repo}: 欠落・改変 ${#problems[@]} 件"
            fi
          done <<< "${repos}"

          echo "対象 ${total} リポジトリ / 指摘 ${flagged} リポジトリ"
          {
            echo "total=${total}"
            echo "flagged=${flagged}"
          } >> "${GITHUB_OUTPUT}"

      - name: "結果を issue に反映"
        shell: bash
        env:
          GH_TOKEN: ${{ github.token }}
          TOTAL: ${{ steps.audit.outputs.total }}
          FLAGGED: ${{ steps.audit.outputs.flagged }}
          LABEL: security-audit
          TITLE: "🔍 セキュリティ検知ファイルの欠落・改変があります"
        run: |
          set -euo pipefail
          run_url="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"
          doc_url="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/blob/main/docs/SETUP/FREE.md"

          gh label create "${LABEL}" -R "${GITHUB_REPOSITORY}" --force \
            --color "D93F0B" --description "セキュリティ監査ワークフローの自動起票"

          existing=$(gh issue list -R "${GITHUB_REPOSITORY}" --label "${LABEL}" --state open \
            --json number --jq '.[0].number // empty')

          if [ "${FLAGGED}" -gt 0 ]; then
            body="${RUNNER_TEMP}/body.md"
            {
              echo "日次監査（[実行ログ](${run_url})）で、対象 ${TOTAL} リポジトリ中 ${FLAGGED} リポジトリに検知ワークフロー関連ファイルの欠落・改変が見つかりました。"
              echo "各ファイルの配置内容は [docs/SETUP/FREE.md](${doc_url}) の 2.2〜2.3 を参照してください。"
              echo
              cat "${RUNNER_TEMP}/report.md"
            } > "${body}"
            if [ -n "${existing}" ]; then
              gh issue edit "${existing}" -R "${GITHUB_REPOSITORY}" --body-file "${body}"
              echo "issue #${existing} を更新しました"
            else
              gh issue create -R "${GITHUB_REPOSITORY}" --title "${TITLE}" --label "${LABEL}" --body-file "${body}"
            fi
          elif [ -n "${existing}" ]; then
            gh issue close "${existing}" -R "${GITHUB_REPOSITORY}" \
              --comment "監査で全リポジトリの解消を確認しました（[実行ログ](${run_url})）"
          fi
```

監査ワークフローは App トークンを owner 全体に付与するため、本リポジトリの zizmor（`github-app`）/ ghalint（`github_app_should_limit_repositories`）のチェックで fail する。同じ PR で以下の 2 ファイルも本リポジトリに追加する（既にファイルがある場合は追記）:

`.github/zizmor.yml`:

```yaml
rules:
  github-app:
    ignore:
      # 監査（security-audit）は org 全リポジトリの走査が目的のため、owner 全体へのトークン付与を許可する
      - security-audit.yml
```

`ghalint.yml`（リポジトリ直下）:

```yaml
excludes:
  # 監査（security-audit）は org 全リポジトリの走査が目的のため repositories を限定しない
  - policy_name: github_app_should_limit_repositories
    workflow_file_path: .github/workflows/security-audit.yml
    job_name: audit
    step_id: app-token
```

#### 2.4.2 読み取り専用 GitHub App を作成

走査には org 全リポジトリを読めるトークンが必要なため、読み取り専用の GitHub App を作成する:

1. Organization → Settings → Developer settings → **GitHub Apps** → **New GitHub App** で作成:
   - GitHub App name: `<org>-security-audit` など（Homepage URL は本リポジトリの URL など任意）
   - Webhook: **Active のチェックを外す**
   - Repository permissions: `Contents: Read-only` のみ（Metadata: Read-only は自動付与）
   - Where can this GitHub App be installed?: `Only on this account`
2. 作成後の設定画面で **Client ID** を控え、**Private keys** → **Generate a private key** で秘密鍵（.pem）をダウンロード
3. 左メニューの **Install App** から org にインストールし、対象は **All repositories** を選択
4. 本リポジトリの Settings → Secrets and variables → **Actions** に登録:
   - **Variables**: `AUDIT_APP_CLIENT_ID` = 2. の Client ID
   - **Secrets**: `AUDIT_APP_PRIVATE_KEY` = 2. の .pem の中身
5. Actions タブ → 「🔍 Security audit」 → **Run workflow** で手動実行し、動作を確認

- `AUDIT_APP_CLIENT_ID` が未設定の間、ワークフローは skip される（2.4.1 の配置が先行しても fail しない）
- App に書き込み権限は付与しない（鍵漏洩時の影響を読み取りに限定する。配置・修復は人が PR で行う）
- 監査内容: caller の存在と 9 ワークフローの `@main` 呼び出し・`pull_request` トリガー、`.github/zizmor.yml` / `ghalint.yml` の存在と必須設定

---
## 3. 📏 運用ルールを明文化して周知

以下はサーバー側で強制されないため、開発ルールとして明文化して周知する:

- 変更は必ず PR 経由で行う（main への直接 push 禁止）
- 1 名以上の Approve を得てからマージする
- 「🛡️ Security checks」が fail した PR はマージしない
- 抑制設定（`.gitleaksignore` / `.trivyignore` / `.semgrepignore` / `.github/zizmor.yml` / `ghalint.yml` など）を変更する PR はセキュリティチームを手動でレビュアーに指定し、レビューを受ける
- 本リポジトリの `.github/workflows/` と各リポジトリの caller（`security.yml`）を変更する PR も同様にセキュリティチームのレビューを受ける
- コミット前のローカル検知（pre-commit / lefthook / mise + gitleaks など）を各リポジトリで導入する（ツールは任意。本リポジトリ直下の `.pre-commit-config.yaml` が実例。新規リポジトリへの初期設定はテンプレートリポジトリで配布する）
- 既存リポジトリを本構成に乗せる際は、TEAM.md の「🔑 シークレットの混入検知」と同様に全履歴スキャンを一度実施する

> caller（`security.yml`）や許可設定（2.3）の削除・改変はマージ時には止まらないが、日次監査（2.4）が検知して issue を起票する。
> リポジトリ新設時の配置漏れ（2.2〜2.3）も同様に検知される。

### （推奨）public リポジトリにはルールセットを設定する

public リポジトリはリポジトリ単位のルールセットが有効なため、TEAM.md の 2.1〜2.2 相当を各リポジトリの Settings → Rules → Rulesets で設定する（Target repositories の項目がない以外は同じ）。

本リポジトリ（`github-workflows`）を public にできる場合は、上記に加えて CODEOWNERS で `.github/workflows/` をセキュリティチームに割り当て、ルールセットの `Require review from Code Owners` を有効化する。

---
## 4. 💰 Team プランへ移行する場合

1. TEAM.md の「2.」のルールセットを設定する
2. TEAM.md の「1.」の `All-repository write` ロールを追加でアサインする
3. 各リポジトリから caller（`security.yml`）と許可設定（`.github/zizmor.yml` の `<org>/github-workflows/*` 行・`ghalint.yml` の excludes）を削除する（caller が残っていると必須ワークフローと二重実行になり Actions 利用時間を消費する）
4. 監査用の GitHub App（2.4）をアンインストール・削除し、本リポジトリから 2.4.1 で配置した監査ワークフロー一式（`security-audit.yml`・`.github/zizmor.yml` の `github-app` ignore・`ghalint.yml` の excludes）と `AUDIT_APP_CLIENT_ID` / `AUDIT_APP_PRIVATE_KEY` を削除する
