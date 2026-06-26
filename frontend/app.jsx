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
    addProduct:    (url_or_id, target_price) => req("POST", "/api/products", { url_or_id, target_price }),
    deleteProduct: (id)         => req("DELETE", `/api/products/${id}`),
    clearDiscovered: ()         => req("DELETE", "/api/products/discovered"),
    getSettings:   ()           => req("GET",    "/api/settings"),
    saveSettings:  (d)          => req("PUT",    "/api/settings", d),
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
  minDrop:   Math.round((s.price_drop_threshold  ?? 0.15) * 100),
  interval:  s.check_interval_minutes ?? 60,
  minDays:   s.min_repost_days        ?? 7,
  keywords:  s.peripheral_keywords    ?? [],
  blacklist: s.keyword_blacklist      ?? [],
  brands:    (s.brand_whitelist ?? []).map(entry =>
    typeof entry === "string" ? parseBrandStr(entry) : entry
  ),
});
const toApi = (s) => ({
  price_drop_threshold:   s.minDrop / 100,
  check_interval_minutes: Number(s.interval),
  min_repost_days:        Number(s.minDays),
  peripheral_keywords:    s.keywords,
  keyword_blacklist:      s.blacklist,
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

/* ── Tabela de produtos (reutilizada na watchlist e nos descobertos) ── */
function ProductTable({ rows, onDelete }) {
  return (
    <table>
      <thead>
        <tr>
          <th>Produto</th>
          <th className="num-col">Preço atual</th>
          <th className="num-col">Preço mínimo</th>
          <th className="num-col">Alvo</th>
          <th className="num-col">Queda</th>
          <th>Último post</th>
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
              <td className="num-col price">{p.target > 0 ? fmt(p.target) : "—"}</td>
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
                  onClick={() => onDelete(p.id)} aria-label="Remover">
                  <Icon.trash />
                </button>
              </td>
            </tr>
          );
        })}
      </tbody>
    </table>
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
              <ProductTable rows={watched} onDelete={handleDelete} />
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
              <ProductTable rows={discovered} onDelete={handleDelete} />
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
        <div className="page-desc">Cole a URL do produto na AliExpress ou informe o ID. O bot passa a vigiar esse item todo ciclo e posta quando atingir o preço-alvo ou cair abaixo do mínimo histórico.</div>
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
        <div className="field-hint">Se definido, o bot posta assim que o preço chegar nesse valor ou abaixo. Sem alvo, posta quando cair abaixo do mínimo histórico.</div>

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
  const [blInput, setBlInput] = useState("");
  const [saving, setSaving] = useState(false);
  const [savedFlash, setSavedFlash] = useState(false);
  const set = (patch) => setDraft((d) => ({ ...d, ...patch }));

  useEffect(() => {
    api.getSettings()
      .then((s) => setDraft(fromApi(s)))
      .catch((err) => showToast("Erro ao carregar configurações: " + err.message, "err"));
  }, [api]);

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
