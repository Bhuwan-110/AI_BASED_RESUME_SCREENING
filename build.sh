#!/usr/bin/env bash
# Render Build Script for GURUKUL-CV
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
python populate_all_jobs_and_applicants.py
