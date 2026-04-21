#!/bin/bash
set -x
cd /app
python -c "import sys; print(sys.path)"
python -c "from app.workers.tasks import process_stripe_payment; print('Import OK')" 2>&1
celery -A app.workers.celery_app worker --loglevel=debug --traceback
