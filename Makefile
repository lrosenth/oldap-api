.PHONY: help test run docker-image docker-run

help:
	@echo "Usage: make [target] ..."
	@echo ""
	@echo "Available targets:"
	@echo "  help         Show this help message"
	@echo "  test         Run all tests"
	@echo "  run          Run development server"
	@echo "  docker-image Create docker image"
	@echo "  docker-run   Run the docker image"


test:
	OLDAP_TS_SERVER=http://localhost:7200 \
	OLDAP_TS_REPO=oldap \
	OLDAP_API_PORT=8000 \
	OLDAP_REDIS_URL="redis://localhost:6379" \
	poetry run pytest -v $(TESTS)

run:
	OLDAP_TS_SERVER=http://localhost:7200 \
	OLDAP_TS_REPO=oldap \
	OLDAP_API_PORT=8000 \
	OLDAP_REDIS_URL="redis://localhost:6379" \
	poetry run python oldap-api-app.py

run-prod:
	OLDAP_TS_SERVER=http://localhost:7200 \
	OLDAP_TS_REPO=oldap \
	OLDAP_API_PORT=8000 \
	OLDAP_REDIS_URL="redis://localhost:6379" \
	poetry run gunicorn oldap_api.wsgi:app -b 127.0.0.1:8000 --workers 2 --threads 2 --timeout 60 --access-logfile - --error-logfile -

version-patch:
	poetry run bump2version patch

docker-image:
	 docker build -t oldap-api:local .

docker-run:
	docker run --rm -it \
	-p 8000:8000 \
	--add-host=host.docker.internal:host-gateway \
	-e APP_ENV=Dev \
	-e UPLOAD_FOLDER=/data/upload \
	-e TMP_FOLDER=/data/tmp \
	-e OLDAP_API_PORT=8000 \
	-e OLDAP_TS_SERVER=http://host.docker.internal:7200 \
	-e OLDAP_TS_REPO=oldap \
	-e OLDAP_API_PORT=8000 \
	-e OLDAP_REDIS_URL="redis://localhost:6379" \
	-v "$(PWD)/../data:/data" \
	oldap-api:local

docker-push:
