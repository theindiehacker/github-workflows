# 🎊 セットアップ

> 本書は GitHub Team プランが前提（ルールセットによるサーバー側の強制を使う）。Free プランの場合は [FREE.md](./FREE.md) を参照。

## 0. 🏢 Organization の基本設定

以降の章の前提となるアカウント・権限まわりの設定。Organization → Settings で行う。

| 設定箇所 | 設定項目 | 値                                                                                |
|:--------|:--------|:---------------------------------------------------------------------------------|
| Authentication security | Require two-factor authentication for everyone | ✅(有効化した時点で 2FA 未設定のメンバーは org から除外されるため、事前に周知する)                                  |
| Member privileges | Base permissions | `Read`(write はリポジトリ・チーム単位で個別に付与する。承認が Required approvals にカウントされるのは write 保持者のみ) |
| Member privileges | Repository forking(Allow forking of private repositories) | ❌(private コードが個人アカウント側へ複製されるのを防ぐ)                                                |
| Member privileges | Repository creation | ❌(意図しない公開リポジトリの作成を防ぐため、Private, Public 両方のチェックを外し、管理者しかリポジトリを作成できないようにする)        |

---
## 1. 👥 セキュリティチームを作成
Gitleaks や Trivy などがセキュリティ検知をした時に対応するチームを作成します。<br/>
PR でセキュリティ検知された際はこのチームからの Approve がないとマージできない運用になります。

1. Organization → **Teams** → **New team** でチームを作成
2. 対応者をメンバーに追加
3. Organization → Settings → **Organization roles** → **Role assignments** → **New role assignment** で、作成したチームに以下の 2 ロールをアサイン:

| ロール | 目的 |
|:------|:----|
| `Security manager` | 全リポジトリの Read 権限が自動付与され、2.5・2.6 の Required reviewers が**リポジトリごとのチーム登録(Add teams)なしで自動レビュアー指定**されるようになる(新規リポジトリも自動で対象)。org 全体のセキュリティアラートの閲覧・管理権限も付く |
| `All-repository write` | 承認が Required approvals にカウントされるのは write アクセス保持者のレビューのみのため、Read 相当の Security manager と併用する |

※ 自動レビュアー指定が機能するのは「リポジトリへの直接登録(Add teams)」か「Security manager ロール」の場合のみ。`All-repository write` など一般の org role だけでは、承認は可能になるがレビュアーの自動指定はされない。

> ⚠️ 承認者本人が作成した PR は自己承認できない。チームメンバーが 1 人だけの場合は、
> ルールセットの **Bypass list** に org 管理者を追加してマージする。

---
## 2. 📚 Organization ルールセットを設定
Organization ページ → Settings → Repository → Rulesets を選択し、以下のルールを設定して下さい。

> ⚠️ **前提** : branch ruleset(2.1〜2.7)が保護するのは default branch のみ。リリースも default branch(main)のマージ済みコミットから行う運用を前提とする。
> タグやリリースブランチを起点にデプロイする運用を導入する場合は、レビューを経ないコミットからタグを切れてしまうため、別途 tag ruleset / 対象ブランチの追加が必要。

### `New branch ruleset`

<details><summary><b>「🚫 main への直接 push 禁止」</b></summary>

| 設定項目 | 値                      |
|:-------:|:-----------------------|
| Ruleset Name | `🚫 main への直接 push 禁止` |
| Enforcement status | `Active`               |
| Target repositories | `All repositories` |
| Target branches | `Include default branch` |

Rules セクションで以下にチェック:

- ✅ Restrict deletions (デフォルトブランチの削除を制限する)
- ✅ Require a pull request before merging (マージ前にプルリクエストを必須とする)
- ✅ Block force pushes (リモートブランチへの強制プッシュを禁止)

</details>

<details><summary><b>「✅ PR の承認を必須化」</b></summary>

> 全 PR に人間のレビュー承認(1 名以上)がないとマージできないようにするルール

| 設定項目 | 値                        |
|:-------:|:-------------------------|
| Ruleset Name | `✅ PR の承認を必須化`         |
| Enforcement status | `Active`                 |
| Bypass list | 空のまま<br/>開発者が 1 人だけの場合は「1.」の注意書きを参照 |
| Target repositories | `All repositories`       |
| Target branches | `Include default branch` |

