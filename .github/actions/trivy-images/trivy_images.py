"""security.yml の scan-image でビルドしてスキャンするイメージを決め、matrix に渡す JSON 配列を出力 images に書く。

- .github/trivy-image.yml があれば、列挙された image だけをビルドする
- 無ければ Dockerfile / Dockerfile.* / *.Dockerfile を自動検出し、置き場所を build context に、
  最終ステージ (ほかのステージから FROM・COPY --from・RUN --mount の from= で使われないステージ) をすべて target にする。
  最後のステージ (ビルドの既定) は、参照の解釈によらず必ず含める
"""

import json
import os
import re
import stat
import subprocess
import sys
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "_lib"))
import gha

MANIFESTS = [".github/trivy-image.yml", ".github/trivy-image.yaml"]
DIRECTIVE = re.compile(r"#\s*([A-Za-z]+)\s*=\s*(\S*)", re.ASCII)
BLANK_OR_COMMENT = re.compile(r"\s*(#|$)", re.ASCII)
HEREDOC = re.compile(r"""<<(-?)["']?([A-Za-z0-9_]+)["']?(.*)""")


def from_refs(text: str) -> list[str]:
    """Dockerfile の COPY・ADD の --from= と、RUN の --mount の from= に書かれた参照 (ステージ名か番号)。

    命令の引数の文字列 (RUN echo --from=api など) を参照と取り違えないよう、BuildKit と同じく
    パーサーディレクティブの escape・コメント行・継続行・ヒアドキュメントを解釈し、命令の先頭のフラグだけを見る
    """
    refs: list[str] = []
    escape_char = "\\"
    directives = True
    instruction = ""
    heredocs: list[str] = []
    lines = text.split("\n")
    if lines[-1] == "":
        lines.pop()
    for line in lines:
        # ヒアドキュメントの中身は命令ではない。終わりの行まで読み飛ばす (<<- は終わりの行の先頭のタブを無視する)
        if heredocs:
            end = heredocs[0]
            if end.startswith("-"):
                end, line = end[1:], line.lstrip("\t")
            if line == end:
                heredocs.pop(0)
            continue
        # パーサーディレクティブは先頭の「# key=value」の行だけ。escape で継続行の記号が変わる
        if directives and (m := DIRECTIVE.match(line)):
            if m[1].lower() == "escape":
                escape_char = m[2][:1] or escape_char
            continue
        directives = False
        # コメント行と空行 (継続行の途中も含む) は、BuildKit と同じく命令に含めない
        if BLANK_OR_COMMENT.match(line):
            continue
        if re.search(re.escape(escape_char) + r"\s*$", line, re.ASCII):
            instruction += line[: line.rindex(escape_char)] + " "
            continue
        # 単語の区切りは空白とタブだけ（シェルの read -a と同じ）
        words = [word for word in re.split(r"[ \t]+", instruction + line) if word]
        instruction = ""
        if words[0].upper() not in ("COPY", "ADD", "RUN"):
            continue
        for word in words[1:]:
            if not word.startswith("--"):
                break
            flag, sep, value = word.partition("=")
            if sep and flag.lower() == "--from":
                refs.append(value)
            elif sep and flag.lower() == "--mount":
                refs += [option[len("from=") :] for option in value.split(",") if option.startswith("from=")]
        # この命令が始めるヒアドキュメント (<<EOF・<<-EOF・<<"EOF" など。1 つの命令に複数書ける)
        rest = " ".join(words)
        while m := HEREDOC.search(rest):
            heredocs.append(m[1] + m[2])
            rest = m[3]
    return refs


def select_final_stages(dockerfile: str, targets: list[dict], refs: list[str]) -> list[dict]:
    """buildx の --call=targets の結果と、--from= の参照から、最終ステージを {dockerfile, target} で返す。

    参照はステージ名か番号 (外部イメージの参照はどのステージにも当たらない)。
    最終ステージが最後のステージだけなら、target を付けない (ビルドの既定と同じで、job 名も変わらない)
    """
    used = {(t.get("base") or "").lower() for t in targets} | {ref.lower() for ref in refs}
    stages = [
        {"id": str(i), "name": (t.get("name") or "").lower() or None, "default": t.get("default", False)}
        for i, t in enumerate(targets)
    ]
    # 名前でも番号でも参照されていないステージが最終ステージ。名前のないステージは --target で選べないので除く
    others = [s for s in stages if not s["default"] and s["name"] and s["name"] not in used and s["id"] not in used]
    if not others:
        return [{"dockerfile": dockerfile}]
    # 最後のステージは、参照されていると読めても必ず入れる (Dockerfile がスキャンから丸ごと外れないようにする)
    last = stages[-1]["name"] or ""
    return [{"dockerfile": dockerfile, "target": s["name"]} for s in others] + [
        {"dockerfile": dockerfile, "target": last}
    ]


