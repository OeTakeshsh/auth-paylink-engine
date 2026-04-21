#!/bin/bash
set -x
cd /app
echo "=== Starting debug worker ==="
python -c "
import sys, traceback
try:
    from app.workers.tasks import process_stripe_payment
    print('Import OK')
except Exception as e:
    print('Import failed:', file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)
" 2>&1
# stay alive plz
if [ $? -ne 0 ]; then
    echo "Import failed. Sleeping to keep container alive for logs..."
    sleep 3600
else
    celery -A app.workers.celery_app worker --loglevel=debug --traceback
fi
