# flake-parts module: signoff lit packages/apps.
# See https://flake.parts/options/flake-parts-modules.html (imports into mkFlake).

{ ... }:
{
  perSystem =
    { pkgs, ... }:
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
        run-design = tools.run-design;
        ci-signoff-lit = tools.ci-signoff-lit;
      };

      apps = {
        ci-signoff-lit = {
          type = "app";
          program = "${tools.ci-signoff-lit}/bin/ci-signoff-lit";
        };
        run-design = {
          type = "app";
          program = "${tools.run-design}/bin/run-design";
        };
      };
    };
}
