#!/usr/bin/env bash
# GitHub release のアーカイブを SHA-256 を検証して展開し、TOOL を /usr/local/bin に導入する
set -euo pipefail

case "${TOOL}" in
  actionlint)
    repo="rhysd/actionlint"
    asset="actionlint_${VERSION#v}_linux_amd64.tar.gz"
    member="actionlint"
    ;;
  bun)
    repo="oven-sh/bun"
    asset="bun-linux-x64.zip"
    member="bun-linux-x64/bun"
    ;;
  ghalint)
    repo="suzuki-shunsuke/ghalint"
    asset="ghalint_${VERSION#v}_linux_amd64.tar.gz"
    member="ghalint"
    ;;
  gitleaks)
    repo="gitleaks/gitleaks"
    asset="gitleaks_${VERSION#v}_linux_x64.tar.gz"
    member="gitleaks"
    ;;
  shellcheck)
    repo="koalaman/shellcheck"
    asset="shellcheck-${VERSION}.linux.x86_64.tar.xz"
    member="shellcheck-${VERSION}/shellcheck"
    ;;
  zizmor)
    repo="zizmorcore/zizmor"
    asset="zizmor-x86_64-unknown-linux-gnu.tar.gz"
    member="zizmor"
    ;;
  *)
    echo "::error::導入できないツールです: ${TOOL}"
    exit 1
    ;;
esac

archive="${RUNNER_TEMP}/${asset}"
curl -sSfL -o "${archive}" "https://github.com/${repo}/releases/download/${VERSION}/${asset}"

# SHA-256 検証（改ざん・破損を検知）
echo "${SHA256}  ${archive}" | sha256sum -c -

extracted="${RUNNER_TEMP}/setup-${TOOL}"
mkdir -p "${extracted}"
case "${asset}" in
  *.zip) unzip -q -o "${archive}" "${member}" -d "${extracted}" ;;
  *) tar -x -C "${extracted}" -f "${archive}" "${member}" ;;
esac

sudo install -m 755 "${extracted}/${member}" "/usr/local/bin/${TOOL}"
"${TOOL}" --version
