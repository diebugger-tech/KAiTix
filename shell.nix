{ pkgs ? import <nixpkgs> {} }:
pkgs.mkShell {
  buildInputs = with pkgs; [
    python312
    mariadb-connector-c
    openssl
    pkg-config
  ];

  shellHook = ''
    export LD_LIBRARY_PATH="${pkgs.mariadb-connector-c}/lib:${pkgs.openssl.out}/lib:$LD_LIBRARY_PATH"
    export PYTHONNOUSERSITE=1
    export PIP_REQUIRE_VIRTUALENV=false
    echo "=== KAiTix Dev Shell ==="
    echo "Python: \$(python3 --version)"
    echo "Tipp: python3 -m venv .venv && source .venv/bin/activate && make install"
  '';
}
