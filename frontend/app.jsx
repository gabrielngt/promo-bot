const { useState, useEffect, useRef, useCallback } = React;

/* ── Icons ── */
const Icon = {
  bolt: (p) => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" {...p}>
      <path d="M13 2L4.5 13.5H11l-1 8.5L19.5 10H13l0-8z" fill="currentColor"/>
    </svg>
  ),
  boltSmall: (p) => (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" {...p}>
      <path d="M13 2L4.5 13.5H11l-1 8.5L19.5 10H13l0-8z" fill="currentColor"/>
    </svg>
  ),
  trash: (p) => (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <path d="M3 6h18M8 6V4a1 1 0 011-1h6a1 1 0 011 1v2m2 0v14a1 1 0 01-1 1H6a1 1 0 01-1-1V6"/>
      <path d="M10 11v6M14 11v6"/>
    </svg>
  ),
  plus: (p) => (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" {...p}>
      <path d="M12 5v14M5 12h14"/>
    </svg>
  ),
  edit: (p) => (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"/>
      <path d="M18.5 2.5a2.12 2.12 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/>
    </svg>
  ),
  x: (p) => (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" {...p}>
      <path d="M6 6l12 12M18 6L6 18"/>
    </svg>
  ),
  box: (p) => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <path d="M21 8l-9-5-9 5 9 5 9-5zM3 8v8l9 5 9-5V8M12 13v8"/>
    </svg>
  ),
  check: (p) => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <path d="M20 6L9 17l-5-5"/>
    </svg>
  ),
  logout: (p) => (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9"/>
    </svg>
  ),
  refresh: (p) => (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <path d="M1 4v6h6M23 20v-6h-6"/>
      <path d="M20.49 9A9 9 0 005.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 013.51 15"/>
    </svg>
  ),
  eye: (p) => (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" {...p}>
      <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z"/>
      <circle cx="12" cy="12" r="3"/>
    </svg>
  ),
};

/* ── API client ── */
function makeApi(baseUrl, apiKey) {
  const base = baseUrl.replace(/\/$/, "");
  const h = { "Content-Type": "application/json", "X-API-Key": apiKey };
  const req = async (method, path, body) => {
    const res = await fetch(base + path, {
      method, headers: h,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
    const data = await res.json().catch(() => ({ detail: res.statusText }));
    if (!res.ok) throw new Error(data.detail || res.statusText);
    return data;
  };
  return {
    health:        ()           => req("GET",    "/api/health"),
    products:      ()           => req("GET",    "/api/products"),
    addProduct:    (url_or_id, target_price) => req("POST", "/api/products", { url_or_id, target_price }),
    deleteProduct: (id)         => req("DELETE", `/api/products/${id}`),
    clearDiscovered: ()         => req("DELETE", "/api/products/discovered"),
    setTarget:     (id, target_price) => req("PUT", `/api/products/${id}/target`, { target_price }),
    watchProduct:  (id)         => req("PUT", `/api/products/${id}/watch`),
    getSettings:   ()           => req("GET",    "/api/settings"),
    saveSettings:  (d)          => req("PUT",    "/api/settings", d),
    getStatus:     ()           => req("GET",    "/api/status"),
    getCoupons:    ()           => req("GET",    "/api/coupons"),
    addCoupon:     (c)          => req("POST",   "/api/coupons", c),
    deleteCoupon:  (code)       => req("DELETE", `/api/coupons/${encodeURIComponent(code)}`),
    getSales:      (days)       => req("GET",    `/api/sales?days=${days}`),
    excludeOrder:  (oid, sid, excluded) => req("PUT", `/api/sales/${oid}/${sid}/excluded`, { excluded }),
    runNow:        ()           => req("POST",   "/api/run"),
  };
}

/* ── Settings conversion (API uses decimals, UI uses percentages) ── */
const parseBrandStr = (str) => {
  const [name, kws] = str.split(":");
  return { name: name.trim(), keywords: kws ? kws.split(",").map(k => k.trim()).filter(Boolean) : [] };
};
const serializeBrand = (b) =>
  b.keywords.length > 0 ? `${b.name}:${b.keywords.join(",")}` : b.name;

const fromApi = (s) => ({
  minDrop:    Math.round((s.price_drop_threshold ?? 0.15) * 100),
  coldStart:  Math.round((s.cold_start_threshold ?? 0.30) * 100),
  interval:   s.check_interval_minutes ?? 60,
  maxPosts:   s.max_posts_per_cycle    ?? 5,
  maxDaily:   s.max_posts_per_day      ?? 20,
  minDays:    s.min_repost_days        ?? 7,
  importTax:  Math.round((s.import_tax_rate ?? 0)    * 100),
  icms:       Math.round((s.icms_rate       ?? 0.17) * 100),
  campaigns:  (s.coupon_campaigns ?? [])
    .map(c => typeof c === "string" ? c : `${c.code} ${c.min_spend} ${c.discount}`)
    .join("\n"),
  keywords:   s.peripheral_keywords   ?? [],
  blacklist:  s.keyword_blacklist      ?? [],
  shopeeBrands: (s.shopee_brand_whitelist ?? []).map(b => typeof b === 'string' ? b : b.name),
  brands:     (s.brand_whitelist ?? []).map(entry =>
    typeof entry === "string" ? parseBrandStr(entry) : entry
  ),
  monitoring: s.monitoring_enabled ?? true,
  filters:    s.filters_enabled    ?? true,
});
const toApi = (s) => ({
  price_drop_threshold:   s.minDrop / 100,
  cold_start_threshold:   s.coldStart / 100,
  check_interval_minutes: Number(s.interval),
  max_posts_per_cycle:    Number(s.maxPosts),
  max_posts_per_day:      Number(s.maxDaily),
  min_repost_days:        Number(s.minDays),
  import_tax_rate:        s.importTax / 100,
  icms_rate:              s.icms / 100,
  coupon_campaigns:       s.campaigns.split("\n").map(l => l.trim()).filter(Boolean),
  peripheral_keywords:    s.keywords,
  keyword_blacklist:      s.blacklist,
  shopee_brand_whitelist: s.shopeeBrands,
  brand_whitelist:        s.brands.map(serializeBrand),
});

/* ── Product mapping ── */
const mapProduct = (p) => ({
  id:         p.product_id,
  name:       p.title || "Sem título",
  link:       p.link || "",
  current:    p.last_price ?? 0,
  min:        p.min_price  ?? 0,
  drop_pct:   p.drop_pct   ?? 0,
  watched:    !!p.is_watched,
  target:     p.target_price ?? 0,
  reactPos:   p.reactions_positive ?? 0,
  reactNeg:   p.reactions_negative ?? 0,
  lastPosted: p.posted_at
    ? new Date(p.posted_at).toLocaleDateString("pt-BR")
    : "—",
});

/* ── Helpers ── */
const LS_AUTH = "promobot.auth";
const loadAuth = () => { try { return JSON.parse(localStorage.getItem(LS_AUTH)); } catch { return null; } };
const saveAuth = (v) => { try { localStorage.setItem(LS_AUTH, JSON.stringify(v)); } catch {} };
const fmt = (n) => n > 0 ? "R$ " + n.toFixed(2).replace(".", ",") : "—";
// variante que mostra 0,00 em vez de "—" — zero é um valor real em vendas
// (nenhuma venda no período), diferente de "sem preço definido".
// A comissão de afiliado é liquidada em USD, então o símbolo vem do dado.
const CURRENCY_SYMBOLS = { BRL: "R$", USD: "US$", EUR: "€" };
const fmtMoney = (n, currency) =>
  (CURRENCY_SYMBOLS[currency] || currency || "R$") + " " + (n ?? 0).toFixed(2).replace(".", ",");
const timeAgo = (iso) => {
  if (!iso) return "nunca";
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 0) return "agora mesmo";
  if (s < 60) return "agora mesmo";
  if (s < 3600) return `há ${Math.floor(s / 60)} min`;
  if (s < 86400) return `há ${Math.floor(s / 3600)} h`;
  return `há ${Math.floor(s / 86400)} d`;
};

/* ── Toast ── */
function useToast() {
  const [state, setState] = useState({ msg: null, type: "ok" });
  const timer = useRef(null);
  const show = useCallback((msg, type = "ok") => {
    setState({ msg, type });
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setState({ msg: null, type: "ok" }), 3000);
  }, []);
  const node = (
    <div className={"toast" + (state.msg ? " show" : "")}>
      {state.type === "ok"
        ? <span style={{ color: "var(--green)", display: "inline-flex" }}><Icon.check /></span>
        : <span style={{ color: "var(--danger)", fontWeight: 600 }}>!</span>}
      {state.msg}
    </div>
  );
  return [node, show];
}

