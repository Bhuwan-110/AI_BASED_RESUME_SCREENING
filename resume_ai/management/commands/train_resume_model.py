"""
Django Management Command: train_resume_model
=============================================
Academic AI/ML Model Training Command for GURUKUL-CV.

Trains a scikit-learn Pipeline (TfidfVectorizer + LogisticRegression)
on a labelled resume-job dataset, validates data integrity, evaluates
performance on held-out test data, compares against the existing Cosine
Similarity baseline, and safely serializes the model artifact and metadata.

Usage:
    python manage.py train_resume_model
    python manage.py train_resume_model --dataset path/to/dataset.csv
    python manage.py train_resume_model --test-size 0.25 --random-state 42
"""

import os
import sys
from django.core.management.base import BaseCommand, CommandError
from resume_ai.ml_model import (
    train_resume_model,
    DatasetValidationError,
    DEFAULT_MODEL_PATH,
    DEFAULT_METADATA_PATH,
)


class Command(BaseCommand):
    help = "Train and evaluate the GURUKUL-CV Resume-Job Relevance Machine Learning Model."

    def add_arguments(self, parser):
        default_dataset = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'data',
            'resume_job_dataset.csv'
        )
        parser.add_argument(
            '--dataset',
            type=str,
            default=default_dataset,
            help=f"Path to the CSV dataset (default: {default_dataset})"
        )
        parser.add_argument(
            '--test-size',
            type=float,
            default=0.25,
            help="Fraction of dataset to reserve for held-out evaluation (default: 0.25)"
        )
        parser.add_argument(
            '--random-state',
            type=int,
            default=42,
            help="Random seed for deterministic train/test splitting (default: 42)"
        )
        parser.add_argument(
            '--model-path',
            type=str,
            default=DEFAULT_MODEL_PATH,
            help=f"Path to save serialized model (default: {DEFAULT_MODEL_PATH})"
        )
        parser.add_argument(
            '--metadata-path',
            type=str,
            default=DEFAULT_METADATA_PATH,
            help=f"Path to save evaluation metadata JSON (default: {DEFAULT_METADATA_PATH})"
        )

    def handle(self, *args, **options):
        dataset_path = options['dataset']
        test_size = options['test_size']
        random_state = options['random_state']
        model_path = options['model_path']
        metadata_path = options['metadata_path']

        self.stdout.write(self.style.MIGRATE_HEADING("\n" + "=" * 70))
        self.stdout.write(self.style.MIGRATE_HEADING("   GURUKUL-CV - AI/ML Resume-Job Relevance Classifier Training"))
        self.stdout.write(self.style.MIGRATE_HEADING("=" * 70))
        self.stdout.write(f"Target Dataset : {dataset_path}")
        self.stdout.write(f"Test Split Size: {test_size * 100:.1f}%")
        self.stdout.write(f"Random State   : {random_state}")
        self.stdout.write(f"Model Artifact : {model_path}\n")

        if not os.path.exists(dataset_path):
            raise CommandError(
                f"Dataset file does not exist: {dataset_path}\n"
                f"Please ensure a valid CSV file exists with columns: resume_text, job_description, relevant."
            )

        # Execute training pipeline
        try:
            report = train_resume_model(
                dataset_path_or_df=dataset_path,
                test_size=test_size,
                random_state=random_state,
                save_model=True,
                model_path=model_path,
                metadata_path=metadata_path
            )
        except DatasetValidationError as dve:
            raise CommandError(f"Dataset Validation Failed:\n  {str(dve)}")
        except Exception as ex:
            raise CommandError(f"Model training failed unexpectedly:\n  {str(ex)}")

        stats = report['dataset_statistics']
        config = report['training_config']
        ml_eval = report['ml_model_evaluation']
        baseline = report['baseline_comparison']
        delta = report['performance_delta']

        # 1. Dataset Information
        self.stdout.write(self.style.SUCCESS("[OK] Dataset Validated Successfully"))
        self.stdout.write(f"    * Total Initial Records: {stats['initial_rows']}")
        self.stdout.write(f"    * Valid Training Pairs : {stats['valid_rows']}")
        self.stdout.write(f"    * Class 1 (Relevant)   : {stats['class_distribution']['relevant_1']}")
        self.stdout.write(f"    * Class 0 (Non-Relevant): {stats['class_distribution']['non_relevant_0']}")
        self.stdout.write(f"    * Relevant Ratio       : {stats['relevant_ratio'] * 100:.1f}%\n")

        # 2. Pipeline Configuration
        self.stdout.write(self.style.SUCCESS("[OK] Pipeline Architecture Configured"))
        self.stdout.write(f"    * Model Type           : {report['model_type']}")
        self.stdout.write(f"    * Training Samples     : {config['train_samples']}")
        self.stdout.write(f"    * Held-out Test Samples: {config['test_samples']}")
        self.stdout.write(f"    * Vocabulary Size      : {config['vocabulary_size']} features\n")

        # 3. Model Evaluation Table
        self.stdout.write(self.style.MIGRATE_HEADING("-" * 70))
        self.stdout.write(self.style.MIGRATE_HEADING("   HELD-OUT TEST SET EVALUATION & BASELINE COMPARISON"))
        self.stdout.write(self.style.MIGRATE_HEADING("-" * 70))
        header = f"{'Metric':<20} | {'ML Model (Pipeline)':<22} | {'Cosine Baseline':<20} | {'Delta':<10}"
        self.stdout.write(header)
        self.stdout.write("-" * 80)

        metrics_display = [
            ("Accuracy", f"{ml_eval['accuracy']:.4f}", f"{baseline['accuracy']:.4f}", f"{delta['accuracy_improvement']:+.4f}"),
            ("Precision", f"{ml_eval['precision']:.4f}", f"{baseline['precision']:.4f}", f"{delta['precision_improvement']:+.4f}"),
            ("Recall", f"{ml_eval['recall']:.4f}", f"{baseline['recall']:.4f}", f"{delta['recall_improvement']:+.4f}"),
            ("F1-Score", f"{ml_eval['f1_score']:.4f}", f"{baseline['f1_score']:.4f}", f"{delta['f1_improvement']:+.4f}"),
        ]

        for name, ml_val, base_val, diff in metrics_display:
            self.stdout.write(f"{name:<20} | {ml_val:<22} | {base_val:<20} | {diff:<10}")

        if ml_eval['roc_auc'] is not None:
            base_auc_str = f"{baseline['roc_auc']:.4f}" if baseline['roc_auc'] is not None else "N/A"
            self.stdout.write(f"{'ROC-AUC':<20} | {ml_eval['roc_auc']:<22.4f} | {base_auc_str:<20} | {'--':<10}")

        self.stdout.write("-" * 80)
        self.stdout.write(f"\n[OK] Confusion Matrix (Test Split):")
        cm = ml_eval['confusion_matrix']
        self.stdout.write(f"    * True Negative : {cm[0][0]}   | False Positive: {cm[0][1]}")
        self.stdout.write(f"    * False Negative: {cm[1][0]}   | True Positive : {cm[1][1]}\n")

        # 4. Artifact & Integrity
        self.stdout.write(self.style.SUCCESS(f"[OK] Model artifact saved to: {model_path}"))
        self.stdout.write(self.style.SUCCESS(f"[OK] Metadata JSON saved to : {metadata_path}"))
        self.stdout.write(self.style.WARNING(f"\n[!] Human-in-the-loop Notice: {report['ethical_notice']}\n"))
