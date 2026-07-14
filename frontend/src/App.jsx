import { useState } from "react";
import axios from "axios";

// ── Property taxonomy (dropdowns) ─────────────────────────────────────────────
// 10-category taxonomy — aligned 1:1 with the notebook TAXONOMY (Model_MLchemTools.ipynb, cell 9)
const PROPERTIES = {
  "THERMODYNAMIC PROPERTIES": ["Gibbs free energy","Enthalpy","Entropy","Heat capacity","Solubility","Phase equilibria","Henry's constant","Activity coefficient","Fugacity / chemical potential","Free energy of mixing","Solvation free energy"],
  "KINETIC & REACTION PROPERTIES": ["Reaction mechanism","Activation energy","Transition state","Reaction rate","Reaction pathway","Catalytic activity","Bond breaking","Bond formation","Decomposition mechanism","Degradation mechanism","Reaction kinetics"],
  "TRANSPORT PROPERTIES": ["Diffusivity","Diffusion","Permeability","Viscosity","Thermal conductivity","Mass transfer coefficient","Ionic conductivity","Ion transport"],
  "STRUCTURAL & ELECTRONIC PROPERTIES": ["Molecular geometry","Bond length","Bond angle","Electronic structure","Band gap","Density of states","Charge distribution","Surface structure","Crystal structure","Lattice parameters","Amorphous structure","Structural stability","Structural assignment","Regioisomer"],
  "MOLECULAR INTERACTION PROPERTIES": ["Binding energy","Adsorption energy","Adsorption mechanism","Adsorption behavior","Intermolecular forces","Hydrogen bonding","Van der Waals interactions","Electrostatic interactions","Solute–solvent interaction","Host–guest interaction","Non-covalent interactions","Force field parameterization","Drug–nanocarrier interaction","Drug–micelle interaction","Metal–ligand interaction","Interfacial adhesion","Protein–nanoparticle interaction","Protein–metal interaction"],
  "ADSORPTION & POROUS MEDIA PROPERTIES": ["Adsorption isotherms","Adsorption capacity","Adsorption selectivity","Competitive adsorption","Pore filling behavior","Surface coverage","Gas adsorption","Gas sensing"],
  "MULTICOMPONENT & PROCESS-LEVEL PROPERTIES": ["Mixture selectivity","Phase behavior of mixtures","Process thermodynamics","Scale-up prediction","Coupled transport–reaction","Extraction","Separation","Screening"],
  "BIOMEDICAL & BIOCHEMICAL PROPERTIES": ["Drug–protein interaction","Protein–ligand interaction","Conformational change","Enzyme reaction mechanism","Docking scoring","Biomolecular stability","Molecular docking","Protein extraction","Biointerface"],
  "ENERGY & ENVIRONMENTAL PROPERTIES": ["Gas separation selectivity","CO₂ absorption capacity","H₂S removal efficiency","Membrane performance","Electrochemical properties","Battery material properties","Hydrogen storage","Photocatalytic activity","Catalytic performance","Water desalination","Salt rejection"],
  "OPTICAL & SPECTROSCOPIC PROPERTIES": ["Optical properties","Nonlinear optical (NLO) properties","Photophysical properties","Dielectric relaxation","Spectral fingerprint","Vibrational spectra","Charge transfer","Intramolecular charge transfer (ICT)","Chiroptical properties","Excited-state proton transfer (ESIPT)","Optical limiting","Fluorescence","Absorption spectra","Raman spectra","Infrared (IR) spectra","UV–Vis spectroscopy"],
};

const APPLICATION_DOMAINS = [
  "Gas separation","CO2 capture","Carbon capture & storage","Catalysis","Heterogeneous catalysis",
  "Battery / energy storage","Fuel cells","Drug design / pharmaceuticals","Water treatment",
  "Membrane separation","Adsorption / porous materials","Corrosion","Polymer engineering",
  "Solvent design / screening","Electrochemistry","Biomolecular / enzyme systems",
  "Hydrogen storage","Distillation / extraction","Environmental remediation",
];
const SYSTEM_TYPES = [
  "Ionic liquids","Deep eutectic solvents","MOFs (Metal-organic frameworks)","Zeolites","Polymers",
  "Aqueous solutions","Electrolytes","Proteins / enzymes","Nanomaterials","Metal surfaces / catalysts",
  "Gas mixtures","Organic solvents","Membranes","2D materials","Molecular crystals","Semiconductors",
];

