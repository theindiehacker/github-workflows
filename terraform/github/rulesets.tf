# Organization のルールセット。
# branch ruleset が保護するのは default branch のみ。リリースも default branch（main）のマージ済みコミットから行う運用を前提とする。
# タグやリリースブランチを起点にデプロイする運用を導入する場合は、レビューを経ないコミットからタグを切れてしまうため、
# 別途 tag ruleset / 対象ブランチの追加が必要。
#
# 必須ワークフローのルールセット（security_scan / style_check）の bypass には何も入れないこと
# （入れると、失敗した検査を無視してマージできるようになる）。

locals {
  all_merge_methods = ["merge", "squash", "rebase"]

  # Renovate の更新 PR を承認なしで自動マージするため、pull_request_approval の bypass に入れる（PR のときだけ）
  renovate_app_id = tonumber(data.github_app.renovate.id)

  # Release ワークフローの GITHUB_TOKEN でリリースタグを作るため、「🏷️ リリースタグの作成を制限」の bypass に入れる
  github_actions_app_id = tonumber(data.github_app.github_actions.id)

  required_workflow_repository_id = data.github_repository.github_workflows.repo_id
}

resource "github_organization_ruleset" "main_push" {
  name        = "🚫 main への直接 push 禁止"
  target      = "branch"
  enforcement = "active"

  conditions {
    ref_name {
      include = ["~DEFAULT_BRANCH"]
      exclude = []
    }
    repository_name {
      include = ["~ALL"]
      exclude = []
    }
  }

  rules {
    deletion         = true
    non_fast_forward = true

    pull_request {
      allowed_merge_methods = local.all_merge_methods
    }
  }
}

# 全 PR に人間のレビュー承認（1 名以上）がないとマージできないようにする。
# 承認が Required approvals にカウントされるのは write アクセス保持者のレビューのみ。PR 作成者本人による自己承認はできない
resource "github_organization_ruleset" "pull_request_approval" {
  name        = "✅ PR の承認を必須化"
  target      = "branch"
  enforcement = "active"

  bypass_actors {
    actor_type  = "Integration"
    actor_id    = local.renovate_app_id
    bypass_mode = "pull_request"
  }

  bypass_actors {
    actor_type  = "OrganizationAdmin"
    bypass_mode = "always"
  }

  conditions {
    ref_name {
      include = ["~DEFAULT_BRANCH"]
      exclude = []
    }
    repository_name {
      include = ["~ALL"]
      exclude = []
    }
  }

  rules {
    pull_request {
      required_approving_review_count = 1
      # 承認後に push されたコミットが再レビューなしでマージされるのを防ぐ
      dismiss_stale_reviews_on_push     = true
      require_code_owner_review         = false
      require_last_push_approval        = false
      required_review_thread_resolution = false
      allowed_merge_methods             = local.all_merge_methods
    }
  }
}

# シークレット・GitHub Actions の設定・アプリケーションコード・依存パッケージと IaC・イメージの検査（security.yml）
resource "github_organization_ruleset" "security_scan" {
  name        = "🛡️ 脆弱性・IaC 設定ミス検知"
  target      = "branch"
  enforcement = "active"

  conditions {
    ref_name {
      include = ["~DEFAULT_BRANCH"]
      exclude = []
    }
    repository_name {
      include = ["~ALL"]
      exclude = []
    }
  }

  rules {
    required_workflows {
      do_not_enforce_on_create = true

      required_workflow {
        repository_id = local.required_workflow_repository_id
        path          = ".github/workflows/security.yml"
        ref           = "refs/heads/main"
      }
    }
  }
}

# ワークフロー定義・シェルスクリプト・Terraform・Python・TypeScript の検査と、バンドルサイズの増減のコメント（style.yml）。
# ランナーで依存を導入できない repo は、bypass ではなく conditions で対象から外す（docs/SETUP.md の「例外運用」）
resource "github_organization_ruleset" "style_check" {
  name        = "✏️ スタイルチェック"
  target      = "branch"
  enforcement = "active"

  conditions {
    ref_name {
      include = ["~DEFAULT_BRANCH"]
      exclude = []
    }
    repository_name {
      include = ["~ALL"]
      exclude = []
    }
  }

  rules {
    required_workflows {
      do_not_enforce_on_create = true

      required_workflow {
        repository_id = local.required_workflow_repository_id
        path          = ".github/workflows/style.yml"
        ref           = "refs/heads/main"
      }
    }
  }
}

# 秘密鍵や .env などの機密ファイルを、履歴に入る前にサーバー側で拒否する
# （Gitleaks は PR 時の検知のため、検知された時点で秘密情報はリモートの履歴に残っている）。
# ファイル内容に対するコミット前のローカル検知は、各リポジトリの git hook（任意運用）が担う
resource "github_organization_ruleset" "sensitive_files" {
  name        = "🚫 機密ファイルの push 禁止"
  target      = "push"
  enforcement = "active"

  conditions {
    repository_name {
      include = ["~ALL"]
      exclude = []
    }
  }

  rules {
    # .env.example 等のテンプレートを誤ブロックしないよう .env.* は対象にしない（実値が入った .env.* は Gitleaks が検知する）
    file_path_restriction {
      restricted_file_paths = [
        ".env",
        "**/.env",
        "id_rsa",
        "**/id_rsa",
        "id_ed25519",
        "**/id_ed25519",
      ]
    }

    # tfplan（terraform plan -out の出力）は、sensitive な値も含めて平文で入る
    file_extension_restriction {
      restricted_file_extensions = [
        "*.pem",
        "*.key",
        "*.p12",
        "*.pfx",
        "*.jks",
        "*.keystore",
        "*.tfstate",
        "*.tfplan",
      ]
    }

    max_file_size {
      max_file_size = 5
    }
  }
}

# 付けたタグが別のコミットに付け替えられると、呼び出し側の `@<SHA>  # vX.Y.Z` のコメントと実際の SHA がずれ、
# Renovate の更新も壊れるため、リリースタグの更新・削除を禁止する。誤ったタグを付けた場合も付け替えず、修正を入れた次のバージョンを出す
resource "github_organization_ruleset" "release_tags" {
  name        = "🔒 リリースタグの変更禁止"
  target      = "tag"
  enforcement = "active"

  conditions {
    ref_name {
      include = ["refs/tags/v*"]
      exclude = []
    }
    repository_id = [local.required_workflow_repository_id]
  }

  rules {
    update           = true
    deletion         = true
    non_fast_forward = true
  }
}

# リリースタグを作れるのを、GitHub Actions (Release ワークフローの GITHUB_TOKEN) だけにする。
# @claude の job で Claude App の書き込みトークンが漏れても、レビューを経ないコミットにリリースタグを付けられないようにするため
# (claude-code-action は Claude を動かす前に、checkout が残す GITHUB_TOKEN を消して Claude App のトークンに替える)。
# release_tags とは分けること。同じルールセットで bypass すると、GitHub Actions に更新・削除も許してしまう
resource "github_organization_ruleset" "release_tag_creation" {
  name        = "🏷️ リリースタグの作成を制限"
  target      = "tag"
  enforcement = "active"

  bypass_actors {
    actor_type  = "Integration"
    actor_id    = local.github_actions_app_id
    bypass_mode = "always"
  }

  conditions {
    ref_name {
      include = ["refs/tags/v*"]
      exclude = []
    }
    repository_id = [local.required_workflow_repository_id]
  }

  rules {
    creation = true
  }
}