Rules セクションで以下のチェックを外す:

- ⬜︎ **Restrict deletions**
- ⬜︎ **Block force pushes**

以下のチェックを入れる:

- ✅ **Require a pull request before merging**

| 設定項目 | 値 |
|:--------|:--|
| Required approvals | `1` |
| Dismiss stale pull request approvals when new commits are pushed | ✅(承認後に push されたコミットが再レビューなしでマージされるのを防ぐ) |
| Require review from Code Owners | ❌ |
| Require approval of the most recent reviewable push | ❌ |
| Require conversation resolution before merging | ❌ |
| Allowed merge methods | `Merge` / `Squash` / `Rebase`(すべて許可) |

※ 承認が Required approvals にカウントされるのは write アクセス保持者のレビューのみ。PR 作成者本人による自己承認はできない。

</details>

<details><summary><b>「🔑 シークレットの混入検知」</b></summary>

| 設定項目 | 値                        |
|:-------:|:-------------------------|
| Ruleset Name | `🔑 シークレットの混入検知`         |
| Enforcement status | `Active`                 |
| Bypass list | 空のまま                     |
| Target repositories | `All repositories`       |
| Target branches | `Include default branch` |

Rules セクションで以下のチェックを外す:

- ⬜︎ Restrict deletions
- ⬜︎ Block force pushes

以下のチェックを入れる:

 - ✅ **Require workflows to pass before merging** (PRマージ前に指定したワークフローの成功を必須にする) — 「Add workflow」から以下を追加:

| Repository | Branch | Workflow |
|:-----------|:-------|:---------|
| `github-workflows` | `main` | `.github/workflows/gitleaks.yml` |

※ コミット前のローカル検知(シークレットを履歴に入れる前に止めるレイヤー)はリポジトリごとの任意運用とし、中央からは強制しない。pre-commit / lefthook / mise + gitleaks などツールも書き方もリポジトリによって異なり、設定ファイルの存在を機械的に検査すると正しく運用しているリポジトリまで fail するため。新規リポジトリへの初期設定はテンプレートリポジトリで配布する(本リポジトリ直下の `.pre-commit-config.yaml` が実例)。

※ PR 時のスキャン対象は差分(base..head)のみ。導入前から履歴に混入しているシークレットは検査されないため、既存リポジトリを本ルールセットに乗せる際は全履歴を一度スキャンしておく(検知されたらローテーション+履歴からの除去を行う):

```bash
gitleaks git . --redact --exit-code 1 --ignore-gitleaks-allow
```

</details>

<details><summary><b>「🛡️ 脆弱性・IaC 設定ミス検知」</b></summary>

| 設定項目 | 値 |
|:-------:|:--|
| Ruleset Name | `🛡️ 脆弱性・IaC 設定ミス検知` |
| Enforcement status | `Active` |
| Bypass list | 空のまま |
| Target repositories | `All repositories` |
| Target branches | `Include default branch` |

Rules セクションで以下のチェックを外す:

- ⬜︎ **Restrict deletions**
- ⬜︎ **Block force pushes**

以下のチェックを入れる:

- ✅ **Require workflows to pass before merging** (PRマージ前に指定したワークフローの成功を必須にする) — 「Add workflow」から以下を追加:

| Repository | Branch | Workflow |
|:-----------|:-------|:---------|
| `github-workflows` | `main` | `.github/workflows/trivy.yml` |
| `github-workflows` | `main` | `.github/workflows/zizmor.yml` |
| `github-workflows` | `main` | `.github/workflows/semgrep.yml` |
| `github-workflows` | `main` | `.github/workflows/ghalint.yml` |

※ `ghalint` は必須ワークフローのため全 PR で起動されるが、GitHub Actions 関連ファイル(`.github/workflows/` と ghalint の設定ファイル)に変更がない PR ではワークフロー内の判定で lint を skip し success になる。

</details>

<details><summary><b>「✔️ セキュリティ設定ファイル変更の承認必須化」</b></summary>

> セキュリティ検知の設定ファイル(`.gitleaksignore` / `.trivyignore` など)を変更する PR にセキュリティチーム(`security`)の承認を必須化するルール

