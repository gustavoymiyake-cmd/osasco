# Painel de Ocupação · Airbnb

Portal estático (GitHub Pages) para acompanhar quantos dias das próximas
**12 semanas** estão reservados/bloqueados em anúncios públicos do Airbnb,
com atualização automática diária via GitHub Actions.

⚠️ **Importante antes de usar**
Como você não é anfitrião desses imóveis, a única fonte de dados possível é
o calendário público exibido na própria página do anúncio — não existe API
oficial do Airbnb para isso. O script (`scripts/fetch_availability.py`) faz
uma requisição HTTP simples à página e extrai o calendário embutido no HTML.
Isso é **scraping de dados públicos**, não invasivo (não usa login, não
acessa nada privado), mas:
- o Airbnb pode mudar o layout da página a qualquer momento, quebrando a
  extração — quando isso acontece, o anúncio aparece no painel com status
  de erro em vez de travar os outros;
- acesso automatizado e repetido pode, em tese, esbarrar nos Termos de
  Serviço do Airbnb — isso é uma decisão sua enquanto usuário da ferramenta;
- não é possível distinguir com certeza "reservado" de "bloqueado
  manualmente pelo anfitrião" — o script trata ambos como "indisponível".

## O que tem aqui

```
index.html                        → o painel (GitHub Pages serve isso)
listings.json                     → lista de anúncios monitorados (editada pelo painel)
data/occupancy.json               → dados calculados, gerados automaticamente
scripts/fetch_availability.py     → scraper que roda no GitHub Actions
.github/workflows/daily-update.yml→ agendamento diário (cron)
```

## Passo a passo para publicar

### 1. Criar o repositório
Crie um repositório novo no GitHub (pode ser privado ou público) e suba
todos estes arquivos para a branch `main`.

```bash
git init
git add .
git commit -m "Painel de ocupação inicial"
git branch -M main
git remote add origin https://github.com/SEU-USUARIO/SEU-REPO.git
git push -u origin main
```

### 2. Ativar o GitHub Pages
No repositório: **Settings → Pages → Build and deployment → Source:
"Deploy from a branch"** → branch `main`, pasta `/ (root)`. Salve. Em
alguns minutos o painel estará em `https://SEU-USUARIO.github.io/SEU-REPO/`.

### 3. Permitir que a Action grave no repositório
Em **Settings → Actions → General → Workflow permissions**, marque
**"Read and write permissions"**. Sem isso o commit diário automático falha.

### 4. Gerar um token de acesso pessoal (para adicionar imóveis pelo painel)
Vá em **Settings da sua conta → Developer settings → Personal access
tokens → Fine-grained tokens → Generate new token**:
- **Repository access:** apenas este repositório.
- **Permissions:** `Contents` → Read and write; `Actions` → Read and write
  (só é necessário se quiser usar o botão "Forçar atualização agora").
- Copie o token gerado (começa com `github_pat_...`).

No painel, clique em **Configurações**, preencha usuário, nome do
repositório, branch (`main`) e cole o token. Ele fica salvo **só no seu
navegador** (localStorage) — nunca é enviado para nenhum servidor além da
API do próprio GitHub.

### 5. Adicionar imóveis
Clique em **"+ Adicionar imóvel"**, cole o link do anúncio (ex:
`https://www.airbnb.com.br/rooms/12345678`) e um apelido opcional. Isso
grava direto no `listings.json` do repositório via API do GitHub.

### 6. Primeira atualização
A Action roda todo dia às 06:00 UTC (03:00 em Brasília — ajuste o `cron`
em `.github/workflows/daily-update.yml` se quiser outro horário). Para não
esperar até o dia seguinte, use o botão **"Forçar atualização agora"** nas
Configurações do painel, ou vá em **Actions → "Atualização diária de
ocupação" → Run workflow** manualmente.

## Como a ocupação é calculada

Para cada anúncio, o script olha os **84 dias a partir de hoje** (12
semanas) e, para cada dia em que o Airbnb informa disponibilidade, marca
como "reservado/bloqueado" ou "livre". A taxa de ocupação exibida é:

```
dias reservados ÷ dias com dado conhecido
```

Dias sem informação de calendário (fora do alcance que o Airbnb expõe, por
exemplo) não entram na conta.

## Rodando localmente para testar o scraper

```bash
pip install requests beautifulsoup4
python scripts/fetch_availability.py
```

Isso lê `listings.json` e regrava `data/occupancy.json` com os dados mais
recentes — útil para conferir se a extração ainda está funcionando antes de
depender só do agendamento automático.
