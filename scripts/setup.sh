#!/bin/bash
set -e
echo "=== Setup pkm-vault-app ==="

if ! command -v uv &> /dev/null; then
    echo "uv non trouvé. Installation..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.local/bin/env
fi

uv sync --dev
cp config.yaml.example config.yaml

echo ""
echo "Setup terminé. Éditer config.yaml :"
echo "  vault:"
echo "    data_path: \"../pkm-vault-data\""
