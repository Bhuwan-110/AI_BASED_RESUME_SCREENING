"""
GURUKUL AI Resume-Job Relevance Machine Learning Module
======================================================
Academic Project Implementation:
Supervised Machine Learning Relevance Classifier using scikit-learn Pipeline
(TF-IDF Vectorizer + Logistic Regression) with held-out test evaluation,
leakage prevention, and baseline comparison against Cosine Similarity.

ACADEMIC DEFENSE & ARCHITECTURAL FOUNDATION:
--------------------------------------------
1. Supervised Learning Paradigm:
   - Unlike purely heuristic or unsupervised cosine similarity, this module learns
     discriminative token weights from ground-truth labelled resume-job pairs.
   - Problem Formulation: Binary classification:
     y in {0, 1}, where 1 = Relevant Match, 0 = Non-Relevant Match.

2. Feature Engineering & Modeling Pipeline:
   - Preprocessing: Standard lowercasing, punctuation normalization, and whitespace cleanup.
   - Pair Representation: Concatenation of Job Context (duties, required skills) and CV text.
   - Vectorization: TF-IDF Vectorizer (n-gram range (1, 2), English stop-words filtering,
     sublinear TF scaling).
   - Estimator: Logistic Regression with L2 regularization and balanced class weighting.
   - Encapsulation: scikit-learn Pipeline guarantees vectorizer and estimator are fit together,
     preventing vocabulary leakage between train and test splits.

3. Evaluation & Rigorous Baseline Comparison:
   - Evaluated on held-out test data using: Precision, Recall, F1-Score, ROC-AUC, and Confusion Matrix.
   - Baseline Comparison: Evaluates the existing TF-IDF Cosine Similarity approach on the identical
     held-out test split. The baseline decision threshold is tuned exclusively on training data
     to prevent evaluation data leakage.

4. Ethical AI & Decision Support Guarantee:
   - The ML model outputs an estimated relevance classification and calibrated probability score.
   - Output is strictly decision support for human recruiters and NEVER automates hiring or rejection.
"""

import os
import json
import logging
from typing import Dict, Any, Tuple, Optional, Union
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import joblib
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    accuracy_score,
    roc_auc_score,
    confusion_matrix,
    classification_report
)

from resume_ai.service import clean_text

logger = logging.getLogger(__name__)

# Default file paths
DEFAULT_MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ml_assets')
DEFAULT_MODEL_PATH = os.path.join(DEFAULT_MODEL_DIR, 'resume_classifier.joblib')
DEFAULT_METADATA_PATH = os.path.join(DEFAULT_MODEL_DIR, 'model_metadata.json')

# Global in-memory cache for the loaded pipeline and its metadata
_CACHED_PIPELINE: Optional[Pipeline] = None
_CACHED_METADATA: Optional[Dict[str, Any]] = None
_CACHED_MODEL_MTIME: Optional[float] = None


class DatasetValidationError(ValueError):
    """Raised when training dataset does not conform to required schema or quality standards."""
    pass


def construct_pair_text(resume_text: str, job_description: str) -> str:
    """
    Constructs an information-rich text representation of a (Resume, Job Description) pair.

    Architecture:
    1. Origin Prefixing: Tokens from the vacancy are prefixed with 'job_' and tokens from
       the candidate CV are prefixed with 'res_'. This prevents conflation of vacancy requirements
       with candidate credentials in linear models.
    2. Cross-Document Intersection: Tokens appearing in BOTH vacancy and resume are extracted
       as 'match_<token>' features. This allows the TF-IDF vectorizer and Logistic Regression
       classifier to learn strong discriminative weights for true qualifications and skills.
    3. Global Alignment Signals: Overlap density tokens ('density_high_match', 'density_moderate_match',
       'density_zero_match') reflect the overall keyword convergence.
    """
    c_job = clean_text(job_description or "").split()
    c_res = clean_text(resume_text or "").split()

    stops = {
        'and', 'the', 'in', 'of', 'to', 'with', 'for', 'a', 'an', 'is', 'on', 'at',
        'by', 'this', 'that', 'from', 'as', 'are', 'or', 'we', 'our', 'be', 'must',
        'have', 'has', 'will', 'you', 'your', 'candidate', 'should', 'experience'
    }

    job_words = [w for w in c_job if w not in stops and len(w) > 2]
    res_words = [w for w in c_res if w not in stops and len(w) > 2]
    common = set(job_words) & set(res_words)

    parts = []
    # Origin-tagged unigrams
    parts.extend([f"job_{w}" for w in job_words])
    parts.extend([f"res_{w}" for w in res_words])

    # Intersecting match features (weighted by repetition)
    parts.extend([f"match_{w}" for w in common] * 4)

    # Global density indicator
    if len(common) >= 3:
        parts.extend(['density_high_match'] * 5)
    elif len(common) >= 1:
        parts.extend(['density_moderate_match'] * 3)
    else:
        parts.extend(['density_zero_match'] * 5)

    return " ".join(parts).strip()