/* ── Login ── */
function Login({ onLogin }) {
  const [url, setUrl] = useState("");
  const [key, setKey] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    if (!url.trim() || !key.trim()) return;
    setLoading(true);
    setError("");
    try {
      await makeApi(url.trim(), key.trim()).health();
      onLogin({ url: url.trim(), key: key.trim() });
    } catch {
      setError("API Key inválida ou URL incorreta.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-wrap">
      <form className="card login-card" onSubmit={submit}>
        <div className="login-head">
          <div className="logo-badge"><Icon.bolt style={{ color: "#fff" }} /></div>
          <div className="login-title">Promo Bot</div>
          <div className="login-sub">Painel de administração</div>
        </div>
        <div className="login-form">
          <div>
            <label className="field-label" htmlFor="api-url">API URL (Azure)</label>
            <input id="api-url" className="input mono" type="text"
              placeholder="https://promo-bot-rg-bmbncmgnfbc0eham.westeurope-01.azurewebsites.net"
              value={url} onChange={(e) => setUrl(e.target.value)} autoComplete="off" autoFocus />
          </div>
          <div>
            <label className="field-label" htmlFor="api-key">API Key</label>
            <input id="api-key" className="input mono" type="password" placeholder="••••••••••••"
              value={key} onChange={(e) => setKey(e.target.value)} autoComplete="off" />
          </div>
          {error && <div style={{ color: "var(--danger)", fontSize: 13 }}>{error}</div>}
          <button className="btn btn-primary" type="submit" disabled={loading || !url.trim() || !key.trim()}>
            {loading ? "Verificando..." : "Entrar"}
          </button>
        </div>
      </form>
    </div>
  );
}

/* ── Tabela de produtos (reutilizada na watchlist e nos descobertos) ── */
function ProductTable({ rows, onDelete, onSaveTarget, onWatch, showTarget = true }) {
  const [editingId, setEditingId] = useState(null);
  const [editVal, setEditVal] = useState("");

  const save = (p) => {
    const t = editVal.trim();
    const val = t === "" ? null : Number(t.replace(",", "."));
    if (val !== null && (isNaN(val) || val < 0)) return;
    onSaveTarget(p.id, val);
    setEditingId(null);
  };

  return (
    <table>
      <thead>
        <tr>
          <th>Produto</th>
          <th className="num-col">Preço atual</th>
          <th className="num-col">Preço mínimo</th>
          {showTarget && <th className="num-col" title="Comparado com o preço FINAL estimado (cupom + impostos, sem frete). Sem alvo, posta quando cair abaixo do mínimo dos últimos 30 dias.">Alvo ⓘ</th>}
          <th className="num-col">vs Mínimo</th>
          <th>Último post</th>
          <th className="num-col" title="Reações do público no post do Telegram">Reações</th>
          <th className="actions-col"></th>
        </tr>
      </thead>
      <tbody>
        {rows.map((p) => {
          const below = p.drop_pct > 0;
          return (
            <tr key={p.id}>
              <td>
                {p.link
                  ? <a className="prod-name" href={p.link} target="_blank" rel="noopener noreferrer">{p.name}</a>
                  : <div className="prod-name">{p.name}</div>}
                <div className="prod-id">
                  #{p.id}
                  {p.watched && <span className="watch-badge" title="Vigiado pela watchlist">👁 vigiado</span>}
                </div>
              </td>
              <td className="num-col price">{fmt(p.current)}</td>
              <td className="num-col price price-min">{fmt(p.min)}</td>
              {showTarget && (
                <td className="num-col price">
                  {editingId === p.id ? (
                    <input className="input mono target-input" type="number" min="0" step="0.01" autoFocus
                      value={editVal} onChange={(e) => setEditVal(e.target.value)}
                      onKeyDown={(e) => { if (e.key === "Enter") save(p); if (e.key === "Escape") setEditingId(null); }}
                      placeholder="—" />
                  ) : (p.target > 0 ? fmt(p.target) : "—")}
                </td>
              )}
              <td className="num-col">
                {p.drop_pct === 0 ? (
                  <span className="drop-badge flat">—</span>
                ) : (
                  <span className={"drop-badge" + (below ? "" : " flat")}>
                    {below ? "−" : "+"}{Math.abs(p.drop_pct).toFixed(1)}%
                  </span>
                )}
              </td>
              <td className="muted-cell">{p.lastPosted}</td>
              <td className="num-col">
                {p.reactPos > 0 || p.reactNeg > 0 ? (
                  <span className="react-cell">
                    <span className="react-pos">👍 {p.reactPos}</span>
                    <span className="react-neg">👎 {p.reactNeg}</span>
                  </span>
                ) : (
                  <span className="muted-cell">—</span>
                )}
              </td>
              <td className="actions-col">
                {editingId === p.id ? (
                  <>
                    <button className="btn btn-ghost" title="Salvar"
                      onClick={() => save(p)} aria-label="Salvar"><Icon.check /></button>
                    <button className="btn btn-ghost-danger" title="Cancelar"
                      onClick={() => setEditingId(null)} aria-label="Cancelar"><Icon.x /></button>
                  </>
                ) : (
                  <>
                    {p.watched && onSaveTarget && (
                      <button className="btn btn-ghost" title="Editar preço-alvo"
                        onClick={() => { setEditingId(p.id); setEditVal(p.target > 0 ? String(p.target) : ""); }}
                        aria-label="Editar preço-alvo"><Icon.edit /></button>
                    )}
                    {!p.watched && onWatch && (
                      <button className="btn btn-ghost" title="Adicionar à watchlist"
                        onClick={() => onWatch(p.id)} aria-label="Adicionar à watchlist"><Icon.eye /></button>
                    )}
                    <button className="btn btn-ghost-danger" title="Remover produto"
                      onClick={() => onDelete(p.id)} aria-label="Remover"><Icon.trash /></button>
                  </>
                )}
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

/* ── Barra de status + verificar agora ── */
function StatusBar({ api, showToast, onRan }) {
  const [status, setStatus] = useState(null);
  const [failed, setFailed] = useState(false);
  const [running, setRunning] = useState(false);
  const pollRef = useRef(null);

  const load = useCallback(async () => {
    try { setStatus(await api.getStatus()); setFailed(false); }
    catch { setFailed(true); }
  }, [api]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => () => clearInterval(pollRef.current), []);  // limpa ao desmontar

  const ph = status ? null : (failed ? "—" : "…");  // placeholder por estado

  const runNow = async () => {
    setRunning(true);
    try {
      await api.runNow();
      showToast("Verificação disparada — o ciclo pode levar alguns minutos.");
      // o ciclo roda em background por minutos; recarrega ao longo de ~1 min
      // pra pegar o início ("agora mesmo") e os posts que forem surgindo
      clearInterval(pollRef.current);
      let n = 0;
      pollRef.current = setInterval(() => {
        load(); onRan && onRan();
        if (++n >= 12) clearInterval(pollRef.current);  // ~12 x 6s = ~72s
      }, 6000);
      setTimeout(() => { load(); onRan && onRan(); }, 1500);  // 1º refresh rápido
    } catch (err) {
      showToast("Erro: " + err.message, "err");
    } finally {
      setRunning(false);
    }
  };

  const mon = status?.monitoring_enabled;
  const dotClass = "dot" + (status ? (mon ? "" : " paused") : (failed ? " paused" : " off"));

  return (
    <div className="card status-card">
      <div className="status-stats">
        <div className="status-item">
          <span className="label">Monitoramento</span>
          <span className="value"><span className={dotClass}></span>{
            status ? (mon ? "Ativo" : "Pausado") : (failed ? "Indisponível" : "…")
          }{status && !status.filters_enabled ? " · sem filtros" : ""}</span>
        </div>
        <div className="status-item">
          <span className="label">Última verificação</span>
          <span className="value">{status ? timeAgo(status.last_check_at) : ph}</span>
        </div>
        <div className="status-item">
          <span className="label">Posts (24h)</span>
          <span className="value">{status ? status.posts_24h : ph}</span>
        </div>
        <div className="status-item">
          <span className="label">Vigiados</span>
          <span className="value">{status ? status.watched_count : ph}</span>
        </div>
        <div className="status-item">
          <span className="label">Descobertos</span>
          <span className="value">{status ? status.discovered_count : ph}</span>
        </div>
      </div>
      <button className="btn btn-primary" onClick={runNow} disabled={running || !mon}
        title={
          failed ? "Status indisponível — backend pode estar desatualizado"
          : mon === false ? "Ative o monitoramento para verificar"
          : "Roda um ciclo agora, sem esperar o intervalo"
        }>
        <Icon.bolt style={{ width: 15, height: 15 }} /> {running ? "Disparando..." : "Verificar agora"}
      </button>
    </div>
  );
}

/* ── Produtos ── */
function Produtos({ api, showToast }) {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [clearing, setClearing] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.products();
      setProducts(data.map(mapProduct));
    } catch (err) {
      showToast("Erro ao carregar produtos: " + err.message, "err");
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async (id) => {
    try {
      await api.deleteProduct(id);
      setProducts((ps) => ps.filter((p) => p.id !== id));
      showToast("Produto removido.");
    } catch (err) {
      showToast("Erro ao remover: " + err.message, "err");
    }
  };

  const watched = products.filter((p) => p.watched);
  const discovered = products.filter((p) => !p.watched);

  const handleClearDiscovered = async () => {
    if (discovered.length === 0) return;
    if (!confirm(`Excluir os ${discovered.length} produtos descobertos automaticamente? A watchlist é mantida.`)) return;
    setClearing(true);
    try {
      const r = await api.clearDiscovered();
      showToast(`${r.deleted} produtos removidos.`);
      load();
    } catch (err) {
      showToast("Erro ao limpar: " + err.message, "err");
    } finally {
      setClearing(false);
    }
  };

  const handleSaveTarget = async (id, target) => {
    try {
      await api.setTarget(id, target);
      showToast(target === null ? "Preço-alvo removido." : "Preço-alvo atualizado.");
      load();
    } catch (err) {
      showToast("Erro: " + err.message, "err");
    }
  };

  const handleWatch = async (id) => {
    try {
      await api.watchProduct(id);
      showToast("Adicionado à watchlist.");
      load();
    } catch (err) {
      showToast("Erro: " + err.message, "err");
    }
  };

  return (
    <div className="page">
      <div className="page-head" style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <div className="page-title">Produtos</div>
          <div className="page-desc">Watchlist são os itens que você adiciona à mão. Descobertos são achados automaticamente pelo bot.</div>
        </div>
        <button className="btn btn-secondary" onClick={load} disabled={loading} style={{ marginTop: 2 }}>
          <Icon.refresh /> Atualizar
        </button>
      </div>

      <StatusBar api={api} showToast={showToast} onRan={load} />

      {loading ? (
        <div className="card table-card"><div className="empty"><div className="empty-sub">Carregando...</div></div></div>
      ) : (
        <>
          <div className="section-head">
            <div className="section-title">👁 Watchlist {watched.length > 0 && <span className="count-pill">{watched.length}</span>}</div>
          </div>
          <div className="card table-card">
            {watched.length === 0 ? (
              <div className="empty"><div className="empty-sub">Nenhum produto vigiado. Adicione um na aba "Adicionar produto".</div></div>
            ) : (
              <ProductTable rows={watched} onDelete={handleDelete} onSaveTarget={handleSaveTarget} />
            )}
          </div>

          <div className="section-head" style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <div className="section-title">🔍 Descobertos automaticamente {discovered.length > 0 && <span className="count-pill">{discovered.length}</span>}</div>
            {discovered.length > 0 && (
              <button className="btn btn-ghost-danger" onClick={handleClearDiscovered} disabled={clearing}>
                <Icon.trash /> {clearing ? "Limpando..." : "Limpar lista"}
              </button>
            )}
          </div>
          <div className="card table-card">
            {discovered.length === 0 ? (
              <div className="empty"><div className="empty-sub">Nenhum produto descoberto no momento.</div></div>
            ) : (
              <ProductTable rows={discovered} onDelete={handleDelete} onWatch={handleWatch} showTarget={false} />
            )}
          </div>
        </>
      )}
    </div>
  );
}

/* ── Adicionar produto ── */
function Adicionar({ api, showToast, onAdded }) {
  const [value, setValue] = useState("");
  const [target, setTarget] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!value.trim() || loading) return;
    setLoading(true);
    try {
      const targetPrice = target.trim() === "" ? null : Number(target);
      await api.addProduct(value.trim(), targetPrice);
      showToast("Produto adicionado à watchlist.");
      setValue("");
      setTarget("");
      onAdded();
    } catch (err) {
      showToast("Erro: " + err.message, "err");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <div className="page-head">
        <div className="page-title">Adicionar produto</div>
        <div className="page-desc">Cole a URL do produto na AliExpress ou informe o ID. O bot passa a vigiar esse item todo ciclo e posta quando o preço final (cupom + impostos) atingir o alvo ou o preço cair abaixo do mínimo recente.</div>
      </div>

      <form className="card add-card" onSubmit={submit}>
        <label className="field-label" htmlFor="add-url">URL ou ID do produto</label>
        <input id="add-url" className="input mono" type="text"
          placeholder="https://aliexpress.com/item/1005006789012.html"
          value={value} onChange={(e) => setValue(e.target.value)} autoFocus disabled={loading} />
        <div className="field-hint">Aceita link completo, link curto ou apenas o ID numérico do item.</div>

        <label className="field-label" htmlFor="add-target" style={{ marginTop: 18, display: "block" }}>Preço-alvo (opcional)</label>
        <div className="num-input-wrap">
          <input id="add-target" className="input mono" type="number" min="0" step="0.01"
            placeholder="ex: 199,90"
            value={target} onChange={(e) => setTarget(e.target.value)} disabled={loading} />
          <span className="num-suffix">R$</span>
        </div>
        <div className="field-hint">Se definido, o bot posta assim que o preço <b>final estimado</b> (com cupom e impostos do checkout, sem frete) chegar nesse valor ou abaixo. Sem alvo, posta quando cair abaixo do mínimo dos últimos 30 dias.</div>

        <div style={{ marginTop: 20 }}>
          <button className="btn btn-primary" type="submit" disabled={!value.trim() || loading}>
            <Icon.plus /> {loading ? "Adicionando..." : "Adicionar"}
          </button>
        </div>
      </form>
    </div>
  );
}

/* ── Configurações ── */
function ControlToggle({ label, hint, on, disabled, onChange }) {
  return (
    <div className="control-row">
      <div className="control-meta">
        <label className="field-label">{label}</label>
        <div className="field-hint" style={{ marginTop: 2 }}>{hint}</div>
      </div>
      <button type="button" role="switch" aria-checked={on} aria-label={label}
        className={"switch" + (on ? " on" : "")} disabled={disabled}
        onClick={() => onChange(!on)} />
    </div>
  );
}

function NumberSetting({ label, hint, value, suffix, onChange, min = 0 }) {
  return (
    <div className="setting-row">
      <div className="setting-meta">
        <label className="field-label">{label}</label>
        <div className="field-hint" style={{ marginTop: 2 }}>{hint}</div>
      </div>
      <div className="setting-control">
        <div className="num-input-wrap">
          <input className="input mono" type="number" min={min} value={value}
            onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))} />
          {suffix && <span className="num-suffix">{suffix}</span>}
        </div>
      </div>
    </div>
  );
}

function Configuracoes({ api, showToast }) {
  const [draft, setDraft] = useState(null);
  const [kwInput, setKwInput] = useState("");
  const [blInput, setBlInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [savedFlash, setSavedFlash] = useState(false);
  const set = (patch) => setDraft((d) => ({ ...d, ...patch }));

  const [coupons, setCoupons] = useState([]);
  const [cpForm, setCpForm] = useState({ code: "", min_spend: "", discount: "", expires_at: "" });
  const [cpSaving, setCpSaving] = useState(false);

  const loadCoupons = useCallback(() => {
    api.getCoupons().then(setCoupons).catch(() => {});
  }, [api]);

  useEffect(() => {
    api.getSettings()
      .then((s) => setDraft(fromApi(s)))
      .catch((err) => showToast("Erro ao carregar configurações: " + err.message, "err"));
    loadCoupons();
  }, [api, loadCoupons]);

  // cupons salvam na hora (têm botão próprio) — não dependem do "Salvar configurações"
  const addCoupon = async () => {
    const code = cpForm.code.trim();
    if (!code) { showToast("Informe o código do cupom.", "err"); return; }
    setCpSaving(true);
    try {
      await api.addCoupon({
        code,
        min_spend: Number(cpForm.min_spend || 0),
        discount: Number(cpForm.discount || 0),
        expires_at: cpForm.expires_at || null,
      });
      setCpForm({ code: "", min_spend: "", discount: "", expires_at: "" });
      showToast("Cupom adicionado.");
      loadCoupons();
    } catch (err) {
      showToast("Erro: " + err.message, "err");
    } finally {
      setCpSaving(false);
    }
  };

  const removeCoupon = async (code) => {
    try {
      await api.deleteCoupon(code);
      showToast("Cupom removido.");
      loadCoupons();
    } catch (err) {
      showToast("Erro: " + err.message, "err");
    }
  };

  const [newBrandInput, setNewBrandInput] = useState("");
  const [brandKwInputs, setBrandKwInputs] = useState({});

  const addKeyword = () => {
    const k = kwInput.trim().toLowerCase();
    if (!k || draft.keywords.includes(k)) { setKwInput(""); return; }
    set({ keywords: [...draft.keywords, k] });
    setKwInput("");
  };
  const removeKeyword = (k) => set({ keywords: draft.keywords.filter((x) => x !== k) });
  const onKwKey = (e) => {
    if (e.key === "Enter" || e.key === ",") { e.preventDefault(); addKeyword(); }
    else if (e.key === "Backspace" && !kwInput && draft.keywords.length) {
      set({ keywords: draft.keywords.slice(0, -1) });
    }
  };

  const addBlacklist = () => {
    const k = blInput.trim().toLowerCase();
    if (!k || draft.blacklist.includes(k)) { setBlInput(""); return; }
    set({ blacklist: [...draft.blacklist, k] });
    setBlInput("");
  };
  const removeBlacklist = (k) => set({ blacklist: draft.blacklist.filter((x) => x !== k) });
  const onBlKey = (e) => {
    if (e.key === "Enter" || e.key === ",") { e.preventDefault(); addBlacklist(); }
    else if (e.key === "Backspace" && !blInput && draft.blacklist.length) {
      set({ blacklist: draft.blacklist.slice(0, -1) });
    }
  };

  const [sbInput, setSbInput] = useState("");
  const addShopeeBrand = () => {
    const k = sbInput.trim().toLowerCase();
    if (!k || draft.shopeeBrands.includes(k)) { setSbInput(""); return; }
    set({ shopeeBrands: [...draft.shopeeBrands, k] });
    setSbInput("");
  };
  const removeShopeeBrand = (k) => set({ shopeeBrands: draft.shopeeBrands.filter((x) => x !== k) });
  const onSbKey = (e) => {
    if (e.key === "Enter" || e.key === ",") { e.preventDefault(); addShopeeBrand(); }
    else if (e.key === "Backspace" && !sbInput && draft.shopeeBrands.length) {
      set({ shopeeBrands: draft.shopeeBrands.slice(0, -1) });
    }
  };

  const addBrand = () => {
    const name = newBrandInput.trim();
    if (!name || draft.brands.some(b => b.name.toLowerCase() === name.toLowerCase())) {
      setNewBrandInput(""); return;
    }
    set({ brands: [...draft.brands, { name, keywords: [] }] });
    setNewBrandInput("");
  };
  const removeBrand = (idx) => set({ brands: draft.brands.filter((_, i) => i !== idx) });
  const addBrandKw = (idx) => {
    const key = draft.brands[idx].name;
    const kw = (brandKwInputs[key] || "").trim().toLowerCase();
    if (!kw || draft.brands[idx].keywords.includes(kw)) {
      setBrandKwInputs(p => ({ ...p, [key]: "" })); return;
    }
    set({ brands: draft.brands.map((b, i) => i === idx ? { ...b, keywords: [...b.keywords, kw] } : b) });
    setBrandKwInputs(p => ({ ...p, [key]: "" }));
  };
  const removeBrandKw = (idx, kw) => set({
    brands: draft.brands.map((b, i) => i === idx ? { ...b, keywords: b.keywords.filter(k => k !== kw) } : b)
  });

  // Toggles de controle aplicam na hora (não esperam o botão Salvar): uma
  // chave-mestra que você esquece de salvar é um perigo. Reverte se a API falhar.
  const toggleControl = async (draftKey, apiKey, value) => {
    set({ [draftKey]: value });
    try {
      await api.saveSettings({ [apiKey]: value });
      showToast(value ? "Ativado." : "Desativado.");
    } catch (err) {
      set({ [draftKey]: !value });
      showToast("Erro: " + err.message, "err");
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.saveSettings(toApi(draft));
      setSavedFlash(true);
      setTimeout(() => setSavedFlash(false), 2200);
      showToast("Configurações salvas.");
    } catch (err) {
      showToast("Erro ao salvar: " + err.message, "err");
    } finally {
      setSaving(false);
    }
  };

  if (!draft) return (
    <div className="page"><div className="empty"><div className="empty-sub">Carregando...</div></div></div>
  );

  return (
    <div className="page">
      <div className="page-head">
        <div className="page-title">Configurações</div>
        <div className="page-desc">Regras de monitoramento e de postagem no canal do Telegram.</div>
      </div>

      <div className="card control-card">
        <ControlToggle
          label="Monitoramento ativo"
          hint="Chave-mestra. Desligado, o bot para de buscar e postar — nada é perdido, é só religar."
          on={draft.monitoring}
          onChange={(v) => toggleControl("monitoring", "monitoring_enabled", v)} />
        <ControlToggle
          label="Filtros ativos"
          hint="Keywords, blacklist e marcas. Desligado, o bot considera qualquer produto das categorias (as listas continuam salvas)."
          on={draft.filters}
          onChange={(v) => toggleControl("filters", "filters_enabled", v)} />
      </div>

      <div className="card form-card">
        <div className="settings-grid">
          <NumberSetting
            label="Queda mínima de preço (%)"
            hint="Só posta quando o preço cair pelo menos esse percentual em relação ao mínimo histórico."
            value={draft.minDrop} suffix="%" onChange={(v) => set({ minDrop: v })} min={1} />
          <NumberSetting
            label="Desconto mínimo para novos produtos (%)"
            hint="Para produtos sem histórico de preço, só posta se o desconto sobre o original for pelo menos esse valor."
            value={draft.coldStart} suffix="%" onChange={(v) => set({ coldStart: v })} min={1} />
          <NumberSetting
            label="Máximo de posts por ciclo"
            hint="Limite de produtos postados a cada verificação."
            value={draft.maxPosts} suffix="posts" onChange={(v) => set({ maxPosts: v })} min={1} />
          <NumberSetting
            label="Máximo de posts por dia"
            hint="Teto de segurança nas últimas 24h. Atingido o limite, o bot para de postar até o dia virar — protege o canal de flood se muitos produtos parecerem em promoção ao mesmo tempo."
            value={draft.maxDaily} suffix="posts" onChange={(v) => set({ maxDaily: v })} min={1} />
          <NumberSetting
            label="Intervalo de verificação (minutos)"
            hint="Com que frequência o bot consulta os preços na AliExpress."
            value={draft.interval} suffix="min" onChange={(v) => set({ interval: v })} />
          <NumberSetting
            label="Dias mínimos entre reposts"
            hint="Evita repostar o mesmo produto antes de passar esse período."
            value={draft.minDays} suffix="dias" onChange={(v) => set({ minDays: v })} />
          <NumberSetting
            label="Imposto de importação (%)"
            hint="II federal somado no checkout. Zerado por MP para compras até US$50 desde mai/2026 — ajuste aqui se a regra mudar."
            value={draft.importTax} suffix="%" onChange={(v) => set({ importTax: v })} min={0} />
          <NumberSetting
            label="ICMS no checkout (%)"
            hint="Cobrado 'por dentro' pelo AliExpress no pagamento (17–20% conforme o estado). Usado no total estimado do post."
            value={draft.icms} suffix="%" onChange={(v) => set({ icms: v })} min={0} />

          <div className="setting-row" style={{ gridTemplateColumns: "1fr", paddingBottom: 4 }}>
            <div className="setting-meta">
              <label className="field-label">Cupons de campanha</label>
              <div className="field-hint" style={{ marginTop: 2 }}>
                Cupons que o bot aplica nos posts. Os <b>manuais</b> você adiciona aqui (com validade,
                se quiser — vencido, sai sozinho). Os <b>automáticos</b> são descobertos nos anúncios
                que o bot escaneia e valem por 72h desde a última vez que foram vistos.
              </div>
            </div>
            <div className="coupon-form">
              <input className="input" placeholder="Código" value={cpForm.code}
                onChange={(e) => setCpForm({ ...cpForm, code: e.target.value })} />
              <input className="input mono" type="number" min="0" step="0.01" placeholder="Gasto mín."
                value={cpForm.min_spend} onChange={(e) => setCpForm({ ...cpForm, min_spend: e.target.value })} />
              <input className="input mono" type="number" min="0" step="0.01" placeholder="Desconto"
                value={cpForm.discount} onChange={(e) => setCpForm({ ...cpForm, discount: e.target.value })} />
              <input className="input mono" type="date" title="Validade (opcional)"
                value={cpForm.expires_at} onChange={(e) => setCpForm({ ...cpForm, expires_at: e.target.value })} />
              <button type="button" className="btn btn-secondary" onClick={addCoupon} disabled={cpSaving}>
                <Icon.plus /> Adicionar
              </button>
            </div>

            {coupons.length === 0 ? (
              <div className="no-tags" style={{ marginTop: 10 }}>Nenhum cupom ativo no momento.</div>
            ) : (
              <div className="coupon-list">
                {coupons.map((c) => (
                  <div className={"coupon-row" + (c.active ? "" : " expired")} key={c.code}>
                    <span className="coupon-code">{c.code}</span>
                    <span className="coupon-vals">
                      −R$ {Number(c.discount).toFixed(2)} · mín. R$ {Number(c.min_spend).toFixed(2)}
                    </span>
                    <span className={"coupon-src" + (c.source === "manual" ? " manual" : "")}>
                      {c.source === "manual" ? "manual" : "auto"}
                    </span>
                    <span className="coupon-exp">
                      {c.expires_at
                        ? (c.active ? "vence " : "venceu ") + new Date(c.expires_at).toLocaleDateString("pt-BR")
                        : (c.source === "manual" ? "sem validade" : "")}
                    </span>
                    <button type="button" className="btn btn-ghost-danger" title="Remover cupom"
                      onClick={() => removeCoupon(c.code)}><Icon.trash /></button>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="setting-row" style={{ gridTemplateColumns: "1fr", paddingBottom: 4 }}>
            <div className="setting-meta">
              <label className="field-label">Marcas da Shopee</label>
              <div className="field-hint" style={{ marginTop: 2 }}>
                Whitelist separada da AliExpress — as marcas de lá (akko, mchose, attack shark...)
                quase não existem no varejo nacional, então a Shopee tem a sua.
                Deixe vazio para aceitar qualquer marca que passe nos filtros de qualidade.
              </div>
            </div>
            <div className="tags-box">
              {draft.shopeeBrands.length > 0 ? (
                <div className="tags-wrap">
                  {draft.shopeeBrands.map((k) => (
                    <span className="tag" key={k}>
                      {k}
                      <button type="button" onClick={() => removeShopeeBrand(k)} aria-label={"Remover " + k}><Icon.x /></button>
                    </span>
                  ))}
                </div>
              ) : (
                <div className="no-tags">Sem filtro de marca na Shopee.</div>
              )}
              <div className="tag-add-row">
                <input className="input" type="text" placeholder="Digite e pressione Enter"
                  value={sbInput} onChange={(e) => setSbInput(e.target.value)} onKeyDown={onSbKey} />
                <button type="button" className="btn btn-secondary" onClick={addShopeeBrand}><Icon.plus /> Add</button>
              </div>
            </div>
          </div>

          <div className="setting-row" style={{ gridTemplateColumns: "1fr", paddingBottom: 4 }}>
            <div className="setting-meta">
              <label className="field-label">Keywords de periféricos</label>
              <div className="field-hint" style={{ marginTop: 2 }}>Produtos cujo título contém uma destas palavras são monitorados pelo bot.</div>
            </div>
            <div className="tags-box">
              {draft.keywords.length > 0 ? (
                <div className="tags-wrap">
                  {draft.keywords.map((k) => (
                    <span className="tag" key={k}>
                      {k}
                      <button type="button" onClick={() => removeKeyword(k)} aria-label={"Remover " + k}><Icon.x /></button>
                    </span>
                  ))}
                </div>
              ) : (
                <div className="no-tags">Nenhuma keyword adicionada.</div>
              )}
              <div className="tag-add-row">
                <input className="input" type="text" placeholder="Digite e pressione Enter"
                  value={kwInput} onChange={(e) => setKwInput(e.target.value)} onKeyDown={onKwKey} />
                <button type="button" className="btn btn-secondary" onClick={addKeyword}><Icon.plus /> Add</button>
              </div>
            </div>
          </div>

          <div className="setting-row" style={{ gridTemplateColumns: "1fr", paddingBottom: 4 }}>
            <div className="setting-meta">
              <label className="field-label">Blacklist de palavras</label>
              <div className="field-hint" style={{ marginTop: 2 }}>Produtos cujo título contiver qualquer uma dessas palavras são ignorados.</div>
            </div>
            <div className="tags-box">
              {draft.blacklist.length > 0 ? (
                <div className="tags-wrap">
                  {draft.blacklist.map((k) => (
                    <span className="tag tag-danger" key={k}>
                      {k}
                      <button type="button" onClick={() => removeBlacklist(k)} aria-label={"Remover " + k}><Icon.x /></button>
                    </span>
                  ))}
                </div>
              ) : (
                <div className="no-tags">Nenhuma palavra bloqueada.</div>
              )}
              <div className="tag-add-row">
                <input className="input" type="text" placeholder="Digite e pressione Enter"
                  value={blInput} onChange={(e) => setBlInput(e.target.value)} onKeyDown={onBlKey} />
                <button type="button" className="btn btn-secondary" onClick={addBlacklist}><Icon.plus /> Add</button>
              </div>
            </div>
          </div>

          <div className="setting-row" style={{ gridTemplateColumns: "1fr", borderBottom: "none", paddingBottom: 4 }}>
            <div className="setting-meta">
              <label className="field-label">Whitelist de marcas</label>
              <div className="field-hint" style={{ marginTop: 2 }}>
                Só posta produtos das marcas listadas. Adicione filtros por tipo de produto em cada marca (ex: só mouses da ATK). Vazio = aceita qualquer marca.
              </div>
            </div>
            <div className="tags-box">
              {draft.brands.length === 0 && (
                <div className="no-tags">Vazio — todas as marcas aceitas.</div>
              )}
              {draft.brands.map((entry, idx) => {
                const bKey = entry.name;
                const kwVal = brandKwInputs[bKey] || "";
                const addKw = () => addBrandKw(idx);
                return (
                  <div key={bKey} className="brand-entry">
                    <div className="brand-entry-head">
                      <span className="brand-entry-name">{entry.name}</span>
                      <button type="button" className="btn btn-ghost-danger" onClick={() => removeBrand(idx)} aria-label={"Remover " + entry.name}><Icon.trash /></button>
                    </div>
                    <div className="brand-entry-kws">
                      {entry.keywords.length === 0
                        ? <span className="brand-kws-empty">Todos os produtos desta marca</span>
                        : (
                          <div className="tags-wrap" style={{ marginBottom: 8 }}>
                            {entry.keywords.map(kw => (
                              <span className="tag" key={kw}>
                                {kw}
                                <button type="button" onClick={() => removeBrandKw(idx, kw)} aria-label={"Remover " + kw}><Icon.x /></button>
                              </span>
                            ))}
                          </div>
                        )
                      }
                      <div className="tag-add-row">
                        <input className="input" type="text" placeholder="tipo de produto (ex: mouse)"
                          style={{ fontSize: 12.5 }}
                          value={kwVal}
                          onChange={(e) => setBrandKwInputs(p => ({ ...p, [bKey]: e.target.value }))}
                          onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addKw(); } }}
                        />
                        <button type="button" className="btn btn-secondary" onClick={addKw}><Icon.plus /> Add</button>
                      </div>
                    </div>
                  </div>
                );
              })}
              <div className="tag-add-row" style={{ marginTop: draft.brands.length > 0 ? 8 : 0 }}>
                <input className="input" type="text" placeholder="Nome da marca (ex: Logitech)"
                  value={newBrandInput}
                  onChange={(e) => setNewBrandInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addBrand(); } }}
                />
                <button type="button" className="btn btn-secondary" onClick={addBrand}><Icon.plus /> Marca</button>
              </div>
            </div>
          </div>
        </div>

        <div className="form-footer">
          <span className={"save-hint" + (savedFlash ? " saved-flash" : "")}>
            {savedFlash ? "Configurações salvas." : "As alterações se aplicam à próxima verificação."}
          </span>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? "Salvando..." : "Salvar configurações"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── Vendas ── */
const SALES_PERIODS = [7, 30, 90];

// Path com cantos arredondados só no topo (4px), reto na base — "data-end
// arredondado, quadrado na baseline" do spec de marcas.
function topRoundedBarPath(x, y, w, h, r) {
  if (h <= 0) return "";
  r = Math.min(r, w / 2, h);
  return `M${x},${y + h} L${x},${y + r} Q${x},${y} ${x + r},${y} `
       + `L${x + w - r},${y} Q${x + w},${y} ${x + w},${y + r} L${x + w},${y + h} Z`;
}

// Y-tick "redondo": maior número limpo (1/2/5 × 10^n) que cabe acima do valor máximo.
function niceCeil(v) {
  if (v <= 0) return 1;
  const mag = Math.pow(10, Math.floor(Math.log10(v)));
  for (const step of [1, 2, 5, 10]) {
    if (step * mag >= v) return step * mag;
  }
  return 10 * mag;
}

function SalesChart({ series, days, currency }) {
  // completa os dias sem pedido com paid_total=0, pra barra aparecer no lugar certo
  const byDate = new Map(series.map((d) => [d.order_date, d]));
  const points = [];
  for (let i = days - 1; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    const found = byDate.get(key);
    points.push({ date: key, count: found?.count ?? 0, paid_total: Number(found?.paid_total ?? 0) });
  }

  const W = 900, H = 220, padL = 4, padR = 4, padT = 18, padB = 26;
  const baseline = H - padB;
  const max = niceCeil(Math.max(...points.map((p) => p.paid_total), 0.01));
  const n = points.length;
  const slot = (W - padL - padR) / n;
  const barW = Math.max(2, Math.min(24, slot - 2));

  const [hover, setHover] = useState(null);
  const hasAny = points.some((p) => p.paid_total > 0);

  const xOf = (i) => padL + i * slot + (slot - barW) / 2;
  const yScale = (v) => (max > 0 ? (v / max) * (baseline - padT) : 0);

  // amostra ticks do eixo X pra não colidir (~6 labels no máximo)
  const tickEvery = Math.max(1, Math.ceil(n / 6));

  return (
    <div style={{ position: "relative" }}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} role="img" aria-label={`Receita diária, últimos ${days} dias`}>
        {/* gridlines recessivas: baseline (0) e o topo (max arredondado) */}
        <line x1={padL} y1={baseline} x2={W - padR} y2={baseline} stroke="var(--border-soft)" strokeWidth="1" />
        <line x1={padL} y1={padT} x2={W - padR} y2={padT} stroke="var(--border-soft)" strokeWidth="1" />
        <text x={W - padR} y={padT - 5} textAnchor="end" fontSize="10.5" fill="var(--muted-2)" fontFamily="var(--mono)">
          {fmtMoney(max, currency)}
        </text>

        {points.map((p, i) => {
          const h = Math.max(hasAny && p.paid_total > 0 ? 2 : 0, yScale(p.paid_total));
          const y = baseline - h;
          const x = xOf(i);
          const isHover = hover === i;
          return (
            <g key={p.date}
               onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover((v) => (v === i ? null : v))}
               onFocus={() => setHover(i)} onBlur={() => setHover((v) => (v === i ? null : v))}
               tabIndex={0} role="img" aria-label={`${p.date}: ${fmtMoney(p.paid_total, currency)}, ${p.count} venda(s)`}>
              {/* hit target maior que a barra, pra facilitar o hover */}
              <rect x={x - (slot - barW) / 2} y={padT} width={slot} height={baseline - padT} fill="transparent" />
              <path d={topRoundedBarPath(x, y, barW, h, 4)}
                    fill="var(--green)" opacity={isHover ? 1 : 0.8}
                    style={{ transition: "opacity .1s ease" }} />
              {i % tickEvery === 0 && (
                <text x={x + barW / 2} y={H - 8} textAnchor="middle" fontSize="10" fill="var(--muted-2)" fontFamily="var(--mono)">
                  {p.date.slice(5)}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {hover != null && (
        <div className="chart-tooltip" style={{ left: `${((xOf(hover) + barW / 2) / W) * 100}%` }}>
          <div className="chart-tooltip-value">{fmtMoney(points[hover].paid_total, currency)}</div>
          <div className="chart-tooltip-label">
            {new Date(points[hover].date + "T00:00:00").toLocaleDateString("pt-BR")} · {points[hover].count} venda{points[hover].count === 1 ? "" : "s"}
          </div>
        </div>
      )}
    </div>
  );
}

function Vendas({ api, showToast }) {
  const [days, setDays] = useState(30);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await api.getSales(days));
    } catch (err) {
      showToast("Erro ao carregar vendas: " + err.message, "err");
    } finally {
      setLoading(false);
    }
  }, [api, days]);

  useEffect(() => { load(); }, [load]);

  const summary = data?.summary;
  const orders = data?.orders ?? [];

  const toggleExcluded = async (o) => {
    try {
      await api.excludeOrder(o.order_id, o.sub_order_id, !o.excluded);
      showToast(o.excluded ? "Pedido reincluído nos totais." : "Pedido marcado como compra própria.");
      load();
    } catch (err) {
      showToast("Erro: " + err.message, "err");
    }
  };

  return (
    <div className="page">
      <div className="page-head">
        <div className="page-title">Vendas</div>
        <div className="page-desc">Pedidos e comissão rastreados pela API de afiliados da AliExpress. Sincroniza a cada ciclo do bot.</div>
      </div>

      <div className="period-toggle">
        {SALES_PERIODS.map((p) => (
          <button key={p} className={"period-btn" + (days === p ? " active" : "")} onClick={() => setDays(p)}>
            {p} dias
          </button>
        ))}
      </div>

      <div className="sales-stats">
        <div className="card sales-stat">
          <span className="label">Vendas no período</span>
          <span className="stat-value">{loading ? "…" : (summary?.count ?? 0)}</span>
        </div>
        <div className="card sales-stat">
          <span className="label" title="Soma da base de comissão — valor do produto antes dos cupons do comprador">Valor base</span>
          <span className="stat-value">{loading ? "…" : fmtMoney(summary?.paid_total, summary?.currency)}</span>
        </div>
        <div className="card sales-stat">
          <span className="label">Comissão estimada</span>
          <span className="stat-value accent">{loading ? "…" : fmtMoney(summary?.commission_total, summary?.currency)}</span>
        </div>
      </div>

      <div className="card chart-card">
        {loading ? (
          <div className="empty"><div className="empty-sub">Carregando...</div></div>
        ) : (
          <SalesChart series={data.series} days={days} currency={summary?.currency} />
        )}
      </div>

      <div className="section-head">
        <div className="section-title">Pedidos recentes</div>
        <div className="field-hint" style={{ marginTop: 4 }}>
          A AliExpress liquida em dólar; os valores acima já estão convertidos
          {summary?.usd_brl_rate ? ` (US$ 1 = R$ ${Number(summary.usd_brl_rate).toFixed(2)})` : ""}.
          A coluna <b>Base</b> é o valor sobre o qual sua comissão é calculada — é o preço do produto
          <b> antes</b> dos cupons do comprador, então é maior do que ele pagou no checkout.
          Compras próprias não geram comissão e a API não as identifica — use o ✕ para tirá-las dos totais.
        </div>
      </div>
      {orders.length === 0 && !loading ? (
        <div className="card">
          <div className="empty">
            <div className="empty-icon"><Icon.box /></div>
            <div className="empty-title">Nenhum pedido sincronizado ainda</div>
            <div className="empty-sub">Pedidos aparecem aqui depois do primeiro ciclo com vendas rastreadas pelo link de afiliado.</div>
          </div>
        </div>
      ) : (
        <div className="card table-card">
          <table>
            <thead>
              <tr>
                <th>Produto</th>
                <th>Status</th>
                <th>Data</th>
                <th className="num-col" title="Base usada pela AliExpress para calcular sua comissão. É o valor do produto ANTES dos cupons que o comprador aplicou, então costuma ser maior do que ele pagou de fato.">Base ⓘ</th>
                <th className="num-col">Comissão</th>
                <th className="actions-col"></th>
              </tr>
            </thead>
            <tbody>
              {orders.map((o) => (
                <tr key={o.order_id + "-" + o.sub_order_id}
                    style={o.excluded ? { opacity: 0.45 } : undefined}>
                  <td>
                    {o.product_id ? (
                      <a className="prod-name" href={`https://www.aliexpress.com/item/${o.product_id}.html`} target="_blank" rel="noopener noreferrer">
                        {o.product_title || "Produto #" + o.product_id}
                      </a>
                    ) : (o.product_title || "—")}
                  </td>
                  <td className="muted-cell">{o.order_status || "—"}</td>
                  <td className="muted-cell">{o.order_date ? new Date(o.order_date + "T00:00:00").toLocaleDateString("pt-BR") : "—"}</td>
                  <td className="num-col price">{fmtMoney(o.paid_amount, o.currency)}</td>
                  <td className="num-col price">{fmtMoney(o.estimated_commission, o.currency)}</td>
                  <td className="actions-col">
                    <button className={o.excluded ? "btn btn-ghost" : "btn btn-ghost-danger"}
                      title={o.excluded ? "Reincluir nos totais" : "Marcar como compra própria (não gera comissão)"}
                      onClick={() => toggleExcluded(o)}>
                      {o.excluded ? <Icon.plus /> : <Icon.x />}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/* ── App ── */
const TABS = [
  { id: "produtos",   label: "Produtos" },
  { id: "adicionar", label: "Adicionar produto" },
  { id: "vendas",    label: "Vendas" },
  { id: "config",    label: "Configurações" },
];

function App() {
  const [auth, setAuth]    = useState(() => loadAuth());
  const [tab, setTab]      = useState("produtos");
  const [api, setApi]      = useState(() => auth ? makeApi(auth.url, auth.key) : null);
  const [toast, showToast] = useToast();

  const login = (a) => {
    saveAuth(a);
    setAuth(a);
    setApi(makeApi(a.url, a.key));
    setTab("produtos");
  };

  const logout = () => {
    setAuth(null);
    setApi(null);
    localStorage.removeItem(LS_AUTH);
  };

  if (!auth) return <Login onLogin={login} />;

  const apiHost = (() => { try { return new URL(auth.url).host; } catch { return auth.url; } })();

  return (
    <React.Fragment>
      <header className="topbar">
        <div className="brand">
          <div className="logo-badge"><Icon.boltSmall style={{ color: "#fff" }} /></div>
          <span className="brand-name">Promo Bot</span>
        </div>
        <div className="topbar-right">
          <span className="status-pill"><span className="dot"></span>Online</span>
          <span className="api-chip">{apiHost}</span>
          <button className="link-btn" onClick={logout} title="Sair">
            <Icon.logout style={{ display: "inline", verticalAlign: "-2px" }} /> Sair
          </button>
        </div>
      </header>

      <nav className="tabs">
        {TABS.map((t) => (
          <button key={t.id} className={"tab" + (tab === t.id ? " active" : "")} onClick={() => setTab(t.id)}>
            {t.label}
          </button>
        ))}
      </nav>

      {tab === "produtos"   && <Produtos  api={api} showToast={showToast} />}
      {tab === "adicionar"  && <Adicionar api={api} showToast={showToast} onAdded={() => setTab("produtos")} />}
      {tab === "vendas"     && <Vendas    api={api} showToast={showToast} />}
      {tab === "config"     && <Configuracoes api={api} showToast={showToast} />}

      {toast}
    </React.Fragment>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