const ALL_METHODS = ["COSMO-RS", "DFT", "MD"];
const METHOD_COLORS = { "COSMO-RS": "#0d9488", "DFT": "#4f46e5", "MD": "#ea580c" };
const METHOD_ICON   = { "COSMO-RS": "◇", "DFT": "⬡", "MD": "◈" };
const RANK_STYLES = [
  { bg: "linear-gradient(135deg,#fde68a,#f59e0b)", fg: "#7c4a03" },
  { bg: "linear-gradient(135deg,#e5e7eb,#9ca3af)", fg: "#374151" },
  { bg: "linear-gradient(135deg,#fed7aa,#c2764a)", fg: "#5c3411" },
];
const chip = (color) => ({ padding: "5px 12px", borderRadius: 20, background: color + "14", color, border: `1px solid ${color}33`, fontSize: 12, fontWeight: 700 });

// ── Circular gauge (SVG) ──────────────────────────────────────────────────────
function Gauge({ pct = 0, color = "#4f46e5", size = 132 }) {
  const stroke = 11, r = (size - stroke) / 2, cx = size / 2, C = 2 * Math.PI * r;
  const off = C * (1 - Math.max(0, Math.min(100, pct)) / 100);
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={`Confidence ${pct}%`}>
      <circle cx={cx} cy={cx} r={r} fill="none" stroke="#eef2f7" strokeWidth={stroke} />
      <circle cx={cx} cy={cx} r={r} fill="none" stroke={color} strokeWidth={stroke} strokeLinecap="round"
        strokeDasharray={C} strokeDashoffset={off} transform={`rotate(-90 ${cx} ${cx})`}
        style={{ transition: "stroke-dashoffset 1s cubic-bezier(.2,.8,.2,1)" }} />
      <text x="50%" y="47%" textAnchor="middle" dominantBaseline="middle" fontSize={size * 0.24} fontWeight="800" fill="#0f172a">{Math.round(pct)}</text>
      <text x="50%" y="63%" textAnchor="middle" dominantBaseline="middle" fontSize={size * 0.11} fontWeight="600" fill="#94a3b8">% conf.</text>
    </svg>
  );
}

