# Flake surface: pins/apps only; ops in nix/, tests in test/lit.
# Requires pkgs.llvmPackages_23 (no version fallbacks).

{ pkgs }:

let
  tools = pkgs.callPackage ./signoff-tools.nix {
    llvmPackages_23 = pkgs.llvmPackages_23;
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
