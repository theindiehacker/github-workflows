"""PR への push (synchronize) で外れた Claude の承認を、「修正の確認」で戻せるかを決める。

ruleset の dismiss_stale_reviews_on_push で、承認後の push は承認を外す (DISMISSED になる)。
nit を直しただけでも外れるため、変更が Claude のコメント箇所 (前後 MARGIN 行) だけなら、
通常のレビュー (新しい nit が付き、終わらない) ではなく、修正の確認で承認し直す。
それ以外は自動では戻さない (安全側。/code-review で再レビューを頼む)。

mode を GITHUB_OUTPUT に書く:
- full: 通常のレビュー (synchronize 以外)
- verify: 修正の確認。base (前回コメントしたコミット) と dir (comments.json・changes.diff) も書く
- skip: 何もしない

checkout (履歴付き) の後に、python3 -I (カレントディレクトリにある対象 repo のモジュールを import しない) で動かす。
"""

import json
import os
import re
import subprocess
from pathlib import Path

BOT = "claude[bot]"
# 判定のレビュー。インラインコメントの COMMENTED は判定ではないため除く
VERDICTS = {"APPROVED", "CHANGES_REQUESTED", "DISMISSED"}
SHA = re.compile(r"[0-9a-f]{40}")
HUNK = re.compile(r"@@ -(\d+)(?:,(\d+))? \+\d+(?:,\d+)? @@")
# git diff の拡張・変換を使わない (対象 repo の設定で外部コマンドを動かさない)
DIFF = ["diff", "--no-ext-diff", "--no-textconv", "--no-renames"]


def annotate(level: str, message: str) -> None:
    """注釈を出す。対象 repo 由来のパスが入るため、ワークフローコマンドとしてエスケープする"""
    message = message.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    print(f"::{level}::{message}", flush=True)


def output(**values: str) -> None:
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
        f.writelines(f"{key}={value}\n" for key, value in values.items())


def skip(reason: str) -> None:
    annotate(
        "notice",
        f"{reason}ため、承認を自動では戻しません。再レビューは /code-review で依頼してください",
    )
    output(mode="skip")


def gh_list(path: str) -> list[dict]:
    """GitHub API の一覧を全ページ取り、古い順に並べる"""
    # 引数はシェルを通さずに渡す。S603 / S607 は CI の --select S でだけ有効になり、
    # 既定の ruff check はその noqa を不要 (RUF100) とするため、RUF100 も並べる
    result = subprocess.run(  # noqa: S603, RUF100
        ["gh", "api", "--paginate", "--slurp", path],  # noqa: S607, RUF100
        check=True,
        capture_output=True,
        text=True,
    )
    items = [item for page in json.loads(result.stdout) for item in page]
    return sorted(items, key=lambda item: item["id"])


def git(*args: str) -> str:
    return subprocess.run(  # noqa: S603, RUF100
        ["git", *args],  # noqa: S607, RUF100
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def by_bot(item: dict) -> bool:
    return (item.get("user") or {}).get("login") == BOT


def regions_of(comments: list[dict]) -> dict[str, list[tuple[float, float]]]:
    """コメント箇所 (コメントしたコミットでの行の範囲) をファイルごとに返す。ファイル単位のコメントはファイル全体"""
    regions: dict[str, list[tuple[float, float]]] = {}
    for c in comments:
        if c.get("subject_type") == "file":
            regions.setdefault(c["path"], []).append((1, float("inf")))
        # LEFT は base 側 (削除した行) の行番号で、コメントしたコミットの行と比べられない
        elif c.get("original_line") and c.get("side", "RIGHT") == "RIGHT":
            end = c["original_line"]
            regions.setdefault(c["path"], []).append(
                (c.get("original_start_line") or end, end)
            )
    return regions


def outside(
    base: str, regions: dict[str, list[tuple[float, float]]], margin: int
) -> str | None:
    """base から HEAD までの変更のうち、コメント箇所の外にある最初の場所を返す。全部が内側なら None"""
    fields = git(*DIFF, "--name-status", "-z", base, "HEAD").split("\0")
    for status, path in zip(fields[0::2], fields[1::2]):
        # 追加・削除・種別の変更は、コメント箇所の修正ではない
        if status != "M":
            return f"{status} {path}"
        if path not in regions:
            return path
        for line in git(
            *DIFF, "-U0", base, "HEAD", "--", f":(literal){path}"
        ).splitlines():
            if line.startswith(("Binary files ", "old mode ", "new mode ")):
                return path
            if not (m := HUNK.match(line)):
                continue
            start, count = int(m[1]), int(m[2] or 1)
            # count が 0 なら start 行の後ろへの挿入
            first, last = (
                (start, start + 1) if count == 0 else (start, start + count - 1)
            )
            if not any(
                s - margin <= first and last <= e + margin for s, e in regions[path]
            ):
                return f"{path}:{first}"
    return None


def main() -> None:
    if os.environ["EVENT_ACTION"] != "synchronize":
        output(mode="full")
        return

    pulls = f"repos/{os.environ['GITHUB_REPOSITORY']}/pulls/{os.environ['PR_NUMBER']}"
    verdicts = [
        r for r in gh_list(f"{pulls}/reviews") if by_bot(r) and r["state"] in VERDICTS
    ]
    if not verdicts or verdicts[-1]["state"] != "DISMISSED":
        state = verdicts[-1]["state"] if verdicts else "なし"
        skip(f"Claude の承認が外れていない (最後の判定: {state})")
        return

    # 返信 (@claude の応答など) は指摘ではないため除く
    comments = [
        c
        for c in gh_list(f"{pulls}/comments")
        if by_bot(c) and not c.get("in_reply_to_id")
    ]
    if not comments:
        skip("Claude のコメントが無い")
        return

    base = comments[-1]["original_commit_id"]
    if not SHA.fullmatch(base or ""):
        skip("前回コメントしたコミットが分からない")
        return
    ancestor = subprocess.run(  # noqa: S603, RUF100
        ["git", "merge-base", "--is-ancestor", base, "HEAD"],  # noqa: S607, RUF100
        capture_output=True,
        check=False,
    )
    if ancestor.returncode != 0:
        skip("前回コメントしたコミットが PR の履歴に無い (force-push など)")
        return

    latest = [c for c in comments if c["original_commit_id"] == base]
    if where := outside(base, regions_of(latest), int(os.environ["MARGIN"])):
        skip(f"コメント箇所以外の変更 ({where}) がある")
        return

    out = Path(os.environ["RUNNER_TEMP"]) / "claude-recheck"
    out.mkdir(parents=True, exist_ok=True)
    keys = ("path", "subject_type", "original_start_line", "original_line", "body")
    (out / "comments.json").write_text(
        json.dumps(
            [{k: c.get(k) for k in keys} for c in latest], ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )
    (out / "changes.diff").write_text(git(*DIFF, "-U5", base, "HEAD"), encoding="utf-8")
    output(mode="verify", base=base, dir=str(out))


if __name__ == "__main__":
    main()
