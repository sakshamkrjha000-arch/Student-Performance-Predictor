"""
ml/generate_data.py
Generates educational sample datasets (synthetic, no real student data).

Run:  python ml/generate_data.py

Creates:
  ml/datasets/performance_dataset.csv
  ml/datasets/placement_dataset.csv
"""
import os

import numpy as np
import pandas as pd

DATASET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "datasets")
os.makedirs(DATASET_DIR, exist_ok=True)

rng = np.random.default_rng(seed=42)   # reproducible random numbers

N_PERFORMANCE = 600
N_PLACEMENT = 600


# ---------------------------------------------------------------
# 1. PERFORMANCE DATASET
# ---------------------------------------------------------------
def generate_performance() -> pd.DataFrame:
    """
    Each student gets a hidden 'effort level' 0..1 that drives every
    feature together, so the labels are learnable but noisy.
    """
    rows = []
    for i in range(N_PERFORMANCE):
        effort = rng.random()                      # hidden factor
        noise = rng.normal(0, 6)                   # random noise

        attendance = float(np.clip(40 + effort * 55 + noise * 0.8, 0, 100))
        assign_marks = float(np.clip(35 + effort * 60 + noise, 0, 100))
        internal = float(np.clip(38 + effort * 55 + noise, 0, 100))
        prev_sem = float(np.clip(35 + effort * 60 + noise, 0, 100))
        study_hours = float(np.clip(0.5 + effort * 7 + rng.normal(0, 0.8),
                                    0, 12))
        completed = int(np.clip(round(4 + effort * 26 + rng.normal(0, 3)),
                                0, 30))
        participation = float(np.clip(1 + effort * 8.5 + rng.normal(0, 0.9),
                                      0, 10))

        # ---- label rule (weighted score -> Good / Average / Needs) ----
        score = (0.22 * attendance
                 + 0.18 * assign_marks
                 + 0.18 * internal
                 + 0.17 * prev_sem
                 + 0.10 * (study_hours / 12 * 100)
                 + 0.075 * (completed / 30 * 100)
                 + 0.075 * (participation / 10 * 100))

        if score >= 78:
            label = "Good"
        elif score >= 62:
            label = "Average"
        else:
            label = "Needs Improvement"

        rows.append([attendance, assign_marks, internal, prev_sem,
                     round(study_hours, 1), completed,
                     round(participation, 1), label])

    return pd.DataFrame(rows, columns=[
        "attendance_pct", "assignment_marks", "internal_marks",
        "prev_semester_marks", "study_hours", "assignments_completed",
        "participation_score", "performance_category"])


# ---------------------------------------------------------------
# 2. PLACEMENT DATASET
# ---------------------------------------------------------------
def generate_placement() -> pd.DataFrame:
    """
    'readiness' (0..1) drives skills; placement = 1 when readiness
    clears a threshold with some randomness (companies reject strong
    candidates sometimes, and weak ones get lucky occasionally).
    """
    rows = []
    for i in range(N_PLACEMENT):
        readiness = rng.random()

        cgpa = float(np.clip(4.5 + readiness * 5.4 + rng.normal(0, 0.5),
                             0, 10))
        attendance = float(np.clip(50 + readiness * 48 + rng.normal(0, 5),
                                   0, 100))
        technical = float(np.clip(25 + readiness * 70 + rng.normal(0, 7),
                                  0, 100))
        communication = float(np.clip(25 + readiness * 70 + rng.normal(0, 8),
                                      0, 100))
        projects = int(np.clip(round(readiness * 10 + rng.normal(0, 1.5)),
                               0, 15))
        intern_months = int(np.clip(round(readiness * 6 + rng.normal(0, 1)),
                                    0, 12))
        certs = int(np.clip(round(readiness * 5 + rng.normal(0, 1)), 0, 8))
        aptitude = float(np.clip(30 + readiness * 65 + rng.normal(0, 7),
                                 0, 100))

        # weighted readiness score with randomness
        p = (0.28 * (cgpa / 10)
             + 0.15 * (technical / 100)
             + 0.15 * (communication / 100)
             + 0.12 * (aptitude / 100)
             + 0.10 * min(projects / 8, 1)
             + 0.10 * min(intern_months / 6, 1)
             + 0.05 * min(certs / 4, 1)
             + 0.05 * (attendance / 100))
        placed = 1 if (p + rng.normal(0, 0.09)) > 0.52 else 0

        rows.append([round(cgpa, 2), round(attendance, 1), round(technical, 1),
                     round(communication, 1), projects, intern_months,
                     certs, round(aptitude, 1), placed])

    return pd.DataFrame(rows, columns=[
        "cgpa", "attendance", "technical_score", "communication_score",
        "projects_completed", "internship_months", "certifications",
        "aptitude_score", "placed"])


def add_missing_values(df: pd.DataFrame, fraction: float = 0.02) -> None:
    """Sprinkle a few NaNs so students can demonstrate data cleaning."""
    n = max(1, int(len(df) * fraction))
    for col in rng.choice(df.columns[:-1], size=3, replace=False):
        idx = rng.choice(df.index, size=n, replace=False)
        df.loc[idx, col] = np.nan


if __name__ == "__main__":
    perf = generate_performance()
    add_missing_values(perf)
    perf.to_csv(os.path.join(DATASET_DIR, "performance_dataset.csv"),
                index=False)
    print(f"performance_dataset.csv  -> {len(perf)} rows, "
          f"classes: {perf['performance_category'].value_counts().to_dict()}")

    place = generate_placement()
    add_missing_values(place)
    place.to_csv(os.path.join(DATASET_DIR, "placement_dataset.csv"),
                 index=False)
    print(f"placement_dataset.csv    -> {len(place)} rows, "
          f"placed: {int(place['placed'].sum())} / not placed: "
          f"{int((place['placed'] == 0).sum())}")
