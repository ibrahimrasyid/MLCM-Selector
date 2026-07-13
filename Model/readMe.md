# 🧪 MLChem Tools — Machine Learning Model Integration Guide

This repository contains the Machine Learning (ML) model assets designed to classify computational chemistry literature into 3 primary methodologies: **DFT**, **MD**, or **COSMO-RS**, based on academic text input.

This documentation is intended for the web application team (UI/Frontend/Backend) to simplify integrating the model into the dropdown interface and the prediction system.

---

## 📦 1. Model Artifact (Deployment Assets)

All inference components are bundled into a single compressed binary file for transparency and architectural consistency:
* **File name:** `production_chemistry_classifier.pkl`
* **Bundle contents (dictionary keys):**
  * `"pipeline"`: An `sklearn.pipeline.Pipeline` object containing the built-in *TF-IDF Vectorizer* together with the weights of the best model selected during evaluation.
  * `"label_encoder"`: A `LabelEncoder` object that maps numeric predictions (`0, 1, 2`) back to the original class strings (`DFT`, `MD`, `COSMO-RS`).
  * `"model_name"`: A string with the name of the selected best-model architecture, kept for system documentation.

---

## 🚀 2. How to Load and Use the Model in the Backend (Python)

Make sure the backend server environment has the required libraries installed (`scikit-learn` and `joblib`). The UI/Backend team does not need to perform text extraction (TF-IDF) manually, because the processing pipeline is already embedded inside the model object.

### Example Inference Code:
```python
import joblib

# 1. Load the model artifact
artifacts = joblib.load("production_chemistry_classifier.pkl")
model_pipeline = artifacts["pipeline"]
label_encoder = artifacts["label_encoder"]

# 2. Prepare the raw text input from the UI form
# The model was built by concatenating 4 text components using a dot separator (" . ")
property_input = "Gibbs free energy"
sub_property_input = "Solubility"
application_domain = "Gas separation"
system_type = "Ionic liquids"

# Concatenate following the model's training format
constructed_text = f"{property_input} . {sub_property_input} . {application_domain} . {system_type}"

# 3. Run an instant prediction
# The model expects a list or array of raw text strings
predicted_numeric = model_pipeline.predict([constructed_text])

# 4. Decode the numeric label back to the original class name
predicted_class = label_encoder.inverse_transform(predicted_numeric)[0]

print(f"Method classification result: {predicted_class}")
# Example output: "COSMO-RS", "DFT", or "MD"
```
