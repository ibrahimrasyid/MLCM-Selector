"""
MLCheM Selector - Reproducible training script
==============================================
Reproduces the classifier and the tables reported in the manuscript
(Section 8.2: Table 17 = candidate-model comparison, Table 18 = held-out
per-class performance, plus the held-out confusion matrix).

Pipeline (identical to Model/Model_MLchemTools.ipynb):
  1. load Dataset.xlsx (sheet "Dataset") and drop records with a missing label
  2. canonicalise "Primary Method" into 3 classes (COSMO-RS, DFT, MD);
     records mapped to "Other" are excluded (and reported)
  3. TF-IDF features from 4 text fields (property, sub_property,
     Application Domain, System Type)
  4. paper-grouped 85/15 train/test split (GroupShuffleSplit, seed 42)
  5. 5-fold Stratified Group CV on the training pool for 9 candidate models;
     CV accuracy / precision / recall / macro-F1 (mean +- SD over folds),
     train macro-F1 and generalisation gap (= train F1 - CV F1)
  6. selection rule: shortlist models within 0.5% of the best CV macro-F1,
     then pick the one with the smallest generalisation gap
  7. retrain on the whole training pool and evaluate once on the held-out test set

Run:
    pip install -r requirements.txt
    python train.py

Outputs (written next to this script):
    production_chemistry_classifier.pkl   trained pipeline + label encoder
    cv_results.csv                        Table 17 (all candidates, incl. Zero-R)
    classification_report.txt             Table 18 (per-class precision/recall/F1)
    confusion_matrix.csv / .png           held-out confusion matrix
    metrics_summary.json                  headline metrics, baseline, split sizes,
                                          excluded records, library versions

Notes
-----
* Dataset.xlsx must be in this folder. Only the sheet "Dataset" is used.
  The sheet "Validation" (if present) is NOT used for training or evaluation.
* Results depend on library versions. requirements.txt pins scikit-learn
  (1.6.1) and xgboost; running with other versions may change CV numbers and
  even the selected model. A warning is printed if the versions differ.
* XGBoost is required so that all 9 candidates are always evaluated.
  Set ALLOW_NO_XGB=1 only for a quick smoke test (Table 17 will then be
  incomplete and the script says so).
"""
import os
import re
import json
import math
import sys
from collections import Counter

import numpy as np
import pandas as pd
import joblib
import sklearn

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.naive_bayes import MultinomialNB, ComplementNB
from sklearn.ensemble import VotingClassifier
from sklearn.dummy import DummyClassifier
from sklearn.model_selection import StratifiedGroupKFold, GroupShuffleSplit
from sklearn.metrics import (classification_report, confusion_matrix, f1_score,
                             accuracy_score, precision_score, recall_score)
from sklearn.preprocessing import LabelEncoder
from sklearn.pipeline import Pipeline
from sklearn.calibration import CalibratedClassifierCV

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(HERE, "Dataset.xlsx")
RANDOM_STATE = 42
MARGIN_TOL = 0.005                 # shortlist models within 0.5% of best CV macro-F1
PINNED_SKLEARN = "1.6.1"           # version used for the manuscript results
EXPECTED_MODEL = "Complement NB (Alpha 0.5)"   # model reported in the manuscript


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def canonicalize_method(raw: str) -> str:
    """Map heterogeneous 'Primary Method' strings into 3 canonical classes.

    Rules (order matters): any COSMO* -> COSMO-RS (incl. COSMO-SAC);
    DFT / TD-DFT / CDFT / first-principles / NEGF -> DFT;
    molecular dynamics / MD / AIMD / NEMD / SMD / FPMD / ReaxFF -> MD;
    everything else -> "Other" (excluded).
    """
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


