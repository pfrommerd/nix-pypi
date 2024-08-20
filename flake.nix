{
    inputs = {
        attic.url = "github:inductive-research/attic";
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
	atticFlake = attic;

        forEachSupportedSystem = f: nixpkgs.lib.genAttrs supportedSystems (system: f {
            pkgs = import nixpkgs { inherit system; };
	    attic = atticFlake.packages."${system}".attic;
        });
        in {
            devShells = forEachSupportedSystem ({ pkgs, attic }: 
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
                in {
                default = pkgs.mkShell {
                    packages = with pkgs; [ pythonEnv fish attic];
                    # add a PYTHON_PATH to the current directory
                    shellHook = ''
                    export PYTHONPATH=$(pwd)/src:$PYTHONPATH
                    export TMPDIR=/tmp/$USER-nixpy-tmp
                    mkdir -p $TMPDIR
                    exec fish
                    '';
                };
            });
	    packages = forEachSupportedSystem({pkgs, attic}:
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
		in {
		     default=requirements.env.nixpy;
		     nixpy=requirements.env.nixpy;
		     attic=attic;
		}
	    );
        };
}
