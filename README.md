# 🔥 Promo Bot — Ofertas de periféricos no Telegram

Bot que monitora a **API de afiliados da AliExpress** e publica automaticamente as melhores ofertas de periféricos de PC (mouse, teclado, headset, SSD...) em um **canal do Telegram** — com link de afiliado rastreável, **cupom**, **frete + prazo de entrega** e **preço total**.

> Roda 24/7 no Azure (plano gratuito), com painel administrativo web para configurar marcas, filtros e limites — sem precisar mexer no código.

---

## ✨ Funcionalidades

| Recurso | O que faz |
|---|---|
| 🛒 **Descoberta de ofertas** | Busca produtos em alta por **categoria** e por **marca** na AliExpress |
| 📉 **Detecção de promoção** | Posta quando o preço cai abaixo do mínimo histórico **ou** quando há desconto forte sobre o preço original |
| 🎟️ **Cupons** | Extrai o cupom do anúncio (fixo ou percentual), aplica **cupons de campanha** do painel e calcula o **preço final** |
| 🚚 **Frete + prazo** | Busca o frete real para o Brasil e mostra o prazo de entrega |
| 💳 **Total no checkout** | Estima o valor final **com impostos** (II + ICMS configuráveis no painel) |
| 🔗 **Link rastreável** | Gera link de afiliado para 100% de rastreamento de comissão |
| 🧹 **Deduplicação** | Agrupa produtos iguais de sellers diferentes por *fingerprint* de título e mantém o mais barato |
| ✅ **Filtros de qualidade** | Só posta itens com avaliação e volume de vendas mínimos; blacklist e whitelist de marcas |
| 🖥️ **Painel web** | Admin em React para gerenciar produtos, marcas, filtros e parâmetros sem deploy |
| 💵 **Painel de vendas** | Pedidos, valor e comissão estimada sincronizados da API de afiliados, com gráfico diário |

---

## 📨 Exemplo de post

```
🔥 PROMOÇÃO ALIEXPRESS

Mouse Gamer Sem Fio Attack Shark X3 PAW3395 Bluetooth

R$ 246,18  (antes R$ 483,13)
✅ R$ 246,18  (-49%)
🎟 Cupom PONTO40: -R$ 28,19 → R$ 217,99
🚚 Frete: R$ 24,00 · chega em ~15 dias
💳 Total estimado no checkout: R$ 291,55 (impostos inclusos)

⭐⭐⭐⭐⭐ 4.8/5  |  📦 5.583 vendidos

👉 Comprar no AliExpress
```

---

## 🏗️ Arquitetura

```
        AliExpress Affiliate API
   (hotproduct · productdetail · shipping · link.generate)
                    │
                    ▼
              monitor.py  ── dedup, filtros de qualidade, detecção de oferta
                    │
        ┌───────────┼────────────────────────────┐
        ▼           ▼                             ▼
  database.py   telegram_bot.py            (enriquece na hora de postar:
  (Postgres/    └─► Canal do Telegram        frete + cupom + total)
  Supabase:         (foto + legenda HTML)
  produtos,
  histórico,
  settings)

   api.py (FastAPI REST)  ◄──►  frontend (React/Vercel) — painel admin
                    │
   Azure App Service  +  GitHub Actions (deploy + keep-alive a cada 5 min)
```

O scheduler roda em uma thread separada e, a cada ciclo, busca produtos, compara com o histórico de preços no Postgres e posta o que passar nos filtros. Como a AliExpress **não oferece push/webhook**, a arquitetura é baseada em **polling**.

---

## 🛠️ Stack

- **Python** — lógica do bot e scheduler
- **FastAPI** — API REST do painel (autenticação por `X-API-Key`)
- **Postgres (Supabase)** — produtos, histórico de preços e configurações
- **AliExpress Affiliate API** — Standard + Advanced (assinatura MD5 das requisições)
- **Telegram Bot API** — publicação no canal (foto + legenda HTML)
- **React + Babel** (sem build) na **Vercel** — painel administrativo
- **Azure App Service** (deploy) + **GitHub Actions** (CI/CD e keep-alive)

---

## ⚙️ Como funciona a decisão de postagem

Um produto é publicado quando passa por **todos** os filtros (keywords de periférico, blacklist, whitelist de marca, qualidade) **e** atende a pelo menos um critério de oferta:

1. **Queda vs mínimo recente** — o preço caiu uma % configurável abaixo do menor valor dos últimos 30 dias (janela móvel); **ou**
2. **Desconto vs preço original** — o item tem um desconto forte sobre o preço de tabela (com exigência extra de avaliação e vendas, já que o desconto reportado pela API é inflado).

Há ainda **cooldown de repost** (não repostar o mesmo item antes de N dias), **limite de posts por ciclo** e um **teto diário** (24h), para manter o canal ativo sem floodar.

