# GURUKUL-CV: AI/ML-Powered Resume Screening Web Application

Welcome to **GURUKUL-CV**, a Django web application for academic recruitment, vacancy management, and AI-assisted resume screening.

This repository features both:
1. **Unsupervised Heuristic Screening**: TF-IDF Cosine Similarity, deterministic required skill matching (with word-boundary awareness), and conservative qualification/experience hierarchy checks.
2. **Supervised Machine Learning Relevance Classifier**: A scikit-learn Pipeline (`TfidfVectorizer` + regularized `LogisticRegression`) trained on labelled resume-job pairs, featuring origin-tagged feature encoding and cross-document intersection tokens.

> **Decision-Support Guarantee**: Both screening engines strictly provide quantitative guidance for human recruiters. The system **never** automates hiring or rejection decisions; final applicant lifecycle decisions remain exclusively with human administrators.

---

## Quick Start Guide (Windows PowerShell)

### 1. Prerequisites & Virtual Environment
Ensure Python 3.10+ (tested on Python 3.14 on Windows) is installed:
```powershell
python --version
```
*(Optional) If using a virtual environment:*
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Install Required Dependencies
Install the required packages pinned in `requirements.txt`:
```powershell
pip install -r requirements.txt
```

### 3. Database Migrations
Apply Django migrations to prepare the database schema:
```powershell
python manage.py migrate
```
*(All existing database records and uploaded CV files are fully preserved).*

### 4. Train the Machine Learning Model
Train the supervised relevance classifier on the bundled dataset (`resume_ai/data/resume_job_dataset.csv`):
```powershell
python manage.py train_resume_model
```
This command will:
- Validate the dataset schema and class balance.
- Perform a stratified train/test split.
- Train the scikit-learn Pipeline (`TfidfVectorizer` + `LogisticRegression`).
- Evaluate held-out test data (Precision, Recall, F1, Accuracy, Confusion Matrix, ROC-AUC).
- Tune the baseline threshold on the training split and report comparative metrics.
- Save the serialized model artifact to `resume_ai/ml_assets/resume_classifier.joblib`.
- Save full evaluation metrics to `resume_ai/ml_assets/model_metadata.json`.

### 5. Run the Automated Test Suite
Run the comprehensive test suite (74 tests across all apps):
```powershell
python manage.py test
```
To run tests specifically for the AI/ML module:
```powershell
python manage.py test resume_ai
```

### 6. Start the Django Development Server
Launch the local web server:
```powershell
python manage.py runserver
```
Access the application in your browser at:
`http://127.0.0.1:8000/`

---

## Machine Learning Pipeline Architecture

### Pipeline Components
```
Resume Text + Job Description
             │
             ▼
   [construct_pair_text]
   - Prefixing: 'job_<token>', 'res_<token>'
   - Intersection: 'match_<token>' (cross-document overlaps)
   - Density: 'density_high_match', 'density_zero_match'
             │
             ▼
    [scikit-learn Pipeline]
    ├─ TfidfVectorizer (unigrams & bigrams, sublinear TF)
    └─ LogisticRegression (balanced class weights, L2 regularization)
             │
             ▼
   [Inference Outputs]
   - Predicted Class: 'Relevant' (1) or 'Not Relevant' (0)
   - Relevance Probability: e.g., 62.65%
   - Confidence Tier: 'High', 'Moderate', 'Low'
```

### Measured Evaluation on Held-Out Test Data (N=13)
- **Accuracy**: 84.62%
- **Precision**: 83.33%
- **Recall**: 83.33%
- **F1-Score**: 83.33%
- **ROC-AUC**: 0.9762
- **Confusion Matrix**:
  - True Negative: 6 | False Positive: 1
  - False Negative: 1 | True Positive: 5

---

## Project Structure
```
GURUKUL-CV/
├── accounts/                  # User accounts, profiles, admin dashboard
├── applications/              # Job applications, PDF CV uploads
├── core/                      # Navigation, layouts, base templates
├── jobs/                      # Vacancy management, required skills, deadlines
├── resume_ai/                 # AI/ML screening engine
│   ├── data/                  # Labelled training datasets (CSV)
│   ├── ml_assets/             # Trained .joblib pipeline and metadata JSON
│   ├── management/commands/   # train_resume_model command
│   ├── extractor.py           # PDF text extraction (pypdf)
│   ├── service.py             # TF-IDF cosine similarity & skill checking
│   ├── ml_model.py            # Supervised Pipeline, validation & evaluation
│   ├── ml_service.py          # Decoupled Django service layer
│   ├── models.py              # ResumeExtraction, ResumeScreening, ResumeAnalysis
│   ├── views.py               # Admin analysis and diagnostics views
│   └── tests.py               # Unit & integration test suite
├── ACADEMIC_ML_REPORT.md      # Detailed Project-VI academic technical report
├── requirements.txt           # Project dependencies
├── manage.py                  # Django CLI
└── db.sqlite3                 # SQLite database
```

---

## Batch Resume Screening Feature

GURUKUL-CV includes **Batch Resume Screening** for evaluating all candidate applications for a specific vacancy with one click.

### Key Architectural Highlights:
1. **One-Click Batch Evaluation**:
   - `[ Analyze All CVs ]`: Screens all candidates against the selected vacancy.
   - `[ Analyze Pending ]`: Selectively screens unanalyzed or pending applications.
   - `[ Re-analyze All ]`: Re-evaluates all applicants with a confirmation dialog before overwriting.
2. **Single-Job Criteria Caching**:
   - The vacancy's job description, required skills, academic qualification, and experience are queried once and applied consistently to every applicant.
3. **Fault-Isolated Execution**:
   - Corrupted, password-protected, or unreadable PDFs are flagged as `Analysis Failed` (with explicit reasons: *No readable text*, *Invalid PDF*, etc.) without halting or crashing the batch pipeline.
4. **Real-Time Progress UI (Without Celery/Redis)**:
   - A sequential execution engine with live progress counter `Progress: X / Y (Z%)`, dynamic progress bar, and real-time processing ticker log.
5. **Ranked Candidate Table**:
   - Candidates ranked in descending order by AI match percentage by default.
   - Displays matched skills count and badges, missing skills count and badges, status, and direct links to view the full AI analysis or CV document.
6. **Multi-Candidate Manual Shortlisting**:
   - Checkboxes allow selecting multiple candidates for `[ Shortlist Selected ]`.
   - `[ Shortlist Top Candidates ]` allows specifying a match threshold (e.g., $\ge 80\%$) with a preview and confirmation before changing status.
   - Strictly decision support: the system never automatically shortlists or rejects candidates.

### Generating Sample Data for Testing:
Run the built-in management command to populate 5 sample candidates with varying skill matches and an empty CV for fault testing:
```powershell
python manage.py create_batch_sample_applicants
```

---

## Academic Documentation
For the complete Project-VI academic report containing theoretical formulations, baseline comparison methodology, algorithm pseudocode, and ethical considerations, refer to:
[ACADEMIC_ML_REPORT.md](ACADEMIC_ML_REPORT.md)

