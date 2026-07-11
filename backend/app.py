"""
CC Tool Evaluation System — Unified Backend (ML + AI in one Python service)

Engine 1 (ML) : TF-IDF + Complement Naive Bayes  -> COSMO-RS / DFT / MD
Engine 2 (AI) : Groq GPT-OSS 120B validation, grounded in domain knowledge

This single service replaces the old server.js (Node) + ml_service.py split,
so it is easy to host on ONE free backend (e.g. a Hugging Face Space).

Run locally:  python app.py   ->  http://localhost:7860
Env vars   :  GROQ_API_KEY (required for AI), PORT (optional, default 7860)
"""
import os, re, json
from flask import Flask, request, jsonify
from flask_cors import CORS
import joblib

# Load backend/.env if present (for local dev). On hosting, env vars/secrets are
# provided by the platform, so this is a no-op there.
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
except ImportError:
    pass

app = Flask(__name__)
CORS(app)

# ── Config ──────────────────────────────────────────────────────────────────
BASE       = os.path.dirname(__file__)
MODEL_DIR  = os.path.join(BASE, "ml_model")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_KEY   = os.environ.get("GROQ_API_KEY", "")

# ── Load the ML text classifier ─────────────────────────────────────────────
artifacts  = joblib.load(os.path.join(MODEL_DIR, "production_chemistry_classifier.pkl"))
pipeline   = artifacts["pipeline"]
le         = artifacts["label_encoder"]
MODEL_NAME = artifacts.get("model_name", "Text Classifier")
CLASSES    = list(le.classes_)   # ['COSMO-RS', 'DFT', 'MD']
print(f"✅ Loaded ML model: {MODEL_NAME} | classes: {CLASSES}")

METHODS = [
    {"abbr": "COSMO-RS", "full": "Conductor-like Screening Model for Real Solvents"},
    {"abbr": "DFT",      "full": "Density Functional Theory"},
    {"abbr": "MD",       "full": "Molecular Dynamics"},
]
METHOD_ABBRS = [m["abbr"] for m in METHODS]
FULL_NAME    = {m["abbr"]: m["full"] for m in METHODS}

# ── Domain knowledge grounding for the AI (3 methods) ───────────────────────
DOMAIN_KNOWLEDGE = """
COMPUTATIONAL CHEMISTRY METHOD SELECTION GUIDE — 3 CORE METHODS
(Based on peer-reviewed chemical & process engineering literature)

- COSMO-RS (Conductor-like Screening Model for Real Solvents)
  Best for: thermodynamic screening, solvation, activity coefficients, solubility,
  phase equilibria, mixture selectivity, gas-separation screening, ionic-liquid design.
  Systems: ionic liquids, deep eutectic solvents, solvent mixtures, electrolytes.

- DFT (Density Functional Theory)
  Best for: electronic structure, band gap, molecular geometry, bond length/angle,
  crystal/surface structure, catalytic activity, activation energy, reaction mechanism,
  adsorption energy, electrochemical & battery-material properties.
  Systems: catalysts, metal surfaces, MOFs, zeolites, 2D materials, semiconductors.

- MD (Molecular Dynamics)
  Best for: diffusivity, viscosity, thermal conductivity, permeability, ion transport,
  membrane performance, conformational dynamics, transport & time-evolution properties.
  Systems: polymers, membranes, aqueous solutions, electrolytes, proteins, nanomaterials.
"""


def build_text(prop, sub, domain, system):
    return " . ".join([str(prop or ""), str(sub or ""), str(domain or ""), str(system or "")])


