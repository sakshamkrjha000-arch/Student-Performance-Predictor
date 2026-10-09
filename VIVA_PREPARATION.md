# Viva Preparation Guide
## AI-Based Student Performance & Placement Prediction System

---

## PART 1 — BEGINNER-FRIENDLY PROJECT EXPLANATION

**In one line:** Students enter their marks and skills on a website, and
machine-learning models estimate their performance level and placement
chances. Everything is saved in a MySQL database, and admins see
analytics charts.

**Flow of the project:**
1. User opens the site → Flask serves HTML pages (Jinja2 templates).
2. User fills a form → browser sends a POST request to a Flask route.
3. Flask validates the input, prepares the numbers, and calls the
   saved Scikit-learn model (`.pkl` loaded once with Joblib).
4. Model returns a label + probability → Flask saves a row in MySQL
   and renders the result page.
5. Admin pages read tables, aggregate numbers with SQL, and draw
   charts with Matplotlib into `static/images/`.

### What is Flask?
A **micro web-framework** written in Python. It maps URLs to Python
functions called **routes** (`@app.route('/login')`), renders HTML
using **Jinja2** templates, and manages **sessions** so users stay
logged in. "Micro" means it doesn't force a database or form library
on you.

### How do HTML forms talk to Python?
`<form method="POST" action="/performance">` sends the field values to
the `/performance` URL. Flask receives them as
`request.form.get('attendance_pct')`. Jinja then renders the reply:
`{{ label }}` in a template gets replaced by the Python variable
passed to `render_template()`.

### What is MySQL?
A **relational database**: data lives in **tables** (rows/columns),
tables link to each other with **foreign keys**, and you talk to it
with **SQL** (`SELECT/INSERT/UPDATE/DELETE`). We use it because marks
and predictions must survive server restarts and be queryable
("show all students whose attendance < 75").

### What is Pandas?
A Python library for **tabular data**. We read CSVs with
`pd.read_csv()`, inspect with `df.head()`, `df.isnull().sum()`,
`df.value_counts()`, clean with `drop_duplicates()`, and select
columns with `df[columns]`.

### What is Scikit-learn?
The standard Python **machine-learning library**: models
(LogisticRegression, DecisionTree…), tools (train_test_split,
StandardScaler), and metrics (accuracy_score, confusion_matrix).

### How the model is trained vs used
- **Training** (offline, `ml/train_*.py`): dataset → clean → split →
  `model.fit(X_train, y_train)` → evaluate → `joblib.dump(model)`.
- **Prediction** (online, `app.py`): load `.pkl` → build a 2-D array
  of the form values in the same column order → `predict()`.

---

## PART 2 — ML ALGORITHM EXPLANATIONS

**Logistic Regression** — despite the name it is a *classifier*. It
computes a weighted sum of the features and squashes it through the
**sigmoid** function to get a probability. The decision boundary is a
straight line (or plane). Very fast and interpretable — our best model
for both tasks.

**Decision Tree** — asks yes/no questions ("internal_marks > 62?")
and splits data into purer groups, like a flowchart. Gini/entropy
decide the best question at each step. Without `max_depth` it can
memorise (overfit) — we capped depth and leaf size.

**Random Forest** — trains many decision trees on random samples of
the data (bagging) and averages their votes. Reduces overfitting and
gives feature importances. More stable than one tree.

**K-Nearest Neighbours (KNN)** — no training at all: to classify, it
finds the *k* closest training points (Euclidean distance) and takes a
majority vote. Features must be **scaled** first (StandardScaler)
otherwise big-range features dominate the distance.

**Why scale for LR and KNN but not trees?** Scaling changes distances
and gradient descent speed — crucial for KNN/LR. Trees only compare
"greater than", so scaling is irrelevant to them.

**train_test_split** — keeps a test set the model never saw, for an
honest score. We used 80/20 with `stratify=y` so class proportions
match in both sets.

**Metrics:**
- *Accuracy* — % of correct predictions (misleading on imbalanced data).
- *Precision* — of everything predicted positive, how much really was.
- *Recall* — of everything really positive, how much we caught.
- *F1* — harmonic mean of precision and recall; we use **macro-F1**
  for the 3-class task so each class counts equally.
- *Confusion matrix* — a grid of actual vs predicted counts; shows
  *which* classes get confused.
- *ROC-AUC* (placement only) — how well the model separates the two
  classes at all thresholds; 1.0 is perfect, 0.5 is random guessing.

---

## PART 3 — DATABASE TABLES

| Table | Purpose | Key columns |
|---|---|---|
| users | student logins | user_id PK, email UNIQUE, password_hash |
| admins | admin logins | admin_id PK, username UNIQUE |
| students | academic profile | student_id PK, user_id FK→users, roll_number UNIQUE, CHECK constraints |
| performance_records | input history | perf_id PK, student_id FK→students |
| placement_records | input history | place_id PK, student_id FK→students |
| predictions | result log | prediction_id PK, student_id FK, ENUM type, inputs_json |

**Why hash passwords?** Storing plain text means anyone with DB access
knows everyone's password. A hash (scrypt/PBKDF2 via Werkzeug) is a
one-way fingerprint; login re-hashes the typed password and compares.

**Parameterised queries** (`WHERE email = %s` with a params tuple)
make SQL injection impossible because user input is never glued into
the SQL string.

---

## PART 4 — FLASK ROUTES

