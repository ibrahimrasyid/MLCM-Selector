import express from "express";
import cors from "cors";
import dotenv from "dotenv";
import Groq from "groq-sdk";

dotenv.config();

const app = express();
app.use(cors());
app.use(express.json());

const PORT   = process.env.PORT || 5000;
const ML_URL = process.env.ML_URL || "http://localhost:5002";

const groq = new Groq({ apiKey: process.env.GROQ_API_KEY });

// ── The model now predicts ONLY these 3 methods ─────────────────────────────
const METHODS = [
  { abbr: "COSMO-RS", full: "Conductor-like Screening Model for Real Solvents" },
  { abbr: "DFT",      full: "Density Functional Theory" },
  { abbr: "MD",       full: "Molecular Dynamics" },
];
const METHOD_ABBRS = METHODS.map(m => m.abbr);
const FULL_NAME = Object.fromEntries(METHODS.map(m => [m.abbr, m.full]));

// ── Domain Knowledge Grounding (3 methods only) ─────────────────────────────
// AI uses this as its primary reference, consistent with the text classifier
// trained on the same literature corpus (Dataset.xlsx).
const DOMAIN_KNOWLEDGE = `
COMPUTATIONAL CHEMISTRY METHOD SELECTION GUIDE — 3 CORE METHODS
(Based on peer-reviewed chemical & process engineering literature)

- COSMO-RS (Conductor-like Screening Model for Real Solvents)
  → Best for: thermodynamic screening, solvation, activity coefficients, solubility,
    phase equilibria, mixture selectivity, gas-separation screening, ionic-liquid design
  → Systems: ionic liquids, deep eutectic solvents, solvent mixtures, electrolytes
  → Ideal when: fast, low-cost thermodynamic screening is needed

- DFT (Density Functional Theory)
  → Best for: electronic structure, band gap, molecular geometry, bond length/angle,
    crystal/surface structure, catalytic activity, activation energy, reaction mechanism,
    adsorption energy, electrochemical & battery-material properties
  → Systems: catalysts, metal surfaces, MOFs, zeolites, 2D materials, semiconductors
  → Ideal when: quantum-level accuracy for structure/electronics/reactions is needed

- MD (Molecular Dynamics)
  → Best for: diffusivity, viscosity, thermal conductivity, permeability, ion transport,
    membrane performance, conformational dynamics, transport & time-evolution properties
  → Systems: polymers, membranes, aqueous solutions, electrolytes, proteins, nanomaterials
  → Ideal when: dynamics and transport properties are the focus
`;

async function getMLPrediction(property, subProperty, applicationDomain, systemType) {
  const resp = await fetch(`${ML_URL}/predict-best`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ property, subProperty, applicationDomain, systemType }),
    signal: AbortSignal.timeout(10000),
  });

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    throw new Error(err.error || `ML service error ${resp.status}`);
  }

  const data = await resp.json();
  return {
    available:   true,
    model_name:  data.model_name,
    best_method: data.best_method,
    top3:        data.top3,
    all_methods: data.all_methods,
    reasoning:   "",
  };
}

async function getAIPrediction(property, subProperty, applicationDomain, systemType, mlTop3 = []) {
  const methodList = METHOD_ABBRS.join(", ");

  const mlContext = mlTop3.length > 0
    ? `\nML Model ranking (for your reference): ${mlTop3.map(m => `${m.method} (${m.conf_pct}%)`).join(", ")}`
    : "";

  const prompt = `You are an expert computational chemist acting as a scientific validator.

You have been given the following domain knowledge from peer-reviewed literature:

${DOMAIN_KNOWLEDGE}

A researcher has submitted this query:
- Property: ${property}
- Sub-property: ${subProperty}
- Application Domain: ${applicationDomain || "(not specified)"}
- System Type: ${systemType || "(not specified)"}
${mlContext}

Your task:
1. Using the domain knowledge above as your PRIMARY reference, decide which of the 3
   methods is most appropriate for this property / sub-property / domain / system.
2. Assign each method a confidence score from 0 to 100 (higher = more suitable).
   The three scores do NOT need to sum to 100 — judge each method on its own merit.
   IMPORTANT: each score MUST be a plain integer number like 85 — never spell it out as a word.
3. If the ML model ranking aligns with domain knowledge, affirm it. If it differs,
   briefly explain why the domain knowledge supports a different choice.

Available methods (ONLY these 3): ${methodList}

Return ONLY valid JSON, no markdown, no extra text:
{
  "scores": { "COSMO-RS": 85, "DFT": 40, "MD": 55 },
  "best": "COSMO-RS",
  "reasoning": "2-3 sentences explaining why, referencing the domain knowledge, the property, and the system type"
}`;

  const completion = await groq.chat.completions.create({
    model:           "openai/gpt-oss-120b",
    messages:        [{ role: "user", content: prompt }],
    temperature:     0.1,
    response_format: { type: "json_object" },
  });

  const raw = completion.choices[0]?.message?.content || "";
  const jsonMatch = raw.match(/\{[\s\S]*\}/);
  if (!jsonMatch) throw new Error("No JSON in AI response");

  let parsed;
  try {
    parsed = JSON.parse(jsonMatch[0]);
  } catch (e) {
    throw new Error("AI JSON parse failed: " + e.message);
  }

  const scores = parsed.scores || {};
  const all_methods = METHODS.map(m => {
    let raw_score = Number(scores[m.abbr]);
    if (!isFinite(raw_score)) raw_score = 0;
    const conf_pct = Math.max(0, Math.min(100, raw_score));
    return {
      method:     m.abbr,
      fullName:   m.full,
      confidence: Number((conf_pct / 100).toFixed(4)),
      conf_pct:   Number(conf_pct.toFixed(1)),
    };
  }).sort((a, b) => b.conf_pct - a.conf_pct);

  all_methods.forEach((m, i) => { m.rank = i + 1; m.is_best = (i === 0); });

  const best_method =
    (parsed.best && METHOD_ABBRS.includes(parsed.best))
      ? parsed.best
      : all_methods[0].method;

  return {
    available:   true,
    best_method,
    top3:        all_methods.slice(0, 3),
    all_methods,
    reasoning:   parsed.reasoning || "",
  };
}

