"""検査対象を repo のファイルから規約で検出し、JSON で出力する。

「どのディレクトリが何の単位か」の判定はここに一本化する
（各 job で同じ探索を書くと、片方だけ直したときに規約の判定と検査範囲が食い違う）
"""

import json
import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_lib"))
import gha

# 依存に持つフレームワークと、バンドルサイズを計測するファイル。
# ファイル名のハッシュは伏せない。Turbopack のチャンク名はハッシュだけで、Astro（Vite）は同じ名前のチャンクを
# 複数出すことがあり、伏せると別のファイルが同じ名前になって合計が合わなくなるため
FRAMEWORKS = {"next": ".next/static/chunks/**/*.{js,css}", "astro": "dist/**/*.{js,css}"}


def files(*names: str) -> list[str]:
    """git 管理下の、名前が一致するファイルのパス（コミットされたファイルだけなので、未追跡の node_modules は含まない）"""
    return gha.git_z("ls-files", "--", *(f":(glob)**/{name}" for name in names))


def parent(path: str) -> str:
    return str(PurePosixPath(path).parent)


def has_part(path: str, name: str) -> bool:
    return name in PurePosixPath(path).parts


def has_dependency(directory: str, name: str) -> bool:
    """package.json の依存に name があるか。読めない package.json は依存なしとして飛ばす（判定の失敗でマージを止めない）"""
    try:
        package = json.loads(Path(directory, "package.json").read_text(encoding="utf-8"))
        dependencies = {**(package.get("dependencies") or {}), **(package.get("devDependencies") or {})}
    except (OSError, ValueError, AttributeError, TypeError):
        return False
    return dependencies.get(name) not in (None, False)


def relative(path: str, base: str) -> str:
    """base からの相対パス。base が "." か空（どの uv.lock にも属さない）なら path のまま"""
    return "." if path == base else path.removeprefix(f"{base}/")


def nested(projects: list[str]) -> dict[str, list[str]]:
    """プロジェクトごとの、配下にある別のプロジェクト（そのプロジェクトからの相対パス）"""
    return {
        project: [
            relative(other, project)
            for other in projects
            if other != project and (project == "." or other.startswith(f"{project}/"))
        ]
        for project in projects
    }


def owner(directory: str) -> str:
    """最も近い祖先の uv.lock のディレクトリ。どこにも無ければ空"""
    path = PurePosixPath(directory)
    return next((str(d) for d in (path, *path.parents) if Path(d, "uv.lock").exists()), "")


def assign(paths: list[str]) -> list[dict[str, str]]:
    """設定ファイルを、担当プロジェクト（project）とそこからの相対パス（rel）に割り当てる"""
    result = []
    for path in paths:
        directory = parent(path)
        project = owner(directory)
        result.append({"path": path, "project": project, "rel": relative(directory, project)})
    return result


def python() -> dict[str, object]:
    projects = [parent(path) for path in files("uv.lock")]
    pyprojects = gha.git_z(
        "grep", "-lE", r"^\[(project|tool\.poetry|tool\.uv\.workspace)\]", "--", ":(glob)**/pyproject.toml"
    )
    importlinters = gha.git_z(
        "grep",
        "-lE",
        r"^\[(tool\.)?importlinter\]",
        "--",
        ":(glob)**/pyproject.toml",
        ":(glob)**/setup.cfg",
        ":(glob)**/.importlinter",
    )
    return {
        "python_projects": projects,
        "python_nested": nested(projects),
        "python_pyprojects": assign(pyprojects),
        "python_importlinters": assign(importlinters),
    }


def typescript() -> dict[str, object]:
    packages = {parent(path) for path in files("package.json") if not has_part(path, "node_modules")}
    # 導入単位は最上位の package.json。monorepo（workspaces）ではルート 1 箇所、
    # frontend/ と tools/ のように独立プロジェクトが並ぶ構成では各々が単位になる
    roots = [d for d in sorted(packages) if not any(str(a) in packages for a in PurePosixPath(d).parents)]
    # 型チェック単位は tsconfig.json のあるディレクトリ（workspace ごとの tsconfig.json も個別に検査する）
    tsconfigs = sorted({parent(path) for path in files("tsconfig.json") if not has_part(path, "node_modules")})
    return {
        "typescript_roots": roots,
        "typescript_tsconfigs": tsconfigs,
        "typescript_nextjs": [d for d in tsconfigs if has_dependency(d, "next")],
    }


def bundle_size() -> dict[str, object]:
    found = []
    for path in files("package.json"):
        directory = parent(path)
        pattern = next((p for name, p in FRAMEWORKS.items() if has_dependency(directory, name)), None)
        # bun.lock が無いと compressed-size-action は npm install を使うため、workspace の子などは計測しない
        if pattern and (Path(directory, "bun.lock").exists() or Path(directory, "bun.lockb").exists()):
            # PR がそのディレクトリ配下を変更していなければ、2 回のビルドを省くため計測しない
            diff = gha.run(["git", "diff", "--quiet", "HEAD^1", "HEAD", "--", directory], check=False)
            # key は artifact の名前に使う通し番号（ディレクトリ名から作ると、別のディレクトリが同じ名前になり得るため）
            found.append(
                {"dir": directory, "pattern": pattern, "changed": diff.returncode != 0, "key": str(len(found))}
            )
    return {
        "bundle_size_frontends": "true" if found else "false",
        "bundle_size_targets": [target for target in found if target["changed"]],
    }


def terraform() -> dict[str, object]:
    paths = files("*.tf", "*.tf.json")
    # 検査ではディレクトリを 1 行 1 つで扱うため、改行を含むパスは拒否する
    if any(c in path for path in paths for c in "\r\n"):
        raise ValueError("改行を含むパスは検査できません")
    # .terraform はキャッシュ・vendored モジュール置き場のため対象外
    return {"terraform_dirs": sorted({parent(path) for path in paths if not has_part(parent(path), ".terraform")})}


def main() -> int:
    collectors: list[Callable[[], dict[str, object]]] = [bundle_size]
    for name, collector in (("PYTHON", python), ("TYPESCRIPT", typescript), ("TERRAFORM", terraform)):
        if os.environ.get(name) == "true":
            collectors.append(collector)

    status = 0
    for collector in collectors:
        # 1 つの種類の失敗で、ほかの検査の対象が決まらなくならないようにする。
        # 出力は種類ごとにまとめて書き、失敗した種類の出力を半端に残さない
        try:
            outputs = collector()
        except (OSError, ValueError, subprocess.CalledProcessError) as e:
            gha.error(f"{collector.__name__}: {e}")
            status = 1
            continue
        for name, value in outputs.items():
            gha.set_output(name, value)
            # パスは対象 repo 由来だが、行頭が出力名なのでワークフローコマンドとして解釈されない
            print(f"{name}={value if isinstance(value, str) else gha.to_json(value)}")
    return status


if __name__ == "__main__":
    sys.exit(main())
