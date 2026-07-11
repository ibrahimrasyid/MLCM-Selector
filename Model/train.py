"""
MLCheM Selector — Reproducible training script
================================================
Reproduces the classifier reported in the manuscript (Section 6.2):
  - loads the real literature dataset (Dataset.xlsx)
  - canonicalises the primary-method labels into 3 classes (COSMO-RS, DFT, MD)
  - builds TF-IDF features from 4 text fields
  - performs a LEAK-PROOF, paper-grouped train/test split (fixed seed)
  - selects a model by 5-fold Stratified Group CV (min generalisation gap)
  - evaluates on the blind held-out test set and saves all artefacts

Run:
    pip install -r requirements.txt
    python train.py

Outputs (written next to this script):
    production_chemistry_classifier.pkl   trained pipeline + label encoder
    classification_report.txt             per-class precision/recall/F1
    confusion_matrix.png                  held-out confusion matrix
    metrics_summary.json                  accuracy, macro-F1, baseline, lift

NOTE: Dataset.xlsx must be present in this folder. It contains the real
literature records (columns: Paper, Primary Method, property, sub_property,
Application Domain, System Type). The labels are the primary methods actually
reported in each paper — they are NOT synthetically generated.
"""
import os, re, json
import numpy as np
import pandas as pd

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.naive_bayes import MultinomialNB, ComplementNB
from sklearn.ensemble import VotingClassifier
from sklearn.model_selection import StratifiedGroupKFold, GroupShuffleSplit
from sklearn.metrics import classification_report, confusion_matrix, f1_score, accuracy_score
from sklearn.preprocessing import LabelEncoder
from sklearn.pipeline import Pipeline
from sklearn.calibration import CalibratedClassifierCV
import joblib

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

HERE         = os.path.dirname(os.path.abspath(__file__))
DATA_PATH    = os.path.join(HERE, "Dataset.xlsx")
RANDOM_STATE = 42
MARGIN_TOL   = 0.005   # shortlist models within 0.5% of the best CV macro-F1


def canonicalize_method(raw: str) -> str:
    """Map heterogeneous 'Primary Method' strings into 3 canonical classes."""
    s = str(raw).lower()
    if "cosmo" in s:
        return "COSMO-RS"
    if "dft" in s or "cdft" in s or "first-principles" in s or "negf" in s:
        return "DFT"
    if ("molecular dynamics" in s or re.search(r"\bmd\b", s) or "aimd" in s
            or "nemd" in s or "smd" in s or "fpmd" in s or "reaxff" in s):
        return "MD"
    return "Other"


def make_tfidf():
    return TfidfVectorizer(
        max_features=1500, ngram_range=(1, 2),
        min_df=1, sublinear_tf=True, stop_words="english",
    )


