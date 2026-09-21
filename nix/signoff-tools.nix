# Pin lit/filecheck from PyPI (small); thin wrappers around .github/scripts/.
#
# Intentionally NOT llvmPackages_*.libllvm: native llvm-lit/FileCheck pulls a
# large LLVM closure, couples to nixpkgs LLVM major, and diverges from the
# manylinux CI job (which installs the same PyPI tools). Pin versions here and
# keep CI `--with lit==… --with filecheck==…` in lockstep.

{
  lib,
  python3Packages,
  writeShellApplication,
  symlinkJoin,
  jq,
}:

let
  filecheckVersion = "1.0.6";
  filecheck = python3Packages.buildPythonPackage rec {
    pname = "filecheck";
    version = filecheckVersion;
    pyproject = true;
    src = python3Packages.fetchPypi {
      inherit pname version;
      hash = "sha256-xBxR9zOwv9rmcY3KS5T7C99y+rcPNfxo1iv4rGDWRC0=";
    };
    build-system = [ python3Packages.poetry-core ];
    pythonImportsCheck = [ "filecheck" ];
    meta = {
      description = "Python-native clone of LLVM FileCheck";
      mainProgram = "filecheck";
      homepage = "https://github.com/AntonLydike/filecheck";
      license = lib.licenses.asl20;
    };
  };

  litVersion = "18.1.8";
  lit = python3Packages.buildPythonPackage rec {
    pname = "lit";
    version = litVersion;
    pyproject = true;
    src = python3Packages.fetchPypi {
      inherit pname version;
      hash = "sha256-R8F0oYaUGugw8E3tdqNERgC+Z9Xl+4KCw3g/umccTts=";
    };
    build-system = [ python3Packages.setuptools ];
    doCheck = false;
    meta = {
      description = "LLVM Integrated Tester";
      mainProgram = "lit";
      homepage = "https://llvm.org/docs/CommandGuide/lit.html";
      license = lib.licenses.ncsa;
    };
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
    runtimeInputs = [ lit filecheck jq ];
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
    paths = [ lit filecheck ci-signoff-lit jq ];
    meta.description = "lit ${litVersion} + filecheck ${filecheckVersion}; run via ci-signoff-lit";
  };
in
{
  inherit filecheck filecheckVersion lit litVersion ci-run-ics55-gcd ci-signoff-lit signoff-tools;
}
