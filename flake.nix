{
  description = "A devShell example";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.11";
  };

  outputs =
    { self, nixpkgs, ... }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs {
        inherit system;
      };
    in
    {
      devShells."${system}".default =
        with pkgs;
        mkShell {
          packages = [
            python312
            poetry
            uv
            basedpyright
            ruff
          ];

          shellHook = ''
            uv sync
            source ./.venv/bin/activate
            python --version
          '';
        };
    };
}
