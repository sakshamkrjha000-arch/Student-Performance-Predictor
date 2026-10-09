"""
ml/train_performance.py
Full ML pipeline for student performance classification.

Steps: load -> explore -> clean -> encode -> split -> train 4 models
(Logistic Regression, Decision Tree, Random Forest, KNN) -> evaluate
(accuracy, precision, recall, F1, confusion matrix) -> select the best
-> save model + evaluation graphs.

Run:  python ml/train_performance.py
"""
import json
import os

import matplotlib
matplotlib.use("Agg")                    # render without a screen
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (ConfusionMatrixDisplay, accuracy_score,
                             confusion_matrix, f1_score, precision_score,
                             recall_score)
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeClassifier

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET = os.path.join(BASE_DIR, "ml", "datasets",
                       "performance_dataset.csv")
MODEL_DIR = os.path.join(BASE_DIR, "saved_models")
IMAGE_DIR = os.path.join(BASE_DIR, "static", "images")
os.makedirs(MODEL_DIR, exist_ok=True)
os.makedirs(IMAGE_DIR, exist_ok=True)

LABELS = ["Needs Improvement", "Average", "Good"]


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
    print("\nClass distribution:")
    print(df["performance_category"].value_counts().to_string())
    return df


# ---------------------------------------------------------------
# 3. CLEAN + 4. HANDLE MISSING VALUES
# ---------------------------------------------------------------
def clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.drop_duplicates().copy()
    # keep only physically possible values
    df = df[(df["attendance_pct"].isnull())
            | (df["attendance_pct"].between(0, 100))]
    df = df[(df["study_hours"].isnull()) | (df["study_hours"].between(0, 16))]
    # impute missing numbers with the median of the column
    num_cols = df.columns.drop("performance_category")
    imputer = SimpleImputer(strategy="median")
    df[num_cols] = imputer.fit_transform(df[num_cols])
    print("\nSTEP 3-4: CLEANED.  Shape now:", df.shape,
          "| remaining NaNs:", int(df.isnull().sum().sum()))
    return df


# ---------------------------------------------------------------
# 6. ENCODE LABELS  (Good=2, Average=1, Needs Improvement=0)
# ---------------------------------------------------------------
def encode(y: pd.Series):
    mapping = {"Needs Improvement": 0, "Average": 1, "Good": 2}
    return y.map(mapping), mapping


# ---------------------------------------------------------------
# 7-9. SPLIT, TRAIN 4 MODELS, EVALUATE
# ---------------------------------------------------------------
def build_models():
    return {
        "Logistic Regression": Pipeline([
            ("scale", StandardScaler()),
            ("clf", LogisticRegression(max_iter=2000, C=1.0)),
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
    # macro = every class counts equally (classes are slightly imbalanced)
    prec = precision_score(yte, pred, average="macro", zero_division=0)
    rec = recall_score(yte, pred, average="macro", zero_division=0)
    f1 = f1_score(yte, pred, average="macro", zero_division=0)
    cv = cross_val_score(model, Xtr, ytr, cv=5).mean()

    results[name] = {"accuracy": acc, "precision": prec, "recall": rec,
                     "f1": f1, "cv_mean": cv,
                     "cm": confusion_matrix(yte, pred,
                                            labels=[0, 1, 2]).tolist()}
    print(f"{name:22s} acc={acc:.3f} prec={prec:.3f} "
          f"rec={rec:.3f} f1={f1:.3f} cv={cv:.3f}")


# ---------------------------------------------------------------
# GRAPHS
# ---------------------------------------------------------------
def save_graphs(results, best_name, y_test, best_pred, class_names):
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
    ax.set_title("Performance Model - Algorithm Comparison")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(os.path.join(IMAGE_DIR, "performance_model_comparison.png"),
                dpi=130)
    plt.close(fig)

    # --- confusion matrix of the best model ---
    cm = np.array(results[best_name]["cm"])
    fig, ax = plt.subplots(figsize=(6, 5))
    disp = ConfusionMatrixDisplay(cm, display_labels=class_names)
    disp.plot(ax=ax, cmap="Blues", colorbar=False)
    ax.set_title(f"Confusion Matrix - {best_name}")
    fig.tight_layout()
    fig.savefig(os.path.join(IMAGE_DIR, "performance_confusion_matrix.png"),
                dpi=130)
    plt.close(fig)

    # --- feature importances (trees only) ---
    clf = best_model.named_steps.get("clf", best_model)
    importances = getattr(clf, "feature_importances_", None)
    if importances is not None:
        feature_names = FEATURE_COLUMNS
        order = np.argsort(importances)
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.barh(np.array(feature_names)[order], importances[order],
                color="#2e7d32")
        ax.set_title(f"Feature Importance - {best_name}")
        fig.tight_layout()
        fig.savefig(os.path.join(IMAGE_DIR,
                                 "performance_feature_importance.png"),
                    dpi=130)
        plt.close(fig)


# ---------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------
FEATURE_COLUMNS = ["attendance_pct", "assignment_marks", "internal_marks",
                   "prev_semester_marks", "study_hours",
                   "assignments_completed", "participation_score"]

if __name__ == "__main__":
    df = load_and_explore()
    df = clean(df)

    X = df[FEATURE_COLUMNS].values
    y, label_map = encode(df["performance_category"])
    class_names = [k for k, v in sorted(label_map.items(),
                                        key=lambda kv: kv[1])]

    # 7. stratified split keeps class proportions equal in train/test
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y)

    print("\nSTEP 7-9: TRAIN & EVALUATE")
    results = {}
    best_model, best_name, best_f1 = None, None, -1
    for name, model in build_models().items():
        evaluate(name, model, X_train, X_test, y_train, y_test, results)
        if results[name]["f1"] > best_f1:
            best_model, best_name, best_f1 = model, name, results[name]["f1"]

    # 10. SELECT BEST by macro-F1 (fair when classes are imbalanced)
    print(f"\nSTEP 10: SELECTED MODEL -> {best_name} "
          f"(macro-F1 = {best_f1:.3f})")

    best_pred = best_model.predict(X_test)
    save_graphs(results, best_name, y_test, best_pred, class_names)

    # 11. SAVE
    model_path = os.path.join(MODEL_DIR, "performance_model.pkl")
    joblib.dump({"model": best_model,
                 "feature_columns": FEATURE_COLUMNS,
                 "label_names": class_names,
                 "best_algorithm": best_name,
                 "metrics": {k: {m: round(v, 4) for m, v in d.items()
                                 if m != "cm"}
                             for k, d in results.items()}},
                model_path)
    print(f"STEP 11: SAVED -> {model_path}")

    with open(os.path.join(MODEL_DIR, "performance_metrics.json"),
              "w") as f:
        json.dump({"best_algorithm": best_name,
                   "metrics": {k: {m: round(v, 4) for m, v in d.items()
                                   if m != "cm"}
                               for k, d in results.items()}}, f, indent=2)
    print("Done.")
