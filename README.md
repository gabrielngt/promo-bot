# 🔥 Promo Bot — Ofertas de periféricos no Telegram

Bot que monitora a **API de afiliados da AliExpress** e publica automaticamente as melhores ofertas de periféricos de PC (mouse, teclado, headset, SSD...) em um **canal do Telegram** — com link de afiliado rastreável, **cupom**, **frete + prazo de entrega** e **preço total**.

> Roda 24/7 no Azure (plano gratuito), com painel administrativo web para configurar marcas, filtros e limites — sem precisar mexer no código.

---

## ✨ Funcionalidades

| Recurso | O que faz |
|---|---|
| 🛒 **Descoberta de ofertas** | Busca produtos em alta por **categoria** e por **marca** na AliExpress |
| 📉 **Detecção de promoção** | Posta quando o preço cai abaixo do mínimo histórico **ou** quando há desconto forte sobre o preço original |
| 🎟️ **Cupons** | Extrai o cupom do anúncio (código + valor) e calcula o **preço final com cupom** |
| 🚚 **Frete + prazo** | Busca o frete real para o Brasil e mostra **total (produto + frete)** e o prazo de entrega |
| 🔗 **Link rastreável** | Gera link de afiliado para 100% de rastreamento de comissão |
| 🧹 **Deduplicação** | Agrupa produtos iguais de sellers diferentes por *fingerprint* de título e mantém o mais barato |
| ✅ **Filtros de qualidade** | Só posta itens com avaliação e volume de vendas mínimos; blacklist e whitelist de marcas |
| 🖥️ **Painel web** | Admin em React para gerenciar produtos, marcas, filtros e parâmetros sem deploy |

---

## 📨 Exemplo de post

```
🔥 PROMOÇÃO ALIEXPRESS

Mouse Gamer Sem Fio Attack Shark X3 PAW3395 Bluetooth

R$ 246,18  (antes R$ 483,13)
✅ R$ 246,18  (-49%)
🎟 Cupom PONTO40: -R$ 28,19 → R$ 217,99
🚚 Frete: R$ 24,00 · chega em ~15 dias
💰 Total com frete: R$ 241,99
🇧🇷 Sem II federal · ICMS ~20% incluso

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
  (SQLite:      └─► Canal do Telegram        frete + cupom + total)
  produtos,         (foto + legenda HTML)
  histórico,
  settings)

   api.py (FastAPI REST)  ◄──►  frontend (React/Vercel) — painel admin
                    │
   Azure App Service  +  GitHub Actions (deploy + keep-alive a cada 5 min)
```

O scheduler roda em uma thread separada e, a cada ciclo, busca produtos, compara com o histórico de preços no SQLite e posta o que passar nos filtros. Como a AliExpress **não oferece push/webhook**, a arquitetura é baseada em **polling**.

---

## 🛠️ Stack

- **Python** — lógica do bot e scheduler
- **FastAPI** — API REST do painel (autenticação por `X-API-Key`)
- **SQLite** — produtos, histórico de preços e configurações
- **AliExpress Affiliate API** — Standard + Advanced (assinatura MD5 das requisições)
- **Telegram Bot API** — publicação no canal (foto + legenda HTML)
- **React + Babel** (sem build) na **Vercel** — painel administrativo
- **Azure App Service** (deploy) + **GitHub Actions** (CI/CD e keep-alive)

---

## ⚙️ Como funciona a decisão de postagem

Um produto é publicado quando passa por **todos** os filtros (keywords de periférico, blacklist, whitelist de marca, qualidade) **e** atende a pelo menos um critério de oferta:

1. **Queda vs mínimo histórico** — o preço caiu uma % configurável abaixo do menor valor já registrado; **ou**
2. **Desconto vs preço original** — o item tem um desconto forte sobre o preço de tabela (com exigência extra de avaliação e vendas, já que o desconto reportado pela API é inflado).

Há ainda **cooldown de repost** (não repostar o mesmo item antes de N dias) e **limite de posts por ciclo**, para manter o canal ativo sem floodar.

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
aliexpress.py      Cliente da API (assinatura MD5, parser, link/frete/cupom)
telegram_bot.py    Formatação e publicação das mensagens no canal
database.py        Camada SQLite (produtos, histórico, settings)
api.py             API REST (FastAPI) consumida pelo painel
config.py          Carrega .env, categorias e keywords de periféricos
frontend/          Painel admin (React + Babel, deploy na Vercel)
test_bot.py        Testes (pytest)
```

---

## 📌 Decisões de engenharia

- **Polling, não webhook** — a AliExpress não expõe push; o scheduler verifica em intervalo configurável.
- **Imposto no preço** — o preço retornado pela API (BRL) já inclui o ICMS e, para compras < US$50, não há II federal; por isso o "total" é simplesmente **preço + frete**, sem cálculo de imposto separado.
- **Dedup por fingerprint de título** — o mesmo produto aparece de vários sellers; agrupar por palavras normalizadas e manter o mais barato evita spam de itens repetidos.
- **Enriquecimento sob demanda** — frete e cupom são buscados **só na hora de postar** (1 chamada por produto publicado), economizando requisições.
- **Keep-alive** — no plano gratuito do Azure (sem *Always On*), um cron do GitHub Actions pinga o app a cada 5 min para o scheduler não parar.
