"""uv.lock のあるディレクトリ（プロジェクト）を列挙し、pyproject.toml と import-linter の設定を担当プロジェクトに割り当てる。

「どのディレクトリがどの uv.lock に属するか」の判定はここに一本化する
（各 job で同じ探索を書くと、片方だけ直したときに規約の判定と検査範囲が食い違う）
"""

import sys
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_lib"))
import gha


def relative(path: str, base: str) -> str:
    """base からの相対パス。base が "." か空（どの uv.lock にも属さない）なら path のまま"""
    if path == base:
        return "."
    prefix = f"{base}/"
    return path.removeprefix(prefix)


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
        directory = str(PurePosixPath(path).parent)
        project = owner(directory)
        result.append({"path": path, "project": project, "rel": relative(directory, project)})
    return result


def main() -> None:
    projects = [str(PurePosixPath(p).parent) for p in gha.git_z("ls-files", "--", ":(glob)**/uv.lock")]
    gha.set_output("projects", projects)
    gha.set_output("nested", nested(projects))

    pyprojects = gha.git_z(
        "grep", "-lE", r"^\[(project|tool\.poetry|tool\.uv\.workspace)\]", "--", ":(glob)**/pyproject.toml"
    )
    gha.set_output("pyprojects", assign(pyprojects))

    importlinters = gha.git_z(
        "grep",
        "-lE",
        r"^\[(tool\.)?importlinter\]",
        "--",
        ":(glob)**/pyproject.toml",
        ":(glob)**/setup.cfg",
        ":(glob)**/.importlinter",
    )
    gha.set_output("importlinters", assign(importlinters))


if __name__ == "__main__":
    main()
