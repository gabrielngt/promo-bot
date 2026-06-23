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
    addProduct:    (url_or_id)  => req("POST",   "/api/products", { url_or_id }),
    deleteProduct: (id)         => req("DELETE", `/api/products/${id}`),
    getSettings:   ()           => req("GET",    "/api/settings"),
    saveSettings:  (d)          => req("PUT",    "/api/settings", d),
  };
}

/* ── Settings conversion (API uses decimals, UI uses percentages) ── */
const fromApi = (s) => ({
  minDrop:  Math.round((s.price_drop_threshold  ?? 0.15) * 100),
  interval: s.check_interval_minutes ?? 60,
  minDays:  s.min_repost_days        ?? 7,
  keywords: s.peripheral_keywords    ?? [],
});
const toApi = (s) => ({
  price_drop_threshold:   s.minDrop / 100,
  check_interval_minutes: Number(s.interval),
  min_repost_days:        Number(s.minDays),
  peripheral_keywords:    s.keywords,
});

/* ── Product mapping ── */
const mapProduct = (p) => ({
  id:         p.product_id,
  name:       p.title || "Sem título",
  current:    p.last_price ?? 0,
  min:        p.min_price  ?? 0,
  drop_pct:   p.drop_pct   ?? 0,
  lastPosted: p.posted_at
    ? new Date(p.posted_at + "Z").toLocaleDateString("pt-BR")
    : "—",
});

/* ── Helpers ── */
const LS_AUTH = "promobot.auth";
const loadAuth = () => { try { return JSON.parse(localStorage.getItem(LS_AUTH)); } catch { return null; } };
const saveAuth = (v) => { try { localStorage.setItem(LS_AUTH, JSON.stringify(v)); } catch {} };
const fmt = (n) => n > 0 ? "R$ " + n.toFixed(2).replace(".", ",") : "—";

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

/* ── Produtos ── */
function Produtos({ api, showToast }) {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

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

  return (
    <div className="page">
      <div className="page-head" style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <div className="page-title">
            Produtos
            {products.length > 0 && <span className="count-pill">{products.length}</span>}
          </div>
          <div className="page-desc">Produtos monitorados pelo bot. Postagem automática quando o preço cai abaixo do mínimo histórico.</div>
        </div>
        <button className="btn btn-secondary" onClick={load} disabled={loading} style={{ marginTop: 2 }}>
          <Icon.refresh /> Atualizar
        </button>
      </div>

      <div className="card table-card">
        {loading ? (
          <div className="empty"><div className="empty-sub">Carregando...</div></div>
        ) : products.length === 0 ? (
          <div className="empty">
            <div className="empty-icon"><Icon.box /></div>
            <div className="empty-title">Nenhum produto ainda.</div>
            <div className="empty-sub">Adicione um produto na aba "Adicionar produto".</div>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Produto</th>
                <th className="num-col">Preço atual</th>
                <th className="num-col">Preço mínimo</th>
                <th className="num-col">Queda</th>
                <th>Último post</th>
                <th className="actions-col"></th>
              </tr>
            </thead>
            <tbody>
              {products.map((p) => {
                const below = p.drop_pct > 0;
                return (
                  <tr key={p.id}>
                    <td>
                      <div className="prod-name">{p.name}</div>
                      <div className="prod-id">#{p.id}</div>
                    </td>
                    <td className="num-col price">{fmt(p.current)}</td>
                    <td className="num-col price price-min">{fmt(p.min)}</td>
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
                    <td className="actions-col">
                      <button className="btn btn-ghost-danger" title="Remover produto"
                        onClick={() => handleDelete(p.id)} aria-label="Remover">
                        <Icon.trash />
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

/* ── Adicionar produto ── */
function Adicionar({ api, showToast, onAdded }) {
  const [value, setValue] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!value.trim() || loading) return;
    setLoading(true);
    try {
      await api.addProduct(value.trim());
      showToast("Produto adicionado com sucesso.");
      setValue("");
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
        <div className="page-desc">Cole a URL do produto na AliExpress ou informe o ID. O bot começará a monitorar o preço.</div>
      </div>

      <form className="card add-card" onSubmit={submit}>
        <label className="field-label" htmlFor="add-url">URL ou ID do produto</label>
        <input id="add-url" className="input mono" type="text"
          placeholder="https://aliexpress.com/item/1005006789012.html"
          value={value} onChange={(e) => setValue(e.target.value)} autoFocus disabled={loading} />
        <div className="field-hint">Aceita link completo, link curto ou apenas o ID numérico do item.</div>
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
  const [saving, setSaving] = useState(false);
  const [savedFlash, setSavedFlash] = useState(false);
  const set = (patch) => setDraft((d) => ({ ...d, ...patch }));

  useEffect(() => {
    api.getSettings()
      .then((s) => setDraft(fromApi(s)))
      .catch((err) => showToast("Erro ao carregar configurações: " + err.message, "err"));
  }, [api]);

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

      <div className="card form-card">
        <div className="settings-grid">
          <NumberSetting
            label="Queda mínima de preço (%)"
            hint="Só posta quando o preço cair pelo menos esse percentual em relação ao mínimo histórico."
            value={draft.minDrop} suffix="%" onChange={(v) => set({ minDrop: v })} />
          <NumberSetting
            label="Intervalo de verificação (minutos)"
            hint="Com que frequência o bot consulta os preços na AliExpress."
            value={draft.interval} suffix="min" onChange={(v) => set({ interval: v })} />
          <NumberSetting
            label="Dias mínimos entre reposts"
            hint="Evita repostar o mesmo produto antes de passar esse período."
            value={draft.minDays} suffix="dias" onChange={(v) => set({ minDays: v })} />

          <div className="setting-row" style={{ gridTemplateColumns: "1fr", borderBottom: "none", paddingBottom: 4 }}>
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

/* ── App ── */
const TABS = [
  { id: "produtos",   label: "Produtos" },
  { id: "adicionar", label: "Adicionar produto" },
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
      {tab === "config"     && <Configuracoes api={api} showToast={showToast} />}

      {toast}
    </React.Fragment>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