def main():
    # ── Load & clean ────────────────────────────────────────────────────────
    df = pd.read_excel(DATA_PATH)
    df = df.dropna(subset=["Primary Method", "property"]).reset_index(drop=True)

    df["method_final"] = df["Primary Method"].apply(canonicalize_method)
    df = df[df["method_final"] != "Other"].reset_index(drop=True)
    print("Class distribution:\n", df["method_final"].value_counts(), "\n")

    baseline_acc = (df["method_final"] == "DFT").mean()  # Zero-R majority

    # ── Features (4 text fields) & labels ───────────────────────────────────
    for col in ["property", "sub_property", "Application Domain", "System Type"]:
        df[col] = df[col].fillna("").astype(str)

    text_all = (df["property"] + " . " + df["sub_property"] + " . " +
                df["Application Domain"] + " . " + df["System Type"]).values
    le = LabelEncoder()
    y = le.fit_transform(df["method_final"])
    groups = df["Paper"].values
    print("Classes:", list(le.classes_), "| records:", len(text_all))

    # ── Leak-proof, paper-grouped split ─────────────────────────────────────
    gss = GroupShuffleSplit(n_splits=1, test_size=0.15, random_state=RANDOM_STATE)
    train_idx, test_idx = next(gss.split(text_all, y, groups=groups))
    text_train, text_test = text_all[train_idx], text_all[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]
    groups_train = groups[train_idx]
    print(f"Train: {len(train_idx)} rows / {len(np.unique(groups_train))} papers | "
          f"Test: {len(test_idx)} rows / {len(np.unique(groups[test_idx]))} papers\n")

    # ── Candidate models ────────────────────────────────────────────────────
    model_defs = {
        "Multinomial Naive Bayes (Alpha 0.3)": MultinomialNB(alpha=0.3),
        "Complement NB (Alpha 0.1)": ComplementNB(alpha=0.1),
        "Complement NB (Alpha 0.3)": ComplementNB(alpha=0.3),
        "Complement NB (Alpha 0.5)": ComplementNB(alpha=0.5),
        "Logistic Regression (balanced)": LogisticRegression(max_iter=3000, class_weight="balanced", C=2.0),
        "Logistic Regression (standard)": LogisticRegression(max_iter=3000, C=2.0),
        "Linear SVC (calibrated)": CalibratedClassifierCV(LinearSVC(class_weight="balanced", C=1.0), cv=3),
        "Ensemble Soft Voting": VotingClassifier(
            estimators=[
                ("nb", ComplementNB(alpha=0.3)),
                ("lr", LogisticRegression(max_iter=3000, class_weight="balanced", C=2.0)),
                ("svc", CalibratedClassifierCV(LinearSVC(class_weight="balanced"), cv=3)),
            ], voting="soft", weights=[1.5, 1, 1]),
    }
    if HAS_XGB:
        model_defs["XGBoost"] = XGBClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.1,
            subsample=0.9, random_state=RANDOM_STATE, eval_metric="mlogloss")

    # ── Model selection: 5-fold Stratified Group CV, min generalisation gap ──
    sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    cv_results = {}
    for name, clf in model_defs.items():
        val_scores, train_scores = [], []
        for tr, va in sgkf.split(text_train, y_train, groups=groups_train):
            pipe = Pipeline([("tfidf", make_tfidf()), ("clf", clf)])
            pipe.fit(text_train[tr], y_train[tr])
            val_scores.append(f1_score(y_train[va], pipe.predict(text_train[va]), average="macro", zero_division=0))
            train_scores.append(f1_score(y_train[tr], pipe.predict(text_train[tr]), average="macro", zero_division=0))
        cv_f1, train_f1 = np.mean(val_scores), np.mean(train_scores)
        cv_results[name] = (cv_f1, train_f1)
        print(f"  {name:<38} CV F1={cv_f1:.3f} | Train F1={train_f1:.3f} | Gap={train_f1-cv_f1:.3f}")

    max_cv = max(v[0] for v in cv_results.values())
    shortlist = {n: (tr - cv) for n, (cv, tr) in cv_results.items() if (max_cv - cv) <= MARGIN_TOL}
    best_name = min(shortlist, key=shortlist.get)
    print(f"\nSelected model: {best_name} (min generalisation gap = {shortlist[best_name]:.3f})\n")

    # ── Final retrain + blind evaluation ────────────────────────────────────
    best_pipe = Pipeline([("tfidf", make_tfidf()), ("clf", model_defs[best_name])])
    best_pipe.fit(text_train, y_train)
    y_pred = best_pipe.predict(text_test)

    acc = accuracy_score(y_test, y_pred)
    macro_f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)
    report = classification_report(y_test, y_pred, target_names=le.classes_, zero_division=0)
    print("=" * 60)
    print(f"Final model: {best_name}\nTest accuracy: {acc:.3f} | Test macro-F1: {macro_f1:.3f}\n")
    print(report)
    print(f"Zero-R baseline: {baseline_acc:.3f} | Lift: +{(acc-baseline_acc)*100:.1f} pts")

    # ── Save artefacts ──────────────────────────────────────────────────────
    joblib.dump({"pipeline": best_pipe, "label_encoder": le, "model_name": best_name},
                os.path.join(HERE, "production_chemistry_classifier.pkl"))
    with open(os.path.join(HERE, "classification_report.txt"), "w") as f:
        f.write(f"Model: {best_name}\nAccuracy: {acc:.3f}\nMacro-F1: {macro_f1:.3f}\n\n{report}\n")
        f.write(f"Zero-R baseline: {baseline_acc:.3f}\nLift: +{(acc-baseline_acc)*100:.1f} pts\n")
    with open(os.path.join(HERE, "metrics_summary.json"), "w") as f:
        json.dump({"model": best_name, "accuracy": round(acc, 4),
                   "macro_f1": round(macro_f1, 4), "baseline_zero_r": round(baseline_acc, 4),
                   "lift_points": round((acc - baseline_acc) * 100, 1),
                   "classes": list(le.classes_), "n_train": int(len(train_idx)),
                   "n_test": int(len(test_idx))}, f, indent=2)

    # Confusion matrix figure (optional, requires matplotlib)
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        cm = confusion_matrix(y_test, y_pred)
        fig, ax = plt.subplots(figsize=(5, 4.5))
        im = ax.imshow(cm, cmap="Blues")
        ax.set_xticks(range(len(le.classes_))); ax.set_yticks(range(len(le.classes_)))
        ax.set_xticklabels(le.classes_); ax.set_yticklabels(le.classes_)
        ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
        ax.set_title(f"Confusion Matrix — {best_name}")
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                ax.text(j, i, cm[i, j], ha="center", va="center",
                        color="white" if cm[i, j] > cm.max() / 2 else "black", fontweight="bold")
        fig.tight_layout(); fig.savefig(os.path.join(HERE, "confusion_matrix.png"), dpi=200)
        print("Saved confusion_matrix.png")
    except Exception as e:
        print("(confusion matrix figure skipped:", e, ")")

    print("\nDone. Artefacts written to:", HERE)


if __name__ == "__main__":
    main()
