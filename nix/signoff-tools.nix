# FileCheck from llvmPackages_23.llvm (tools output of libllvm); lit from nixpkgs
# `lit` (upstream LLVM Integrated Tester — llvm-lit is not shipped on the
# llvmPackages_23.llvm bin output in current nixpkgs).
#
# CI (manylinux) installs Nix then nix-shells these two + jq —
# see .github/scripts/ci_install_nix.sh and ci_signoff_lit_nix.sh.
# Do not install the PyPI lit/filecheck packages in CI.

{
  lib,
  lit,
  llvmPackages_23 ? null,
  llvmPackages ? null,
  writeShellApplication,
  symlinkJoin,
  jq,
}:

let
  llvmPkgs =
    if llvmPackages_23 != null then llvmPackages_23
    else if llvmPackages != null then llvmPackages
    else throw "signoff-tools: pass llvmPackages_23 or llvmPackages";

  # FileCheck lives on the tools output (`.llvm`), not bare `.libllvm`.
  llvm = llvmPkgs.llvm;

  filecheck = writeShellApplication {
    name = "filecheck";
    runtimeInputs = [ llvm ];
    text = ''
      exec FileCheck "$@"
    '';
  };

  exportCsvSh = ../.github/scripts/export_signoff_csv.sh;
  materializeSh = ../.github/scripts/materialize_signoff_workspace.sh;
  ciRunSh = ../.github/scripts/ci_run_ics55_gcd.sh;
  ciSignoffLitSh = ../.github/scripts/ci_signoff_lit.sh;

  ci-run-ics55-gcd = writeShellApplication {
    name = "ci-run-ics55-gcd";
    text = ''
      root="''${ECC_REPO_ROOT:-$PWD}"
      export ECC_REPO_ROOT="$root"
      exec bash ${ciRunSh} "$@"
    '';
  };

  ci-signoff-lit = writeShellApplication {
    name = "ci-signoff-lit";
    runtimeInputs = [
      lit
      filecheck
      jq
    ];
    text = ''
      root="''${ECC_REPO_ROOT:-$PWD}"
      export ECC_REPO_ROOT="$root"
      export ECC_EXPORT_SIGNOFF_CSV="''${ECC_EXPORT_SIGNOFF_CSV:-${exportCsvSh}}"
      export ECC_MATERIALIZE_READY="''${ECC_MATERIALIZE_READY:-${materializeSh}}"
      export FILECHECK="''${FILECHECK:-filecheck}"
      export LIT="''${LIT:-lit}"
      if [ -x "$root/.venv/bin/python" ]; then
        export PYTHON="$root/.venv/bin/python"
      fi
      exec bash ${ciSignoffLitSh} "$@"
    '';
  };

  signoff-tools = symlinkJoin {
    name = "ecc-signoff-tools";
    paths = [
      lit
      filecheck
      ci-signoff-lit
      jq
    ];
    meta.description = "nixpkgs lit + FileCheck (llvmPackages_23.llvm); run via ci-signoff-lit";
  };
in
{
  inherit
    filecheck
    lit
    ci-run-ics55-gcd
    ci-signoff-lit
    signoff-tools
    ;
  llvmPackages = llvmPkgs;
}
