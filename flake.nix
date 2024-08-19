{
    inputs = {
        attic.url = "github:inductive-research/attic";
	attic.inputs.nixpkgs.url = "flake:nixpkgs";
	attic.inputs.flake-utils.url = "github:inductive-research/flake-utils";
    };
    outputs = { self, nixpkgs, attic }:
        let
        # The systems supported for this flake
        supportedSystems = [
            "x86_64-linux" # 64-bit Intel/AMD Linux
            "aarch64-linux" # 64-bit ARM Linux
            "x86_64-darwin" # 64-bit Intel macOS
            "aarch64-darwin" # 64-bit ARM macOS
            "powerpc64le-linux"
        ];

        forEachSupportedSystem = f: nixpkgs.lib.genAttrs supportedSystems (system: f {
            pkgs = import nixpkgs { inherit system; };
        });
        in {
            devShells = forEachSupportedSystem ({ pkgs }: 
                let py = pkgs.python312; 
                    requirements = (import ./requirements.nix) {
                        buildPythonPackage = py.pkgs.buildPythonPackage;
                        fetchurl = pkgs.fetchurl;
                        nixpkgs = pkgs;
                        python = py;
                    };
                    pythonEnv = py.withPackages(
                        ps: [requirements.env.nixpy]
                    );
		    atticCli = attic.packages."${pkgs.system}".attic-static;
                in {
                default = pkgs.mkShell {
                    packages = with pkgs; [ pythonEnv fish atticCli ];
                    # add a PYTHON_PATH to the current directory
                    shellHook = ''
                    export PYTHONPATH=$(pwd)/src:$PYTHONPATH
                    export TMPDIR=/tmp/$USER-nixpy-tmp
                    mkdir -p $TMPDIR
                    exec fish
                    '';
                };
            });
        };
}
