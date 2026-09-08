# 🔒 github-workflows
Organization 共通のルールセット/CI/セキュリティワークフローを管理するリポジトリ
> ⚠️ **注意** : GitHub Team プランであることが前提です

```mermaid
graph TD;
    subgraph gw ["🔒 github-workflows"]
        Gitleaks["🔑 Gitleaks<br/>シークレット情報混入検知"]
        Trivy["🛡️ Trivy<br/>設定ミス / 脆弱性の検知"]
        Zizmor["🔎 zizmor<br/>GitHub Actions の静的解析"]
        Semgrep["🔬 Semgrep<br/>アプリコードの SAST"]
    end
    ruleset(["Org ルールセット<br/>Require workflows to pass<br/>+ Required reviewers"])
    RepoA["リポジトリA の PR"]
    RepoB["リポジトリB の PR"]
    
    engineer(("👦 管理者")) -->|🎮 設定| ruleset

    ruleset -.->|強制| RepoA
    ruleset -.->|強制| RepoB
    RepoA -->|🏃 実行| gw
    RepoB -->|🏃 実行| gw
```

## 🚧 防止・検知レイヤー

**開発時**:
```mermaid
sequenceDiagram
    actor Engineer as エンジニア
    box 🐙 GitHub
        participant PR
        participant workflows as Workflows
        participant main 
    end

    Engineer->>Engineer: git commit
    Note over Engineer: 🔑 コミット前のローカル検知（任意）<br/>pre-commit / lefthook / mise など手段はリポジトリごと

    Engineer->>main: ❌ push
    Note over Engineer,main: 🚫 main ブランチへの直 push を禁止

    Engineer->>PR: push

    PR->>+workflows: ワークフロー起動（🛡️ gitleaks.yml）
    workflows->>workflows: 🔑 シークレットの混入検知
    workflows->>-PR: ✅ / ❌

    alt ✅ success
        Note over PR: 🛡️ ルールセット<br/>1. Gitleaksの設定ファイル変更時は Approve が必須
        Engineer->>PR: merge
    else ❌ fail
        Engineer-->>PR: 🚫 merge
    end
```

## ♻️ 依存関係の自動更新

Renovate によるアップデート PR の起票は `renovate-config` リポジトリのセルフホストランナーが担う(構成・運用はそちらの README を参照)。更新 PR も通常の PR と同じく必須ワークフローを通過しないとマージできない。

## ❓ 使い方
### 🎊 セットアップ

[docs/SETUP.md](./docs/SETUP.md) を参照して、実行してください。