# 🧪 MLChem Tools - Machine Learning Model Integration Guide

Repository ini berisi aset model Machine Learning (ML) yang dirancang untuk mengklasifikasikan literatur kimia komputasi ke dalam 3 metodologi utama: **DFT**, **MD**, atau **COSMO-RS** berdasarkan input teks akademis.

Dokumentasi ini ditujukan bagi tim pengembang aplikasi web (UI/Frontend/Backend) untuk mempermudah proses integrasi model ke antarmuka dropdown dan sistem prediksi.

---

## 📦 1. Artefak Model (Deployment Assets)

Seluruh komponen pendukung inferensi telah dibundel ke dalam satu file binary terkompresi demi transparansi dan konsistensi arsitektur:
* **Nama File:** `production_chemistry_classifier.pkl`
* **Isi Bundel (Dictionary Key):**
  * `"pipeline"`: Objek `sklearn.pipeline.Pipeline` yang berisi *TF-IDF Vectorizer* bawaan sekaligus bobot algoritma model terbaik hasil evaluasi.
  * `"label_encoder"`: Objek `LabelEncoder` untuk menerjemahkan prediksi numerik (`0, 1, 2`) kembali menjadi string teks kelas asli (`DFT`, `MD`, `COSMO-RS`).
  * `"model_name"`: String nama arsitektur model terbaik yang terpilih untuk dokumentasi sistem.

---

## 🚀 2. Cara Load dan Menggunakan Model di Backend (Python)

Pastikan lingkungan server backend telah menginstal pustaka yang dibutuhkan (`scikit-learn` dan `joblib`). Tim UI/Backend tidak perlu melakukan proses ekstraksi teks (TF-IDF) secara manual karena pipa pemrosesan sudah tertanam di dalam objek model.

### Contoh Implementasi Kode Inferensi:
```python
import joblib

# 1. Load artefak model
artifacts = joblib.load("production_chemistry_classifier.pkl")
model_pipeline = artifacts["pipeline"]
label_encoder = artifacts["label_encoder"]

# 2. Siapkan input teks mentah dari form UI
# Alur model dibangun dengan menggabungkan 4 komponen teks menggunakan pembatas titik (" . ")
property_input = "Gibbs free energy"
sub_property_input = "Solubility"
application_domain = "Gas separation"
system_type = "Ionic liquids"

# Gabungkan sesuai format training model
constructed_text = f"{property_input} . {sub_property_input} . {application_domain} . {system_type}"

# 3. Lakukan prediksi instan
# Model menerima input berupa list atau array berisi string teks mentah
predicted_numeric = model_pipeline.predict([constructed_text])

# 4. Decode label numerik ke teks nama kelas asli
predicted_class = label_encoder.inverse_transform(predicted_numeric)[0]

print(f"Hasil Klasifikasi Metode: {predicted_class}")
# Output contoh: "COSMO-RS" atau "DFT" atau "MD"
