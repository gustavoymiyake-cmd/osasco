#!/usr/bin/env bash
# Roda o scraper localmente e publica o resultado no GitHub.
# Pensado para ser chamado por cron (Mac/Linux) todo dia.
#
# Antes de agendar, rode este script uma vez manualmente no terminal para
# confirmar que ele funciona e que o git não pede senha interativamente
# (veja "Configurar credenciais do git" no README).

set -euo pipefail

# Vai para a raiz do repositório (uma pasta acima de scripts/)
cd "$(dirname "${BASH_SOURCE[0]}")/.."

echo "== $(date '+%Y-%m-%d %H:%M:%S') Atualizando repositório local =="
git pull --ff-only

echo "== Buscando disponibilidade dos anúncios =="
python3 scripts/fetch_availability.py

echo "== Publicando dados atualizados =="
git add data/occupancy.json
if git diff --quiet --cached; then
  echo "Nada novo para commitar."
else
  git commit -m "Atualização de ocupação (local) [skip ci]"
  git push
  echo "Publicado com sucesso."
fi
