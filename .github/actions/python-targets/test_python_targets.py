import json

import python_targets


def test_relative():
    assert python_targets.relative("backend", "backend") == "."
    assert python_targets.relative("backend/svc", "backend") == "svc"
    assert python_targets.relative("backend/svc", ".") == "backend/svc"
    assert python_targets.relative("backend/svc", "") == "backend/svc"


def test_nested():
    assert python_targets.nested([".", "backend", "backend/svc", "backend-2"]) == {
        ".": ["backend", "backend/svc", "backend-2"],
        "backend": ["svc"],
        "backend/svc": [],
        "backend-2": [],
    }


def test_main(repo, outputs):
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
    python_targets.main()
    result = {name: json.loads(value) for name, value in outputs().items()}
    assert result["projects"] == ["backend", "."]
    assert result["nested"] == {"backend": [], ".": ["backend"]}
    assert result["pyprojects"] == [
        {"path": "backend/pyproject.toml", "project": "backend", "rel": "."},
        {"path": "packages/a/pyproject.toml", "project": ".", "rel": "packages/a"},
        {"path": "pyproject.toml", "project": ".", "rel": "."},
        {"path": "tools/日本語/pyproject.toml", "project": ".", "rel": "tools/日本語"},
    ]
    assert result["importlinters"] == [
        {"path": "backend/svc/.importlinter", "project": "backend", "rel": "svc"},
        {"path": "pyproject.toml", "project": ".", "rel": "."},
    ]


def test_main_without_lock(repo, outputs):
    repo({"app/pyproject.toml": "[project]\n"})
    python_targets.main()
    assert outputs() == {
        "projects": "[]",
        "nested": "{}",
        "pyprojects": '[{"path":"app/pyproject.toml","project":"","rel":"app"}]',
        "importlinters": "[]",
    }
