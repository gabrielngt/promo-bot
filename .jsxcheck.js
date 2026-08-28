const { useState, useEffect, useRef, useCallback } = React;
const Icon = {
  bolt: (p) => /* @__PURE__ */ React.createElement("svg", { width: "20", height: "20", viewBox: "0 0 24 24", fill: "none", ...p }, /* @__PURE__ */ React.createElement("path", { d: "M13 2L4.5 13.5H11l-1 8.5L19.5 10H13l0-8z", fill: "currentColor" })),
  boltSmall: (p) => /* @__PURE__ */ React.createElement("svg", { width: "15", height: "15", viewBox: "0 0 24 24", fill: "none", ...p }, /* @__PURE__ */ React.createElement("path", { d: "M13 2L4.5 13.5H11l-1 8.5L19.5 10H13l0-8z", fill: "currentColor" })),
  trash: (p) => /* @__PURE__ */ React.createElement("svg", { width: "15", height: "15", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "1.8", strokeLinecap: "round", strokeLinejoin: "round", ...p }, /* @__PURE__ */ React.createElement("path", { d: "M3 6h18M8 6V4a1 1 0 011-1h6a1 1 0 011 1v2m2 0v14a1 1 0 01-1 1H6a1 1 0 01-1-1V6" }), /* @__PURE__ */ React.createElement("path", { d: "M10 11v6M14 11v6" })),
  plus: (p) => /* @__PURE__ */ React.createElement("svg", { width: "15", height: "15", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "2", strokeLinecap: "round", ...p }, /* @__PURE__ */ React.createElement("path", { d: "M12 5v14M5 12h14" })),
  edit: (p) => /* @__PURE__ */ React.createElement("svg", { width: "15", height: "15", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "1.8", strokeLinecap: "round", strokeLinejoin: "round", ...p }, /* @__PURE__ */ React.createElement("path", { d: "M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7" }), /* @__PURE__ */ React.createElement("path", { d: "M18.5 2.5a2.12 2.12 0 013 3L12 15l-4 1 1-4 9.5-9.5z" })),
  x: (p) => /* @__PURE__ */ React.createElement("svg", { width: "12", height: "12", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "2.4", strokeLinecap: "round", ...p }, /* @__PURE__ */ React.createElement("path", { d: "M6 6l12 12M18 6L6 18" })),
  box: (p) => /* @__PURE__ */ React.createElement("svg", { width: "20", height: "20", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "1.6", strokeLinecap: "round", strokeLinejoin: "round", ...p }, /* @__PURE__ */ React.createElement("path", { d: "M21 8l-9-5-9 5 9 5 9-5zM3 8v8l9 5 9-5V8M12 13v8" })),
  check: (p) => /* @__PURE__ */ React.createElement("svg", { width: "14", height: "14", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "2.4", strokeLinecap: "round", strokeLinejoin: "round", ...p }, /* @__PURE__ */ React.createElement("path", { d: "M20 6L9 17l-5-5" })),
  logout: (p) => /* @__PURE__ */ React.createElement("svg", { width: "15", height: "15", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "1.8", strokeLinecap: "round", strokeLinejoin: "round", ...p }, /* @__PURE__ */ React.createElement("path", { d: "M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9" })),
  refresh: (p) => /* @__PURE__ */ React.createElement("svg", { width: "14", height: "14", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "2", strokeLinecap: "round", strokeLinejoin: "round", ...p }, /* @__PURE__ */ React.createElement("path", { d: "M1 4v6h6M23 20v-6h-6" }), /* @__PURE__ */ React.createElement("path", { d: "M20.49 9A9 9 0 005.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 013.51 15" })),
  external: (p) => /* @__PURE__ */ React.createElement("svg", { width: "13", height: "13", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "2", strokeLinecap: "round", strokeLinejoin: "round", ...p }, /* @__PURE__ */ React.createElement("path", { d: "M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6" }), /* @__PURE__ */ React.createElement("path", { d: "M15 3h6v6M10 14L21 3" })),
  eye: (p) => /* @__PURE__ */ React.createElement("svg", { width: "15", height: "15", viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: "1.8", strokeLinecap: "round", strokeLinejoin: "round", ...p }, /* @__PURE__ */ React.createElement("path", { d: "M1 12s4-7 11-7 11 7 11 7-4 7-11 7-11-7-11-7z" }), /* @__PURE__ */ React.createElement("circle", { cx: "12", cy: "12", r: "3" }))
};
function makeApi(baseUrl, apiKey) {
  const base = baseUrl.replace(/\/$/, "");
  const h = { "Content-Type": "application/json", "X-API-Key": apiKey };
  const req = async (method, path, body) => {
    const res = await fetch(base + path, {
      method,
      headers: h,
      body: body !== void 0 ? JSON.stringify(body) : void 0
    });
    const data = await res.json().catch(() => ({ detail: res.statusText }));
    if (!res.ok) throw new Error(data.detail || res.statusText);
    return data;
  };
  return {
    health: () => req("GET", "/api/health"),
    products: () => req("GET", "/api/products"),
    addProduct: (url_or_id, target_price) => req("POST", "/api/products", { url_or_id, target_price }),
    deleteProduct: (id) => req("DELETE", `/api/products/${id}`),
    clearDiscovered: () => req("DELETE", "/api/products/discovered"),
    setTarget: (id, target_price) => req("PUT", `/api/products/${id}/target`, { target_price }),
    watchProduct: (id) => req("PUT", `/api/products/${id}/watch`),
    getSettings: () => req("GET", "/api/settings"),
    saveSettings: (d) => req("PUT", "/api/settings", d),
    getStatus: () => req("GET", "/api/status"),
    getCoupons: () => req("GET", "/api/coupons"),
    addCoupon: (c) => req("POST", "/api/coupons", c),
    deleteCoupon: (code) => req("DELETE", `/api/coupons/${encodeURIComponent(code)}`),
    getSales: (days) => req("GET", `/api/sales?days=${days}`),
    excludeOrder: (oid, sid, excluded) => req("PUT", `/api/sales/${oid}/${sid}/excluded`, { excluded }),
    runNow: () => req("POST", "/api/run")
  };
}
const parseBrandStr = (str) => {
  const [name, kws] = str.split(":");
  return { name: name.trim(), keywords: kws ? kws.split(",").map((k) => k.trim()).filter(Boolean) : [] };
};
const serializeBrand = (b) => b.keywords.length > 0 ? `${b.name}:${b.keywords.join(",")}` : b.name;
const fromApi = (s) => ({
  minDrop: Math.round((s.price_drop_threshold ?? 0.15) * 100),
  coldStart: Math.round((s.cold_start_threshold ?? 0.3) * 100),
  interval: s.check_interval_minutes ?? 60,
  maxPosts: s.max_posts_per_cycle ?? 5,
  maxDaily: s.max_posts_per_day ?? 20,
  minDays: s.min_repost_days ?? 7,
  importTax: Math.round((s.import_tax_rate ?? 0) * 100),
  icms: Math.round((s.icms_rate ?? 0.17) * 100),
  campaigns: (s.coupon_campaigns ?? []).map((c) => typeof c === "string" ? c : `${c.code} ${c.min_spend} ${c.discount}`).join("\n"),
  keywords: s.peripheral_keywords ?? [],
  blacklist: s.keyword_blacklist ?? [],
  shopeeBrands: (s.shopee_brand_whitelist ?? []).map((b) => typeof b === "string" ? b : b.name),
  brands: (s.brand_whitelist ?? []).map(
    (entry) => typeof entry === "string" ? parseBrandStr(entry) : entry
  ),
  monitoring: s.monitoring_enabled ?? true,
  filters: s.filters_enabled ?? true
});
const toApi = (s) => ({
  price_drop_threshold: s.minDrop / 100,
  cold_start_threshold: s.coldStart / 100,
  check_interval_minutes: Number(s.interval),
  max_posts_per_cycle: Number(s.maxPosts),
  max_posts_per_day: Number(s.maxDaily),
  min_repost_days: Number(s.minDays),
  import_tax_rate: s.importTax / 100,
  icms_rate: s.icms / 100,
  coupon_campaigns: s.campaigns.split("\n").map((l) => l.trim()).filter(Boolean),
  peripheral_keywords: s.keywords,
  keyword_blacklist: s.blacklist,
  shopee_brand_whitelist: s.shopeeBrands,
  brand_whitelist: s.brands.map(serializeBrand)
});
const mapProduct = (p) => ({
  id: p.product_id,
  name: p.title || "Sem t\xEDtulo",
  link: p.link || "",
  current: p.last_price ?? 0,
  min: p.min_price ?? 0,
  drop_pct: p.drop_pct ?? 0,
  watched: !!p.is_watched,
  target: p.target_price ?? 0,
  reactPos: p.reactions_positive ?? 0,
  reactNeg: p.reactions_negative ?? 0,
  lastPosted: p.posted_at ? new Date(p.posted_at).toLocaleDateString("pt-BR") : "\u2014"
});
const LS_AUTH = "promobot.auth";
const loadAuth = () => {
  try {
    return JSON.parse(localStorage.getItem(LS_AUTH));
  } catch {
    return null;
  }
};
const saveAuth = (v) => {
  try {
    localStorage.setItem(LS_AUTH, JSON.stringify(v));
  } catch {
  }
};
const fmt = (n) => n > 0 ? "R$ " + n.toFixed(2).replace(".", ",") : "\u2014";
const CURRENCY_SYMBOLS = { BRL: "R$", USD: "US$", EUR: "\u20AC" };
const fmtMoney = (n, currency) => (CURRENCY_SYMBOLS[currency] || currency || "R$") + " " + (n ?? 0).toFixed(2).replace(".", ",");
const timeAgo = (iso) => {
  if (!iso) return "nunca";
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1e3);
  if (s < 0) return "agora mesmo";
  if (s < 60) return "agora mesmo";
  if (s < 3600) return `h\xE1 ${Math.floor(s / 60)} min`;
  if (s < 86400) return `h\xE1 ${Math.floor(s / 3600)} h`;
  return `h\xE1 ${Math.floor(s / 86400)} d`;
};
function useToast() {
  const [state, setState] = useState({ msg: null, type: "ok" });
  const timer = useRef(null);
  const show = useCallback((msg, type = "ok") => {
    setState({ msg, type });
    clearTimeout(timer.current);
    timer.current = setTimeout(() => setState({ msg: null, type: "ok" }), 3e3);
  }, []);
  const node = /* @__PURE__ */ React.createElement("div", { className: "toast" + (state.msg ? " show" : "") }, state.type === "ok" ? /* @__PURE__ */ React.createElement("span", { style: { color: "var(--green)", display: "inline-flex" } }, /* @__PURE__ */ React.createElement(Icon.check, null)) : /* @__PURE__ */ React.createElement("span", { style: { color: "var(--danger)", fontWeight: 600 } }, "!"), state.msg);
  return [node, show];
}
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
      setError("API Key inv\xE1lida ou URL incorreta.");
    } finally {
      setLoading(false);
    }
  };
  return /* @__PURE__ */ React.createElement("div", { className: "login-wrap" }, /* @__PURE__ */ React.createElement("form", { className: "card login-card", onSubmit: submit }, /* @__PURE__ */ React.createElement("div", { className: "login-head" }, /* @__PURE__ */ React.createElement("div", { className: "logo-badge" }, /* @__PURE__ */ React.createElement(Icon.bolt, { style: { color: "#fff" } })), /* @__PURE__ */ React.createElement("div", { className: "login-title" }, "Promo Bot"), /* @__PURE__ */ React.createElement("div", { className: "login-sub" }, "Painel de administra\xE7\xE3o")), /* @__PURE__ */ React.createElement("div", { className: "login-form" }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("label", { className: "field-label", htmlFor: "api-url" }, "API URL (Azure)"), /* @__PURE__ */ React.createElement(
    "input",
    {
      id: "api-url",
      className: "input mono",
      type: "text",
      placeholder: "https://promo-bot-rg-bmbncmgnfbc0eham.westeurope-01.azurewebsites.net",
      value: url,
      onChange: (e) => setUrl(e.target.value),
      autoComplete: "off",
      autoFocus: true
    }
  )), /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("label", { className: "field-label", htmlFor: "api-key" }, "API Key"), /* @__PURE__ */ React.createElement(
    "input",
    {
      id: "api-key",
      className: "input mono",
      type: "password",
      placeholder: "\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022\u2022",
      value: key,
      onChange: (e) => setKey(e.target.value),
      autoComplete: "off"
    }
  )), error && /* @__PURE__ */ React.createElement("div", { style: { color: "var(--danger)", fontSize: 13 } }, error), /* @__PURE__ */ React.createElement("button", { className: "btn btn-primary", type: "submit", disabled: loading || !url.trim() || !key.trim() }, loading ? "Verificando..." : "Entrar"))));
}
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
  return /* @__PURE__ */ React.createElement("table", null, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("th", null, "Produto"), /* @__PURE__ */ React.createElement("th", { className: "num-col" }, "Pre\xE7o atual"), /* @__PURE__ */ React.createElement("th", { className: "num-col" }, "Pre\xE7o m\xEDnimo"), showTarget && /* @__PURE__ */ React.createElement("th", { className: "num-col", title: "Comparado com o pre\xE7o FINAL estimado (cupom + impostos, sem frete). Sem alvo, posta quando cair abaixo do m\xEDnimo dos \xFAltimos 30 dias." }, "Alvo \u24D8"), /* @__PURE__ */ React.createElement("th", { className: "num-col" }, "vs M\xEDnimo"), /* @__PURE__ */ React.createElement("th", null, "\xDAltimo post"), /* @__PURE__ */ React.createElement("th", { className: "num-col", title: "Rea\xE7\xF5es do p\xFAblico no post do Telegram" }, "Rea\xE7\xF5es"), /* @__PURE__ */ React.createElement("th", { className: "actions-col" }))), /* @__PURE__ */ React.createElement("tbody", null, rows.map((p) => {
    const below = p.drop_pct > 0;
    return /* @__PURE__ */ React.createElement("tr", { key: p.id }, /* @__PURE__ */ React.createElement("td", null, p.link ? /* @__PURE__ */ React.createElement("a", { className: "prod-name", href: p.link, target: "_blank", rel: "noopener noreferrer" }, p.name) : /* @__PURE__ */ React.createElement("div", { className: "prod-name" }, p.name), /* @__PURE__ */ React.createElement("div", { className: "prod-id" }, "#", p.id, p.watched && /* @__PURE__ */ React.createElement("span", { className: "watch-badge", title: "Vigiado pela watchlist" }, "\u{1F441} vigiado"))), /* @__PURE__ */ React.createElement("td", { className: "num-col price" }, fmt(p.current)), /* @__PURE__ */ React.createElement("td", { className: "num-col price price-min" }, fmt(p.min)), showTarget && /* @__PURE__ */ React.createElement("td", { className: "num-col price" }, editingId === p.id ? /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "input mono target-input",
        type: "number",
        min: "0",
        step: "0.01",
        autoFocus: true,
        value: editVal,
        onChange: (e) => setEditVal(e.target.value),
        onKeyDown: (e) => {
          if (e.key === "Enter") save(p);
          if (e.key === "Escape") setEditingId(null);
        },
        placeholder: "\u2014"
      }
    ) : p.target > 0 ? fmt(p.target) : "\u2014"), /* @__PURE__ */ React.createElement("td", { className: "num-col" }, p.drop_pct === 0 ? /* @__PURE__ */ React.createElement("span", { className: "drop-badge flat" }, "\u2014") : /* @__PURE__ */ React.createElement("span", { className: "drop-badge" + (below ? "" : " flat") }, below ? "\u2212" : "+", Math.abs(p.drop_pct).toFixed(1), "%")), /* @__PURE__ */ React.createElement("td", { className: "muted-cell" }, p.lastPosted), /* @__PURE__ */ React.createElement("td", { className: "num-col" }, p.reactPos > 0 || p.reactNeg > 0 ? /* @__PURE__ */ React.createElement("span", { className: "react-cell" }, /* @__PURE__ */ React.createElement("span", { className: "react-pos" }, "\u{1F44D} ", p.reactPos), /* @__PURE__ */ React.createElement("span", { className: "react-neg" }, "\u{1F44E} ", p.reactNeg)) : /* @__PURE__ */ React.createElement("span", { className: "muted-cell" }, "\u2014")), /* @__PURE__ */ React.createElement("td", { className: "actions-col" }, editingId === p.id ? /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn btn-ghost",
        title: "Salvar",
        onClick: () => save(p),
        "aria-label": "Salvar"
      },
      /* @__PURE__ */ React.createElement(Icon.check, null)
    ), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn btn-ghost-danger",
        title: "Cancelar",
        onClick: () => setEditingId(null),
        "aria-label": "Cancelar"
      },
      /* @__PURE__ */ React.createElement(Icon.x, null)
    )) : /* @__PURE__ */ React.createElement(React.Fragment, null, p.watched && onSaveTarget && /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn btn-ghost",
        title: "Editar pre\xE7o-alvo",
        onClick: () => {
          setEditingId(p.id);
          setEditVal(p.target > 0 ? String(p.target) : "");
        },
        "aria-label": "Editar pre\xE7o-alvo"
      },
      /* @__PURE__ */ React.createElement(Icon.edit, null)
    ), !p.watched && onWatch && /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn btn-ghost",
        title: "Adicionar \xE0 watchlist",
        onClick: () => onWatch(p.id),
        "aria-label": "Adicionar \xE0 watchlist"
      },
      /* @__PURE__ */ React.createElement(Icon.eye, null)
    ), /* @__PURE__ */ React.createElement(
      "button",
      {
        className: "btn btn-ghost-danger",
        title: "Remover produto",
        onClick: () => onDelete(p.id),
        "aria-label": "Remover"
      },
      /* @__PURE__ */ React.createElement(Icon.trash, null)
    ))));
  })));
}
function StatusBar({ api, showToast, onRan }) {
  const [status, setStatus] = useState(null);
  const [failed, setFailed] = useState(false);
  const [running, setRunning] = useState(false);
  const pollRef = useRef(null);
  const load = useCallback(async () => {
    try {
      setStatus(await api.getStatus());
      setFailed(false);
    } catch {
      setFailed(true);
    }
  }, [api]);
  useEffect(() => {
    load();
  }, [load]);
  useEffect(() => () => clearInterval(pollRef.current), []);
  const ph = status ? null : failed ? "\u2014" : "\u2026";
  const runNow = async () => {
    setRunning(true);
    try {
      await api.runNow();
      showToast("Verifica\xE7\xE3o disparada \u2014 o ciclo pode levar alguns minutos.");
      clearInterval(pollRef.current);
      let n = 0;
      pollRef.current = setInterval(() => {
        load();
        onRan && onRan();
        if (++n >= 12) clearInterval(pollRef.current);
      }, 6e3);
      setTimeout(() => {
        load();
        onRan && onRan();
      }, 1500);
    } catch (err) {
      showToast("Erro: " + err.message, "err");
    } finally {
      setRunning(false);
    }
  };
  const mon = status?.monitoring_enabled;
  const dotClass = "dot" + (status ? mon ? "" : " paused" : failed ? " paused" : " off");
  return /* @__PURE__ */ React.createElement("div", { className: "card status-card" }, /* @__PURE__ */ React.createElement("div", { className: "status-stats" }, /* @__PURE__ */ React.createElement("div", { className: "status-item" }, /* @__PURE__ */ React.createElement("span", { className: "label" }, "Monitoramento"), /* @__PURE__ */ React.createElement("span", { className: "value" }, /* @__PURE__ */ React.createElement("span", { className: dotClass }), status ? mon ? "Ativo" : "Pausado" : failed ? "Indispon\xEDvel" : "\u2026", status && !status.filters_enabled ? " \xB7 sem filtros" : "")), /* @__PURE__ */ React.createElement("div", { className: "status-item" }, /* @__PURE__ */ React.createElement("span", { className: "label" }, "\xDAltima verifica\xE7\xE3o"), /* @__PURE__ */ React.createElement("span", { className: "value" }, status ? timeAgo(status.last_check_at) : ph)), /* @__PURE__ */ React.createElement("div", { className: "status-item" }, /* @__PURE__ */ React.createElement("span", { className: "label" }, "Posts (24h)"), /* @__PURE__ */ React.createElement("span", { className: "value" }, status ? status.posts_24h : ph)), /* @__PURE__ */ React.createElement("div", { className: "status-item" }, /* @__PURE__ */ React.createElement("span", { className: "label" }, "Vigiados"), /* @__PURE__ */ React.createElement("span", { className: "value" }, status ? status.watched_count : ph)), /* @__PURE__ */ React.createElement("div", { className: "status-item" }, /* @__PURE__ */ React.createElement("span", { className: "label" }, "Descobertos"), /* @__PURE__ */ React.createElement("span", { className: "value" }, status ? status.discovered_count : ph))), /* @__PURE__ */ React.createElement(
    "button",
    {
      className: "btn btn-primary",
      onClick: runNow,
      disabled: running || !mon,
      title: failed ? "Status indispon\xEDvel \u2014 backend pode estar desatualizado" : mon === false ? "Ative o monitoramento para verificar" : "Roda um ciclo agora, sem esperar o intervalo"
    },
    /* @__PURE__ */ React.createElement(Icon.bolt, { style: { width: 15, height: 15 } }),
    " ",
    running ? "Disparando..." : "Verificar agora"
  ));
}
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
  useEffect(() => {
    load();
  }, [load]);
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
    if (!confirm(`Excluir os ${discovered.length} produtos descobertos automaticamente? A watchlist \xE9 mantida.`)) return;
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
      showToast(target === null ? "Pre\xE7o-alvo removido." : "Pre\xE7o-alvo atualizado.");
      load();
    } catch (err) {
      showToast("Erro: " + err.message, "err");
    }
  };
  const handleWatch = async (id) => {
    try {
      await api.watchProduct(id);
      showToast("Adicionado \xE0 watchlist.");
      load();
    } catch (err) {
      showToast("Erro: " + err.message, "err");
    }
  };
  return /* @__PURE__ */ React.createElement("div", { className: "page" }, /* @__PURE__ */ React.createElement("div", { className: "page-head", style: { display: "flex", alignItems: "flex-start", justifyContent: "space-between" } }, /* @__PURE__ */ React.createElement("div", null, /* @__PURE__ */ React.createElement("div", { className: "page-title" }, "Produtos"), /* @__PURE__ */ React.createElement("div", { className: "page-desc" }, "Watchlist s\xE3o os itens que voc\xEA adiciona \xE0 m\xE3o. Descobertos s\xE3o achados automaticamente pelo bot.")), /* @__PURE__ */ React.createElement("button", { className: "btn btn-secondary", onClick: load, disabled: loading, style: { marginTop: 2 } }, /* @__PURE__ */ React.createElement(Icon.refresh, null), " Atualizar")), /* @__PURE__ */ React.createElement(StatusBar, { api, showToast, onRan: load }), loading ? /* @__PURE__ */ React.createElement("div", { className: "card table-card" }, /* @__PURE__ */ React.createElement("div", { className: "empty" }, /* @__PURE__ */ React.createElement("div", { className: "empty-sub" }, "Carregando..."))) : /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("div", { className: "section-head" }, /* @__PURE__ */ React.createElement("div", { className: "section-title" }, "\u{1F441} Watchlist ", watched.length > 0 && /* @__PURE__ */ React.createElement("span", { className: "count-pill" }, watched.length))), /* @__PURE__ */ React.createElement("div", { className: "card table-card" }, watched.length === 0 ? /* @__PURE__ */ React.createElement("div", { className: "empty" }, /* @__PURE__ */ React.createElement("div", { className: "empty-sub" }, 'Nenhum produto vigiado. Adicione um na aba "Adicionar produto".')) : /* @__PURE__ */ React.createElement(ProductTable, { rows: watched, onDelete: handleDelete, onSaveTarget: handleSaveTarget })), /* @__PURE__ */ React.createElement("div", { className: "section-head", style: { display: "flex", alignItems: "center", justifyContent: "space-between" } }, /* @__PURE__ */ React.createElement("div", { className: "section-title" }, "\u{1F50D} Descobertos automaticamente ", discovered.length > 0 && /* @__PURE__ */ React.createElement("span", { className: "count-pill" }, discovered.length)), discovered.length > 0 && /* @__PURE__ */ React.createElement("button", { className: "btn btn-ghost-danger", onClick: handleClearDiscovered, disabled: clearing }, /* @__PURE__ */ React.createElement(Icon.trash, null), " ", clearing ? "Limpando..." : "Limpar lista")), /* @__PURE__ */ React.createElement("div", { className: "card table-card" }, discovered.length === 0 ? /* @__PURE__ */ React.createElement("div", { className: "empty" }, /* @__PURE__ */ React.createElement("div", { className: "empty-sub" }, "Nenhum produto descoberto no momento.")) : /* @__PURE__ */ React.createElement(ProductTable, { rows: discovered, onDelete: handleDelete, onWatch: handleWatch, showTarget: false }))));
}
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
      showToast("Produto adicionado \xE0 watchlist.");
      setValue("");
      setTarget("");
      onAdded();
    } catch (err) {
      showToast("Erro: " + err.message, "err");
    } finally {
      setLoading(false);
    }
  };
  return /* @__PURE__ */ React.createElement("div", { className: "page" }, /* @__PURE__ */ React.createElement("div", { className: "page-head" }, /* @__PURE__ */ React.createElement("div", { className: "page-title" }, "Adicionar produto"), /* @__PURE__ */ React.createElement("div", { className: "page-desc" }, "Cole a URL do produto na AliExpress ou informe o ID. O bot passa a vigiar esse item todo ciclo e posta quando o pre\xE7o final (cupom + impostos) atingir o alvo ou o pre\xE7o cair abaixo do m\xEDnimo recente.")), /* @__PURE__ */ React.createElement("form", { className: "card add-card", onSubmit: submit }, /* @__PURE__ */ React.createElement("label", { className: "field-label", htmlFor: "add-url" }, "URL ou ID do produto"), /* @__PURE__ */ React.createElement(
    "input",
    {
      id: "add-url",
      className: "input mono",
      type: "text",
      placeholder: "https://aliexpress.com/item/1005006789012.html",
      value,
      onChange: (e) => setValue(e.target.value),
      autoFocus: true,
      disabled: loading
    }
  ), /* @__PURE__ */ React.createElement("div", { className: "field-hint" }, "Aceita link completo, link curto ou apenas o ID num\xE9rico do item."), /* @__PURE__ */ React.createElement("label", { className: "field-label", htmlFor: "add-target", style: { marginTop: 18, display: "block" } }, "Pre\xE7o-alvo (opcional)"), /* @__PURE__ */ React.createElement("div", { className: "num-input-wrap" }, /* @__PURE__ */ React.createElement(
    "input",
    {
      id: "add-target",
      className: "input mono",
      type: "number",
      min: "0",
      step: "0.01",
      placeholder: "ex: 199,90",
      value: target,
      onChange: (e) => setTarget(e.target.value),
      disabled: loading
    }
  ), /* @__PURE__ */ React.createElement("span", { className: "num-suffix" }, "R$")), /* @__PURE__ */ React.createElement("div", { className: "field-hint" }, "Se definido, o bot posta assim que o pre\xE7o ", /* @__PURE__ */ React.createElement("b", null, "final estimado"), " (com cupom e impostos do checkout, sem frete) chegar nesse valor ou abaixo. Sem alvo, posta quando cair abaixo do m\xEDnimo dos \xFAltimos 30 dias."), /* @__PURE__ */ React.createElement("div", { style: { marginTop: 20 } }, /* @__PURE__ */ React.createElement("button", { className: "btn btn-primary", type: "submit", disabled: !value.trim() || loading }, /* @__PURE__ */ React.createElement(Icon.plus, null), " ", loading ? "Adicionando..." : "Adicionar"))));
}
function ControlToggle({ label, hint, on, disabled, onChange }) {
  return /* @__PURE__ */ React.createElement("div", { className: "control-row" }, /* @__PURE__ */ React.createElement("div", { className: "control-meta" }, /* @__PURE__ */ React.createElement("label", { className: "field-label" }, label), /* @__PURE__ */ React.createElement("div", { className: "field-hint", style: { marginTop: 2 } }, hint)), /* @__PURE__ */ React.createElement(
    "button",
    {
      type: "button",
      role: "switch",
      "aria-checked": on,
      "aria-label": label,
      className: "switch" + (on ? " on" : ""),
      disabled,
      onClick: () => onChange(!on)
    }
  ));
}
function NumberSetting({ label, hint, value, suffix, onChange, min = 0 }) {
  return /* @__PURE__ */ React.createElement("div", { className: "setting-row" }, /* @__PURE__ */ React.createElement("div", { className: "setting-meta" }, /* @__PURE__ */ React.createElement("label", { className: "field-label" }, label), /* @__PURE__ */ React.createElement("div", { className: "field-hint", style: { marginTop: 2 } }, hint)), /* @__PURE__ */ React.createElement("div", { className: "setting-control" }, /* @__PURE__ */ React.createElement("div", { className: "num-input-wrap" }, /* @__PURE__ */ React.createElement(
    "input",
    {
      className: "input mono",
      type: "number",
      min,
      value,
      onChange: (e) => onChange(e.target.value === "" ? "" : Number(e.target.value))
    }
  ), suffix && /* @__PURE__ */ React.createElement("span", { className: "num-suffix" }, suffix))));
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
    api.getCoupons().then(setCoupons).catch(() => {
    });
  }, [api]);
  useEffect(() => {
    api.getSettings().then((s) => setDraft(fromApi(s))).catch((err) => showToast("Erro ao carregar configura\xE7\xF5es: " + err.message, "err"));
    loadCoupons();
  }, [api, loadCoupons]);
  const addCoupon = async () => {
    const code = cpForm.code.trim();
    if (!code) {
      showToast("Informe o c\xF3digo do cupom.", "err");
      return;
    }
    setCpSaving(true);
    try {
      await api.addCoupon({
        code,
        min_spend: Number(cpForm.min_spend || 0),
        discount: Number(cpForm.discount || 0),
        expires_at: cpForm.expires_at || null
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
    if (!k || draft.keywords.includes(k)) {
      setKwInput("");
      return;
    }
    set({ keywords: [...draft.keywords, k] });
    setKwInput("");
  };
  const removeKeyword = (k) => set({ keywords: draft.keywords.filter((x) => x !== k) });
  const onKwKey = (e) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addKeyword();
    } else if (e.key === "Backspace" && !kwInput && draft.keywords.length) {
      set({ keywords: draft.keywords.slice(0, -1) });
    }
  };
  const addBlacklist = () => {
    const k = blInput.trim().toLowerCase();
    if (!k || draft.blacklist.includes(k)) {
      setBlInput("");
      return;
    }
    set({ blacklist: [...draft.blacklist, k] });
    setBlInput("");
  };
  const removeBlacklist = (k) => set({ blacklist: draft.blacklist.filter((x) => x !== k) });
  const onBlKey = (e) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addBlacklist();
    } else if (e.key === "Backspace" && !blInput && draft.blacklist.length) {
      set({ blacklist: draft.blacklist.slice(0, -1) });
    }
  };
  const [sbInput, setSbInput] = useState("");
  const addShopeeBrand = () => {
    const k = sbInput.trim().toLowerCase();
    if (!k || draft.shopeeBrands.includes(k)) {
      setSbInput("");
      return;
    }
    set({ shopeeBrands: [...draft.shopeeBrands, k] });
    setSbInput("");
  };
  const removeShopeeBrand = (k) => set({ shopeeBrands: draft.shopeeBrands.filter((x) => x !== k) });
  const onSbKey = (e) => {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      addShopeeBrand();
    } else if (e.key === "Backspace" && !sbInput && draft.shopeeBrands.length) {
      set({ shopeeBrands: draft.shopeeBrands.slice(0, -1) });
    }
  };
  const addBrand = () => {
    const name = newBrandInput.trim();
    if (!name || draft.brands.some((b) => b.name.toLowerCase() === name.toLowerCase())) {
      setNewBrandInput("");
      return;
    }
    set({ brands: [...draft.brands, { name, keywords: [] }] });
    setNewBrandInput("");
  };
  const removeBrand = (idx) => set({ brands: draft.brands.filter((_, i) => i !== idx) });
  const addBrandKw = (idx) => {
    const key = draft.brands[idx].name;
    const kw = (brandKwInputs[key] || "").trim().toLowerCase();
    if (!kw || draft.brands[idx].keywords.includes(kw)) {
      setBrandKwInputs((p) => ({ ...p, [key]: "" }));
      return;
    }
    set({ brands: draft.brands.map((b, i) => i === idx ? { ...b, keywords: [...b.keywords, kw] } : b) });
    setBrandKwInputs((p) => ({ ...p, [key]: "" }));
  };
  const removeBrandKw = (idx, kw) => set({
    brands: draft.brands.map((b, i) => i === idx ? { ...b, keywords: b.keywords.filter((k) => k !== kw) } : b)
  });
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
      showToast("Configura\xE7\xF5es salvas.");
    } catch (err) {
      showToast("Erro ao salvar: " + err.message, "err");
    } finally {
      setSaving(false);
    }
  };
  if (!draft) return /* @__PURE__ */ React.createElement("div", { className: "page" }, /* @__PURE__ */ React.createElement("div", { className: "empty" }, /* @__PURE__ */ React.createElement("div", { className: "empty-sub" }, "Carregando...")));
  return /* @__PURE__ */ React.createElement("div", { className: "page" }, /* @__PURE__ */ React.createElement("div", { className: "page-head" }, /* @__PURE__ */ React.createElement("div", { className: "page-title" }, "Configura\xE7\xF5es"), /* @__PURE__ */ React.createElement("div", { className: "page-desc" }, "Regras de monitoramento e de postagem no canal do Telegram.")), /* @__PURE__ */ React.createElement("div", { className: "card control-card" }, /* @__PURE__ */ React.createElement(
    ControlToggle,
    {
      label: "Monitoramento ativo",
      hint: "Chave-mestra. Desligado, o bot para de buscar e postar \u2014 nada \xE9 perdido, \xE9 s\xF3 religar.",
      on: draft.monitoring,
      onChange: (v) => toggleControl("monitoring", "monitoring_enabled", v)
    }
  ), /* @__PURE__ */ React.createElement(
    ControlToggle,
    {
      label: "Filtros ativos",
      hint: "Keywords, blacklist e marcas. Desligado, o bot considera qualquer produto das categorias (as listas continuam salvas).",
      on: draft.filters,
      onChange: (v) => toggleControl("filters", "filters_enabled", v)
    }
  )), /* @__PURE__ */ React.createElement("div", { className: "card form-card" }, /* @__PURE__ */ React.createElement("div", { className: "settings-grid" }, /* @__PURE__ */ React.createElement(
    NumberSetting,
    {
      label: "Queda m\xEDnima de pre\xE7o (%)",
      hint: "S\xF3 posta quando o pre\xE7o cair pelo menos esse percentual em rela\xE7\xE3o ao m\xEDnimo hist\xF3rico.",
      value: draft.minDrop,
      suffix: "%",
      onChange: (v) => set({ minDrop: v }),
      min: 1
    }
  ), /* @__PURE__ */ React.createElement(
    NumberSetting,
    {
      label: "Desconto m\xEDnimo para novos produtos (%)",
      hint: "Para produtos sem hist\xF3rico de pre\xE7o, s\xF3 posta se o desconto sobre o original for pelo menos esse valor.",
      value: draft.coldStart,
      suffix: "%",
      onChange: (v) => set({ coldStart: v }),
      min: 1
    }
  ), /* @__PURE__ */ React.createElement(
    NumberSetting,
    {
      label: "M\xE1ximo de posts por ciclo",
      hint: "Limite de produtos postados a cada verifica\xE7\xE3o.",
      value: draft.maxPosts,
      suffix: "posts",
      onChange: (v) => set({ maxPosts: v }),
      min: 1
    }
  ), /* @__PURE__ */ React.createElement(
    NumberSetting,
    {
      label: "M\xE1ximo de posts por dia",
      hint: "Teto de seguran\xE7a nas \xFAltimas 24h. Atingido o limite, o bot para de postar at\xE9 o dia virar \u2014 protege o canal de flood se muitos produtos parecerem em promo\xE7\xE3o ao mesmo tempo.",
      value: draft.maxDaily,
      suffix: "posts",
      onChange: (v) => set({ maxDaily: v }),
      min: 1
    }
  ), /* @__PURE__ */ React.createElement(
    NumberSetting,
    {
      label: "Intervalo de verifica\xE7\xE3o (minutos)",
      hint: "Com que frequ\xEAncia o bot consulta os pre\xE7os na AliExpress.",
      value: draft.interval,
      suffix: "min",
      onChange: (v) => set({ interval: v })
    }
  ), /* @__PURE__ */ React.createElement(
    NumberSetting,
    {
      label: "Dias m\xEDnimos entre reposts",
      hint: "Evita repostar o mesmo produto antes de passar esse per\xEDodo.",
      value: draft.minDays,
      suffix: "dias",
      onChange: (v) => set({ minDays: v })
    }
  ), /* @__PURE__ */ React.createElement(
    NumberSetting,
    {
      label: "Imposto de importa\xE7\xE3o (%)",
      hint: "II federal somado no checkout. Zerado por MP para compras at\xE9 US$50 desde mai/2026 \u2014 ajuste aqui se a regra mudar.",
      value: draft.importTax,
      suffix: "%",
      onChange: (v) => set({ importTax: v }),
      min: 0
    }
  ), /* @__PURE__ */ React.createElement(
    NumberSetting,
    {
      label: "ICMS no checkout (%)",
      hint: "Cobrado 'por dentro' pelo AliExpress no pagamento (17\u201320% conforme o estado). Usado no total estimado do post.",
      value: draft.icms,
      suffix: "%",
      onChange: (v) => set({ icms: v }),
      min: 0
    }
  ), /* @__PURE__ */ React.createElement("div", { className: "setting-row", style: { gridTemplateColumns: "1fr", paddingBottom: 4 } }, /* @__PURE__ */ React.createElement("div", { className: "setting-meta" }, /* @__PURE__ */ React.createElement("label", { className: "field-label" }, "Cupons de campanha"), /* @__PURE__ */ React.createElement("div", { className: "field-hint", style: { marginTop: 2 } }, "Cupons que o bot aplica nos posts. Os ", /* @__PURE__ */ React.createElement("b", null, "manuais"), " voc\xEA adiciona aqui (com validade, se quiser \u2014 vencido, sai sozinho). Os ", /* @__PURE__ */ React.createElement("b", null, "autom\xE1ticos"), " s\xE3o descobertos nos an\xFAncios que o bot escaneia e valem por 72h desde a \xFAltima vez que foram vistos.")), /* @__PURE__ */ React.createElement("div", { className: "coupon-form" }, /* @__PURE__ */ React.createElement(
    "input",
    {
      className: "input",
      placeholder: "C\xF3digo",
      value: cpForm.code,
      onChange: (e) => setCpForm({ ...cpForm, code: e.target.value })
    }
  ), /* @__PURE__ */ React.createElement(
    "input",
    {
      className: "input mono",
      type: "number",
      min: "0",
      step: "0.01",
      placeholder: "Gasto m\xEDn.",
      value: cpForm.min_spend,
      onChange: (e) => setCpForm({ ...cpForm, min_spend: e.target.value })
    }
  ), /* @__PURE__ */ React.createElement(
    "input",
    {
      className: "input mono",
      type: "number",
      min: "0",
      step: "0.01",
      placeholder: "Desconto",
      value: cpForm.discount,
      onChange: (e) => setCpForm({ ...cpForm, discount: e.target.value })
    }
  ), /* @__PURE__ */ React.createElement(
    "input",
    {
      className: "input mono",
      type: "date",
      title: "Validade (opcional)",
      value: cpForm.expires_at,
      onChange: (e) => setCpForm({ ...cpForm, expires_at: e.target.value })
    }
  ), /* @__PURE__ */ React.createElement("button", { type: "button", className: "btn btn-secondary", onClick: addCoupon, disabled: cpSaving }, /* @__PURE__ */ React.createElement(Icon.plus, null), " Adicionar")), coupons.length === 0 ? /* @__PURE__ */ React.createElement("div", { className: "no-tags", style: { marginTop: 10 } }, "Nenhum cupom ativo no momento.") : /* @__PURE__ */ React.createElement("div", { className: "coupon-list" }, coupons.map((c) => /* @__PURE__ */ React.createElement("div", { className: "coupon-row" + (c.active ? "" : " expired"), key: c.code }, /* @__PURE__ */ React.createElement("span", { className: "coupon-code" }, c.code), /* @__PURE__ */ React.createElement("span", { className: "coupon-vals" }, "\u2212R$ ", Number(c.discount).toFixed(2), " \xB7 m\xEDn. R$ ", Number(c.min_spend).toFixed(2)), /* @__PURE__ */ React.createElement("span", { className: "coupon-src" + (c.source === "manual" ? " manual" : "") }, c.source === "manual" ? "manual" : "auto"), /* @__PURE__ */ React.createElement("span", { className: "coupon-exp" }, c.expires_at ? (c.active ? "vence " : "venceu ") + new Date(c.expires_at).toLocaleDateString("pt-BR") : c.source === "manual" ? "sem validade" : ""), /* @__PURE__ */ React.createElement(
    "button",
    {
      type: "button",
      className: "btn btn-ghost-danger",
      title: "Remover cupom",
      onClick: () => removeCoupon(c.code)
    },
    /* @__PURE__ */ React.createElement(Icon.trash, null)
  ))))), /* @__PURE__ */ React.createElement("div", { className: "setting-row", style: { gridTemplateColumns: "1fr", paddingBottom: 4 } }, /* @__PURE__ */ React.createElement("div", { className: "setting-meta" }, /* @__PURE__ */ React.createElement("label", { className: "field-label" }, "Marcas da Shopee"), /* @__PURE__ */ React.createElement("div", { className: "field-hint", style: { marginTop: 2 } }, "Whitelist separada da AliExpress \u2014 as marcas de l\xE1 (akko, mchose, attack shark...) quase n\xE3o existem no varejo nacional, ent\xE3o a Shopee tem a sua. Deixe vazio para aceitar qualquer marca que passe nos filtros de qualidade.")), /* @__PURE__ */ React.createElement("div", { className: "tags-box" }, draft.shopeeBrands.length > 0 ? /* @__PURE__ */ React.createElement("div", { className: "tags-wrap" }, draft.shopeeBrands.map((k) => /* @__PURE__ */ React.createElement("span", { className: "tag", key: k }, k, /* @__PURE__ */ React.createElement("button", { type: "button", onClick: () => removeShopeeBrand(k), "aria-label": "Remover " + k }, /* @__PURE__ */ React.createElement(Icon.x, null))))) : /* @__PURE__ */ React.createElement("div", { className: "no-tags" }, "Sem filtro de marca na Shopee."), /* @__PURE__ */ React.createElement("div", { className: "tag-add-row" }, /* @__PURE__ */ React.createElement(
    "input",
    {
      className: "input",
      type: "text",
      placeholder: "Digite e pressione Enter",
      value: sbInput,
      onChange: (e) => setSbInput(e.target.value),
      onKeyDown: onSbKey
    }
  ), /* @__PURE__ */ React.createElement("button", { type: "button", className: "btn btn-secondary", onClick: addShopeeBrand }, /* @__PURE__ */ React.createElement(Icon.plus, null), " Add")))), /* @__PURE__ */ React.createElement("div", { className: "setting-row", style: { gridTemplateColumns: "1fr", paddingBottom: 4 } }, /* @__PURE__ */ React.createElement("div", { className: "setting-meta" }, /* @__PURE__ */ React.createElement("label", { className: "field-label" }, "Keywords de perif\xE9ricos"), /* @__PURE__ */ React.createElement("div", { className: "field-hint", style: { marginTop: 2 } }, "Produtos cujo t\xEDtulo cont\xE9m uma destas palavras s\xE3o monitorados pelo bot.")), /* @__PURE__ */ React.createElement("div", { className: "tags-box" }, draft.keywords.length > 0 ? /* @__PURE__ */ React.createElement("div", { className: "tags-wrap" }, draft.keywords.map((k) => /* @__PURE__ */ React.createElement("span", { className: "tag", key: k }, k, /* @__PURE__ */ React.createElement("button", { type: "button", onClick: () => removeKeyword(k), "aria-label": "Remover " + k }, /* @__PURE__ */ React.createElement(Icon.x, null))))) : /* @__PURE__ */ React.createElement("div", { className: "no-tags" }, "Nenhuma keyword adicionada."), /* @__PURE__ */ React.createElement("div", { className: "tag-add-row" }, /* @__PURE__ */ React.createElement(
    "input",
    {
      className: "input",
      type: "text",
      placeholder: "Digite e pressione Enter",
      value: kwInput,
      onChange: (e) => setKwInput(e.target.value),
      onKeyDown: onKwKey
    }
  ), /* @__PURE__ */ React.createElement("button", { type: "button", className: "btn btn-secondary", onClick: addKeyword }, /* @__PURE__ */ React.createElement(Icon.plus, null), " Add")))), /* @__PURE__ */ React.createElement("div", { className: "setting-row", style: { gridTemplateColumns: "1fr", paddingBottom: 4 } }, /* @__PURE__ */ React.createElement("div", { className: "setting-meta" }, /* @__PURE__ */ React.createElement("label", { className: "field-label" }, "Blacklist de palavras"), /* @__PURE__ */ React.createElement("div", { className: "field-hint", style: { marginTop: 2 } }, "Produtos cujo t\xEDtulo contiver qualquer uma dessas palavras s\xE3o ignorados.")), /* @__PURE__ */ React.createElement("div", { className: "tags-box" }, draft.blacklist.length > 0 ? /* @__PURE__ */ React.createElement("div", { className: "tags-wrap" }, draft.blacklist.map((k) => /* @__PURE__ */ React.createElement("span", { className: "tag tag-danger", key: k }, k, /* @__PURE__ */ React.createElement("button", { type: "button", onClick: () => removeBlacklist(k), "aria-label": "Remover " + k }, /* @__PURE__ */ React.createElement(Icon.x, null))))) : /* @__PURE__ */ React.createElement("div", { className: "no-tags" }, "Nenhuma palavra bloqueada."), /* @__PURE__ */ React.createElement("div", { className: "tag-add-row" }, /* @__PURE__ */ React.createElement(
    "input",
    {
      className: "input",
      type: "text",
      placeholder: "Digite e pressione Enter",
      value: blInput,
      onChange: (e) => setBlInput(e.target.value),
      onKeyDown: onBlKey
    }
  ), /* @__PURE__ */ React.createElement("button", { type: "button", className: "btn btn-secondary", onClick: addBlacklist }, /* @__PURE__ */ React.createElement(Icon.plus, null), " Add")))), /* @__PURE__ */ React.createElement("div", { className: "setting-row", style: { gridTemplateColumns: "1fr", borderBottom: "none", paddingBottom: 4 } }, /* @__PURE__ */ React.createElement("div", { className: "setting-meta" }, /* @__PURE__ */ React.createElement("label", { className: "field-label" }, "Whitelist de marcas"), /* @__PURE__ */ React.createElement("div", { className: "field-hint", style: { marginTop: 2 } }, "S\xF3 posta produtos das marcas listadas. Adicione filtros por tipo de produto em cada marca (ex: s\xF3 mouses da ATK). Vazio = aceita qualquer marca.")), /* @__PURE__ */ React.createElement("div", { className: "tags-box" }, draft.brands.length === 0 && /* @__PURE__ */ React.createElement("div", { className: "no-tags" }, "Vazio \u2014 todas as marcas aceitas."), draft.brands.map((entry, idx) => {
    const bKey = entry.name;
    const kwVal = brandKwInputs[bKey] || "";
    const addKw = () => addBrandKw(idx);
    return /* @__PURE__ */ React.createElement("div", { key: bKey, className: "brand-entry" }, /* @__PURE__ */ React.createElement("div", { className: "brand-entry-head" }, /* @__PURE__ */ React.createElement("span", { className: "brand-entry-name" }, entry.name), /* @__PURE__ */ React.createElement("button", { type: "button", className: "btn btn-ghost-danger", onClick: () => removeBrand(idx), "aria-label": "Remover " + entry.name }, /* @__PURE__ */ React.createElement(Icon.trash, null))), /* @__PURE__ */ React.createElement("div", { className: "brand-entry-kws" }, entry.keywords.length === 0 ? /* @__PURE__ */ React.createElement("span", { className: "brand-kws-empty" }, "Todos os produtos desta marca") : /* @__PURE__ */ React.createElement("div", { className: "tags-wrap", style: { marginBottom: 8 } }, entry.keywords.map((kw) => /* @__PURE__ */ React.createElement("span", { className: "tag", key: kw }, kw, /* @__PURE__ */ React.createElement("button", { type: "button", onClick: () => removeBrandKw(idx, kw), "aria-label": "Remover " + kw }, /* @__PURE__ */ React.createElement(Icon.x, null))))), /* @__PURE__ */ React.createElement("div", { className: "tag-add-row" }, /* @__PURE__ */ React.createElement(
      "input",
      {
        className: "input",
        type: "text",
        placeholder: "tipo de produto (ex: mouse)",
        style: { fontSize: 12.5 },
        value: kwVal,
        onChange: (e) => setBrandKwInputs((p) => ({ ...p, [bKey]: e.target.value })),
        onKeyDown: (e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            addKw();
          }
        }
      }
    ), /* @__PURE__ */ React.createElement("button", { type: "button", className: "btn btn-secondary", onClick: addKw }, /* @__PURE__ */ React.createElement(Icon.plus, null), " Add"))));
  }), /* @__PURE__ */ React.createElement("div", { className: "tag-add-row", style: { marginTop: draft.brands.length > 0 ? 8 : 0 } }, /* @__PURE__ */ React.createElement(
    "input",
    {
      className: "input",
      type: "text",
      placeholder: "Nome da marca (ex: Logitech)",
      value: newBrandInput,
      onChange: (e) => setNewBrandInput(e.target.value),
      onKeyDown: (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          addBrand();
        }
      }
    }
  ), /* @__PURE__ */ React.createElement("button", { type: "button", className: "btn btn-secondary", onClick: addBrand }, /* @__PURE__ */ React.createElement(Icon.plus, null), " Marca"))))), /* @__PURE__ */ React.createElement("div", { className: "form-footer" }, /* @__PURE__ */ React.createElement("span", { className: "save-hint" + (savedFlash ? " saved-flash" : "") }, savedFlash ? "Configura\xE7\xF5es salvas." : "As altera\xE7\xF5es se aplicam \xE0 pr\xF3xima verifica\xE7\xE3o."), /* @__PURE__ */ React.createElement("button", { className: "btn btn-primary", onClick: handleSave, disabled: saving }, saving ? "Salvando..." : "Salvar configura\xE7\xF5es"))));
}
const AFFILIATE_PANELS = [
  { name: "AliExpress", url: "https://portals.aliexpress.com/", color: "#ff4747" },
  { name: "Shopee", url: "https://affiliate.shopee.com.br/", color: "#ee4d2d" },
  { name: "Mercado Livre", url: "https://www.mercadolivre.com.br/afiliados/", color: "#ffe600" }
];
function AffiliatePanelLinks() {
  return /* @__PURE__ */ React.createElement("div", { className: "panel-links" }, /* @__PURE__ */ React.createElement("span", { className: "panel-links-label" }, "Pain\xE9is de afiliado"), AFFILIATE_PANELS.map((p) => /* @__PURE__ */ React.createElement(
    "a",
    {
      key: p.name,
      className: "card panel-link",
      href: p.url,
      target: "_blank",
      rel: "noopener noreferrer"
    },
    /* @__PURE__ */ React.createElement("span", { className: "panel-dot", style: { background: p.color } }),
    p.name,
    /* @__PURE__ */ React.createElement(Icon.external, { className: "panel-link-arrow" })
  )));
}
const SALES_PERIODS = [7, 30, 90];
function topRoundedBarPath(x, y, w, h, r) {
  if (h <= 0) return "";
  r = Math.min(r, w / 2, h);
  return `M${x},${y + h} L${x},${y + r} Q${x},${y} ${x + r},${y} L${x + w - r},${y} Q${x + w},${y} ${x + w},${y + r} L${x + w},${y + h} Z`;
}
function niceCeil(v) {
  if (v <= 0) return 1;
  const mag = Math.pow(10, Math.floor(Math.log10(v)));
  for (const step of [1, 2, 5, 10]) {
    if (step * mag >= v) return step * mag;
  }
  return 10 * mag;
}
function SalesChart({ series, days, currency }) {
  const byDate = new Map(series.map((d) => [d.order_date, d]));
  const points = [];
  for (let i = days - 1; i >= 0; i--) {
    const d = /* @__PURE__ */ new Date();
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
  const yScale = (v) => max > 0 ? v / max * (baseline - padT) : 0;
  const tickEvery = Math.max(1, Math.ceil(n / 6));
  return /* @__PURE__ */ React.createElement("div", { style: { position: "relative" } }, /* @__PURE__ */ React.createElement("svg", { viewBox: `0 0 ${W} ${H}`, width: "100%", height: H, role: "img", "aria-label": `Receita di\xE1ria, \xFAltimos ${days} dias` }, /* @__PURE__ */ React.createElement("line", { x1: padL, y1: baseline, x2: W - padR, y2: baseline, stroke: "var(--border-soft)", strokeWidth: "1" }), /* @__PURE__ */ React.createElement("line", { x1: padL, y1: padT, x2: W - padR, y2: padT, stroke: "var(--border-soft)", strokeWidth: "1" }), /* @__PURE__ */ React.createElement("text", { x: W - padR, y: padT - 5, textAnchor: "end", fontSize: "10.5", fill: "var(--muted-2)", fontFamily: "var(--mono)" }, fmtMoney(max, currency)), points.map((p, i) => {
    const h = Math.max(hasAny && p.paid_total > 0 ? 2 : 0, yScale(p.paid_total));
    const y = baseline - h;
    const x = xOf(i);
    const isHover = hover === i;
    return /* @__PURE__ */ React.createElement(
      "g",
      {
        key: p.date,
        onMouseEnter: () => setHover(i),
        onMouseLeave: () => setHover((v) => v === i ? null : v),
        onFocus: () => setHover(i),
        onBlur: () => setHover((v) => v === i ? null : v),
        tabIndex: 0,
        role: "img",
        "aria-label": `${p.date}: ${fmtMoney(p.paid_total, currency)}, ${p.count} venda(s)`
      },
      /* @__PURE__ */ React.createElement("rect", { x: x - (slot - barW) / 2, y: padT, width: slot, height: baseline - padT, fill: "transparent" }),
      /* @__PURE__ */ React.createElement(
        "path",
        {
          d: topRoundedBarPath(x, y, barW, h, 4),
          fill: "var(--green)",
          opacity: isHover ? 1 : 0.8,
          style: { transition: "opacity .1s ease" }
        }
      ),
      i % tickEvery === 0 && /* @__PURE__ */ React.createElement("text", { x: x + barW / 2, y: H - 8, textAnchor: "middle", fontSize: "10", fill: "var(--muted-2)", fontFamily: "var(--mono)" }, p.date.slice(5))
    );
  })), hover != null && /* @__PURE__ */ React.createElement("div", { className: "chart-tooltip", style: { left: `${(xOf(hover) + barW / 2) / W * 100}%` } }, /* @__PURE__ */ React.createElement("div", { className: "chart-tooltip-value" }, fmtMoney(points[hover].paid_total, currency)), /* @__PURE__ */ React.createElement("div", { className: "chart-tooltip-label" }, (/* @__PURE__ */ new Date(points[hover].date + "T00:00:00")).toLocaleDateString("pt-BR"), " \xB7 ", points[hover].count, " venda", points[hover].count === 1 ? "" : "s")));
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
  useEffect(() => {
    load();
  }, [load]);
  const summary = data?.summary;
  const orders = data?.orders ?? [];
  const toggleExcluded = async (o) => {
    try {
      await api.excludeOrder(o.order_id, o.sub_order_id, !o.excluded);
      showToast(o.excluded ? "Pedido reinclu\xEDdo nos totais." : "Pedido marcado como compra pr\xF3pria.");
      load();
    } catch (err) {
      showToast("Erro: " + err.message, "err");
    }
  };
  return /* @__PURE__ */ React.createElement("div", { className: "page" }, /* @__PURE__ */ React.createElement("div", { className: "page-head" }, /* @__PURE__ */ React.createElement("div", { className: "page-title" }, "Vendas"), /* @__PURE__ */ React.createElement("div", { className: "page-desc" }, "Pedidos e comiss\xE3o rastreados pela API de afiliados da AliExpress. Sincroniza a cada ciclo do bot.")), /* @__PURE__ */ React.createElement(AffiliatePanelLinks, null), /* @__PURE__ */ React.createElement("div", { className: "period-toggle" }, SALES_PERIODS.map((p) => /* @__PURE__ */ React.createElement("button", { key: p, className: "period-btn" + (days === p ? " active" : ""), onClick: () => setDays(p) }, p, " dias"))), /* @__PURE__ */ React.createElement("div", { className: "sales-stats" }, /* @__PURE__ */ React.createElement("div", { className: "card sales-stat" }, /* @__PURE__ */ React.createElement("span", { className: "label" }, "Vendas no per\xEDodo"), /* @__PURE__ */ React.createElement("span", { className: "stat-value" }, loading ? "\u2026" : summary?.count ?? 0)), /* @__PURE__ */ React.createElement("div", { className: "card sales-stat" }, /* @__PURE__ */ React.createElement("span", { className: "label", title: "Soma da base de comiss\xE3o \u2014 valor do produto antes dos cupons do comprador" }, "Valor base"), /* @__PURE__ */ React.createElement("span", { className: "stat-value" }, loading ? "\u2026" : fmtMoney(summary?.paid_total, summary?.currency))), /* @__PURE__ */ React.createElement("div", { className: "card sales-stat" }, /* @__PURE__ */ React.createElement("span", { className: "label" }, "Comiss\xE3o estimada"), /* @__PURE__ */ React.createElement("span", { className: "stat-value accent" }, loading ? "\u2026" : fmtMoney(summary?.commission_total, summary?.currency)))), /* @__PURE__ */ React.createElement("div", { className: "card chart-card" }, loading ? /* @__PURE__ */ React.createElement("div", { className: "empty" }, /* @__PURE__ */ React.createElement("div", { className: "empty-sub" }, "Carregando...")) : /* @__PURE__ */ React.createElement(SalesChart, { series: data.series, days, currency: summary?.currency })), /* @__PURE__ */ React.createElement("div", { className: "section-head" }, /* @__PURE__ */ React.createElement("div", { className: "section-title" }, "Pedidos recentes"), /* @__PURE__ */ React.createElement("div", { className: "field-hint", style: { marginTop: 4 } }, "A AliExpress liquida em d\xF3lar; os valores acima j\xE1 est\xE3o convertidos", summary?.usd_brl_rate ? ` (US$ 1 = R$ ${Number(summary.usd_brl_rate).toFixed(2)})` : "", ". A coluna ", /* @__PURE__ */ React.createElement("b", null, "Base"), " \xE9 o valor sobre o qual sua comiss\xE3o \xE9 calculada \u2014 \xE9 o pre\xE7o do produto", /* @__PURE__ */ React.createElement("b", null, " antes"), " dos cupons do comprador, ent\xE3o \xE9 maior do que ele pagou no checkout. Compras pr\xF3prias n\xE3o geram comiss\xE3o e a API n\xE3o as identifica \u2014 use o \u2715 para tir\xE1-las dos totais.")), orders.length === 0 && !loading ? /* @__PURE__ */ React.createElement("div", { className: "card" }, /* @__PURE__ */ React.createElement("div", { className: "empty" }, /* @__PURE__ */ React.createElement("div", { className: "empty-icon" }, /* @__PURE__ */ React.createElement(Icon.box, null)), /* @__PURE__ */ React.createElement("div", { className: "empty-title" }, "Nenhum pedido sincronizado ainda"), /* @__PURE__ */ React.createElement("div", { className: "empty-sub" }, "Pedidos aparecem aqui depois do primeiro ciclo com vendas rastreadas pelo link de afiliado."))) : /* @__PURE__ */ React.createElement("div", { className: "card table-card" }, /* @__PURE__ */ React.createElement("table", null, /* @__PURE__ */ React.createElement("thead", null, /* @__PURE__ */ React.createElement("tr", null, /* @__PURE__ */ React.createElement("th", null, "Produto"), /* @__PURE__ */ React.createElement("th", null, "Status"), /* @__PURE__ */ React.createElement("th", null, "Data"), /* @__PURE__ */ React.createElement("th", { className: "num-col", title: "Base usada pela AliExpress para calcular sua comiss\xE3o. \xC9 o valor do produto ANTES dos cupons que o comprador aplicou, ent\xE3o costuma ser maior do que ele pagou de fato." }, "Base \u24D8"), /* @__PURE__ */ React.createElement("th", { className: "num-col" }, "Comiss\xE3o"), /* @__PURE__ */ React.createElement("th", { className: "actions-col" }))), /* @__PURE__ */ React.createElement("tbody", null, orders.map((o) => /* @__PURE__ */ React.createElement(
    "tr",
    {
      key: o.order_id + "-" + o.sub_order_id,
      style: o.excluded ? { opacity: 0.45 } : void 0
    },
    /* @__PURE__ */ React.createElement("td", null, o.product_id ? /* @__PURE__ */ React.createElement("a", { className: "prod-name", href: `https://www.aliexpress.com/item/${o.product_id}.html`, target: "_blank", rel: "noopener noreferrer" }, o.product_title || "Produto #" + o.product_id) : o.product_title || "\u2014"),
    /* @__PURE__ */ React.createElement("td", { className: "muted-cell" }, o.order_status || "\u2014"),
    /* @__PURE__ */ React.createElement("td", { className: "muted-cell" }, o.order_date ? (/* @__PURE__ */ new Date(o.order_date + "T00:00:00")).toLocaleDateString("pt-BR") : "\u2014"),
    /* @__PURE__ */ React.createElement("td", { className: "num-col price" }, fmtMoney(o.paid_amount, o.currency)),
    /* @__PURE__ */ React.createElement("td", { className: "num-col price" }, fmtMoney(o.estimated_commission, o.currency)),
    /* @__PURE__ */ React.createElement("td", { className: "actions-col" }, /* @__PURE__ */ React.createElement(
      "button",
      {
        className: o.excluded ? "btn btn-ghost" : "btn btn-ghost-danger",
        title: o.excluded ? "Reincluir nos totais" : "Marcar como compra pr\xF3pria (n\xE3o gera comiss\xE3o)",
        onClick: () => toggleExcluded(o)
      },
      o.excluded ? /* @__PURE__ */ React.createElement(Icon.plus, null) : /* @__PURE__ */ React.createElement(Icon.x, null)
    ))
  ))))));
}
const TABS = [
  { id: "produtos", label: "Produtos" },
  { id: "adicionar", label: "Adicionar produto" },
  { id: "vendas", label: "Vendas" },
  { id: "config", label: "Configura\xE7\xF5es" }
];
function App() {
  const [auth, setAuth] = useState(() => loadAuth());
  const [tab, setTab] = useState("produtos");
  const [api, setApi] = useState(() => auth ? makeApi(auth.url, auth.key) : null);
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
  if (!auth) return /* @__PURE__ */ React.createElement(Login, { onLogin: login });
  const apiHost = (() => {
    try {
      return new URL(auth.url).host;
    } catch {
      return auth.url;
    }
  })();
  return /* @__PURE__ */ React.createElement(React.Fragment, null, /* @__PURE__ */ React.createElement("header", { className: "topbar" }, /* @__PURE__ */ React.createElement("div", { className: "brand" }, /* @__PURE__ */ React.createElement("div", { className: "logo-badge" }, /* @__PURE__ */ React.createElement(Icon.boltSmall, { style: { color: "#fff" } })), /* @__PURE__ */ React.createElement("span", { className: "brand-name" }, "Promo Bot")), /* @__PURE__ */ React.createElement("div", { className: "topbar-right" }, /* @__PURE__ */ React.createElement("span", { className: "status-pill" }, /* @__PURE__ */ React.createElement("span", { className: "dot" }), "Online"), /* @__PURE__ */ React.createElement("span", { className: "api-chip" }, apiHost), /* @__PURE__ */ React.createElement("button", { className: "link-btn", onClick: logout, title: "Sair" }, /* @__PURE__ */ React.createElement(Icon.logout, { style: { display: "inline", verticalAlign: "-2px" } }), " Sair"))), /* @__PURE__ */ React.createElement("nav", { className: "tabs" }, TABS.map((t) => /* @__PURE__ */ React.createElement("button", { key: t.id, className: "tab" + (tab === t.id ? " active" : ""), onClick: () => setTab(t.id) }, t.label))), tab === "produtos" && /* @__PURE__ */ React.createElement(Produtos, { api, showToast }), tab === "adicionar" && /* @__PURE__ */ React.createElement(Adicionar, { api, showToast, onAdded: () => setTab("produtos") }), tab === "vendas" && /* @__PURE__ */ React.createElement(Vendas, { api, showToast }), tab === "config" && /* @__PURE__ */ React.createElement(Configuracoes, { api, showToast }), toast);
}
ReactDOM.createRoot(document.getElementById("root")).render(/* @__PURE__ */ React.createElement(App, null));
