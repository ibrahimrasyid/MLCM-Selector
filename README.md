# 🧪 CC Tool Evaluation System
### Computational Chemistry Method Decision Support System
> Hybrid ML + AI — TF-IDF Text Classifier (Complement NB) × LLaMA 3.1 8B (Groq)

![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![Node.js](https://img.shields.io/badge/Node.js-43853D?style=for-the-badge&logo=node.js&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-F7931E?style=for-the-badge&logo=scikit-learn&logoColor=white)

---

## 🌐 Live Demo

> **Just want to try it? No installation needed!**

🔗 **[https://cc-tool-upgrade.vercel.app](https://cc-tool-upgrade.vercel.app)**

---

## 📖 What is This?

**CC Tool Evaluation System** helps researchers and engineers select the most suitable computational chemistry method for their study. Describe your problem with four text inputs — property, sub-property, application domain, and system type — and the system recommends the best method using two engines running in parallel:

1. 🤖 **ML Text Classifier** — TF-IDF + Complement Naive Bayes trained on 323 rows of literature
2. 🧠 **LLaMA 3.1 8B via Groq** — AI validation grounded in peer-reviewed literature

### Supported Methods

| Method | Full Name |
|--------|-----------|
| COSMO-RS | Conductor-like Screening Model for Real Solvents |
| DFT | Density Functional Theory |
| MD | Molecular Dynamics |

---

## 🚀 Run Locally — Step by Step

### What You Need First

Make sure these are installed on your computer:

| Tool | Download Link | Check if installed |
|------|--------------|-------------------|
| Python 3.8+ | [python.org](https://python.org) | `python --version` |
| Node.js 18+ | [nodejs.org](https://nodejs.org) | `node --version` |
| Git | [git-scm.com](https://git-scm.com) | `git --version` |

---

### Step 1 — Clone the Repository

Open your terminal (CMD / PowerShell / Terminal) and run:

```bash
git clone https://github.com/ibrahimrasyid/cc-tool-upgrade.git
cd cc-tool-upgrade
```

---

### Step 2 — Get Your Free Groq API Key

This project uses **Groq API** to run the LLaMA 3.1 8B AI model for free.

1. Go to [console.groq.com](https://console.groq.com) and create a free account
2. Navigate to **API Keys** in the sidebar
3. Click **"Create API Key"**
4. Copy your key — it looks like: `gsk_xxxxxxxxxxxxxxxxxxxx`

> 🔒 Keep your API key private. Never share it or upload it to GitHub.

---

### Step 3 — Create Your `.env` File

Navigate to the `backend/` folder and create a file named **`.env`**.

Using any text editor, create a new file called `.env` inside the `backend/` folder and paste:

```env
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
```

> ⚠️ Replace `gsk_xxxxxxxxxxxxxxxxxxxx` with your actual Groq API key from Step 2.

After this, your `backend/` folder should look like:

```
backend/
├── ml_model/
├── .env              ← the file you just created ✅
├── ml_service.py
├── package.json
├── requirements.txt
└── server.js
```

---

### Step 4 — Start the Application (2 Terminals)

You only need **2 terminal windows** now — the ML model and the Groq AI run in one Python backend (`app.py`).

---

#### 🐍 Terminal 1 — Python Backend (ML + AI) *(Run this FIRST)*

```bash
cd backend
pip install -r requirements.txt
python app.py
```

✅ Success message: `🚀 Unified backend → http://0.0.0.0:7860`

> Reads `backend/.env` automatically for `GROQ_API_KEY`. Without it, ML still works and the AI panel shows "unavailable".

---

#### ⚛️ Terminal 2 — React Frontend *(Run this SECOND)*

```bash
cd frontend
npm install
npm run dev
```

✅ Success message: `Local: http://localhost:5173`

---

### Step 5 — Open the App

Open your browser and go to:

🔗 **[http://localhost:5173](http://localhost:5173)**

---

## 🎯 How to Use

1. **Select a Property** *(required)* — choose the chemical/physical property category
2. **Select a Sub-property** *(required)* — pick the specific sub-property
3. **Application Domain** *(optional)* — e.g. Gas separation, Catalysis, CO2 capture (pick a preset or type your own)
4. **System Type** *(optional)* — e.g. Ionic liquids, MOFs, Polymers (pick a preset or type your own)
5. **Click Compare** — the system will return:
   - ✅ Best recommended method (of COSMO-RS, DFT, MD)
   - 📊 Confidence (probability) for all 3 methods
   - 🤖 ML Model ranking
   - 🧠 AI reasoning and validation

> ℹ Accuracy and cost levels are no longer required — the new text classifier infers the method directly from your description.

---

## 🏗️ Architecture

```
Browser (React · port 5173 / Vercel)
         ↓
Python Backend (Flask · port 7860 / Hugging Face)
    ↙               ↘
ML Text Classifier   Groq AI API
(Complement NB)      (GPT-OSS 120B)
    ↘               ↙
     Combined Result
     + Side-by-side Comparison
```

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|----------|
| `Port 5000 already in use` | Run: `taskkill /IM node.exe /F` (Windows) or `lsof -ti:5000 \| xargs kill` (Mac/Linux) |
| `Port 5002 already in use` | Close the previous Python terminal |
| `pip install` fails | Try: `pip install flask flask-cors scikit-learn pandas numpy xgboost joblib` |
| `GROQ_API_KEY` error | Make sure `.env` file exists inside `backend/` folder with correct key |
| ML model not found | Make sure `backend/ml_model/` folder contains all `.pkl` files |
| CORS error in browser | Make sure all 3 services are running (ports 5000, 5002, 5173) |
| AI returns no result | Check your Groq API key is valid at [console.groq.com](https://console.groq.com) |

---

## 📁 Project Structure

```
cc-tool-upgrade/
├── backend/
│   ├── ml_model/               # Trained model files
│   │   ├── production_chemistry_classifier.pkl   # ← ACTIVE model (TF-IDF + Complement NB)
│   │   ├── model_metadata.json
│   │   └── (legacy xgb_regressor.pkl / le_*.pkl — no longer used)
│   ├── .env                    # ⚠️ Create this yourself (see Step 3)
│   ├── ml_service.py           # Flask ML microservice
│   ├── server.js               # Express backend + Groq integration
│   ├── package.json
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   └── App.jsx             # Main React application
│   ├── index.html
│   └── package.json
└── README.md
```

---

## 🤖 ML Model Details

| Info | Details |
|------|---------|
| Algorithm | TF-IDF (1–2 grams) + Complement Naive Bayes |
| Training Rows | 323 literature rows (grouped by paper, leak-proof split) |
| Input Features | `property . sub_property . application_domain . system_type` (raw text) |
| Output | Probability per method (COSMO-RS, DFT, MD) |
| Classes | 3 methods — COSMO-RS, DFT, MD |
| Bundle | `production_chemistry_classifier.pkl` → `{pipeline, label_encoder, model_name}` |
| Data Source | Dataset.xlsx (peer-reviewed CC engineering literature) |

> The model file is a scikit-learn Pipeline. To swap in a retrained model later, just replace
> `backend/ml_model/production_chemistry_classifier.pkl` (keep the same bundle keys) — no code changes needed.

