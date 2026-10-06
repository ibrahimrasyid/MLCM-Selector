# 🧪 MLCheM Selector
### Machine Learning-based Computational Chemistry Method Selector
> A literature-derived ML classifier (TF-IDF + Complement Naive Bayes) with an optional AI-assisted explanation (GPT-OSS 120B via Groq)

![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21317506.svg)](https://doi.org/10.5281/zenodo.21317506)

---

## 🌐 Live Demo

🔗 **https://mlcm-selector.vercel.app**

> No installation needed — open the link, describe your calculation, and get a recommended method with an AI-assisted explanation.

---

## 📖 What is This?

**MLCheM Selector** is a proof-of-concept decision-support tool that accompanies a review of computational chemistry (CC) in engineering. Describe your problem with four text inputs — property, sub-property, application domain, and system type — and the tool recommends one of three CC methods.

1. 🤖 **ML Classifier (primary recommendation)** — TF-IDF + Complement Naive Bayes trained on **323 records from real published studies**. The label of each record is the *primary method reported in the paper*.
2. 🧠 **AI-Assisted Explanation (optional)** — GPT-OSS 120B via Groq writes a human-readable explanation of the recommendation. It does **not** change the ML recommendation and does **not** take part in model training, prediction, or evaluation.

### Supported Methods

| Method | Full Name |
|--------|-----------|
| COSMO-RS | Conductor-like Screening Model for Real Solvents |
| DFT | Density Functional Theory |
| MD | Molecular Dynamics |

### Scope and Limitations

- The classifier learns **literature-derived method-use patterns**. A published method choice reflects historical practice, software availability, author expertise and study objectives; it is **not** ground truth for methodological optimality.
- Only **three** method classes are covered, and the task is **single-label** (many real studies combine methods, e.g. DFT + MD or QM/MM).
- No independent expert-labelled benchmark exists yet; the tool supports, and does not replace, expert judgement.

---

## 🚀 Run Locally — Step by Step

### What You Need First

| Tool | Download Link | Check |
|------|--------------|-------|
| Python 3.9+ | [python.org](https://python.org) | `python --version` |
| Node.js 18+ | [nodejs.org](https://nodejs.org) | `node --version` |
| Git | [git-scm.com](https://git-scm.com) | `git --version` |

### Step 1 — Clone the Repository

```bash
git clone https://github.com/ibrahimrasyid/MLCM-Selector.git
cd MLCM-Selector
```

### Step 2 — Get Your Free Groq API Key (optional, for the AI explanation)

1. Go to [console.groq.com](https://console.groq.com) and create a free account
2. Open **API Keys** → **Create API Key**
3. Copy your key — it looks like `gsk_xxxxxxxxxxxxxxxxxxxx`

> 🔒 Keep your key private. Never share it or commit it to GitHub.

### Step 3 — Create Your `backend/.env` File

Create a file named **`.env`** inside the `backend/` folder:

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
```

> Without a key, the ML classifier still works and the AI explanation panel shows "unavailable".

### Step 4 — Start the Application (2 Terminals)

The ML classifier and the Groq explanation run together in one Python backend (`app.py`).

**🐍 Terminal 1 — Python Backend**
```bash
cd backend
pip install -r requirements.txt
python app.py
```
✅ `🚀 Unified backend → http://0.0.0.0:7860`

**⚛️ Terminal 2 — React Frontend**
```bash
cd frontend
npm install
npm run dev
```
✅ Open `http://localhost:5173`

---

## 🎯 How to Use

1. **Property** *(required)* — choose the property category (thermodynamic, transport, structural/electronic, …)
2. **Sub-property** *(required)* — pick the specific sub-property
3. **Application Domain** *(optional)* — e.g. Gas separation, Catalysis, CO₂ capture (pick a preset or type your own)
4. **System Type** *(optional)* — e.g. Ionic liquids, MOFs, Polymers (pick a preset or type your own)
5. Click **ML Recommendation & AI Explanation** — the result shows the recommended method, the classifier's confidence score for all three methods, and the AI-assisted explanation.

> The model is a TF-IDF text classifier, so Application Domain and System Type are free text that add context; they are optional.

---

## 🏗️ Architecture

```
Browser (React · Vercel)
         │  POST /evaluate
         ▼
Python Backend (Flask)
         │
         ▼
ML Classifier (TF-IDF + Complement NB)  ──►  Recommended method + confidence
         │
         ▼
AI-Assisted Explanation (GPT-OSS 120B, Groq)  ──►  Human-readable explanation
```

The ML classifier produces the recommendation first; the explanation module is optional and runs afterwards.

---

## 🤖 ML Model Details

| Info | Details |
|------|---------|
| Algorithm | TF-IDF (1–2 grams, 1500 features) + Complement Naive Bayes (α = 0.5) |
| Task | Single-label classification (COSMO-RS / DFT / MD) |
| Training data | **323 records from real published studies** (label = primary method reported) |
| Class distribution | DFT 143 · MD 103 · COSMO-RS 77 |
| Input features | `property · sub_property · application_domain · system_type` (raw text, concatenated) |
| Validation | Paper-grouped split (`GroupShuffleSplit`, train 273 rows / test 50 rows); TF-IDF fitted inside a scikit-learn `Pipeline`; 5-fold `StratifiedGroupKFold` for model selection |
| Held-out accuracy | **88.0%** (macro-F1 **0.877**) |
| Baseline (Zero-R) | 44.3% |

Per-method results (held-out test, n = 50 rows):

| Method | Precision | Recall | F1 | Support |
|--------|-----------|--------|----|---------|
| COSMO-RS | 0.80 | 0.92 | 0.86 | 13 |
| DFT | 1.00 | 0.82 | 0.90 | 22 |
| MD | 0.82 | 0.93 | 0.88 | 15 |

The confidence shown in the interface is the classifier's predicted class probability; it has not been calibrated.

### AI-Assisted Explanation (optional)

- Model: Groq-hosted `openai/gpt-oss-120b`, temperature 0.1, JSON output, prompt-grounded on short profiles of the three methods (no external retrieval).
- It receives the classifier's output as context and writes an explanation of the recommendation. It **does not modify** the ML recommendation.
- The panel also displays relative suitability scores and an "AI pick"/"ML pick" tag for transparency. Because the explanation is conditioned on the classifier's output, these are **not** an independent assessment, and agreement between the two panels is **not** used as validation evidence.
- It is excluded from all quantitative evaluation because LLM outputs are non-deterministic.

---

## 🔬 Reproducibility

The dataset, training script, notebook and released model are provided in `Model/`:

```bash
cd Model
pip install -r requirements.txt
python train.py
```

`train.py` rebuilds the pipeline from `Dataset.xlsx`, writes `classification_report.txt`, `confusion_matrix.png` and `metrics_summary.json`, and **overwrites** `production_chemistry_classifier.pkl`.

> **Note:** the deployed classifier is the released `production_chemistry_classifier.pkl` (Complement NB, α = 0.5), which produces the held-out results reported above. Several candidates are nearly tied in cross-validation, so re-running the automatic selection step may pick a different candidate. To check the released model, evaluate the provided `.pkl` on the paper-grouped test split (`GroupShuffleSplit`, `test_size=0.15`, `random_state=42`).

Further details: [`REPRODUCIBILITY.md`](REPRODUCIBILITY.md) and `Model/Model_MLchemTools.ipynb`.

---

## 📁 Project Structure

```
MLCM-Selector/
├── backend/                    # Python backend (Vercel)
│   ├── api/index.py            # Vercel entry (WSGI)
│   ├── app.py                  # ML classifier + AI-assisted explanation (Flask)
│   ├── vercel.json             # Vercel config
│   ├── requirements.txt
│   ├── ml_model/
│   │   ├── production_chemistry_classifier.pkl   # active model
│   │   └── model_metadata.json
│   └── .env                    # ⚠️ create yourself (not committed)
├── frontend/                   # React app (Vercel)
│   └── src/App.jsx
├── Model/                      # Training / reproducibility
│   ├── Dataset.xlsx            # literature-derived dataset
│   ├── train.py
│   ├── Model_MLchemTools.ipynb
│   ├── production_chemistry_classifier.pkl
│   └── requirements.txt
├── CITATION.cff
├── REPRODUCIBILITY.md
└── README.md
```

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| Frontend "Connection error" | Check `VITE_API_URL` (no trailing `/`) and redeploy the frontend |
| AI explanation "unavailable" | `GROQ_API_KEY` missing/invalid — the ML classifier still works; set the key and redeploy |
| `Port 7860 already in use` | Close the previous `python app.py`, or set another `PORT` |
| ML model not found | Ensure `backend/ml_model/production_chemistry_classifier.pkl` exists |
| First request slow | Serverless cold start — retry after a few seconds |

---

## 📚 Citation

If you use this software or dataset, please cite the archived release:

> Rasyid, M. I., Suharlan, K. Z., Latif, R. A., & Rosalina, R. (2026). *MLCheM Selector — Machine Learning-based Computational Chemistry Method Selector* (v1.1.1). Zenodo. https://doi.org/10.5281/zenodo.21317506

DOI: [10.5281/zenodo.21317506](https://doi.org/10.5281/zenodo.21317506) (all versions — always resolves to the latest release; version-specific DOIs are listed on the Zenodo page) · citation metadata in `CITATION.cff`.

---

## 📜 License

Released under the MIT License (see `LICENSE`).

**Repository:** https://github.com/ibrahimrasyid/MLCM-Selector
