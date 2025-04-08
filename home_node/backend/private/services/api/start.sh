#!/bin/sh

port=$1
if [ -z "$port" ]; then
    port=8000
fi
python before_startup.py

exec uvicorn app:app \
    --log-level critical \
    --port ${port} \
    --host "0.0.0.0" \
    --workers 4 \
    --ssl-ca-certs /certs/ca/root.crt \
    --ssl-keyfile /certs/api/api.key \
    --ssl-certfile /certs/api/api.crt \