| 設定項目 | 値                        |
|:-------:|:-------------------------|
| Ruleset Name | `✔️ セキュリティ設定変更の承認必須化`    |
| Enforcement status | `Active`                 |
| Bypass list | 空のまま<br/>承認者が 1 人だけの場合は「1.」の注意書きを参照                |
| Target repositories | `All repositories`       |
| Target branches | `Include default branch` |

Rules セクションで以下のチェックを外す:

- ⬜︎ **Restrict deletions**
- ⬜︎ **Block force pushes**

以下のチェックを入れる:

- ✅ **Require a pull request before merging**

| 設定項目 | 値 |
|:--------|:--|
| Required approvals | `0`(承認必須化は下記の Required reviewers で行う) |
| Dismiss stale pull request approvals when new commits are pushed | ✅ |
| Require review from Code Owners | ❌ |
| Require approval of the most recent reviewable push | ❌ |
| Require conversation resolution before merging | ❌ |
| Allowed merge methods | `Merge` / `Squash` / `Rebase`(すべて許可) |

同ルール内の **Require review from specific teams** に以下を追加:

| 設定項目 | 値                                                                                                                                                                                                        |
|:--------|:---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Reviewer | `security` チーム(「1.」で作成)                                                                                                                                                                                  |
| Approvals | `1`                                                                                                                                                                                                      |

File patterns:
```
.gitleaksignore
.gitleaks.toml
.trivyignore
.trivyignore.yaml
trivy.yaml
.github/trivy-image.yml
.github/trivy-image.yaml
.github/zizmor.yml
.semgrepignore
**/.semgrepignore
ghalint.yml
ghalint.yaml
.ghalint.yml
.ghalint.yaml
.github/ghalint.yml
.github/ghalint.yaml
```

※ `trivy.yaml`(リポジトリ直下)は Trivy が自動読込する設定ファイルで、`ignorefile` / `ignore-policy` により抑制先を差し替えられるため対象に含める。レビュー時はこの 2 項目が上記対象外のファイルを指していないかを確認する<br/>
※ `**/.semgrepignore` は Semgrepignore v2(Semgrep 1.117 以降のデフォルト)でサブディレクトリの `.semgrepignore` も有効になるため対象に含める<br/>
※ zizmor の設定はワークフロー側(`.github/workflows/zizmor.yml` の `--config` / `--no-config`)で `.github/zizmor.yml` に固定しているため、自動探索され得る他パス(リポジトリ直下の `zizmor.yml` 等)の列挙は不要

</details>

<details><summary><b>「🛠️ 検知ワークフロー変更の承認必須化」</b></summary>

> 必須ワークフローの実体(本リポジトリの `.github/workflows/`)を変更する PR にセキュリティチーム(`security`)の承認を必須化するルール。
> 必須ワークフロー(2.3〜2.4・2.7)は本リポジトリの `main` 上の定義を参照しているため、検知を弱める変更(severity の引き下げ・`exit-code: 0` 化など)が通常の承認(2.2)だけで通ると org 全体の検知が無効化されてしまう

| 設定項目 | 値                        |
|:-------:|:-------------------------|
| Ruleset Name | `🛠️ 検知ワークフロー変更の承認必須化`    |
| Enforcement status | `Active`                 |
| Bypass list | 空のまま<br/>承認者が 1 人だけの場合は「1.」の注意書きを参照 |
| Target repositories | `Select repositories` → `github-workflows` のみ |
| Target branches | `Include default branch` |

Rules セクションで以下のチェックを外す:

- ⬜︎ **Restrict deletions**
- ⬜︎ **Block force pushes**

以下のチェックを入れる:

- ✅ **Require a pull request before merging**

| 設定項目 | 値 |
|:--------|:--|
| Required approvals | `0`(承認必須化は下記の Required reviewers で行う) |
| Dismiss stale pull request approvals when new commits are pushed | ✅ |
| Require review from Code Owners | ❌ |
| Require approval of the most recent reviewable push | ❌ |
| Require conversation resolution before merging | ❌ |
| Allowed merge methods | `Merge` / `Squash` / `Rebase`(すべて許可) |

同ルール内の **Require review from specific teams** に以下を追加:

| 設定項目 | 値 |
|:--------|:--|
| Reviewer | `security` チーム(「1.」で作成) |
| Approvals | `1` |

