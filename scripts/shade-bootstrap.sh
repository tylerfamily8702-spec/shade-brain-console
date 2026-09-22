#!/usr/bin/env bash
# Provisioning script for a fresh/rebuilt umbra host.
# Run once, before starting the containers in ../config/.
#
# What it does:
#   1. creates a dedicated 'shade' system user (so the stack doesn't run
#      as your personal account)
#   2. sets up the vault directory structure under the shade user's home
#   3. installs Ollama and the Python dependencies Cognee (memory layer)
#      needs
#   4. runs a smoke test at the end to confirm the pieces came up clean
#
# Usage:
#   sudo bash scripts/shade-bootstrap.sh

set -euo pipefail

echo "[1/4] creating shade system user..."
id -u shade &>/dev/null || useradd -r -m -s /usr/sbin/nologin shade

echo "[2/4] setting up vault directory structure..."
mkdir -p /home/shade/vault/{entities,functions,logs}
chown -R shade:shade /home/shade/vault

echo "[3/4] installing ollama + cognee deps..."
curl -fsSL https://ollama.com/install.sh | sh
sudo -u shade python3 -m pip install --user cognee

echo "[4/4] running smoke test..."
systemctl is-active --quiet ollama && echo "ollama: OK" || echo "ollama: FAILED"
curl -sf http://localhost:11434/api/tags >/dev/null && echo "ollama API: OK" || echo "ollama API: FAILED"

echo "bootstrap complete."
