"""
ML Microservice — CC Tool Recommendation System
Engine 1: TF-IDF + Complement Naive Bayes (Text Classifier)

Model  : production_chemistry_classifier.pkl
Input  : property . sub_property . application_domain . system_type  (raw text)
Output : probability for 3 methods -> COSMO-RS, DFT, MD

Run: python ml_service.py  ->  http://localhost:5002
"""
from flask import Flask, request, jsonify
import joblib, os

app = Flask(__name__)

# Flask-CORS optional; fall back to manual headers if not installed
try:
    from flask_cors import CORS
    CORS(app)
except Exception:
    @app.after_request
    def _add_cors(resp):
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
        resp.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
        return resp

BASE      = os.path.dirname(__file__)
MODEL_DIR = os.path.join(BASE, "ml_model")

# ── Load the new production text classifier ─────────────────────────────────
# Bundle keys: "pipeline" (TF-IDF + classifier), "label_encoder", "model_name"
artifacts   = joblib.load(os.path.join(MODEL_DIR, "production_chemistry_classifier.pkl"))
pipeline    = artifacts["pipeline"]
le          = artifacts["label_encoder"]
MODEL_NAME  = artifacts.get("model_name", "Text Classifier")

CLASSES = list(le.classes_)   # -> ['COSMO-RS', 'DFT', 'MD']
print(f"✅ Loaded Model: {MODEL_NAME}  |  classes: {CLASSES}")

# Only 3 methods are predicted by this model
METHODS = [
    {"abbr": "COSMO-RS", "full": "Conductor-like Screening Model for Real Solvents"},
    {"abbr": "DFT",      "full": "Density Functional Theory"},
    {"abbr": "MD",       "full": "Molecular Dynamics"},
]
FULL_NAME = {m["abbr"]: m["full"] for m in METHODS}


def build_text(prop, sub, domain, system):
    """Recreate the exact training-time text format: 4 fields joined by ' . '."""
    parts = [str(prop or ""), str(sub or ""), str(domain or ""), str(system or "")]
    return " . ".join(parts)


@app.route("/", methods=["GET"])
def health():
    return jsonify({
        "status": "ML Service running (TF-IDF + Complement NB Engine)",
        "model_name": MODEL_NAME,
        "known_methods": CLASSES,
    })


@app.route("/predict-best", methods=["POST", "OPTIONS"])
def predict_best():
    if request.method == "OPTIONS":
        return ("", 204)

    body       = request.get_json(silent=True) or {}
    prop_name  = body.get("property", "")
    sub_name   = body.get("subProperty", "")
    domain     = body.get("applicationDomain", "")
    system     = body.get("systemType", "")

    # Minimum requirement: property + sub-property. Domain/system optional but recommended.
    if not str(prop_name).strip() or not str(sub_name).strip():
        return jsonify({"error": "Property and sub-property are required", "known": False}), 400

    text = build_text(prop_name, sub_name, domain, system)

    # Predict probabilities across the 3 classes
    try:
        proba = pipeline.predict_proba([text])[0]
    except AttributeError:
        # Fallback for classifiers without predict_proba
        pred_idx = int(pipeline.predict([text])[0])
        proba = [1.0 if i == pred_idx else 0.0 for i in range(len(CLASSES))]

    ranked = []
    for i, cls in enumerate(CLASSES):
        confidence = float(proba[i])
        ranked.append({
            "method":     cls,
            "fullName":   FULL_NAME.get(cls, cls),
            "confidence": round(confidence, 4),
            "conf_pct":   round(confidence * 100, 1),
        })

    ranked.sort(key=lambda x: x["confidence"], reverse=True)
    for i, r in enumerate(ranked):
        r["rank"] = i + 1
        r["is_best"] = (i == 0)

    best = ranked[0]

    return jsonify({
        "property":          prop_name,
        "subProperty":       sub_name,
        "applicationDomain": domain,
        "systemType":        system,
        "input_text":        text,
        "model_name":        MODEL_NAME,
        "best_method":       best["method"],
        "best_full":         best["fullName"],
        "best_confidence":   best["conf_pct"],
        "all_methods":       ranked,
        "top3":              ranked[:3],
        "known":             True,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    print(f"🤖 ML Service ({MODEL_NAME}) → http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
