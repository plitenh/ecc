# Flake surface: pins/apps only; ops in .github/scripts, tests in test/lit.
# lit/FileCheck come from llvmPackages_23 (see signoff-tools.nix).

{ pkgs }:

let
  llvmPackages_23 =
    if pkgs ? llvmPackages_23 then pkgs.llvmPackages_23
    else null;
  llvmPackages = pkgs.llvmPackages or pkgs.llvmPackages_21 or pkgs.llvmPackages_19;
  tools = pkgs.callPackage ./signoff-tools.nix {
    inherit llvmPackages_23 llvmPackages;
  };
in
{
  packages = {
    filecheck = tools.filecheck;
    lit = tools.lit;
    signoff-tools = tools.signoff-tools;
    ci-run-ics55-gcd = tools.ci-run-ics55-gcd;
    ci-signoff-lit = tools.ci-signoff-lit;
  };

  apps = {
    ci-signoff-lit = {
      type = "app";
      program = "${tools.ci-signoff-lit}/bin/ci-signoff-lit";
    };
    ci-run-ics55-gcd = {
      type = "app";
      program = "${tools.ci-run-ics55-gcd}/bin/ci-run-ics55-gcd";
    };
  };

  nativeBuildInputs = [
    tools.signoff-tools
    tools.ci-run-ics55-gcd
  ];

  shellHook = ''
    export ECC_REPO_ROOT="$PWD"
  '';
}