> ⚠️ **Mudar a fonte do preço desloca o histórico.** O baseline de "queda" compara o preço de agora com o mínimo dos últimos 30 dias; se a origem do preço mudar (foi o caso ao passar a usar `target_app_sale_price`, ~10-14% menor que o do site), todos os produtos parecem ter caído de uma vez e o bot posta em massa. O teto diário é a rede de segurança; ao fazer uma mudança dessas, considere baixá-lo por um dia.

---

## 🚀 Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (source .venv/bin/activate no Linux/Mac)
pip install -r requirements.txt

cp .env.example .env             # preencha os tokens
python main.py
```

Variáveis principais (ver `.env.example`): `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHANNEL_ID`, `ADMIN_API_KEY`, `ALIEXPRESS_APP_KEY`, `ALIEXPRESS_APP_SECRET`, `ALIEXPRESS_TRACKING_ID`.

A API sempre sobe; o scheduler só inicia se todas as credenciais estiverem presentes.

---

## 🧪 Testes

```bash
pytest
```

---

## 📁 Estrutura

```
main.py            Entry point: sobe a API e (se houver credenciais) o scheduler
monitor.py         Lógica de monitoramento: dedup, filtros, detecção de oferta
aliexpress.py      Cliente da API (assinatura MD5, parser, link/frete/cupom/pedidos)
telegram_bot.py    Formatação e publicação das mensagens no canal
sales.py           Sincroniza pedidos/comissão de afiliado com o banco
database.py        Camada Postgres/Supabase (produtos, histórico, settings, vendas)
api.py             API REST (FastAPI) consumida pelo painel
config.py          Carrega .env, categorias e keywords de periféricos
frontend/          Painel admin (React + Babel, deploy na Vercel)
test_bot.py        Testes (pytest)
```

---

## 📌 Decisões de engenharia

- **Polling, não webhook** — a AliExpress não expõe push; o scheduler verifica em intervalo configurável.
- **Imposto no preço** — o preço retornado pela API vem **sem** os tributos que o AliExpress soma no checkout (Remessa Conforme). O post mostra o **total estimado**: `(preço + frete) × (1 + II) ÷ (1 − ICMS)`, com alíquotas configuráveis no painel — padrão II 0% (zerado por MP em mai/2026 para compras ≤ US$50) e ICMS 17% "por dentro" (17–20% conforme o estado; validado contra checkout real).
- **Preço do app** — quando a API manda `target_app_sale_price` menor que o preço do site, o bot usa o do app (o link de afiliado abre o app e é esse o valor do checkout) e indica no post.
- **Cupons de campanha** — a API não lista cupons ativos (nem de loja); só o `promo_code_info` de cada anúncio. Como os códigos de campanha são globais, o bot **colhe automaticamente** os cupons fixos vistos em qualquer anúncio escaneado e os reaplica nos demais posts por 72h. O painel aceita campanhas adicionais coladas em formato livre (ex: "Código BRT28 — compras acima de R$ 141,00: R$ 28,00 OFF").
- **Vendas** — `sales.py` sincroniza `aliexpress.affiliate.order.listbyindex` a cada ciclo (janela móvel de 60 dias, dois status documentados: pago e confirmado) e grava em `affiliate_orders`. O painel mostra vendas/valor/comissão do período com gráfico diário. Dois detalhes do formato, descobertos contra pedidos reais e não documentados: os valores vêm em **centavos** como inteiro (`3792` = 37,92) e a moeda é a de **liquidação da conta de afiliado** (USD), não a do anúncio. O painel converte para BRL com a cotação do dia (atualizada a cada sync via AwesomeAPI, com fallback ao último valor conhecido). **Compra própria não gera comissão** ([regra do programa](https://portals.aliexpress.com/help.htm?page=help_center)) mas a API a devolve junto das vendas reais, sem campo que a identifique — por isso o painel tem um botão para excluir o pedido dos totais, e a coluna `raw_json` guarda o payload completo para investigar se existe algum campo não documentado que sirva de discriminador. ⚠️ O formato de `start_time`/`end_time` e o campo de paginação da resposta **não são fixados pela documentação oficial** — o código assume um formato comum às APIs Alibaba; rode `python diagnose_api.py` no servidor pra confirmar contra a resposta real antes de confiar em contas com muitos pedidos (paginação além da 1ª página é best-effort).
- **Dedup por fingerprint de título** — o mesmo produto aparece de vários sellers; agrupar por palavras normalizadas e manter o mais barato evita spam de itens repetidos.
- **Enriquecimento sob demanda** — frete e cupom são buscados **só na hora de postar** (1 chamada por produto publicado), economizando requisições.
- **Keep-alive** — no plano gratuito do Azure (sem *Always On*), um cron do GitHub Actions pinga o app a cada 5 min para o scheduler não parar.
