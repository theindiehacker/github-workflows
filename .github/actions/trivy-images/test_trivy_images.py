import os

import pytest
import trivy_images


@pytest.mark.parametrize(
    ("dockerfile", "refs"),
    [
        ("FROM a AS b\nCOPY --from=build /a /b\nADD --chown=1 --FROM=Tools /a /b\n", ["build", "Tools"]),
        # --mount は from= だけを拾う。命令の引数（echo の後ろ）は参照ではない
        ("RUN --mount=type=bind,from=deps,target=/d --mount=type=cache,target=/c echo --from=api\n", ["deps"]),
        ("COPY /a /b --from=late\nRUN --network=none --from=x true\n", ["x"]),
        ("COPY --from /a /b\n", []),  # = の無いフラグは参照ではない
        # 継続行と、その途中のコメント行・空行
        ("COPY \\\n  # comment\n\n  --from=deps /a /b\n", ["deps"]),
        # escape ディレクティブで継続行の記号が変わる（\ は継続行ではなくなる）
        ("# escape=`\nCOPY `\n  --from=deps /a /b\nCOPY \\\n--from=no /a /b\n", ["deps"]),
        # ディレクティブは先頭だけ。命令の後の「# escape=`」はコメント
        ("FROM a\n# escape=`\nCOPY \\\n  --from=deps /a /b\n", ["deps"]),
        # ヒアドキュメントの中身は命令ではない（<<- は終わりの行の先頭のタブを無視する）
        ("RUN <<EOF\nCOPY --from=a /x /y\nEOF\nCOPY --from=b /x /y\n", ["b"]),
        ("RUN <<-\"END\" cat <<'TWO'\nCOPY --from=a /x /y\n\tEND\nCOPY --from=c /x /y\nTWO\nCOPY --from=d . .", ["d"]),
    ],
)
def test_from_refs(dockerfile, refs):
    assert trivy_images.from_refs(dockerfile) == refs


def test_select_final_stages():
    targets = [
        {"name": "Build", "base": "golang"},
        {"name": "test", "base": "build"},
        {"name": "tools", "base": "alpine"},
        {"base": "alpine"},  # 名前のないステージは --target で選べない
        {"name": "api", "base": "alpine"},
        {"name": "final", "base": "scratch", "default": True},
    ]
    assert trivy_images.select_final_stages("Dockerfile", targets, ["2", "API"]) == [
        {"dockerfile": "Dockerfile", "target": "test"},
        {"dockerfile": "Dockerfile", "target": "final"},
    ]


def test_select_final_stages_only_last():
    targets = [{"name": "a", "base": "alpine"}, {"base": "a", "default": True}]
    assert trivy_images.select_final_stages("x/Dockerfile", targets, []) == [{"dockerfile": "x/Dockerfile"}]


def test_to_matrix():
    item = {"dockerfile": "svc/api/Dockerfile.prod", "target": "web", "build-args": {"A": "b", "N": 1, "F": True}}
    assert trivy_images.to_matrix(item) == {
        "dockerfile": "svc/api/Dockerfile.prod",
        "context": "svc/api",
        "target": "web",
        "build_args": "A=b\nN=1\nF=true",
        "label": "svc/api/Dockerfile.prod (web)",
        "suffix": "svc-api-Dockerfile-prod-web",
    }
    assert trivy_images.to_matrix({"dockerfile": "Dockerfile", "context": "app", "target": None}) == {
        "dockerfile": "Dockerfile",
        "context": "app",
        "target": "",
        "build_args": "",
        "label": "Dockerfile",
        "suffix": "Dockerfile",
    }


def test_find_dockerfiles(tmp_path, monkeypatch):
    for name in [
        "Dockerfile",
        "b/Dockerfile.prod",
        "a b/app.Dockerfile",
        ".hidden/Dockerfile",
        "Dockerfile.dockerignore",
        ".git/Dockerfile",
        "README.md",
    ]:
        (tmp_path / name).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / name).write_text("FROM a\n")
    os.symlink("Dockerfile", tmp_path / "b/Dockerfile")  # symlink は対象外（find -type f と同じ）
    monkeypatch.chdir(tmp_path)
    assert trivy_images.find_dockerfiles() == [
        ".hidden/Dockerfile",
        "Dockerfile",
        "a b/app.Dockerfile",
        "b/Dockerfile.prod",
    ]


def test_find_dockerfiles_non_utf8_path(tmp_path, monkeypatch):
    # UTF-8 でないパスは U+FFFD に置き換える（GITHUB_OUTPUT に書けずに traceback で止まらない）
    os.makedirs(os.path.join(os.fsencode(tmp_path), b"a\xff"))
    (tmp_path / os.fsdecode(b"a\xff") / "Dockerfile").write_text("FROM a\n")
    monkeypatch.chdir(tmp_path)
    assert trivy_images.find_dockerfiles() == ["a\ufffd/Dockerfile"]


def test_final_stages_log_does_not_start_with_path(monkeypatch, capsys):
    # 解析できないときのログの行頭は固定の文言にする（:: で始まるパスがワークフローコマンドにならない）
    monkeypatch.setenv("PATH", "")
    assert trivy_images.final_stages("::stop-commands::x/Dockerfile") == [
        {"dockerfile": "::stop-commands::x/Dockerfile"}
    ]
    assert capsys.readouterr().err.splitlines()[-1].startswith("解析できない Dockerfile: ::stop-commands::x/Dockerfile")
