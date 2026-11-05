import json

import gha
import pytest

import targets

PACKAGE_NEXT = '{"dependencies":{"next":"15.0.0"}}'
PATTERN_NEXT = targets.FRAMEWORKS["next"]


@pytest.fixture
def enable(monkeypatch):
    """入力を true / false にする"""

    def set_inputs(*names):
        for name in ("PYTHON", "TYPESCRIPT", "TERRAFORM"):
            monkeypatch.setenv(name, "true" if name in names else "false")

    return set_inputs


def parsed(outputs):
    return {name: json.loads(value) for name, value in outputs().items()}


def commit(root, files):
    for name, content in files.items():
        (root / name).write_text(content, encoding="utf-8")
    git = ["git", "-C", str(root), "-c", "user.name=test", "-c", "user.email=test@example.com"]
    gha.run([*git, "add", "-A"])
    gha.run([*git, "commit", "-q", "-m", "next"])


def test_relative():
    assert targets.relative("backend", "backend") == "."
    assert targets.relative("backend/svc", "backend") == "svc"
    assert targets.relative("backend/svc", ".") == "backend/svc"
    assert targets.relative("backend/svc", "") == "backend/svc"


def test_nested():
    assert targets.nested([".", "backend", "backend/svc", "backend-2"]) == {
        ".": ["backend", "backend/svc", "backend-2"],
        "backend": ["svc"],
        "backend/svc": [],
        "backend-2": [],
    }


def test_python(repo):
    repo(
        {
            "pyproject.toml": "[project]\n[tool.importlinter]\n",
            "uv.lock": "",
            "packages/a/pyproject.toml": "[project]\n",
            "backend/pyproject.toml": "[tool.poetry]\n",
            "backend/uv.lock": "",
            "backend/svc/.importlinter": "[importlinter]\n",
            "tools/日本語/pyproject.toml": "[project]\n",
            "docs/pyproject.toml": "[tool.ruff]\n",  # [project] などが無いものは割り当てない
        }
    )
    assert targets.python() == {
        "python_projects": ["backend", "."],
        "python_nested": {"backend": [], ".": ["backend"]},
        "python_pyprojects": [
            {"path": "backend/pyproject.toml", "project": "backend", "rel": "."},
            {"path": "packages/a/pyproject.toml", "project": ".", "rel": "packages/a"},
            {"path": "pyproject.toml", "project": ".", "rel": "."},
            {"path": "tools/日本語/pyproject.toml", "project": ".", "rel": "tools/日本語"},
        ],
        "python_importlinters": [
            {"path": "backend/svc/.importlinter", "project": "backend", "rel": "svc"},
            {"path": "pyproject.toml", "project": ".", "rel": "."},
        ],
    }


def test_python_without_lock(repo):
    repo({"app/pyproject.toml": "[project]\n"})
    assert targets.python() == {
        "python_projects": [],
        "python_nested": {},
        "python_pyprojects": [{"path": "app/pyproject.toml", "project": "", "rel": "app"}],
        "python_importlinters": [],
    }


def test_typescript(repo):
    repo(
        {
            "frontend/package.json": PACKAGE_NEXT,
            "frontend/tsconfig.json": "{}",
            "frontend/packages/ui/package.json": "{}",  # 祖先に package.json があるので導入単位にしない
            "frontend/packages/ui/tsconfig.json": "{}",
            "tools/package.json": '{"devDependencies":{"next":"15.0.0"}}',
            "tools/tsconfig.json": "{}",
            "broken/package.json": "not json",
            "broken/tsconfig.json": "{}",
            "only-config/tsconfig.json": "{}",
            "frontend/node_modules/x/package.json": PACKAGE_NEXT,
            "frontend/node_modules/x/tsconfig.json": "{}",
        }
    )
    assert targets.typescript() == {
        "typescript_roots": ["broken", "frontend", "tools"],
        "typescript_tsconfigs": ["broken", "frontend", "frontend/packages/ui", "only-config", "tools"],
        "typescript_nextjs": ["frontend", "tools"],
    }


def test_typescript_root_package(repo):
    repo({"package.json": "{}", "tsconfig.json": "{}", "packages/a/package.json": "{}"})
    result = targets.typescript()
    assert result["typescript_roots"] == ["."]
    assert result["typescript_tsconfigs"] == ["."]


@pytest.mark.parametrize(
    ("package", "expected"),
    [
        ('{"dependencies":{"next":""}}', True),  # jq と同じく、空文字は依存ありとして扱う
        ('{"dependencies":{"next":false}}', False),
        ('{"dependencies":["next"]}', False),
        ("[]", False),
        ("not json", False),
    ],
)
def test_has_dependency(repo, package, expected):
    repo({"package.json": package})
    assert targets.has_dependency(".", "next") is expected


def test_bundle_size(repo):
    root = repo(
        {
            "frontend/package.json": PACKAGE_NEXT,
            "frontend/bun.lock": "",
            "frontend/page.tsx": "1",
            "site/package.json": '{"dependencies":{"astro":"5.0.0"}}',
            "site/bun.lockb": "",
            "no-lock/package.json": PACKAGE_NEXT,  # bun.lock が無いものは計測しない
            "other/package.json": '{"dependencies":{"zod":"3.0.0"}}',
            "other/bun.lock": "",
            "broken/package.json": "not json",
            "broken/bun.lock": "",
        }
    )
    commit(root, {"frontend/page.tsx": "2"})
    assert targets.bundle_size() == {
        "bundle_size_frontends": "true",
        # key は変更がないものも含めた通し番号（frontend が 0、site が 1）
        "bundle_size_targets": [{"dir": "frontend", "pattern": PATTERN_NEXT, "changed": True, "key": "0"}],
    }


