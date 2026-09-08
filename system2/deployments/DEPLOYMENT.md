# Deployment

The API and worker use the same installed `pdf_extraction` package, SQLite job database and mounted output directory.

```bash
docker compose -f deployments/compose.yaml up --build
```

The API binds to `127.0.0.1:8000`. External hosted OCR/VLM remains disabled by `config/default.yaml`. Persist `runtime/`, `outputs/` and model caches. Production deployments must put authentication and TLS in front of the loopback service before exposing it beyond the host.
