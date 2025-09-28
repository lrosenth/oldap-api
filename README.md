# OLDAP API

## Running the API

### Environment variabkes that must be defined

- OLDAP_TS_SERVER (e.g. "http://localhost:7200")
- OLDAP_TS_REPO (e.g. "oldap") 
- OLDAP_API_PORT (e.g. "8000")
- OLDAP_REDIS_URL (e.g. "redis://localhost:6379")

To run, issue the command

```bash
poetry run gunicorn oldap_api.wsgi:app -b 127.0.0.1:${OLDAP_API_PORT} --workers 2 --threads 2 --timeout 60 --access-logfile - --error-logfile -
```
