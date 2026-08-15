# Roda o scraper localmente e publica o resultado no GitHub.
# Pensado para ser chamado pelo Agendador de Tarefas do Windows todo dia.
#
# Antes de agendar, rode este script uma vez manualmente no PowerShell para
# confirmar que funciona e que o git não pede senha interativamente
# (veja "Configurar credenciais do git" no README).

$ErrorActionPreference = "Stop"

# Vai para a raiz do repositório (uma pasta acima de scripts/)
Set-Location -Path (Split-Path -Parent $PSScriptRoot)

Write-Host "== $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') Atualizando repositório local =="
git pull --ff-only

Write-Host "== Buscando disponibilidade dos anúncios =="
python scripts\fetch_availability.py

Write-Host "== Publicando dados atualizados =="
git add data/occupancy.json
git diff --quiet --cached
if ($LASTEXITCODE -ne 0) {
    git commit -m "Atualização de ocupação (local) [skip ci]"
    git push
    Write-Host "Publicado com sucesso."
} else {
    Write-Host "Nada novo para commitar."
}
