# 🧪 MLCheM Selector
### Machine Learning-based Computational Chemistry Method Selector
> Hybrid decision support — TF-IDF Text Classifier (Complement NB) × GPT-OSS 120B (Groq)

![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21317507.svg)](https://doi.org/10.5281/zenodo.21317507)

---

## 🌐 Live Demo

🔗 **https://mlcm-selector.vercel.app**

> No installation needed — open the link, describe your calculation, and compare the ML and AI recommendations side by side.

---

## 📖 What is This?

**MLCheM Selector** helps researchers and engineers choose a suitable computational chemistry method for a given study. Describe your problem with four text inputs — property, sub-property, application domain, and system type — and the system recommends a method using two engines shown side by side:

1. 🤖 **ML Text Classifier** — TF-IDF + Complement Naive Bayes trained on **323 records from real published studies** (the method actually used in each paper).
2. 🧠 **GPT-OSS 120B via Groq** — an optional AI "second opinion" grounded in domain knowledge. It does **not** change the ML recommendation.

### Supported Methods

| Method | Full Name |
|--------|-----------|
| COSMO-RS | Conductor-like Screening Model for Real Solvents |
| DFT | Density Functional Theory |
| MD | Molecular Dynamics |

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

### Step 2 — Get Your Free Groq API Key

1. Go to [console.groq.com](https://console.groq.com) and create a free account
2. Open **API Keys** → **Create API Key**
3. Copy your key — it looks like `gsk_xxxxxxxxxxxxxxxxxxxx`

> 🔒 Keep your key private. Never share it or commit it to GitHub.

### Step 3 — Create Your `backend/.env` File

Create a file named **`.env`** inside the `backend/` folder:

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
```

> ⚠️ Replace with your actual key from Step 2. Without it, the ML engine still works and the AI panel shows "unavailable".

### Step 4 — Start the Application (2 Terminals)

The ML model and the Groq AI run together in one Python backend (`app.py`).

**🐍 Terminal 1 — Python Backend (ML + AI)**
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
5. **Compare ML vs AI** — returns the best method, a confidence for all three methods, the AI second opinion, and an agreement banner

> The model is a TF-IDF text classifier, so Application Domain and System Type are free text that add context; they are optional.

---

## 🏗️ Architecture

```
Browser (React · Vercel)
         │  POST /evaluate
         ▼
Python Backend (Flask)
    ┌──────────────┬───────────────┐
    ▼              ▼
ML Classifier   Groq AI API
(Complement NB) (GPT-OSS 120B)
    └──────────────┴───────────────┘
         ▼
   Combined result + side-by-side comparison
```

---

## 🤖 ML Model Details

| Info | Details |
|------|---------|
| Algorithm | TF-IDF (1–2 grams, 1500 features) + Complement Naive Bayes (α = 0.5) |
| Task | Single-label classification |
| Training data | **323 records from real published studies** (labels = primary method reported) |
| Class distribution | DFT 143 · MD 103 · COSMO-RS 77 |
| Input features | `property · sub_property · application_domain · system_type` (raw text) |
| Validation | Leak-proof, paper-grouped split (train 273 / test 50); TF-IDF fitted on train only |
| Held-out accuracy | **88.0%** (macro-F1 **0.877**) |
| Baseline (Zero-R) | 44.3% → **+43.7 points** |

Per-method (held-out test, n=50):

| Method | Precision | Recall | F1 | Support |
|--------|-----------|--------|----|---------|
| COSMO-RS | 0.80 | 0.92 | 0.86 | 13 |
| DFT | 1.00 | 0.82 | 0.90 | 22 |
| MD | 0.82 | 0.93 | 0.88 | 15 |

### AI validation component

Optional and non-authoritative. Groq-hosted `openai/gpt-oss-120b`, temperature 0.1, JSON output, **prompt-grounded** on the same method profiles (no external retrieval). Shown side by side; it does not modify the ML recommendation and is excluded from the quantitative evaluation because LLM outputs are non-deterministic.

---

## 🔬 Reproducibility

The dataset, training script, and evaluation are provided:

```bash
cd Model
pip install -r requirements.txt
python train.py
```

Regenerates the model, `classification_report.txt`, `confusion_matrix.png`, and `metrics_summary.json` from `Dataset.xlsx`.

---

## 📁 Project Structure

```
MLCM-Selector/
├── backend/                    # Python backend (Vercel)
│   ├── api/index.py            # Vercel entry (WSGI)
│   ├── app.py                  # ML classifier + Groq AI + comparison (Flask)
│   ├── vercel.json             # Vercel config
│   ├── requirements.txt
│   ├── ml_model/
│   │   ├── production_chemistry_classifier.pkl   # active model
│   │   └── model_metadata.json
│   └── .env                    # ⚠️ create yourself (not committed)
├── frontend/                   # React app (Vercel)
│   └── src/App.jsx
├── Model/                      # Training / reproducibility
│   ├── Dataset.xlsx            # real literature dataset
│   ├── train.py
│   ├── Model_MLchemTools.ipynb
│   └── requirements.txt
│
└── README.md
```

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| Frontend "Connection error" | Check `VITE_API_URL` (no trailing `/`) and redeploy the frontend |
| AI panel "unavailable" | `GROQ_API_KEY` missing/invalid — ML still works; set the key and redeploy |
| `Port 7860 already in use` | Close the previous `python app.py`, or set another `PORT` |
| ML model not found | Ensure `backend/ml_model/production_chemistry_classifier.pkl` exists |
| First request slow | Serverless cold start — retry after a few seconds |

---

## 📚 Citation

If you use this software or dataset, please cite the archived release:

> Rasyid, M. I., Suharlan, K. Z., Latif, R. A., & Rosalina, R. (2026). *MLCheM Selector — Machine Learning-based Computational Chemistry Method Selector* (v1.0.0). Zenodo. https://doi.org/10.5281/zenodo.21317507

DOI: [10.5281/zenodo.21317507](https://doi.org/10.5281/zenodo.21317507) · citation metadata in `CITATION.cff`.

---

## 📜 License

Released under the MIT License (see `LICENSE`).

**Repository:** https://github.com/ibrahimrasyid/MLCM-Selector