def wilson_ci(k, n, z=1.96):
    """95% Wilson score interval for a proportion k/n."""
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    denom = 1 + z ** 2 / n
    centre = (p + z ** 2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / denom
    return (centre - half, centre + half)


def build_models():
    """The 9 candidate models of Table 17 (identical to the notebook)."""
    models = {
        "Multinomial Naive Bayes (Alpha 0.3)": MultinomialNB(alpha=0.3),
        "Complement NB (Alpha 0.1)": ComplementNB(alpha=0.1),
        "Complement NB (Alpha 0.3)": ComplementNB(alpha=0.3),
        "Complement NB (Alpha 0.5)": ComplementNB(alpha=0.5),
        "Logistic Regression (balanced)": LogisticRegression(
            max_iter=3000, class_weight="balanced", C=2.0),
        "Logistic Regression (standard)": LogisticRegression(
            max_iter=3000, C=2.0),
        "Linear SVC (calibrated)": CalibratedClassifierCV(
            LinearSVC(class_weight="balanced", C=1.0), cv=3),
        "Ensemble Soft Voting": VotingClassifier(
            estimators=[
                ("nb", ComplementNB(alpha=0.3)),
                ("lr", LogisticRegression(max_iter=3000, class_weight="balanced", C=2.0)),
                ("svc", CalibratedClassifierCV(LinearSVC(class_weight="balanced"), cv=3)),
            ],
            voting="soft", weights=[1.5, 1, 1]),
    }
    if HAS_XGB:
        # Same settings as the notebook (no subsample argument).
        models["XGBoost"] = XGBClassifier(
            n_estimators=200, max_depth=4, learning_rate=0.1,
            eval_metric="mlogloss", random_state=RANDOM_STATE)
    return models


def cross_validate(name, clf, text_train, y_train, groups_train, sgkf):
    """5-fold Stratified Group CV; returns a dict of fold-averaged metrics."""
    accs, precs, recs, f1s, tr_f1s = [], [], [], [], []
    for tr, va in sgkf.split(text_train, y_train, groups=groups_train):
        pipe = Pipeline([("tfidf", make_tfidf()), ("clf", clf)])
        pipe.fit(text_train[tr], y_train[tr])
        p_va = pipe.predict(text_train[va])
        p_tr = pipe.predict(text_train[tr])
        accs.append(accuracy_score(y_train[va], p_va))
        precs.append(precision_score(y_train[va], p_va, average="macro", zero_division=0))
        recs.append(recall_score(y_train[va], p_va, average="macro", zero_division=0))
        f1s.append(f1_score(y_train[va], p_va, average="macro", zero_division=0))
        tr_f1s.append(f1_score(y_train[tr], p_tr, average="macro", zero_division=0))
    return {
        "Model": name,
        "CV_Accuracy": float(np.mean(accs)), "CV_Accuracy_SD": float(np.std(accs)),
        "CV_Precision": float(np.mean(precs)),
        "CV_Recall": float(np.mean(recs)),
        "CV_MacroF1": float(np.mean(f1s)), "CV_MacroF1_SD": float(np.std(f1s)),
        "Train_MacroF1": float(np.mean(tr_f1s)),
        "Generalization_Gap": float(np.mean(tr_f1s) - np.mean(f1s)),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    # -- environment checks ---------------------------------------------------
    if sklearn.__version__ != PINNED_SKLEARN:
        print(f"WARNING: scikit-learn {sklearn.__version__} in use; manuscript results "
              f"were produced with {PINNED_SKLEARN}. CV numbers (and the selected "
              f"model) may differ.\n")
    if not HAS_XGB:
        if os.environ.get("ALLOW_NO_XGB") == "1":
            print("WARNING: xgboost not installed -> only 8 of 9 candidates evaluated "
                  "(Table 17 incomplete). Smoke-test mode.\n")
        else:
            sys.exit("ERROR: xgboost is required (pip install -r requirements.txt) so that "
                     "all 9 candidate models are evaluated. "
                     "Set ALLOW_NO_XGB=1 for a quick smoke test only.")

    # -- load & clean ---------------------------------------------------------
    raw = pd.read_excel(DATA_PATH, sheet_name="Dataset")
    n_raw = len(raw)
    df = raw.dropna(subset=["Primary Method", "property"]).reset_index(drop=True)
    n_missing = n_raw - len(df)

    df["method_final"] = df["Primary Method"].apply(canonicalize_method)
    excluded = df[df["method_final"] == "Other"]
    excluded_methods = dict(Counter(excluded["Primary Method"].astype(str)))
    df = df[df["method_final"] != "Other"].reset_index(drop=True)

    print(f"Rows in sheet: {n_raw} | dropped (missing label/property): {n_missing} | "
          f"excluded as non-DFT/MD/COSMO-RS: {len(excluded)} | kept: {len(df)}")
    print("Class distribution:\n", df["method_final"].value_counts(), "\n")

    # -- features & labels ----------------------------------------------------
    for col in ["property", "sub_property", "Application Domain", "System Type"]:
        df[col] = df[col].fillna("").astype(str)
    text_all = (df["property"] + " . " + df["sub_property"] + " . " +
                df["Application Domain"] + " . " + df["System Type"]).values
    le = LabelEncoder()
    y = le.fit_transform(df["method_final"])
    groups = df["Paper"].values
    n_papers_total = int(len(np.unique(groups)))
    print(f"Classes: {list(le.classes_)} | records: {len(text_all)} | unique papers: {n_papers_total}")

    # -- paper-grouped split ----------------------------------------------------
    gss = GroupShuffleSplit(n_splits=1, test_size=0.15, random_state=RANDOM_STATE)
    train_idx, test_idx = next(gss.split(text_all, y, groups=groups))
    text_train, text_test = text_all[train_idx], text_all[test_idx]
    y_train, y_test = y[train_idx], y[test_idx]
    groups_train = groups[train_idx]
    n_pap_train = int(len(np.unique(groups_train)))
    n_pap_test = int(len(np.unique(groups[test_idx])))
    assert not (set(groups_train) & set(groups[test_idx])), "paper leaked across split"
    print(f"Train: {len(train_idx)} records / {n_pap_train} papers | "
          f"Test: {len(test_idx)} records / {n_pap_test} papers\n")

    # -- cross-validated model comparison (Table 17) ---------------------------
    sgkf = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    rows = []

    # Zero-R majority baseline evaluated with the SAME CV protocol
    rows.append(cross_validate("Zero-R (Majority Baseline)",
                               DummyClassifier(strategy="most_frequent"),
                               text_train, y_train, groups_train, sgkf))

    models = build_models()
    for name, clf in models.items():
        rows.append(cross_validate(name, clf, text_train, y_train, groups_train, sgkf))

    cv_df = pd.DataFrame(rows)
    hdr = (f"{'Model':<38} | {'CV Acc':<14} | {'CV Prec':<7} | {'CV Rec':<7} | "
           f"{'CV Macro-F1':<15} | {'Train F1':<8} | {'Gap':<5}")
    print("MODEL COMPARISON (5-fold Stratified Group CV, SD = std over folds)")
    print("-" * len(hdr)); print(hdr); print("-" * len(hdr))
    for r in rows:
        print(f"{r['Model']:<38} | {r['CV_Accuracy']:.3f} +- {r['CV_Accuracy_SD']:.3f} | "
              f"{r['CV_Precision']:.3f}   | {r['CV_Recall']:.3f}   | "
              f"{r['CV_MacroF1']:.3f} +- {r['CV_MacroF1_SD']:.3f} | "
              f"{r['Train_MacroF1']:.3f}  | {r['Generalization_Gap']:.3f}")
    cv_df.round(4).to_csv(os.path.join(HERE, "cv_results.csv"), index=False)

    # -- model selection (Zero-R is not a candidate) ----------------------------
    cand = {r["Model"]: r for r in rows if not r["Model"].startswith("Zero-R")}
    max_cv = max(r["CV_MacroF1"] for r in cand.values())
    shortlist = {n: r["Generalization_Gap"] for n, r in cand.items()
                 if (max_cv - r["CV_MacroF1"]) <= MARGIN_TOL}
    best_name = min(shortlist, key=shortlist.get)
    print(f"\nBest CV macro-F1: {max_cv:.3f} | shortlist (within {MARGIN_TOL:.3f}): "
          f"{ {k: round(v, 3) for k, v in shortlist.items()} }")
    print(f"Selected model: {best_name} (min generalisation gap = {shortlist[best_name]:.3f})")
    if best_name != EXPECTED_MODEL:
        print(f"WARNING: selected model differs from the one reported in the manuscript "
              f"({EXPECTED_MODEL}). Check library versions (requirements.txt).")
    print()

    # -- final retrain + blind evaluation (Table 18) ---------------------------
    best_pipe = Pipeline([("tfidf", make_tfidf()), ("clf", models[best_name])])
    best_pipe.fit(text_train, y_train)
    y_pred = best_pipe.predict(text_test)

    acc = accuracy_score(y_test, y_pred)
    macro_f1 = f1_score(y_test, y_pred, average="macro", zero_division=0)
    macro_p = precision_score(y_test, y_pred, average="macro", zero_division=0)
    macro_r = recall_score(y_test, y_pred, average="macro", zero_division=0)
    report = classification_report(y_test, y_pred, target_names=le.classes_, zero_division=0)
    ci_lo, ci_hi = wilson_ci(int((y_pred == y_test).sum()), len(y_test))

    # Zero-R on the SAME test set (majority class of the training pool)
    zr = DummyClassifier(strategy="most_frequent").fit(text_train, y_train)
    zr_acc = accuracy_score(y_test, zr.predict(text_test))
    lift = (acc - zr_acc) * 100

    print("=" * 62)
    print(f"Final model: {best_name}")
    print(f"Test accuracy: {acc:.3f} (95% Wilson CI {ci_lo:.3f}-{ci_hi:.3f}) | "
          f"Test macro-F1: {macro_f1:.3f}\n")
    print(report)
    print(f"Zero-R baseline on the test set: {zr_acc:.3f} | Lift: +{lift:.1f} percentage points")

    cm = confusion_matrix(y_test, y_pred)
    pd.DataFrame(cm, index=[f"true_{c}" for c in le.classes_],
                 columns=[f"pred_{c}" for c in le.classes_]).to_csv(
        os.path.join(HERE, "confusion_matrix.csv"))

    # -- save artefacts -----------------------------------------------------------
    joblib.dump({"pipeline": best_pipe, "label_encoder": le, "model_name": best_name},
                os.path.join(HERE, "production_chemistry_classifier.pkl"))
    with open(os.path.join(HERE, "classification_report.txt"), "w") as f:
        f.write(f"Model: {best_name}\nAccuracy: {acc:.3f} "
                f"(95% Wilson CI {ci_lo:.3f}-{ci_hi:.3f})\nMacro-F1: {macro_f1:.3f}\n\n"
                f"{report}\n")
        f.write(f"Zero-R baseline (test set): {zr_acc:.3f}\n"
                f"Lift: +{lift:.1f} percentage points\n")
    summary = {
        "model": best_name,
        "accuracy": round(acc, 4), "accuracy_ci95_wilson": [round(ci_lo, 4), round(ci_hi, 4)],
        "macro_precision": round(macro_p, 4), "macro_recall": round(macro_r, 4),
        "macro_f1": round(macro_f1, 4),
        "baseline_zero_r_test": round(zr_acc, 4),
        "lift_percentage_points": round(lift, 1),
        "classes": list(le.classes_),
        "n_records": int(len(df)), "n_papers_total": n_papers_total,
        "n_train_records": int(len(train_idx)), "n_train_papers": n_pap_train,
        "n_test_records": int(len(test_idx)), "n_test_papers": n_pap_test,
        "rows_in_sheet": int(n_raw), "rows_dropped_missing": int(n_missing),
        "rows_excluded_other_methods": int(len(excluded)),
        "excluded_methods": excluded_methods,
        "selection_rule": f"shortlist within {MARGIN_TOL} of best CV macro-F1, then min (train F1 - CV F1)",
        "random_state": RANDOM_STATE,
        "versions": {"python": sys.version.split()[0], "scikit_learn": sklearn.__version__,
                     "numpy": np.__version__, "pandas": pd.__version__,
                     "xgboost": (__import__("xgboost").__version__ if HAS_XGB else None)},
    }
    with open(os.path.join(HERE, "metrics_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    # -- optional confusion-matrix figure ----------------------------------------
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(5, 4.5))
        ax.imshow(cm, cmap="Blues")
        ax.set_xticks(range(len(le.classes_))); ax.set_yticks(range(len(le.classes_)))
        ax.set_xticklabels(le.classes_); ax.set_yticklabels(le.classes_)
        ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
        ax.set_title(f"Confusion Matrix - {best_name}")
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                ax.text(j, i, cm[i, j], ha="center", va="center", fontweight="bold",
                        color="white" if cm[i, j] > cm.max() / 2 else "black")
        fig.tight_layout()
        fig.savefig(os.path.join(HERE, "confusion_matrix.png"), dpi=200)
        print("Saved confusion_matrix.png")
    except Exception as e:  # matplotlib is optional
        print("(confusion matrix figure skipped:", e, ")")

    print("\nDone. Artefacts written to:", HERE)


if __name__ == "__main__":
    main()
