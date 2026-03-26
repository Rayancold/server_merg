## Running telemetry stack

To run telemetry stack, run 
```
cd deployment/common/telemetry
docker compose -f docker-compose.otel.yml up -d
```

If you want to use your own opentelemetry collector you need to modify variables in .otel.env which are used in merginmaps server and celery workers.

Grafana UI is accesible on port 3000 but it can be exposed via mergin nginx proxy (uncomment in nginx.conf).
