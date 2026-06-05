# KAiTix shell.nix
# Importiert gemeinsame Pakete aus ~/Projekte/nix/common.nix
# Stack: FastAPI + Svelte5 + MySQL
# Nix Single-User auf Ubuntu

{ pkgs ? import <nixpkgs> {} }:
let
  common = import ../../nix/common.nix { inherit pkgs; };
in pkgs.mkShell {
  buildInputs = common.buildInputs;

  shellHook = common.shellHook + ''
    echo "=== KAiTix Dev Shell ==="
    echo "Python: $(python3 --version)"
    echo "Node:   $(node --version)"
    export LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib}/lib:$LD_LIBRARY_PATH"
    echo ""
    echo "Befehle:"
    echo "  source .venv/bin/activate   # venv aktivieren"
    echo "  make dev                    # Backend starten (Port 8003)"
    echo "  make dev-frontend           # Svelte Frontend starten"
    echo "  make dev-all                # Backend + Frontend parallel"
    echo ""
    if [ ! -d ".venv" ]; then
      echo "Tipp: python3 -m venv .venv && source .venv/bin/activate && make install"
    fi
  '';
}