| Route | Methods | Auth | Does |
|---|---|---|---|
| `/` | GET | — | landing page |
| `/register` | GET/POST | — | create users+students rows |
| `/login` | GET/POST | — | student session |
| `/logout` | GET | any | clear session |
| `/dashboard` | GET | student | stats + history |
| `/profile` | GET/POST | student | edit course/sem/CGPA |
| `/performance` | GET/POST | student | form → ML → save |
| `/placement` | GET/POST | student | form → ML → save |
| `/history` | GET | student | all own predictions |
| `/admin/login` | GET/POST | — | admin session |
| `/admin` | GET | admin | stats + recent |
| `/admin/students` | GET | admin | list + search |
| `/admin/students/<id>` | GET | admin | detail |
| `/admin/students/<id>/delete` | POST | admin | delete user (cascades) |
| `/admin/analytics` | GET | admin | 5 charts + metrics tables |

`@login_required` / `@admin_required` are **decorators** that check
the session before the view runs.

---

## PART 5 — 30 VIVA QUESTIONS & ANSWERS

1. **What does this project do?** Predicts a student's performance
   category and placement likelihood using ML models served by Flask,
   storing everything in MySQL.

2. **Why two models instead of one?** Different inputs and different
   outputs: performance is 3-class academic behaviour; placement is a
   binary skill-based outcome.

3. **Which algorithms did you compare?** Logistic Regression, Decision
   Tree, Random Forest, KNN.

4. **Which won and why?** Logistic Regression for both (highest F1) —
   the synthetic data is largely linearly separable, and LR generalises
   better than deep trees on small data.

5. **Why use F1 rather than accuracy to pick the best?** The classes
   are somewhat imbalanced; F1 balances precision and recall and macro
   averaging treats every class equally.

6. **What is overfitting and how did you reduce it?** Memorising the
   training set; reduced with max_depth/min_samples_leaf on trees,
   regularised LR, and by evaluating on unseen test data + 5-fold CV.

7. **What is a confusion matrix?** A table of actual vs predicted
   classes; the diagonal is correct, off-diagonal shows which classes
   get mixed up.

8. **Why stratified splitting?** Keeps the Good/Average/Needs ratio
   the same in train and test, so metrics aren't skewed.

9. **How are missing values handled?** Median imputation with
   SimpleImputer after dropping duplicates and impossible ranges.

10. **What encoding did you need?** Labels mapped to integers
    (Needs=0, Average=1, Good=2); features are already numeric, so no
    one-hot encoding was required.

11. **Why save the model with Joblib?** Serialises fitted sklearn
    objects (including pipelines/scalers) to `.pkl` so Flask can load
    the exact trained model without retraining.

12. **What does predict_proba give?** The probability of each class;
    the highest decides the label, and that value is shown as
    "confidence".

13. **How is the model connected to Flask?** `joblib.load()` once at
    first request; every prediction builds a 2-D feature array in the
    same column order as training.

14. **How do you prevent SQL injection?** Parameterised queries
    (`%s` placeholders) everywhere — input never becomes part of the
    SQL text.

15. **How are passwords stored?** Hashed with Werkzeug
    (`generate_password_hash`, scrypt by default); login uses
    `check_password_hash`.

16. **How does a session work?** Flask signs a session cookie with
    SECRET_KEY; `session['user_id']` survives across requests until
    logout. Views check it via decorators.

17. **Student vs admin auth?** Separate tables and separate session
    variables; `admin_required` rejects anything without
    `role == 'admin'`.

18. **How does HTML talk to Python?** Forms POST fields to routes;
    Flask reads `request.form`; Jinja2 templates render responses
    with `{{ variables }}` and `{% for %}` loops.

19. **Where are the charts and who makes them?** Matplotlib on the
    server saves PNGs into `static/images/`; HTML just shows them with
    `<img>` — zero JavaScript.

20. **Why is the model saved instead of training on each request?**
    Training takes seconds and would repeat per request; loading a
    pickle is instant.

21. **What happens if the model file is missing?** `get_model()`
    returns None and the user sees "ML model not found. Run:
    python ml/train_performance.py".

22. **Explain your validation.** Every numeric field is converted and
    range-checked (marks 0–100, CGPA 0–10, semester 1–8, etc.);
    failures re-render the form with a friendly flash message. HTML
    min/max also helps but server-side checks are the real gate.

23. **What is a foreign key here?** E.g. predictions.student_id
    references students.student_id — you cannot store a prediction
    for a non-existent student.

24. **What does ON DELETE CASCADE do?** Deleting a user removes their
    student row, records and predictions automatically — no orphans.

25. **Why ENUM for prediction_type?** Restricts the column to
    'performance' or 'placement', preventing typo values.

26. **Difference between users and admins tables?** Separate roles
    with separate login routes; simpler and safer than one shared
    table for this scope.

27. **How would you improve the model with real data?** Collect actual
    college records, retrain periodically, monitor drift, try
    gradient boosting, and calibrate probabilities.

28. **What are the system's limitations?** Synthetic training data,
    self-reported inputs, no retraining UI, estimates not guarantees.

29. **How did you handle errors?** try/except around DB and ML calls,
    custom 404/403/500 HTML pages, flash messages for user mistakes.

30. **If accuracy dropped in production, what would you check?** Data
    drift, new class distribution, feature bugs, retrain with recent
    data, and re-validate with cross-validation.

---

## Quick demo script for viva
1. `python ml/train_performance.py` → show console metrics.
2. Start `python app.py`, register a student, predict performance.
3. Show `SELECT * FROM predictions` in MySQL.
4. Admin login → analytics charts → search a student.
