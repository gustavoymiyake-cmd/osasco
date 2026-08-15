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

Abra o painel publicado (`https://SEU-USUARIO.github.io/SEU-REPO/`) e
clique no botão **"Configurações"** no canto superior direito. Vai abrir
uma janela com quatro campos — preencha cada um assim:

| Campo no painel | O que colocar |
|---|---|
| Usuário/organização do GitHub | seu usuário do GitHub (ex: `joaosilva`) |
| Nome do repositório | o nome que você deu ao repositório (ex: `airbnb-occupancy-tracker`) |
| Branch | `main` (ou o nome da branch que você usou no passo 1) |
| Token de acesso pessoal | o token `github_pat_...` gerado no passo 4 |

Depois clique em **"Salvar"**. Os valores ficam guardados **só no seu
navegador** (localStorage) — nunca são enviados para nenhum servidor além
da API do próprio GitHub. Se você abrir o painel em outro navegador ou
computador, vai precisar preencher esses campos de novo lá também.

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

## Quando um anúncio dá erro ("Não encontrei dados de calendário...")

O Airbnb muda o layout das páginas com frequência, então isso pode
acontecer. Toda vez que a leitura de um anúncio falha, o script salva o
HTML bruto recebido em `debug/` e o workflow publica esse conteúdo como um
**artefato** do run (não fica commitado no repositório):

1. No GitHub, vá em **Actions** → abra o run mais recente do workflow
   "Atualização diária de ocupação".
2. Role até o final da página do run e baixe o artefato **debug-html**.
3. Abra o arquivo `.html` de dentro do zip.

Esse arquivo mostra exatamente o que o script recebeu do Airbnb — se for
uma página de captcha/verificação (bloqueio anti-bot) ou uma página normal
mas sem os dados de calendário embutidos (layout mudou, ou os dados agora
só carregam via JavaScript no navegador). Nesses dois casos o ajuste do
parser precisa ser feito olhando o HTML real, então vale enviar esse
arquivo (ou trechos dele) para quem for dar manutenção no script.

## Rodando localmente para testar o scraper

```bash
pip install requests beautifulsoup4
python scripts/fetch_availability.py
```

Isso lê `listings.json` e regrava `data/occupancy.json` com os dados mais
recentes — útil para conferir se a extração ainda está funcionando antes de
depender só do agendamento automático.