def test_bundle_size_at_repo_root(repo):
    """フロントエンドが repo のルートにあると、どのファイルを変えても計測する"""
    root = repo({"package.json": PACKAGE_NEXT, "bun.lock": "", "docs.md": ""})
    commit(root, {"docs.md": "x"})
    result = targets.bundle_size()
    assert result["bundle_size_targets"] == [{"dir": ".", "pattern": PATTERN_NEXT, "changed": True, "key": "0"}]


def test_bundle_size_unchanged(repo):
    root = repo({"frontend/package.json": PACKAGE_NEXT, "frontend/bun.lock": "", "docs.md": ""})
    commit(root, {"docs.md": "x"})
    assert targets.bundle_size() == {"bundle_size_frontends": "true", "bundle_size_targets": []}


def test_bundle_size_without_parent_commit(repo):
    """親コミットが無く git diff が失敗するときは、変更ありとして計測する"""
    repo({"frontend/package.json": PACKAGE_NEXT, "frontend/bun.lock": ""})
    assert targets.bundle_size()["bundle_size_targets"][0]["changed"] is True


def test_bundle_size_none(repo):
    repo({"README.md": ""})
    assert targets.bundle_size() == {"bundle_size_frontends": "false", "bundle_size_targets": []}


def test_terraform(repo):
    repo(
        {
            "main.tf": "",
            "infra/main.tf": "",
            "infra/a.tf": "",  # 同じディレクトリは 1 つにまとめる
            "infra/modules/vpc/main.tf.json": "{}",
            "日本語/main.tf": "",
            "infra/.terraform/modules/x/main.tf": "",
            ".terraform/main.tf": "",
            ".terraform.d/main.tf": "",  # .terraform そのものでなければ対象
            "README.md": "",
        }
    )
    assert targets.terraform() == {"terraform_dirs": [".", ".terraform.d", "infra", "infra/modules/vpc", "日本語"]}


@pytest.mark.parametrize("name", ["a\nb", "a\rb"])
def test_terraform_rejects_line_break(repo, name):
    repo({f"{name}/main.tf": ""})
    with pytest.raises(ValueError, match="改行"):
        targets.terraform()


def test_main_collects_only_enabled(repo, outputs, enable):
    repo({"uv.lock": "", "tsconfig.json": "{}", "main.tf": ""})
    enable("PYTHON")
    assert targets.main() == 0
    assert set(outputs()) == {
        "bundle_size_frontends",
        "bundle_size_targets",
        "python_projects",
        "python_nested",
        "python_pyprojects",
        "python_importlinters",
    }


def test_main_collects_all(repo, outputs, enable):
    repo({"uv.lock": "", "package.json": "{}", "tsconfig.json": "{}", "main.tf": ""})
    enable("PYTHON", "TYPESCRIPT", "TERRAFORM")
    assert targets.main() == 0
    result = parsed(outputs)
    assert result["python_projects"] == ["."]
    assert result["typescript_roots"] == ["."]
    assert result["terraform_dirs"] == ["."]
    assert result["bundle_size_frontends"] is False


def test_main_without_inputs(repo, outputs, monkeypatch):
    """入力の環境変数が無くても、バンドルサイズだけは検出する"""
    for name in ("PYTHON", "TYPESCRIPT", "TERRAFORM"):
        monkeypatch.delenv(name, raising=False)
    repo({"main.tf": ""})
    assert targets.main() == 0
    assert set(outputs()) == {"bundle_size_frontends", "bundle_size_targets"}


def test_main_continues_after_failure(repo, outputs, enable, capsys):
    """1 つの種類が失敗しても残りは出力し、失敗した種類の出力は残さない"""
    repo({"a\nb/main.tf": "", "tsconfig.json": "{}", "uv.lock": ""})
    enable("PYTHON", "TYPESCRIPT", "TERRAFORM")
    assert targets.main() == 1
    result = parsed(outputs)
    assert "terraform_dirs" not in result
    assert result["python_projects"] == ["."]
    assert result["typescript_tsconfigs"] == ["."]
    assert "::error::terraform: 改行を含むパスは検査できません" in capsys.readouterr().out


def test_main_failure_leaves_no_partial_output(repo, outputs, enable, monkeypatch):
    """種類の途中で失敗したら、その種類の出力を 1 つも書かない（python-rule は出力の有無で動くかを決める）"""
    repo({"uv.lock": ""})
    enable("PYTHON")
    original = gha.git_z

    def fail_on_grep(command, *args):
        if command == "grep":
            raise OSError("git grep failed")
        return original(command, *args)

    monkeypatch.setattr(gha, "git_z", fail_on_grep)
    assert targets.main() == 1
    assert not any(name.startswith("python_") for name in outputs())


def test_main_logs_outputs(repo, outputs, enable, capsys):
    repo({"日本語/main.tf": ""})
    enable("TERRAFORM")
    assert targets.main() == 0
    log = capsys.readouterr().out
    assert 'terraform_dirs=["日本語"]\n' in log
    assert "bundle_size_frontends=false\n" in log
    assert outputs()["terraform_dirs"] == '["日本語"]'