# ── Engine 1: ML prediction ─────────────────────────────────────────────────
def ml_predict(prop, sub, domain, system):
    text = build_text(prop, sub, domain, system)
    try:
        proba = pipeline.predict_proba([text])[0]
    except AttributeError:
        idx = int(pipeline.predict([text])[0])
        proba = [1.0 if i == idx else 0.0 for i in range(len(CLASSES))]

    ranked = []
    for i, cls in enumerate(CLASSES):
        conf = float(proba[i])
        ranked.append({
            "method": cls, "fullName": FULL_NAME.get(cls, cls),
            "confidence": round(conf, 4), "conf_pct": round(conf * 100, 1),
        })
    ranked.sort(key=lambda x: x["confidence"], reverse=True)
    for i, r in enumerate(ranked):
        r["rank"] = i + 1
        r["is_best"] = (i == 0)

    return {
        "available": True, "model_name": MODEL_NAME,
        "best_method": ranked[0]["method"], "top3": ranked[:3],
        "all_methods": ranked, "reasoning": "",
    }


# ── Engine 2: AI validation via Groq ────────────────────────────────────────
_groq_client = None
def get_groq():
    global _groq_client
    if _groq_client is None:
        if not GROQ_KEY:
            raise RuntimeError("GROQ_API_KEY is not set")
        from groq import Groq
        _groq_client = Groq(api_key=GROQ_KEY)
    return _groq_client


def ai_predict(prop, sub, domain, system, ml_top3):
    method_list = ", ".join(METHOD_ABBRS)
    ml_context = ""
    if ml_top3:
        ml_context = "\nML Model ranking (for your reference): " + ", ".join(
            f"{m['method']} ({m['conf_pct']}%)" for m in ml_top3)

    prompt = f"""You are an expert computational chemist acting as a scientific validator.

You have been given the following domain knowledge from peer-reviewed literature:

{DOMAIN_KNOWLEDGE}

A researcher has submitted this query:
- Property: {prop}
- Sub-property: {sub}
- Application Domain: {domain or "(not specified)"}
- System Type: {system or "(not specified)"}
{ml_context}

Your task:
1. Using the domain knowledge above as your PRIMARY reference, decide which of the 3
   methods is most appropriate for this property / sub-property / domain / system.
2. Assign each method a confidence score from 0 to 100 (higher = more suitable).
   The three scores do NOT need to sum to 100 — judge each method on its own merit.
   IMPORTANT: each score MUST be a plain integer number like 85 — never spell it out as a word.
3. If the ML model ranking aligns with domain knowledge, affirm it. If it differs,
   briefly explain why the domain knowledge supports a different choice.

Available methods (ONLY these 3): {method_list}

Return ONLY valid JSON, no markdown, no extra text:
{{
  "scores": {{ "COSMO-RS": 85, "DFT": 40, "MD": 55 }},
  "best": "COSMO-RS",
  "reasoning": "2-3 sentences explaining why, referencing the domain knowledge, the property, and the system type"
}}"""

    completion = get_groq().chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    raw = completion.choices[0].message.content or ""
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        raise ValueError("No JSON in AI response")
    parsed = json.loads(match.group(0))

    scores = parsed.get("scores", {}) or {}
    all_methods = []
    for m in METHODS:
        try:
            raw_score = float(scores.get(m["abbr"], 0))
        except (TypeError, ValueError):
            raw_score = 0.0
        conf_pct = max(0.0, min(100.0, raw_score))
        all_methods.append({
            "method": m["abbr"], "fullName": m["full"],
            "confidence": round(conf_pct / 100, 4), "conf_pct": round(conf_pct, 1),
        })
    all_methods.sort(key=lambda x: x["conf_pct"], reverse=True)
    for i, m in enumerate(all_methods):
        m["rank"] = i + 1
        m["is_best"] = (i == 0)

    best = parsed.get("best")
    best_method = best if best in METHOD_ABBRS else all_methods[0]["method"]

    return {
        "available": True, "best_method": best_method,
        "top3": all_methods[:3], "all_methods": all_methods,
        "reasoning": parsed.get("reasoning", ""),
    }


