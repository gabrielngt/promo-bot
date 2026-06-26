const { useState, useEffect, useRef, useCallback } = React;

/* ---------------- Icons ---------------- */
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
};

/* ---------------- Persistence ---------------- */
const LS = {
  auth: "promobot.auth",
  products: "promobot.products",
  settings: "promobot.settings",
};
const load = (k, fb) => {
  try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : fb; }
  catch { return fb; }
};
const save = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} };

const DEFAULT_SETTINGS = {
  minDrop: 15,
  interval: 30,
  minDays: 3,
  keywords: ["teclado", "mouse", "headset", "mousepad"],
};

const SEED_PRODUCTS = [
  { id: "1005006789012", name: "Teclado Mecânico RGB Royal Kludge R87", current: 199.90, min: 179.90, lastPosted: "há 2 dias" },
  { id: "1005004321098", name: "Mouse Sem Fio Logitech G304 Lightspeed", current: 142.50, min: 158.00, lastPosted: "há 6 horas" },
  { id: "1005008765432", name: "Headset Gamer HyperX Cloud III", current: 389.00, min: 349.00, lastPosted: "—" },
];

/* ---------------- Helpers ---------------- */
const fmt = (n) => "R$ " + n.toFixed(2).replace(".", ",");
const dropPct = (current, min) => {
  if (!min || min <= 0) return null;
  return ((min - current) / min) * 100; // positive = below target
};

/* ---------------- Login ---------------- */
function Login({ onLogin }) {
  const [url, setUrl] = useState("");
  const [key, setKey] = useState("");
  const canSubmit = url.trim() && key.trim();

  const submit = (e) => {
    e.preventDefault();
    if (!canSubmit) return;
    onLogin({ url: url.trim(), key: key.trim() });
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
            <label className="field-label" htmlFor="api-url">API URL</label>
            <input id="api-url" className="input mono" type="text" placeholder="https://api.meubot.com"
              value={url} onChange={(e) => setUrl(e.target.value)} autoComplete="off" autoFocus />
          </div>
          <div>
            <label className="field-label" htmlFor="api-key">API Key</label>
            <input id="api-key" className="input mono" type="password" placeholder="••••••••••••"
              value={key} onChange={(e) => setKey(e.target.value)} autoComplete="off" />
          </div>
          <button className="btn btn-primary" type="submit" disabled={!canSubmit}>Entrar</button>
        </div>
      </form>
    </div>
  );
}