def final_stages(dockerfile: str) -> list[dict]:
    """Dockerfile の最終ステージ。ステージと FROM の参照元は buildx の --call=targets で取る"""
    context = str(PurePosixPath(dockerfile).parent)
    args = ["docker", "buildx", "build", "--call=targets,format=json", "--progress=quiet"]
    proc = gha.run([*args, "--file", dockerfile, context], check=False, stdout=subprocess.PIPE)
    if proc.returncode != 0:
        # 解析できない Dockerfile は target を付けずに入れ、ビルドのエラーをその image の scan-image に出す
        # パスは対象 repo 由来のため、改行で次の行をワークフローコマンドにされないようエスケープする
        print(f"{gha.escape(dockerfile)}: ステージを解析できないため、target を付けずにビルドする", file=sys.stderr)
        return [{"dockerfile": dockerfile}]
    text = Path(dockerfile).read_text(encoding="utf-8", errors="replace")
    return select_final_stages(dockerfile, json.loads(proc.stdout).get("targets") or [], from_refs(text))


def is_dockerfile(name: str) -> bool:
    """Dockerfile / Dockerfile.* / *.Dockerfile か。Dockerfile.dockerignore（buildx の Dockerfile 別 ignore ファイル）は除く"""
    patterns = ("Dockerfile", "Dockerfile.*", "*.Dockerfile")
    return any(fnmatchcase(name, p) for p in patterns) and not fnmatchcase(name, "*.dockerignore")


def find_dockerfiles() -> list[str]:
    """作業ツリーの Dockerfile（.git の下と symlink は除く。find . -path ./.git -prune -o -type f と同じ）"""
    found = []
    for root, dirs, files in os.walk("."):
        if root == ".":
            dirs[:] = [d for d in dirs if d != ".git"]
        for name in filter(is_dockerfile, files):
            path = os.path.join(root, name)
            if stat.S_ISREG(os.lstat(path).st_mode):
                found.append(path.removeprefix("./"))
    return sorted(found)


def or_default(value: object, default: object) -> object:
    """jq の // と同じく、null と false を default にする"""
    return default if value is None or value is False else value


def to_matrix(item: dict) -> dict:
    """matrix で使う形に整える（label は job 名、suffix は cache scope / artifact 名に使う）"""
    dockerfile = or_default(item.get("dockerfile"), "")
    target = or_default(item.get("target"), "")
    build_args = or_default(item.get("build-args"), {})
    context = dockerfile.rpartition("/")[0] or "."
    with_target = target != ""
    return {
        "dockerfile": dockerfile,
        "context": or_default(item.get("context"), context),
        "target": target,
        "build_args": "\n".join(
            f"{key}={value if isinstance(value, str) else gha.to_json(value)}" for key, value in build_args.items()
        ),
        "label": dockerfile + (f" ({target})" if with_target else ""),
        "suffix": re.sub(r"[/.]", "-", dockerfile + (f"-{target}" if with_target else "")),
    }


def main() -> None:
    manifest = next((m for m in MANIFESTS if Path(m).is_file()), "")
    # 1. ビルドするイメージの一覧を作る（マニフェスト優先。無ければ Dockerfile を自動検出）
    if manifest:
        print(f"{manifest} に列挙されたイメージをスキャンする")
        out = gha.run(["yq", "--output-format=json", ".images // []", manifest], stdout=subprocess.PIPE).stdout
        items = json.loads(out)
    else:
        print("Dockerfile を自動検出し、最終ステージをすべてスキャンする")
        items = [stage for dockerfile in find_dockerfiles() for stage in final_stages(dockerfile)]

    # 2. matrix で使う形に整える
    images = [to_matrix(item) for item in items]

    # 3. マニフェストの記載ミスは、ビルドを待たずにここで落とす
    for image in images:
        if not image["dockerfile"] or not Path(image["dockerfile"]).is_file():
            gha.error(f"{manifest} の images[].dockerfile が未指定か、ファイルが存在しません: '{image['dockerfile']}'")
            sys.exit(1)

    gha.set_output("images", images)
    print(f"スキャン対象: {gha.to_json(images)}")


if __name__ == "__main__":
    main()