# ── Comparison of the two engines ───────────────────────────────────────────
def build_comparison(ml, ai):
    ml_ok, ai_ok = ml.get("available"), ai.get("available")
    if not ml_ok and not ai_ok:
        return None

    ml_best = ml.get("best_method", "")
    ai_best = ai.get("best_method", "")
    ml_top3 = [m["method"] for m in ml.get("top3", [])]
    ai_top3 = [m["method"] for m in ai.get("top3", [])]
    agree = bool(ml_ok and ai_ok and ml_best == ai_best)
    overlap = [m for m in ml_top3 if m in ai_top3]

    if not ml_ok or not ai_ok:
        color, level = "amber", "Partial Results (one engine unavailable)"
    elif agree:
        color, level = "green", "Strong Agreement — Both engines agree on the best method"
    elif len(overlap) >= 2:
        color, level = "amber", "Moderate Agreement — Similar ranking"
    else:
        color, level = "red", "Low Agreement — Engines suggest different methods"

    method_diffs = []
    for method in METHOD_ABBRS:
        ml_item = next((m for m in ml.get("all_methods", []) if m["method"] == method), None) if ml_ok else None
        ai_item = next((m for m in ai.get("all_methods", []) if m["method"] == method), None) if ai_ok else None
        ml_rank = ml_item["rank"] if ml_item else None
        ai_rank = ai_item["rank"] if ai_item else None
        method_diffs.append({
            "method": method, "mlRank": ml_rank, "aiRank": ai_rank,
            "rankDiff": abs(ml_rank - ai_rank) if (ml_rank and ai_rank) else None,
            "mlInTop3": method in ml_top3, "aiInTop3": method in ai_top3,
            "both": method in ml_top3 and method in ai_top3,
        })

    return {
        "agree": agree, "agreementLevel": level, "agreementColor": color,
        "mlBest": ml_best, "aiBest": ai_best, "mlTop3": ml_top3, "aiTop3": ai_top3,
        "overlapCount": len(overlap), "top3Overlap": overlap, "methodDiffs": method_diffs,
    }


# ── Routes ──────────────────────────────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "Unified backend running 🚀",
        "ml_model": MODEL_NAME, "methods": CLASSES,
        "ai_model": GROQ_MODEL, "ai_configured": bool(GROQ_KEY),
    })


@app.route("/predict-best", methods=["POST", "OPTIONS"])
def predict_best():
    if request.method == "OPTIONS":
        return ("", 204)
    body = request.get_json(silent=True) or {}
    prop = body.get("property", ""); sub = body.get("subProperty", "")
    if not str(prop).strip() or not str(sub).strip():
        return jsonify({"error": "Property and sub-property are required", "known": False}), 400
    result = ml_predict(prop, sub, body.get("applicationDomain", ""), body.get("systemType", ""))
    return jsonify(result)


@app.route("/evaluate", methods=["POST", "OPTIONS"])
def evaluate():
    if request.method == "OPTIONS":
        return ("", 204)
    body = request.get_json(silent=True) or {}
    prop = body.get("property", ""); sub = body.get("subProperty", "")
    domain = body.get("applicationDomain", ""); system = body.get("systemType", "")
    if not str(prop).strip() or not str(sub).strip():
        return jsonify({"error": "Property and sub-property are required"}), 400

    # Engine 1: ML
    try:
        ml = ml_predict(prop, sub, domain, system)
    except Exception as e:
        ml = {"available": False, "error": f"ML error: {e}"}

    # Engine 2: AI (pass ML ranking as context)
    ml_top3 = ml.get("top3", []) if ml.get("available") else []
    try:
        ai = ai_predict(prop, sub, domain, system, ml_top3)
    except Exception as e:
        ai = {"available": False, "error": str(e)}

    return jsonify({"ml": ml, "ai": ai, "comparison": build_comparison(ml, ai)})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 7860))
    print(f"🚀 Unified backend → http://0.0.0.0:{port}  (AI model: {GROQ_MODEL})")
    app.run(host="0.0.0.0", port=port, debug=False)
