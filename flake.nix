{
    outputs = { self, nixpkgs }:
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
                    pythonEnv = py.withPackages(
                        with py.pkgs; ps: [
                            pip
                            venvShellHook
                        ]
                    );
                in {
                default = pkgs.mkShell {
                    packages = with pkgs; [ pythonEnv fish ];
                    shellHook = ''
                    VENV=.venv
                    if test ! -d $VENV; then
                        python3 -m venv $VENV
                    fi
                    source ./$VENV/bin/activate
                    exec fish
                    '';
                };
            });
        };
}