def validate_dataset(data: Union[str, pd.DataFrame]) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Loads and rigorously validates a candidate-job relevance dataset.

    Required CSV Schema:
    - 'resume_text': Extracted CV plain text.
    - 'job_description': Vacancy requirements, description, or skills.
    - 'relevant': Binary integer label (1 for relevant, 0 for non-relevant).

    Validation Rules:
    1. Dataset must not be empty.
    2. Required columns must be present.
    3. Missing/null values in required columns are identified and removed.
    4. Labels must contain only binary values (0 and 1).
    5. Both classes (0 and 1) must be represented.
    6. Minimum sample threshold (at least 10 valid samples, with at least 3 per class).

    Returns:
    (cleaned_df, stats_dict)
    """
    if isinstance(data, (str, os.PathLike)):
        if not os.path.exists(data):
            raise DatasetValidationError(f"Dataset file not found at: {data}")
        try:
            df = pd.read_csv(data)
        except Exception as e:
            raise DatasetValidationError(f"Failed to read CSV dataset: {str(e)}")
    elif isinstance(data, pd.DataFrame):
        df = data.copy()
    else:
        raise DatasetValidationError("Dataset must be a file path string or a pandas DataFrame.")

    if df.empty:
        raise DatasetValidationError("Dataset is empty. At least 10 labelled examples are required.")

    # 1. Check required columns
    required_cols = {'resume_text', 'job_description', 'relevant'}
    missing_cols = required_cols - set(df.columns)
    if missing_cols:
        raise DatasetValidationError(
            f"Dataset is missing required columns: {sorted(list(missing_cols))}. "
            f"Expected schema: 'resume_text', 'job_description', 'relevant'."
        )

    initial_count = len(df)

    # 2. Check for missing values
    df_clean = df.dropna(subset=['resume_text', 'job_description', 'relevant']).copy()
    df_clean['resume_text'] = df_clean['resume_text'].astype(str).str.strip()
    df_clean['job_description'] = df_clean['job_description'].astype(str).str.strip()

    # Filter out empty text rows
    df_clean = df_clean[
        (df_clean['resume_text'].str.len() > 10) &
        (df_clean['job_description'].str.len() > 10)
    ].copy()

    if df_clean.empty:
        raise DatasetValidationError("All records contain empty or near-empty text.")

    # 3. Validate binary labels
    try:
        df_clean['relevant'] = df_clean['relevant'].astype(int)
    except Exception:
        raise DatasetValidationError("Target column 'relevant' must contain numeric binary values (0 or 1).")

    unique_labels = set(df_clean['relevant'].unique())
    invalid_labels = unique_labels - {0, 1}
    if invalid_labels:
        raise DatasetValidationError(
            f"Target column 'relevant' contains invalid labels: {invalid_labels}. Only 0 and 1 are permitted."
        )

    if len(unique_labels) < 2:
        raise DatasetValidationError(
            f"Dataset must contain both positive (1) and negative (0) classes. "
            f"Currently only contains class: {list(unique_labels)}."
        )

    class_counts = df_clean['relevant'].value_counts().to_dict()
    min_class_count = min(class_counts.values())

    if len(df_clean) < 10:
        raise DatasetValidationError(
            f"Dataset has only {len(df_clean)} valid samples. Minimum required is 10 for training."
        )

    if min_class_count < 3:
        raise DatasetValidationError(
            f"Each class must have at least 3 samples for stratified splitting. "
            f"Current distribution: {class_counts}."
        )

    # Check for duplicate pairs
    duplicate_count = int(df_clean.duplicated(subset=['resume_text', 'job_description']).sum())

    stats = {
        'initial_rows': initial_count,
        'valid_rows': len(df_clean),
        'dropped_rows': initial_count - len(df_clean),
        'duplicate_pairs': duplicate_count,
        'class_distribution': {
            'relevant_1': int(class_counts.get(1, 0)),
            'non_relevant_0': int(class_counts.get(0, 0)),
        },
        'relevant_ratio': round(float(class_counts.get(1, 0)) / len(df_clean), 4),
    }

    return df_clean, stats


def build_pipeline(
    max_features: int = 5000,
    ngram_range: Tuple[int, int] = (1, 2),
    C: float = 1.0,
    random_state: int = 42
) -> Pipeline:
    """
    Constructs an end-to-end scikit-learn Pipeline.

    Components:
    1. TfidfVectorizer: Converts raw text pairs into TF-IDF feature vectors.
       - ngram_range: unigrams and bigrams capture domain collocations (e.g., 'machine learning', 'public administration').
       - sublinear_tf: applies sublinear scaling (1 + log(tf)) to prevent high frequency word dominance.
       - stop_words: filtered using standard English stop-words list.
    2. LogisticRegression: Probabilistic linear classifier.
       - class_weight='balanced': compensates for class imbalance.
       - C=1.0: L2 regularization to prevent overfitting on smaller corpora.
    """
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(
            ngram_range=ngram_range,
            max_features=max_features,
            stop_words='english',
            sublinear_tf=True,
            lowercase=True
        )),
        ('clf', LogisticRegression(
            C=C,
            max_iter=1000,
            class_weight='balanced',
            random_state=random_state,
            solver='lbfgs'
        ))
    ])
    return pipeline


def evaluate_cosine_baseline(
    test_df: pd.DataFrame,
    threshold: float = 0.30
) -> Dict[str, Any]:
    """
    Evaluates the existing TF-IDF Cosine Similarity system on a test dataset.

    For each (resume_text, job_description) pair:
    1. Extracts TF-IDF vectors using standard TfidfVectorizer.
    2. Computes cosine similarity in range [0.0, 1.0].
    3. Predicts 1 if similarity >= threshold, else 0.
    4. Computes precision, recall, f1, and accuracy against ground-truth labels.
    """
    from sklearn.metrics.pairwise import cosine_similarity as sk_cosine_similarity

    y_true = test_df['relevant'].to_numpy()
    similarities = []

    vectorizer = TfidfVectorizer(stop_words='english', lowercase=True)

    for _, row in test_df.iterrows():
        job_clean = clean_text(row['job_description'])
        resume_clean = clean_text(row['resume_text'])
        if not job_clean or not resume_clean:
            similarities.append(0.0)
            continue
        try:
            tfidf_mat = vectorizer.fit_transform([job_clean, resume_clean])
            sim = float(sk_cosine_similarity(tfidf_mat[0:1], tfidf_mat[1:2])[0][0])
            similarities.append(max(0.0, min(1.0, sim)))
        except Exception:
            similarities.append(0.0)

    sim_array = np.array(similarities)
    y_pred = (sim_array >= threshold).astype(int)

    acc = float(accuracy_score(y_true, y_pred))
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    rec = float(recall_score(y_true, y_pred, zero_division=0))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    cm = confusion_matrix(y_true, y_pred).tolist()

    try:
        auc = float(roc_auc_score(y_true, sim_array)) if len(np.unique(y_true)) > 1 else None
    except Exception:
        auc = None

    return {
        'method': 'TF-IDF Cosine Similarity (Baseline)',
        'threshold': threshold,
        'accuracy': round(acc, 4),
        'precision': round(prec, 4),
        'recall': round(rec, 4),
        'f1_score': round(f1, 4),
        'roc_auc': round(auc, 4) if auc is not None else None,
        'confusion_matrix': cm,
        'sample_size': len(test_df),
    }


def find_optimal_baseline_threshold(train_df: pd.DataFrame) -> float:
    """
    Finds the optimal cosine similarity decision threshold on TRAINING data ONLY.
    Optimizes F1-score over candidate thresholds [0.10, 0.15, ..., 0.50].
    Prevents test set leakage.
    """
    from sklearn.metrics.pairwise import cosine_similarity as sk_cosine_similarity

    vectorizer = TfidfVectorizer(stop_words='english', lowercase=True)
    similarities = []

    for _, row in train_df.iterrows():
        job_clean = clean_text(row['job_description'])
        resume_clean = clean_text(row['resume_text'])
        if not job_clean or not resume_clean:
            similarities.append(0.0)
            continue
        try:
            tfidf_mat = vectorizer.fit_transform([job_clean, resume_clean])
            sim = float(sk_cosine_similarity(tfidf_mat[0:1], tfidf_mat[1:2])[0][0])
            similarities.append(max(0.0, min(1.0, sim)))
        except Exception:
            similarities.append(0.0)

    sim_array = np.array(similarities)
    y_train = train_df['relevant'].to_numpy()

    best_thresh = 0.30
    best_f1 = -1.0

    for thresh in np.arange(0.10, 0.60, 0.05):
        y_pred = (sim_array >= thresh).astype(int)
        score = f1_score(y_train, y_pred, zero_division=0)
        if score > best_f1:
            best_f1 = score
            best_thresh = float(thresh)

    return round(best_thresh, 2)


def train_resume_model(
    dataset_path_or_df: Union[str, pd.DataFrame],
    test_size: float = 0.2,
    random_state: int = 42,
    save_model: bool = True,
    model_path: str = DEFAULT_MODEL_PATH,
    metadata_path: str = DEFAULT_METADATA_PATH,
    max_features: int = 5000,
    C: float = 1.0,
) -> Dict[str, Any]:
    """
    Full training and evaluation pipeline:
    1. Validates dataset schema, types, and class balance.
    2. Builds paired text representations: construct_pair_text(resume, job).
    3. Performs stratified train/test split to prevent leakage.
    4. Fits scikit-learn Pipeline (TF-IDF + LogisticRegression) on training split.
    5. Tunes baseline threshold on training split.
    6. Evaluates both ML model and Baseline on held-out test split.
    7. Computes Precision, Recall, F1, Accuracy, Confusion Matrix, and ROC-AUC.
    8. Serializes model artifact (.joblib) and metadata (.json) safely.
    9. Returns complete academic evaluation report.
    """
    # 1. Validation
    df, stats = validate_dataset(dataset_path_or_df)

    # 2. Text pair construction
    df['pair_text'] = df.apply(
        lambda row: construct_pair_text(row['resume_text'], row['job_description']),
        axis=1
    )

    X = df['pair_text']
    y = df['relevant'].to_numpy()

    # 3. Stratified Train/Test split
    # For small datasets, ensure test set has at least 1 sample per class
    min_class_count = min(stats['class_distribution'].values())
    if min_class_count < 2:
        stratify_labels = None
    else:
        stratify_labels = y

    X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
        X, y, df.index,
        test_size=test_size,
        random_state=random_state,
        stratify=stratify_labels
    )

    train_df = df.loc[idx_train].copy()
    test_df = df.loc[idx_test].copy()

    # 4. Fit scikit-learn Pipeline on train split only
    pipeline = build_pipeline(
        max_features=max_features,
        ngram_range=(1, 2),
        C=C,
        random_state=random_state
    )
    pipeline.fit(X_train, y_train)

    # 5. Evaluate ML model on held-out test data
    y_test_pred = pipeline.predict(X_test)
    y_test_proba = pipeline.predict_proba(X_test)[:, 1]

    ml_acc = float(accuracy_score(y_test, y_test_pred))
    ml_prec = float(precision_score(y_test, y_test_pred, zero_division=0))
    ml_rec = float(recall_score(y_test, y_test_pred, zero_division=0))
    ml_f1 = float(f1_score(y_test, y_test_pred, zero_division=0))
    ml_cm = confusion_matrix(y_test, y_test_pred).tolist()

    try:
        ml_auc = float(roc_auc_score(y_test, y_test_proba)) if len(np.unique(y_test)) > 1 else None
    except Exception:
        ml_auc = None

    # 6. Evaluate Baseline on the same test split
    optimal_thresh = find_optimal_baseline_threshold(train_df)
    baseline_metrics = evaluate_cosine_baseline(test_df, threshold=optimal_thresh)

    # 7. Model vocabulary size
    tfidf_step = pipeline.named_steps['tfidf']
    vocab_size = len(tfidf_step.vocabulary_)

    # 8. Compile metadata report
    report = {
        'model_name': 'GURUKUL-CV Resume Relevance Classifier',
        'model_type': 'Pipeline(TfidfVectorizer + LogisticRegression)',
        'version': '1.0.0',
        'trained_at': datetime.now(timezone.utc).isoformat(),
        'dataset_statistics': stats,
        'training_config': {
            'test_size': test_size,
            'random_state': random_state,
            'train_samples': len(X_train),
            'test_samples': len(X_test),
            'max_features': max_features,
            'ngram_range': [1, 2],
            'regularization_C': C,
            'vocabulary_size': vocab_size,
        },
        'test_class_distribution': {
            'relevant_1': int((y_test == 1).sum()),
            'non_relevant_0': int((y_test == 0).sum()),
        },
        'ml_model_evaluation': {
            'accuracy': round(ml_acc, 4),
            'precision': round(ml_prec, 4),
            'recall': round(ml_rec, 4),
            'f1_score': round(ml_f1, 4),
            'roc_auc': round(ml_auc, 4) if ml_auc is not None else None,
            'confusion_matrix': ml_cm,
            'confusion_matrix_labels': ['True Negative', 'False Positive', 'False Negative', 'True Positive'],
        },
        'baseline_comparison': baseline_metrics,
        'performance_delta': {
            'f1_improvement': round(ml_f1 - baseline_metrics['f1_score'], 4),
            'precision_improvement': round(ml_prec - baseline_metrics['precision'], 4),
            'recall_improvement': round(ml_rec - baseline_metrics['recall'], 4),
            'accuracy_improvement': round(ml_acc - baseline_metrics['accuracy'], 4),
        },
        'ethical_notice': (
            "This model provides quantitative decision-support indicators. "
            "It does NOT automate recruitment or rejection decisions. Final hiring decisions "
            "remain strictly with human administrators."
        )
    }

    # 9. Serialization
    if save_model:
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        joblib.dump(pipeline, model_path)
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)

        # Invalidate in-memory cache
        global _CACHED_PIPELINE, _CACHED_METADATA, _CACHED_MODEL_MTIME
        _CACHED_PIPELINE = pipeline
        _CACHED_METADATA = report
        try:
            _CACHED_MODEL_MTIME = os.path.getmtime(model_path)
        except OSError:
            _CACHED_MODEL_MTIME = None

    return report


def load_model(
    model_path: str = DEFAULT_MODEL_PATH,
    metadata_path: str = DEFAULT_METADATA_PATH,
    force_reload: bool = False
) -> Tuple[Optional[Pipeline], Optional[Dict[str, Any]]]:
    """
    Safely loads the trained scikit-learn Pipeline and its metadata.

    Security & Safety Rules:
    - Verifies file existence before loading.
    - Validates that loaded object has .predict() and .predict_proba() methods.
    - Uses in-memory caching to avoid disk read overhead on repeated calls.
    - Returns (None, None) gracefully if model is not yet trained.
    """
    global _CACHED_PIPELINE, _CACHED_METADATA, _CACHED_MODEL_MTIME

    if not os.path.exists(model_path):
        return None, None

    try:
        current_mtime = os.path.getmtime(model_path)
    except OSError:
        current_mtime = 0.0

    if not force_reload and _CACHED_PIPELINE is not None and _CACHED_MODEL_MTIME == current_mtime:
        return _CACHED_PIPELINE, _CACHED_METADATA

    try:
        pipeline = joblib.load(model_path)
        if not hasattr(pipeline, 'predict') or not hasattr(pipeline, 'predict_proba'):
            logger.warning("Loaded artifact does not implement scikit-learn predict interface.")
            return None, None

        metadata = None
        if os.path.exists(metadata_path):
            with open(metadata_path, 'r', encoding='utf-8') as f:
                metadata = json.load(f)

        _CACHED_PIPELINE = pipeline
        _CACHED_METADATA = metadata
        _CACHED_MODEL_MTIME = current_mtime
        return _CACHED_PIPELINE, _CACHED_METADATA

    except Exception as e:
        logger.error(f"Failed to load ML model artifact from {model_path}: {e}")
        return None, None


def predict_relevance(
    resume_text: Optional[str],
    job_description: Optional[str],
    model_path: str = DEFAULT_MODEL_PATH,
    metadata_path: str = DEFAULT_METADATA_PATH,
) -> Dict[str, Any]:
    """
    Inference service function:
    Receives resume text and job description, executes preprocessing,
    and queries the trained ML pipeline.

    Returns:
    {
      'is_available': bool,
      'status': 'SUCCESS' | 'NO_MODEL' | 'INSUFFICIENT_TEXT' | 'ERROR',
      'predicted_class': 'Relevant' | 'Not Relevant' | 'Unavailable',
      'label': 1 | 0 | None,
      'relevance_probability': float (0.0 - 1.0) | None,
      'relevance_percentage': float (0.0 - 100.0) | None,
      'confidence_tier': 'High' | 'Moderate' | 'Low' | 'Unavailable',
      'model_version': str,
      'message': str,
      'is_decision_support_only': True
    }
    """
    if not resume_text or not resume_text.strip():
        return {
            'is_available': False,
            'status': 'INSUFFICIENT_TEXT',
            'predicted_class': 'Unavailable',
            'label': None,
            'relevance_probability': None,
            'relevance_percentage': None,
            'confidence_tier': 'Unavailable',
            'model_version': '',
            'message': 'Resume text is missing or unreadable.',
            'is_decision_support_only': True
        }

    if not job_description or not job_description.strip():
        return {
            'is_available': False,
            'status': 'INSUFFICIENT_TEXT',
            'predicted_class': 'Unavailable',
            'label': None,
            'relevance_probability': None,
            'relevance_percentage': None,
            'confidence_tier': 'Unavailable',
            'model_version': '',
            'message': 'Job description is missing.',
            'is_decision_support_only': True
        }

    pipeline, metadata = load_model(model_path=model_path, metadata_path=metadata_path)

    if pipeline is None:
        return {
            'is_available': False,
            'status': 'NO_MODEL',
            'predicted_class': 'Unavailable',
            'label': None,
            'relevance_probability': None,
            'relevance_percentage': None,
            'confidence_tier': 'Unavailable',
            'model_version': '',
            'message': 'No trained ML model found. Run python manage.py train_resume_model to train.',
            'is_decision_support_only': True
        }

    try:
        pair_text = construct_pair_text(resume_text, job_description)
        prediction = int(pipeline.predict([pair_text])[0])
        probas = pipeline.predict_proba([pair_text])[0]
        # Probability of class 1 (Relevant)
        prob_relevant = float(probas[1]) if len(probas) > 1 else float(probas[0])
        pct_relevant = round(prob_relevant * 100.0, 2)

        if prob_relevant >= 0.70 or prob_relevant <= 0.30:
            confidence = 'High'
        elif prob_relevant >= 0.55 or prob_relevant <= 0.45:
            confidence = 'Moderate'
        else:
            confidence = 'Low'

        predicted_class_name = 'Relevant' if prediction == 1 else 'Not Relevant'
        model_version = metadata.get('version', '1.0.0') if metadata else '1.0.0'

        return {
            'is_available': True,
            'status': 'SUCCESS',
            'predicted_class': predicted_class_name,
            'label': prediction,
            'relevance_probability': round(prob_relevant, 4),
            'relevance_percentage': pct_relevant,
            'confidence_tier': confidence,
            'model_version': model_version,
            'message': f"ML Model classified candidate as '{predicted_class_name}' with {pct_relevant}% relevance probability.",
            'is_decision_support_only': True
        }

    except Exception as e:
        logger.error(f"Error during ML inference: {e}")
        return {
            'is_available': False,
            'status': 'ERROR',
            'predicted_class': 'Unavailable',
            'label': None,
            'relevance_probability': None,
            'relevance_percentage': None,
            'confidence_tier': 'Unavailable',
            'model_version': '',
            'message': f"Inference error: {str(e)}",
            'is_decision_support_only': True
        }