File patterns:
```
.github/workflows/**
```

</details>

<details><summary><b>「✏️ スタイルチェック」</b></summary>

> ワークフロー定義の構文チェック(actionlint)、Terraform の lint(tflint)、シェルスクリプトの lint(shellcheck)を必須化するルール。セキュリティ検知(2.3〜2.6)とは性質が異なるため別ルールセットで管理する

| 設定項目 | 値                        |
|:-------:|:-------------------------|
| Ruleset Name | `✏️ スタイルチェック`            |
| Enforcement status | `Active`                 |
| Bypass list | 空のまま                     |
| Target repositories | `All repositories`       |
| Target branches | `Include default branch` |

Rules セクションで以下のチェックを外す:

- ⬜︎ **Restrict deletions**
- ⬜︎ **Block force pushes**

以下のチェックを入れる:

- ✅ **Require workflows to pass before merging** (PRマージ前に指定したワークフローの成功を必須にする) — 「Add workflow」から以下を追加:

| Repository | Branch | Workflow |
|:-----------|:-------|:---------|
| `github-workflows` | `main` | `.github/workflows/actionlint.yml` |
| `github-workflows` | `main` | `.github/workflows/tflint.yml` |
| `github-workflows` | `main` | `.github/workflows/shellcheck.yml` |

※ `actionlint` は必須ワークフローのため全 PR で起動されるが、ワークフロー関連ファイル(`.github/workflows/` と `.github/actionlint.yml`)に変更がない PR ではワークフロー内の判定で lint を skip し success になる。<br/>
※ `tflint` も同様に全 PR で起動されるが、Terraform 関連ファイル(`*.tf` / `*.tfvars` / `.tflint.hcl` 等)に変更がない PR では lint を skip し success になる(Terraform 未使用のリポジトリでも合格する)。設定は「実行ディレクトリ自身の `.tflint.hcl` > リポジトリ直下の `.tflint.hcl`」の優先で適用され、どちらも無ければ組み込み terraform ruleset の recommended プリセットで lint される。<br/>
※ `shellcheck` も同様に全 PR で起動されるが、シェルスクリプト(`*.sh` / `*.bash` / `*.ksh`)に変更がない PR では lint を skip し success になる。指摘は reviewdog が PR のレビューコメントとして投稿し、対象は PR の変更行かつ severity `warning` 以上に限定されるため、既存スクリプトの未修正分でマージがブロックされることはない。抑制設定はリポジトリ直下の `.shellcheckrc` で行う。<br/>
※ `shellcheck` はレビューコメントの投稿に `pull-requests: write` を使うため、fork からの PR(`GITHUB_TOKEN` が read-only に降格される)では fail する。fork を禁止している private リポジトリ(「0.」)では影響しないが、fork PR を受け付ける public リポジトリがある場合は Target repositories をそのリポジトリ以外に限定する。

</details>


### `New push ruleset`

<details><summary><b>「🚫 機密ファイルの push 禁止」</b></summary>

秘密鍵や `.env` などの機密ファイルを、履歴に入る前にサーバー側で拒否する push ルールセット
(Gitleaks は PR 時の検知のため、検知された時点で秘密情報はリモートの履歴に残っている)。
ファイル内容に対するコミット前のローカル検知は各リポジトリの git hook(任意運用)が担う。
2.1〜2.7 とは種類が異なり「**New push ruleset**」から作成する。

| 設定項目 | 値 |
|:-------:|:--|
| Ruleset Name | `🚫 機密ファイルの push 禁止` |
| Enforcement status | `Active` |
| Bypass list | 空のまま |
| Target repositories | `All repositories` |

Rules セクションで以下を設定:

✅ **Restrict file paths**

| File path |
|:----------|
| `.env` |
| `**/.env` |
| `id_rsa` |
| `**/id_rsa` |
| `id_ed25519` |
| `**/id_ed25519` |

※ `.env.example` 等のテンプレートを誤ブロックしないよう `.env.*` は対象にしない(実値が入った `.env.*` は Gitleaks が検知する)。

✅ **Restrict file extensions**

| Extension |
|:----------|
| `pem` / `key` / `p12` / `pfx` / `jks` / `keystore` / `tfstate` |

