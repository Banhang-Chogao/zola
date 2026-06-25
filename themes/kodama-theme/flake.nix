{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
    oxalica.url = "github:oxalica/rust-overlay";
    oxalica.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs = { nixpkgs, oxalica, ... }:
    let
      system = "x86_64-linux";
      pkgs = import nixpkgs {
        inherit system;
        overlay.default = [ oxalica.overlay ];
        config.allowUnfree = true;
      };

    in {

      packages.x86_64-linux = {
        website = pkgs.stdenv.mkDerivation rec {
          version = "0.0.1";
          name = "kodama-theme-${version}";
          src = pkgs.lib.sourceByRegex ./. [
            "^content"
            "^content/.*"
            "^static"
            "^static/.*"
            "^templates"
            "^templates/.*"
            "^templates/macros"
            "^templates/macros.*"
            "^themes"
            "^themes/.*"
            "^styles"
            "^styles/.*\.css"
            "tailwind.config.js"
            "config.toml"
          ];

          buildInputs = [
            pkgs.zola
            pkgs.nodePackages.npm
            pkgs.tailwindcss_4
          ];

          checkPhase = ''
            zola check
          '';

          buildPhase = ''
            tailwindcss -i styles/styles.css -o static/styles/style.css
          '';

          base-url = "https://adfaure.github.io/kodama-theme";
          installPhase = ''
            zola build -o $out --base-url ${base-url}
          '';
        };
      };
      # Use `nix develop` to activate the shell
      devShell.x86_64-linux = pkgs.mkShell {
        buildInputs = with pkgs; [
          zola
          pkgs.tailwindcss_4
        ];
      };
    };
}