/* ---------------- Produtos tab ---------------- */
function Produtos({ products, onDelete }) {
  return (
    <div className="page">
      <div className="page-head">
        <div className="page-title">
          Produtos
          {products.length > 0 && <span className="count-pill">{products.length}</span>}
        </div>
        <div className="page-desc">Produtos monitorados pelo bot. Postagem automática quando o preço cai abaixo da meta.</div>
      </div>

      <div className="card table-card">
        {products.length === 0 ? (
          <div className="empty">
            <div className="empty-icon"><Icon.box /></div>
            <div className="empty-title">Nenhum produto ainda.</div>
            <div className="empty-sub">Adicione um produto na aba “Adicionar produto”.</div>
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
                const d = dropPct(p.current, p.min);
                const below = d !== null && d >= 0;
                return (
                  <tr key={p.id}>
                    <td>
                      <div className="prod-name">{p.name}</div>
                      <div className="prod-id">#{p.id}</div>
                    </td>
                    <td className="num-col price">{fmt(p.current)}</td>
                    <td className="num-col price price-min">{fmt(p.min)}</td>
                    <td className="num-col">
                      {d === null ? (
                        <span className="drop-badge flat">—</span>
                      ) : (
                        <span className={"drop-badge" + (below ? "" : " flat")}>
                          {below ? "−" : "+"}{Math.abs(d).toFixed(1)}%
                        </span>
                      )}
                    </td>
                    <td className="muted-cell">{p.lastPosted}</td>
                    <td className="actions-col">
                      <button className="btn btn-ghost-danger" title="Remover produto"
                        onClick={() => onDelete(p.id)} aria-label="Remover">
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

/* ---------------- Adicionar produto tab ---------------- */
function Adicionar({ onAdd }) {
  const [value, setValue] = useState("");
  const canSubmit = value.trim().length > 0;

  const submit = (e) => {
    e.preventDefault();
    if (!canSubmit) return;
    onAdd(value.trim());
    setValue("");
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
          value={value} onChange={(e) => setValue(e.target.value)} autoFocus />
        <div className="field-hint">Aceita link completo de compartilhamento, link curto ou apenas o ID numérico do item.</div>
        <div style={{ marginTop: 20 }}>
          <button className="btn btn-primary" type="submit" disabled={!canSubmit}>
            <Icon.plus /> Adicionar
          </button>
        </div>
      </form>
    </div>
  );
}

/* ---------------- Configurações tab ---------------- */
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

function Configuracoes({ settings, onSave }) {
  const [draft, setDraft] = useState(settings);
  const [kwInput, setKwInput] = useState("");
  const [savedFlash, setSavedFlash] = useState(false);
  const set = (patch) => setDraft((d) => ({ ...d, ...patch }));

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

  const handleSave = () => {
    onSave(draft);
    setSavedFlash(true);
    setTimeout(() => setSavedFlash(false), 2200);
  };

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
            hint="Só posta quando o preço cair pelo menos esse percentual em relação à meta."
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
              <div className="field-hint" style={{ marginTop: 2 }}>Produtos que contêm uma destas palavras recebem prioridade na fila de postagem.</div>
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
                <input className="input" type="text" placeholder="Adicionar keyword e pressione Enter"
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
          <button className="btn btn-primary" onClick={handleSave}>Salvar configurações</button>
        </div>
      </div>
    </div>
  );
}

/* ---------------- Toast ---------------- */
function useToast() {
  const [msg, setMsg] = useState(null);
  const timer = useRef(null);
  const show = useCallback((m) => {
    setMsg(m);
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setMsg(null), 2600);
  }, []);
  const node = (
    <div className={"toast" + (msg ? " show" : "")}>
      <span style={{ color: "var(--green)", display: "inline-flex" }}><Icon.check /></span>
      {msg}
    </div>
  );
  return [node, show];
}

/* ---------------- App ---------------- */
const TABS = [
  { id: "produtos", label: "Produtos" },
  { id: "adicionar", label: "Adicionar produto" },
  { id: "config", label: "Configurações" },
];

function App() {
  const [auth, setAuth] = useState(() => load(LS.auth, null));
  const [tab, setTab] = useState("produtos");
  const [products, setProducts] = useState(() => load(LS.products, SEED_PRODUCTS));
  const [settings, setSettings] = useState(() => ({ ...DEFAULT_SETTINGS, ...load(LS.settings, {}) }));
  const [toast, showToast] = useToast();

  useEffect(() => { save(LS.products, products); }, [products]);
  useEffect(() => { save(LS.settings, settings); }, [settings]);

  const login = (a) => { setAuth(a); save(LS.auth, a); setTab("produtos"); };
  const logout = () => { setAuth(null); localStorage.removeItem(LS.auth); };

  const addProduct = (raw) => {
    // Extract a numeric id if present, else use raw as the display id
    const m = raw.match(/(\d{8,})/);
    const id = m ? m[1] : String(Date.now());
    if (products.some((p) => p.id === id)) {
      showToast("Produto já está sendo monitorado.");
      setTab("produtos");
      return;
    }
    const newProduct = {
      id,
      name: "Produto " + id.slice(-6),
      current: 0,
      min: 0,
      lastPosted: "—",
    };
    setProducts((ps) => [newProduct, ...ps]);
    showToast("Produto adicionado à fila de monitoramento.");
    setTab("produtos");
  };

  const deleteProduct = (id) => {
    setProducts((ps) => ps.filter((p) => p.id !== id));
    showToast("Produto removido.");
  };

  if (!auth) return <Login onLogin={login} />;

  const apiHost = (() => {
    try { return new URL(auth.url).host; } catch { return auth.url; }
  })();

  return (
    <React.Fragment>
      <header className="topbar">
        <div className="brand">
          <div className="logo-badge"><Icon.boltSmall style={{ color: "#fff" }} /></div>
          <span className="brand-name">Promo Bot</span>
        </div>
        <div className="topbar-right">
          <span className="status-pill"><span className="dot"></span>Bot ativo</span>
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

      {tab === "produtos" && <Produtos products={products} onDelete={deleteProduct} />}
      {tab === "adicionar" && <Adicionar onAdd={addProduct} />}
      {tab === "config" && <Configuracoes settings={settings} onSave={(s) => { setSettings(s); showToast("Configurações salvas."); }} />}

      {toast}
    </React.Fragment>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