✅ **Restrict file size** — `5MB`

</details>

---
## 3. ⚙️ GitHub Actions のセキュリティ設定

Organization → Settings → **Actions** → **General** で以下を設定する。

<details><summary><b>Actions permissions(実行できる action の制限)</b></summary>

| 設定項目 | 値 |
|:--------|:--|
| Policies | `Allow <org>, and select non-<org> actions and reusable workflows` |
| Allow actions created by GitHub | ✅ |
| Allow specified actions and reusable workflows | 下記のパターンを登録 |

```
aquasecurity/trivy-action@*,
docker/setup-buildx-action@*,
docker/build-push-action@*,
dorny/paths-filter@*,
renovatebot/github-action@*,
reviewdog/action-shellcheck@*,
reviewdog/action-setup@*
```

※ 各リポジトリが新しい外部 action を使う場合はこのリストへの追加が必要(SHA ピン留めは各ワークフロー側で行う)。<br/>
※ `reviewdog/action-setup` は `reviewdog/action-shellcheck` が内部で呼び出す composite action のため、併せて許可する必要がある。<br/>
※ `actions/create-github-app-token` は「Allow actions created by GitHub」で許可済みのため個別登録は不要。

</details>

<details><summary><b>Workflow permissions(<code>GITHUB_TOKEN</code> のデフォルト権限)</b></summary>

| 設定項目 | 値 |
|:--------|:--|
| Workflow permissions | `Read repository contents and packages permissions` |
| Allow GitHub Actions to create and approve pull requests | ❌(チェックを外す) |

- `permissions:` を明示しているワークフロー(本リポジトリのものを含む)には影響しない
- 「create and approve pull requests」を無効化することで、`GITHUB_TOKEN` による自己承認で 2.2 / 2.5 / 2.6 の承認必須化が迂回されるのを防ぐ
- この設定は `GITHUB_TOKEN` のみが対象。Renovate(5章)は GitHub App トークンで PR を作るため影響を受けない

</details>

---
## 4. 🚨 Dependabot alerts を有効化

> Trivy は PR 時にしか実行されないため、マージ後に新規公開された CVE は Dependabot alerts で検知する。<br/>
> 依存関係の更新は Renovate が担うため、alerts のみ有効化する。

1. Organization → Settings → **Advanced Security** → **Configurations** を選択
2. 「**Custom configuration**」を選択する
   - 初回は「**Set up Advanced Security**」画面が表示されるが、**Review は押さない**(既定値は有料の Secret Protection / Code Security まで `Enabled` になっており、Dependabot も更新 PR 込みで有効化され Renovate と競合する)
3. 以下の設定で configuration を作成し「**Save configuration**」:

| 設定項目 | 値 |
|:--------|:--|
| Configuration name | `dependabot-alerts` |
| Secret Protection | `Not set`(有料。$19/committer/月) |
| Code Security | `Not set`(有料。$30/committer/月) |
| Dependency graph | `Enabled` |
| Dependabot alerts | `Enabled` |
| Security updates | `Disabled`(更新 PR は Renovate に集約) |
| Malware alerts | `Enabled`(無料。依存関係へのマルウェア混入を通知) |
| Private vulnerability reporting | `Enabled`(初期値のまま。無料・public リポジトリのみ対象) |
| 上記以外の項目 | 初期値のまま変更不要(`Not set` / `Disabled`) |
| Policy: Use as default for newly created repositories | `All repositories`(新規リポジトリに自動適用) |
| Policy: Enforce configuration | `Enforce`(リポジトリ側での設定変更を禁止) |

4. Configurations 一覧で作成した configuration を選択し、**Apply to** → `All repositories` で全リポジトリに適用

---
## 5. ♻️ Renovate を導入

> 依存関係のアップデート PR は、`renovate-config` リポジトリのセルフホスト型 Renovate ランナーが毎日起票する

セットアップ手順(GitHub App の作成・シークレットの登録)と運用方法は `renovate-config` リポジトリの `SETUP.md` / `README.md` を参照。

※ ランナーの実行ログには autodiscover した Org 全リポジトリ名(private 含む)が出力されるため、ランナーは本リポジトリではなく private の `renovate-config` に置いて運用する。
