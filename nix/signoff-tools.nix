# lit + FileCheck from llvmPackages_23.llvm. Caller must pass llvmPackages_23.

{
  lit,
  llvmPackages_23,
  writeShellApplication,
  symlinkJoin,
  jq,
}:

let
  llvm = llvmPackages_23.llvm;

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
    meta.description = "lit + FileCheck (llvmPackages_23); run via ci-signoff-lit";
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
}