// ── Verdict hero ──────────────────────────────────────────────────────────────
function VerdictHero({ mlData, comparison }) {
  if (!mlData?.available) return null;
  const best = mlData.all_methods[0];
  const color = METHOD_COLORS[best.method] || "#4f46e5";
  const agreeColor = comparison?.agreementColor || "amber";
  const pal = { green: ["#f0fdf4","#bbf7d0","#15803d","Both engines agree"], amber: ["#fffbeb","#fde68a","#b45309","Partial agreement"], red: ["#fef2f2","#fecaca","#b91c1c","Engines differ"] };
  const [abg, abd, atx, alabel] = pal[agreeColor] || pal.amber;
  return (
    <div style={{ position: "relative", overflow: "hidden", borderRadius: 20, marginBottom: 22,
      background: `linear-gradient(135deg,${color}0f, #ffffff 55%)`, border: `1px solid ${color}30`,
      boxShadow: "0 14px 40px rgba(15,23,42,0.07)" }}>
      <div style={{ position: "absolute", top: -60, right: -60, width: 200, height: 200, borderRadius: "50%", background: color + "12" }} />
      <div style={{ position: "relative", display: "flex", alignItems: "center", gap: 26, padding: "24px 28px", flexWrap: "wrap" }}>
        <Gauge pct={best.conf_pct} color={color} />
        <div style={{ flex: 1, minWidth: 220 }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1.4, color: "#94a3b8", textTransform: "uppercase", marginBottom: 6 }}>Recommended method</div>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 6, flexWrap: "wrap" }}>
            <span style={{ fontSize: 30, color }}>{METHOD_ICON[best.method]}</span>
            <span style={{ fontSize: 30, fontWeight: 800, letterSpacing: -0.5, color: "#0f172a" }}>{best.method}</span>
          </div>
          <div style={{ fontSize: 14, color: "#64748b", marginBottom: 14 }}>{best.fullName}</div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "6px 13px", borderRadius: 20, background: abg, color: atx, border: `1px solid ${abd}`, fontSize: 12.5, fontWeight: 700 }}>
              {agreeColor === "green" ? "✅" : agreeColor === "amber" ? "⚠️" : "🔀"} {alabel}
            </span>
            {comparison?.aiBest && <span style={chip("#7c3aed")}>AI's pick: {comparison.aiBest}</span>}
            <span style={chip("#2563eb")}>Overlap {comparison?.overlapCount ?? 0}/3</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function MethodRow({ item, best, tag }) {
  const color = METHOD_COLORS[item.method] || "#4f46e5";
  const pct = item.conf_pct ?? 0;
  const s = RANK_STYLES[item.rank - 1] || { bg: "#e2e8f0", fg: "#475569" };
  return (
    <div style={{ border: `1px solid ${best ? color + "66" : "#e8edf3"}`, background: best ? color + "0d" : "#fff",
      borderRadius: 14, padding: "13px 16px", boxShadow: best ? `0 4px 14px ${color}22` : "0 1px 2px rgba(15,23,42,0.04)", transition: "all .2s" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 11, marginBottom: 9 }}>
        <span style={{ width: 26, height: 26, borderRadius: "50%", flexShrink: 0, display: "inline-flex", alignItems: "center", justifyContent: "center", background: s.bg, color: s.fg, fontSize: 12, fontWeight: 800, boxShadow: "0 1px 2px rgba(0,0,0,0.15)" }}>{item.rank}</span>
        <span style={{ fontSize: 16, color, width: 18, textAlign: "center" }}>{METHOD_ICON[item.method]}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap" }}>
            <span style={{ fontSize: 15, fontWeight: 700, color: "#0f172a" }}>{item.method}</span>
            {best && <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: .4, padding: "2px 8px", borderRadius: 20, background: color, color: "#fff" }}>BEST</span>}
            {tag && <span style={{ fontSize: 10, fontWeight: 600, padding: "2px 8px", borderRadius: 20, background: "#eef2ff", color: "#4f46e5", border: "1px solid #e0e7ff" }}>{tag}</span>}
          </div>
          <div style={{ fontSize: 11.5, color: "#94a3b8", marginTop: 1, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{item.fullName}</div>
        </div>
        <span style={{ fontSize: 15, fontWeight: 800, color, fontVariantNumeric: "tabular-nums" }}>{pct}%</span>
      </div>
      <div style={{ height: 8, borderRadius: 20, background: "#eef2f7", overflow: "hidden" }}>
        <div style={{ width: `${pct}%`, height: "100%", borderRadius: 20, background: `linear-gradient(90deg,${color}cc,${color})`, transition: "width .7s cubic-bezier(.2,.8,.2,1)" }} />
      </div>
    </div>
  );
}

function EnginePanel({ kind, data, comparison }) {
  const isML = kind === "ml";
  const accent = isML ? "#2563eb" : "#7c3aed";
  const icon = isML ? "🧮" : "✨";
  const title = isML ? "ML Model" : "Groq AI";
  const subtitle = isML ? (data?.model_name || "Complement Naive Bayes") : "GPT-OSS 120B · scientific validation";
  const otherBest = isML ? comparison?.aiBest : comparison?.mlBest;
  const otherTag = isML ? "AI's pick" : "ML's pick";
  return (
    <div style={{ background: "#fff", border: "1px solid #e8edf3", borderRadius: 18, padding: 18, boxShadow: "0 10px 30px rgba(15,23,42,0.05)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 11, marginBottom: 14, paddingBottom: 12, borderBottom: "1px solid #f1f5f9" }}>
        <div style={{ width: 40, height: 40, borderRadius: 11, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 19, background: accent + "14" }}>{icon}</div>
        <div>
          <div style={{ fontSize: 14.5, fontWeight: 700, color: accent }}>{title}</div>
          <div style={{ fontSize: 11, color: "#94a3b8" }}>{subtitle}</div>
        </div>
      </div>
      {data?.available ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {data.all_methods.map((m, i) => <MethodRow key={m.method} item={m} best={i === 0} tag={m.method === otherBest ? otherTag : null} />)}
          {!isML && data.reasoning && (
            <div style={{ marginTop: 4, background: "#faf9ff", border: "1px solid #eee6ff", borderRadius: 12, padding: "12px 15px" }}>
              <div style={{ fontSize: 10, letterSpacing: 1, color: "#8b5cf6", fontWeight: 700, marginBottom: 5 }}>AI REASONING</div>
              <p style={{ margin: 0, fontSize: 12.5, lineHeight: 1.6, color: "#475569" }}>{data.reasoning}</p>
            </div>
          )}
        </div>
      ) : (
        <div style={{ padding: 16, background: "#fef2f2", border: "1px solid #fecaca", borderRadius: 12, color: "#b91c1c", fontSize: 13 }}>
          ⚠ {isML ? "ML service" : "AI"} unavailable: {data?.error}
        </div>
      )}
    </div>
  );
}

function CompareTable({ mlData, aiData, comparison }) {
  const cell = { padding: "12px 14px", fontSize: 13, color: "#334155", borderBottom: "1px solid #f1f5f9" };
  const th = { padding: "11px 14px", textAlign: "left", fontSize: 11, letterSpacing: .5, color: "#64748b", fontWeight: 700, textTransform: "uppercase" };
  return (
    <div style={{ background: "#fff", border: "1px solid #e8edf3", borderRadius: 16, overflow: "hidden", boxShadow: "0 10px 30px rgba(15,23,42,0.05)" }}>
      <table style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr style={{ background: "#f8fafc" }}>
            <th style={th}>Method</th>
            <th style={{ ...th, color: "#2563eb" }}>🧮 ML Rank</th>
            <th style={{ ...th, color: "#2563eb" }}>ML Conf.</th>
            <th style={{ ...th, color: "#7c3aed" }}>✨ AI Rank</th>
            <th style={{ ...th, color: "#7c3aed" }}>AI Conf.</th>
            <th style={th}>Agreement</th>
          </tr>
        </thead>
        <tbody>
          {ALL_METHODS.map((m) => {
            const mlItem = mlData?.available ? mlData.all_methods.find(x => x.method === m) : null;
            const aiItem = aiData?.available ? aiData.all_methods.find(x => x.method === m) : null;
            const diff = comparison?.methodDiffs?.find(x => x.method === m);
            const bothBest = comparison?.mlBest === m && comparison?.aiBest === m;
            const color = METHOD_COLORS[m];
            return (
              <tr key={m} style={{ background: bothBest ? color + "0a" : "transparent" }}>
                <td style={{ ...cell, fontWeight: 700, color: "#0f172a" }}>
                  <span style={{ color, marginRight: 8 }}>{METHOD_ICON[m]}</span>{m}
                  {bothBest && <span style={{ marginLeft: 7, fontSize: 9.5, padding: "2px 7px", borderRadius: 20, background: color, color: "#fff", fontWeight: 700 }}>BEST</span>}
                </td>
                <td style={{ ...cell, color: "#2563eb", fontWeight: 700 }}>{mlItem ? `#${mlItem.rank}` : "—"}</td>
                <td style={cell}>{mlItem?.conf_pct != null ? `${mlItem.conf_pct}%` : "—"}</td>
                <td style={{ ...cell, color: "#7c3aed", fontWeight: 700 }}>{aiItem ? `#${aiItem.rank}` : "—"}</td>
                <td style={cell}>{aiItem?.conf_pct != null ? `${aiItem.conf_pct}%` : "—"}</td>
                <td style={cell}>
                  {diff ? (diff.rankDiff === 0
                    ? <span style={{ fontSize: 11, padding: "3px 9px", borderRadius: 20, background: "#f0fdf4", color: "#15803d", border: "1px solid #bbf7d0", fontWeight: 600 }}>Same rank</span>
                    : <span style={{ fontSize: 12, color: "#94a3b8" }}>Δ rank: {diff.rankDiff ?? "—"}</span>) : "—"}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [property, setProperty] = useState("");
  const [subProperty, setSubProperty] = useState("");
  const [applicationDomain, setApplicationDomain] = useState("");
  const [systemType, setSystemType] = useState("");
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("compare");

  const subList = property ? PROPERTIES[property] || [] : [];

  const handleEvaluate = async () => {
    if (!property || !subProperty) { setError("Please select a Property and Sub-property (required)."); return; }
    setError(""); setLoading(true); setData(null);
    try {
      const res = await axios.post(`${import.meta.env.VITE_API_URL || "http://localhost:7860"}/evaluate`,
        { property, subProperty, applicationDomain, systemType });
      setData(res.data); setActiveTab("compare");
    } catch (e) {
      setError("Connection error. Make sure the backend is running (locally: python app.py on port 7860, or set VITE_API_URL).");
    } finally { setLoading(false); }
  };

  const reset = () => { setProperty(""); setSubProperty(""); setApplicationDomain(""); setSystemType(""); setData(null); setError(""); };

  return (
    <div style={{ minHeight: "100vh", background: "linear-gradient(180deg,#eef2f9 0%,#f6f8fc 22%,#f6f8fc 100%)", fontFamily: "'Inter',system-ui,-apple-system,Segoe UI,Roboto,sans-serif", color: "#0f172a" }}>

      {/* Header */}
      <header style={{ background: "rgba(255,255,255,0.82)", backdropFilter: "blur(10px)", borderBottom: "1px solid #e8edf3", position: "sticky", top: 0, zIndex: 50 }}>
        <div style={{ height: 3, background: "linear-gradient(90deg,#0d9488,#4f46e5,#ea580c)" }} />
        <div style={{ maxWidth: 1120, margin: "0 auto", padding: "13px 24px", display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{ width: 42, height: 42, borderRadius: 12, background: "linear-gradient(135deg,#4f46e5,#7c3aed)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 21, boxShadow: "0 6px 16px rgba(79,70,229,0.35)" }}>🧪</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 17, fontWeight: 800, letterSpacing: -0.3 }}>MLCheM Selector</div>
            <div style={{ fontSize: 11.5, color: "#94a3b8" }}>Computational chemistry method recommendation · ML vs AI</div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <span style={chip("#2563eb")}>🧮 ML Model</span>
            <span style={chip("#7c3aed")}>✨ Groq AI</span>
          </div>
        </div>
      </header>

      <main style={{ maxWidth: 1120, margin: "0 auto", padding: "32px 24px 64px" }}>

        {/* Input card */}
        <section style={{ background: "#fff", border: "1px solid #e8edf3", borderRadius: 20, padding: 28, marginBottom: 26, boxShadow: "0 12px 34px rgba(15,23,42,0.06)" }}>
          <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: 1.2, color: "#4f46e5", textTransform: "uppercase", marginBottom: 18 }}>Input parameters</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(260px,1fr))", gap: 18, marginBottom: 16 }}>
            <div>
              <label style={lbl}>01 · Property <span style={req}>*</span></label>
              <select value={property} onChange={e => { setProperty(e.target.value); setSubProperty(""); }} style={sel}>
                <option value="">— Select property category —</option>
                {Object.keys(PROPERTIES).map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label style={lbl}>02 · Sub-property <span style={req}>*</span></label>
              <select value={subProperty} onChange={e => setSubProperty(e.target.value)} disabled={!property} style={{ ...sel, opacity: property ? 1 : 0.55 }}>
                <option value="">— Select sub-property —</option>
                {subList.map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label style={lbl}>03 · Application Domain <span style={opt}>(optional)</span></label>
              <input list="domain-list" value={applicationDomain} onChange={e => setApplicationDomain(e.target.value)} placeholder="e.g. Gas separation — pick or type" style={inp} />
              <datalist id="domain-list">{APPLICATION_DOMAINS.map(d => <option key={d} value={d} />)}</datalist>
            </div>
            <div>
              <label style={lbl}>04 · System Type <span style={opt}>(optional)</span></label>
              <input list="system-list" value={systemType} onChange={e => setSystemType(e.target.value)} placeholder="e.g. Ionic liquids — pick or type" style={inp} />
              <datalist id="system-list">{SYSTEM_TYPES.map(s => <option key={s} value={s} />)}</datalist>
            </div>
          </div>

          <div style={{ fontSize: 11.5, color: "#94a3b8", marginBottom: 16, lineHeight: 1.5 }}>
            ℹ The model is a TF-IDF text classifier — Application Domain &amp; System Type add context but are optional. Any free text works; presets are only suggestions.
          </div>

          {error && <div style={{ background: "#fef2f2", border: "1px solid #fecaca", color: "#b91c1c", borderRadius: 12, padding: "11px 15px", fontSize: 13, marginBottom: 14 }}>⚠ {error}</div>}

          <div style={{ display: "flex", gap: 12 }}>
            <button onClick={handleEvaluate} disabled={loading} style={{
              flex: 1, padding: "14px 0", borderRadius: 13, border: "none", cursor: loading ? "not-allowed" : "pointer",
              background: loading ? "#c7d2fe" : "linear-gradient(135deg,#4f46e5,#7c3aed)", color: "#fff",
              fontSize: 14, fontWeight: 700, letterSpacing: .3, fontFamily: "inherit",
              boxShadow: loading ? "none" : "0 8px 20px rgba(79,70,229,0.35)", transition: "all .2s" }}>
              {loading ? "⟳  Running ML + AI…" : "▶  Compare ML vs AI"}
            </button>
            {data && <button onClick={reset} style={{ padding: "14px 22px", borderRadius: 13, background: "#fff", border: "1px solid #e2e8f0", color: "#64748b", fontSize: 13, fontWeight: 600, cursor: "pointer", fontFamily: "inherit" }}>↺ Reset</button>}
          </div>
        </section>

        {/* Results */}
        {data && (
          <div style={{ animation: "fadeIn .45s ease" }}>
            <VerdictHero mlData={data.ml} comparison={data.comparison} />

            <div style={{ display: "flex", gap: 8, marginBottom: 18 }}>
              {[{ key: "compare", label: "⚖ Ranking comparison" }, { key: "table", label: "📊 Full method table" }].map(t => (
                <button key={t.key} onClick={() => setActiveTab(t.key)} style={{
                  padding: "9px 18px", borderRadius: 11, cursor: "pointer", fontSize: 13, fontWeight: 600, fontFamily: "inherit",
                  border: activeTab === t.key ? "1px solid #4f46e5" : "1px solid #e2e8f0",
                  background: activeTab === t.key ? "#eef2ff" : "#fff",
                  color: activeTab === t.key ? "#4f46e5" : "#64748b" }}>{t.label}</button>
              ))}
            </div>

            {activeTab === "compare"
              ? <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(320px,1fr))", gap: 18 }}>
                  <EnginePanel kind="ml" data={data.ml} comparison={data.comparison} />
                  <EnginePanel kind="ai" data={data.ai} comparison={data.comparison} />
                </div>
              : <CompareTable mlData={data.ml} aiData={data.ai} comparison={data.comparison} />}
          </div>
        )}

        {!data && !loading && (
          <div style={{ textAlign: "center", color: "#cbd5e1", fontSize: 13, padding: "30px 0" }}>
            Fill in the parameters above and click <strong style={{ color: "#94a3b8" }}>Compare ML vs AI</strong> to see recommendations.
          </div>
        )}
      </main>

      <footer style={{ textAlign: "center", padding: "24px", fontSize: 12, color: "#cbd5e1", borderTop: "1px solid #eef2f7" }}>
        MLCheM Selector · ML text classifier × GPT-OSS 120B
      </footer>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
        * { box-sizing: border-box; }
        body { margin: 0; }
        select option { color: #0f172a; }
        input::placeholder { color: #b6c0ce; }
        select:focus, input:focus { border-color: #4f46e5 !important; box-shadow: 0 0 0 3px rgba(79,70,229,0.12) !important; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
        ::-webkit-scrollbar { width: 9px; height: 9px; }
        ::-webkit-scrollbar-thumb { background: #d3dae4; border-radius: 6px; }
      `}</style>
    </div>
  );
}

const lbl = { display: "block", fontSize: 11, color: "#64748b", fontWeight: 600, letterSpacing: .3, marginBottom: 7 };
const req = { color: "#ef4444", fontWeight: 700 };
const opt = { color: "#b6c0ce", fontWeight: 500 };
const sel = { width: "100%", padding: "11px 13px", borderRadius: 11, background: "#fff", border: "1px solid #e2e8f0", color: "#0f172a", fontSize: 13.5, outline: "none", fontFamily: "inherit", cursor: "pointer", transition: "all .15s" };
const inp = { width: "100%", padding: "11px 13px", borderRadius: 11, background: "#fff", border: "1px solid #e2e8f0", color: "#0f172a", fontSize: 13.5, outline: "none", fontFamily: "inherit", transition: "all .15s" };
