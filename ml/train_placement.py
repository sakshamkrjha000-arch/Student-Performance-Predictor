"""
ml/train_placement.py
Full ML pipeline for placement prediction (binary classification).

Steps: load -> explore -> clean -> encode -> split -> train 4 models
(Logistic Regression, Decision Tree, Random Forest, KNN) -> evaluate
(accuracy, precision, recall, F1, confusion matrix) -> select the best
-> save model + evaluation graphs.

Run:  python ml/train_placement.py
"""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score,
                             confusion_matrix, f1_score, precision_score,
                             recall_score, roc_auc_score, roc_curve)
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET = os.path.join(BASE_DIR, "ml", "datasets", "placement_dataset.csv")
MODEL_DIR = os.path.join(BASE_DIR, "saved_models")
IMAGE_DIR = os.path.join(BASE_DIR, "static", "images")
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)


# ---------------------------------------------------------------
# 1. LOAD + 2. EXPLORE
# ---------------------------------------------------------------
def load_and_explore():
    df = pd.read_csv(DATASET)
    print("=" * 60)
    print("STEP 1-2: LOAD & EXPLORE")
    print(f"Shape: {df.shape}")
    print(df.head(3).to_string())
    print("\nMissing values per column:")
    print(df.isnull().sum().to_string())
    print("\nClass distribution (placed):")
    print(df["placed"].value_counts().to_string())
    return df


# ---------------------------------------------------------------
# 3. CLEAN + 4. HANDLE MISSING VALUES
# ---------------------------------------------------------------
def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates().copy()
    df = df[(df["cgpa"].isnull()) | (df["cgpa"].between(0, 10))]
    df = df[(df["attendance"].isnull()) | (df["attendance"].between(0, 100))]
    num_cols = df.columns.drop("placed")
    imputer = SimpleImputer(strategy="median")
    df[num_cols] = imputer.fit_transform(df[num_cols])
    print("\nSTEP 3-4: CLEANED.  Shape now:", df.shape,
          "| remaining NaNs:", int(df.isnull().sum().sum()))
    return df


# ---------------------------------------------------------------
# 7-9. SPLIT, TRAIN 4 MODELS, EVALUATE
# ---------------------------------------------------------------
def build_models():
    return {
        "Logistic Regression": Pipeline([
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(max_iter=2000)),
        ]),
        "Decision Tree": DecisionTreeClassifier(
            max_depth=6, min_samples_leaf=8, random_state=42),
        "Random Forest": RandomForestClassifier(
            n_estimators=200, max_depth=10, min_samples_leaf=4,
            random_state=42, n_jobs=-1),
        "KNN": Pipeline([
            ("scale", StandardScaler()),
            ("clf", KNeighborsClassifier(n_neighbors=15)),
        ]),
    }


def evaluate(name, model, Xtr, Xte, ytr, yte, results):
    model.fit(Xtr, ytr)
    pred = model.predict(Xte)
    acc = accuracy_score(yte, pred)
    prec = precision_score(yte, pred, zero_division=0)
    rec = recall_score(yte, pred, zero_division=0)
    f1 = f1_score(yte, pred, zero_division=0)
    cv = cross_val_score(model, Xtr, ytr, cv=5).mean()
    proba = model.predict_proba(Xte)[:, 1]
    auc = roc_auc_score(yte, proba)

    results[name] = {"accuracy": acc, "precision": prec, "recall": rec,
                     "f1": f1, "cv_mean": cv, "roc_auc": auc,
                     "cm": confusion_matrix(yte, pred,
                                            labels=[0, 1]).tolist()}
    print(f"{name:22s} acc={acc:.3f} prec={prec:.3f} rec={rec:.3f} "
          f"f1={f1:.3f} auc={auc:.3f} cv={cv:.3f}")


# ---------------------------------------------------------------
# GRAPHS
# ---------------------------------------------------------------
def save_graphs(results, best_name, X_test, y_test):
    metrics = ["accuracy", "precision", "recall", "f1"]
    x = np.arange(len(results))
    width = 0.2

    # --- comparison bar chart ---
    fig, ax = plt.subplots(figsize=(9, 5))
    for i, m in enumerate(metrics):
        vals = [results[name][m] for name in results]
        ax.bar(x + (i - 1.5) * width, vals, width, label=m.capitalize())
    ax.set_xticks(x)
    ax.set_xticklabels(list(results.keys()), fontsize=9)
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("Score")
    ax.set_title("Placement Model - Algorithm Comparison")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(IMAGE_DIR, "placement_model_comparison.png"),
                dpi=130)
    plt.close(fig)

    # --- confusion matrix of the best model ---
    cm = np.array(results[best_name]["cm"])
    fig, ax = plt.subplots(figsize=(5.5, 5))
    disp = ConfusionMatrixDisplay(cm, display_labels=["Not Placed",
                                                      "Placed"])
    disp.plot(ax=ax, cmap="Greens", colorbar=False)
    ax.set_title(f"Confusion Matrix - {best_name}")
    fig.tight_layout()
    fig.savefig(os.path.join(IMAGE_DIR, "placement_confusion_matrix.png"),
                dpi=130)
    plt.close(fig)

    # --- ROC curves for every model ---
    fig, ax = plt.subplots(figsize=(7, 5.5))
    for name, model in trained_models.items():
        proba = model.predict_proba(X_test)[:, 1]
        fpr, tpr, _ = roc_curve(y_test, proba)
        ax.plot(fpr, tpr, label=f"{name} (AUC={results[name]['roc_auc']:.2f})")
    ax.plot([0, 1], [0, 1], "k--", alpha=0.5)
    ax.set_xlabel("False Positive Rate")
    ax.set_ylabel("True Positive Rate")
    ax.set_title("ROC Curves - Placement Model")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(IMAGE_DIR, "placement_roc_curve.png"), dpi=130)
    plt.close(fig)


# ---------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------
FEATURE_COLUMNS = ["cgpa", "attendance", "technical_score",
                   "communication_score", "projects_completed",
                   "internship_months", "certifications", "aptitude_score"]

if __name__ == "__main__":
    df = load_and_explore()
    df = clean(df)

    X = df[FEATURE_COLUMNS].values
    y = df["placed"].astype(int).values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)

    print("\nSTEP 7-9: TRAIN & EVALUATE")
    results = {}
    trained_models = {}
    best_model, best_name, best_f1 = None, None, -1
    for name, model in build_models().items():
        evaluate(name, model, X_train, X_test, y_train, y_test, results)
        trained_models[name] = model
        if results[name]["f1"] > best_f1:
            best_model, best_name, best_f1 = model, name, results[name]["f1"]

    print(f"\nSTEP 10: SELECTED MODEL -> {best_name} (F1 = {best_f1:.3f})")

    save_graphs(results, best_name, X_test, y_test)

    # 11. SAVE
    model_path = os.path.join(MODEL_DIR, "placement_model.pkl")
    joblib.dump({"model": best_model,
                 "feature_columns": FEATURE_COLUMNS,
                 "label_names": ["Not Placed", "Placed"],
                 "best_algorithm": best_name,
                 "metrics": {k: {m: round(v, 4) for m, v in d.items()
                                 if m != "cm"}
                             for k, d in results.items()}},
                model_path)
    print(f"STEP 11: SAVED -> {model_path}")

    with open(os.path.join(MODEL_DIR, "placement_metrics.json"), "w") as f:
        json.dump({"best_algorithm": best_name,
                   "metrics": {k: {m: round(v, 4) for m, v in d.items()
                                   if m != "cm"}
                               for k, d in results.items()}}, f, indent=2)
    print("Done.")