function buildComparison(mlResult, aiResult) {
  const mlOk = mlResult?.available;
  const aiOk = aiResult?.available;
  if (!mlOk && !aiOk) return null;

  const mlBest = mlResult?.best_method || "";
  const aiBest = aiResult?.best_method || "";
  const mlTop3 = (mlResult?.top3 || []).map(m => m.method || m);
  const aiTop3 = (aiResult?.top3 || []).map(m => m.method || m);
  const agree  = mlOk && aiOk && mlBest === aiBest;
  const overlap = mlTop3.filter(m => aiTop3.includes(m));

  const agreementColor =
    !mlOk || !aiOk      ? "amber" :
    agree               ? "green" :
    overlap.length >= 2 ? "amber" : "red";

  const agreementLevel =
    !mlOk || !aiOk      ? "Partial Results (one service unavailable)" :
    agree               ? "Strong Agreement — Both engines agree on the best method" :
    overlap.length >= 2 ? "Moderate Agreement — Similar ranking" :
                          "Low Agreement — Engines suggest different methods";

  const methodDiffs = METHOD_ABBRS.map(method => {
    const mlItem   = mlOk ? mlResult.all_methods?.find(m => m.method === method) : null;
    const aiItem   = aiOk ? aiResult.all_methods?.find(m => m.method === method) : null;
    const mlRank   = mlItem?.rank ?? null;
    const aiRank   = aiItem?.rank ?? null;
    const mlInTop3 = mlTop3.includes(method);
    const aiInTop3 = aiTop3.includes(method);
    return {
      method, mlRank, aiRank,
      rankDiff: mlRank !== null && aiRank !== null ? Math.abs(mlRank - aiRank) : null,
      mlInTop3, aiInTop3,
      both: mlInTop3 && aiInTop3,
    };
  });

  return {
    agree, agreementLevel, agreementColor,
    mlBest, aiBest, mlTop3, aiTop3,
    overlapCount: overlap.length,
    top3Overlap: overlap,
    methodDiffs,
  };
}

app.get("/", (_req, res) => res.json({ status: "Backend jalan 🚀", methods: METHOD_ABBRS }));

app.get("/ml-status", async (_req, res) => {
  try {
    const r = await fetch(`${ML_URL}/`);
    const d = await r.json();
    res.json({ online: true, ...d });
  } catch {
    res.json({ online: false });
  }
});

app.post("/evaluate", async (req, res) => {
  const { property, subProperty, applicationDomain, systemType } = req.body;
  if (!property || !subProperty)
    return res.status(400).json({ error: "Property and sub-property are required" });

  // Run ML first, then pass its ranking to the AI as extra context
  const mlSettled = await Promise.allSettled([
    getMLPrediction(property, subProperty, applicationDomain, systemType),
  ]);

  const mlResult = mlSettled[0].status === "fulfilled"
    ? mlSettled[0].value
    : { available: false, error: mlSettled[0].reason?.message || "ML service offline" };

  const mlTop3ForAI = mlResult.available ? (mlResult.top3 || []) : [];

  const aiSettled = await Promise.allSettled([
    getAIPrediction(property, subProperty, applicationDomain, systemType, mlTop3ForAI),
  ]);

  const aiResult = aiSettled[0].status === "fulfilled"
    ? aiSettled[0].value
    : { available: false, error: aiSettled[0].reason?.message || "AI unavailable" };

  res.json({
    ml:         mlResult,
    ai:         aiResult,
    comparison: buildComparison(mlResult, aiResult),
  });
});

app.listen(PORT, () => console.log(`✅ Backend running → http://localhost:${PORT}`));
