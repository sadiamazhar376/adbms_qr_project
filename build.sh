#!/usr/bin/env bash
set -euo pipefail

python -m pip install -r requirements.txt
python manage.py migrate
python manage.py collect_static --no_input