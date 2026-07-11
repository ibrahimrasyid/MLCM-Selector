# 🚀 Panduan Deploy Gratis — MLCheM Selector

Panduan lengkap men-deploy aplikasi versi baru (model classifier teks + AI Groq) secara **gratis** menggunakan **Hugging Face Space** (backend Python) dan **Vercel** (frontend React).

> **Arsitektur baru (2 bagian saja):**
> ```
> Browser  ──►  Vercel (frontend React)  ──►  Hugging Face Space (backend Python: ML + Groq AI)  ──►  Groq API
> ```
> Backend Node lama (`server.js`) sudah digantikan oleh `backend/app.py`, jadi cukup 1 backend.

---

## 📋 Sebelum Mulai — yang Anda butuhkan

| Kebutuhan | Link | Catatan |
|-----------|------|---------|
| Akun GitHub | [github.com](https://github.com) | Menyimpan kode |
| Akun Hugging Face | [huggingface.co](https://huggingface.co) | Hosting backend Python |
| Akun Vercel | [vercel.com](https://vercel.com) | Hosting frontend (login pakai GitHub) |
| Groq API Key | [console.groq.com](https://console.groq.com) | Untuk AI validation (yang di `.env` Anda) |
| Git terpasang | [git-scm.com](https://git-scm.com) | Cek: `git --version` |

> ⚠️ **PENTING soal keamanan:** file `backend/.env` berisi API key Anda dan **sudah** masuk `.gitignore`, jadi tidak akan ikut ter-upload ke GitHub. Di hosting, key dipasang lewat menu **Secrets** (bukan di dalam kode). Jangan pernah menaruh key langsung di kode.

---

## BAGIAN 1 — Upload Kode ke GitHub

### 1.1 Buat repository baru
1. Buka [github.com/new](https://github.com/new)
2. **Repository name:** `mlchem-selector` (bebas)
3. Pilih **Public** (wajib public agar Vercel free bisa akses; boleh private juga)
4. **Jangan** centang "Add a README" (kita sudah punya)
5. Klik **Create repository** — salin URL-nya, mis. `https://github.com/USERNAME/mlchem-selector.git`

### 1.2 Upload proyek dari komputer
Buka terminal **di folder proyek** (`...\MLCheM-Selector--main`) lalu jalankan berurutan:

```bash
git init
git add .
git commit -m "MLCheM Selector - versi model baru + backend gabungan"
git branch -M main
git remote add origin https://github.com/USERNAME/mlchem-selector.git
git push -u origin main
```

> Ganti `USERNAME` dengan username GitHub Anda. Kalau diminta login, gunakan akun GitHub Anda (atau Personal Access Token sebagai password).

✅ Cek: buka repo di browser — folder `backend/`, `frontend/`, `Model/` muncul, tapi `backend/.env` **tidak** ada. Itu benar.

---

## BAGIAN 2 — Deploy Backend ke Hugging Face Space

Backend Python (`backend/app.py`) menjalankan model ML **dan** memanggil Groq. Kita host sebagai **Docker Space**.

### 2.1 Buat Space baru
1. Buka [huggingface.co/new-space](https://huggingface.co/new-space)
2. **Space name:** `mlchem-backend` (bebas)
3. **License:** pilih apa saja (mis. MIT)
4. **Select the SDK:** pilih **Docker** → **Blank**
5. **Visibility:** Public
6. Klik **Create Space**

### 2.2 Upload isi folder `backend/` ke Space
Space adalah repo Git tersendiri. Yang di-upload adalah **ISI folder `backend/`** (bukan folder `backend`-nya), sehingga `Dockerfile`, `app.py`, `requirements.txt`, `README.md`, dan folder `ml_model/` berada di **root** Space.

**Cara mudah (lewat web):**
1. Di halaman Space, buka tab **Files** → tombol **Add file** → **Upload files**
2. Dari komputer, masuk folder `backend/`, seleksi semua isinya:
   `app.py`, `Dockerfile`, `README.md`, `requirements.txt`, dan folder `ml_model/` (berisi `production_chemistry_classifier.pkl` dll.)
3. **JANGAN** upload `.env`, `server.js`, `node_modules`, `package.json` (tidak diperlukan)
4. Klik **Commit changes to main**

**Cara alternatif (lewat Git):**
```bash
git clone https://huggingface.co/spaces/USERNAME/mlchem-backend
cd mlchem-backend
# salin ISI folder backend/ proyek ke sini (tanpa .env)
git add .
git commit -m "deploy backend"
git push
```

### 2.3 Pasang API Key sebagai Secret
1. Di Space, buka **Settings** → **Variables and secrets**
2. Klik **New secret**
   - **Name:** `GROQ_API_KEY`
   - **Value:** tempel API key Groq Anda (yang `gsk_...`)
   - Simpan
3. (Opsional) **New variable** → Name `GROQ_MODEL`, Value `openai/gpt-oss-120b` (default sudah ini, jadi opsional)

### 2.4 Tunggu build & catat URL
1. Buka tab **Logs** — tunggu sampai muncul `✅ Loaded ML model` lalu status **Running** (build Docker ~2–4 menit)
2. URL backend Anda berbentuk:
   ```
   https://USERNAME-mlchem-backend.hf.space
   ```
3. **Tes:** buka `https://USERNAME-mlchem-backend.hf.space/` di browser. Harus muncul JSON:
   ```json
   { "status": "Unified backend running 🚀", "ai_configured": true, ... }
   ```
   Kalau `ai_configured: true` → secret sudah terbaca. 🎉

📌 **Simpan URL ini**, dipakai di Bagian 3.

---

## BAGIAN 3 — Deploy Frontend ke Vercel

### 3.1 Import repo
1. Buka [vercel.com/new](https://vercel.com/new) → login dengan GitHub
2. Pilih repo `mlchem-selector` → **Import**

### 3.2 Atur konfigurasi build
- **Root Directory:** klik **Edit** → pilih **`frontend`** ⚠️ (penting, karena React ada di dalam folder `frontend`)
- **Framework Preset:** Vite (biasanya terdeteksi otomatis)
- Build Command & Output (`dist`) biarkan default

### 3.3 Pasang alamat backend
Sebelum klik Deploy, buka **Environment Variables**, tambahkan:

| Name | Value |
|------|-------|
| `VITE_API_URL` | `https://USERNAME-mlchem-backend.hf.space` |

> Pakai URL Space dari Bagian 2.4. **Tanpa** garis miring `/` di akhir.

### 3.4 Deploy
Klik **Deploy**. Tunggu ~1–2 menit. Anda dapat URL seperti `https://mlchem-selector.vercel.app`.

---

## BAGIAN 4 — Uji & Selesai

1. Buka URL Vercel Anda
2. Pilih Property + Sub-property, isi Application Domain & System Type (opsional), klik **Compare ML vs AI**
3. Harus muncul: rekomendasi ML (COSMO-RS/DFT/MD) + panel AI (GPT-OSS 120B) + banner agreement

✅ **Selesai!** Aplikasi Anda live dan gratis.

---

## 🔧 Troubleshooting

| Masalah | Penyebab & Solusi |
|---------|-------------------|
| Frontend muncul, tapi klik Compare → "Connection error" | `VITE_API_URL` salah/ada `/` di akhir. Perbaiki di Vercel → Settings → Environment Variables → **Redeploy**. |
| Panel AI: "AI unavailable" | Secret `GROQ_API_KEY` belum dipasang di HF Space, atau key salah. Cek Space → Settings → Variables and secrets. Setelah menambah secret, buka Space → **Restart**. |
| Request pertama lambat/timeout | HF Space free "tidur" setelah lama tidak dipakai. Request pertama membangunkannya (~30 dtk). Coba lagi. |
| CORS error di browser | Sudah ditangani (`CORS(app)` mengizinkan semua origin). Kalau tetap muncul, pastikan URL backend benar & Space **Running**. |
| Build HF gagal di `scikit-learn` | Pastikan folder `ml_model/` ikut terupload dan `requirements.txt` ada di root Space. |

---

## 🔄 Cara Update Nanti (setelah ada perubahan kode)

- **Backend berubah** → upload ulang file yang berubah ke HF Space (atau `git push` ke repo Space). Space rebuild otomatis.
- **Frontend berubah** → cukup `git push` ke GitHub. Vercel auto-deploy setiap push ke branch `main`.

---

## 📁 Ringkasan File Penting

```
backend/
├── app.py            ← backend gabungan (ML + Groq)  [BARU]
├── Dockerfile        ← untuk Hugging Face Space       [BARU]
├── README.md         ← metadata HF Space              [BARU]
├── requirements.txt  ← dependensi Python (+ groq, gunicorn)
├── ml_model/
│   └── production_chemistry_classifier.pkl  ← model aktif
├── .env              ← key lokal (TIDAK di-upload)
└── server.js         ← lama, tidak dipakai lagi (boleh diabaikan)

frontend/
├── src/App.jsx       ← UI (pakai VITE_API_URL)
└── .env.example      ← contoh konfigurasi URL backend
```
