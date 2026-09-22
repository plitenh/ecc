#!/usr/bin/env bash
# Install Nix in the CI container when missing (manylinux has no Nix by default).
# Single-user / --no-daemon: reliable as root without systemd in GHA containers.
#
# Usage: bash .github/scripts/ci_install_nix.sh

set -euo pipefail

# nix.sh only exports PATH when both HOME and USER are set (non-interactive CI
# often has an empty USER inside the manylinux container).
export HOME="${HOME:-/root}"
export USER="${USER:-$(id -un 2>/dev/null || echo root)}"

nix_profile_bin="${HOME}/.nix-profile/bin"
if [[ -x "${nix_profile_bin}/nix" ]]; then
  export PATH="${nix_profile_bin}:${PATH}"
fi

if command -v nix >/dev/null 2>&1; then
  echo "nix already on PATH: $(command -v nix)"
  nix --version
  exit 0
fi

# Common manylinux gaps for the official installer.
if command -v yum >/dev/null 2>&1; then
  yum install -y curl tar xz gzip bzip2 ca-certificates >/dev/null || true
elif command -v microdnf >/dev/null 2>&1; then
  microdnf install -y curl tar xz gzip bzip2 ca-certificates >/dev/null || true
fi

echo "Installing Nix (no-daemon)…"
# Official script warns on root but still performs a single-user install.
curl -fsSL https://nixos.org/nix/install | sh -s -- --no-daemon --yes

export PATH="${HOME}/.nix-profile/bin:${PATH}"
# shellcheck disable=SC1091
if [[ -f "${HOME}/.nix-profile/etc/profile.d/nix.sh" ]]; then
  # shellcheck source=/dev/null
  . "${HOME}/.nix-profile/etc/profile.d/nix.sh"
  export PATH="${HOME}/.nix-profile/bin:${PATH}"
fi

if ! command -v nix >/dev/null 2>&1; then
  echo "error: nix install finished but nix is not on PATH" >&2
  echo "HOME=$HOME USER=$USER" >&2
  ls -la "${HOME}/.nix-profile/bin" 2>&1 || true
  exit 1
fi

mkdir -p "${HOME}/.config/nix"
conf="${HOME}/.config/nix/nix.conf"
if [[ ! -f "$conf" ]] || ! grep -q 'experimental-features' "$conf"; then
  cat >>"$conf" <<'EOF'
experimental-features = nix-command flakes
EOF
fi

nix --version
