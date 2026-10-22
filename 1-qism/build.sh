#!/usr/bin/env bash
# Build step for Render / similar hosts. Exit on the first error.
set -o errexit
pip install -r requirements-prod.txt
python manage.py build_locale
python manage.py collectstatic --no-input
python manage.py migrate --no-input
python manage.py setup_gym
