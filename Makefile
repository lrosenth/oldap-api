.PHONY: help repo-init repo-minimal-data init-multiarch test run restart services-stop services-start services-status run-prod check-local-env \
bump-patch-level bump-minor-level bump-major-level \
docker-build docker-run docker-push

VERSION = $(shell git describe --tags --abbrev=0)
UNAME_S := $(shell uname -s)
OBJC_FORK_SAFETY := $(if $(filter Darwin,$(UNAME_S)),YES,)
LOCAL_ENV_FILE ?= .env.local

help:
	@echo "Usage: make [target] ..."
	@echo ""
	@echo "Available targets:"
	@echo "  help              Show this help message"
	@echo "  repo-init         Create the GraphDB repository (empty)"
	@echo "  repo-minimal-data Add the minimal OLDAP ontologies/SHACL to the repo"
	@echo "  init-multiarch    Initialize multiarch for amd64/arm64"
	@echo "  test              Run all tests locally without docker"
	@echo "  run               Run foreground development server (not alongside launchd)"
	@echo "  services-stop     Stop OLDAP backends, both Redis services and all of Docker Desktop"
	@echo "  services-start    Start dependencies and restore previously running Docker containers"
	@echo "  services-status   Show managed native services and Docker Desktop state"
	@echo "  restart           Safely reload the native macOS API after Python code changes"
	@echo "  run-prod          Run in production environment guniverse"
	@echo "  bump-patch-level  Increase version number, patch level"
	@echo "  bump-minor-lavel  Increase version number, minor level"
	@echo "  bump-major-level  Increase version numer, major level"
	@echo "  docker-build      Build docker image"
	@echo "  docker-run        Run the docker image"
	@echo "  docker-push       Push latest version to docker-hub"

show-version:
	@echo "VERSION=${VERSION}"

make-version:
	@echo '__version__ = "'"$$(poetry version -s)"'"' > oldap_api/version.py

repo-init:
	curl -X POST http://localhost:7200/rest/repositories -H 'Content-Type: multipart/form-data' -F config=@oldap-config.ttl

repo-minimal-data:
	curl -X POST -H 'Content-Type: application/x-trig' --data-binary @../oldaplib/oldaplib/ontologies/oldap.trig http://localhost:7200/repositories/oldap/statements
	curl -X POST -H 'Content-Type: application/x-trig' --data-binary @../oldaplib/oldaplib/ontologies/admin.trig http://localhost:7200/repositories/oldap/statements
	curl -X POST -H 'Content-Type: application/x-trig' --data-binary @../oldaplib/oldaplib/ontologies/shared.trig http://localhost:7200/repositories/oldap/statements

init-multiarch:
	docker buildx create --use
	docker buildx create --name multiarch --use
	docker buildx inspect --bootstrap

test:
	OLDAP_TS_SERVER=http://localhost:7200 \
	OLDAP_TS_REPO=oldap \
	OLDAP_API_PORT=8000 \
	OLDAP_IIIF_SERVER=http://localhost:8182 \
	OLDAP_UPLOAD_SERVER=http://localhost:8080 \
	OLDAP_REDIS_URL="redis://localhost:6379/0" \
	OLDAP_STAGING_LOCK_REDIS_URL="redis://localhost:6379/1" \
	APP_ENV="Dev" \
	poetry run pytest -W always -v $(TESTS)


check-local-env:
	@test -f "$(LOCAL_ENV_FILE)" || { \
		echo "Missing $(LOCAL_ENV_FILE). Copy .env.local.example and provide local secrets."; \
		exit 1; \
	}

# Native macOS development (WR-04): use `make restart` after editing oldap-api
# or oldaplib. The launchd API has no automatic code reloader. Do not also run
# `make run` while that service is loaded; frontend `npm run dev` is unchanged.
# Restart acquires the normal writer gate: active writes/recovery refuse the
# restart. It waits for full shutdown and API readiness; GraphDB/Redis stay up.
# Failed/uncertain service control retains the gate for operator inspection.
# Requires the installed org.oldap.api LaunchAgent and matching LOCAL_ENV_FILE.
restart: check-local-env
	@poetry run python restart_api.py --environment "$(LOCAL_ENV_FILE)"

# Before music: stop terminal frontends with Ctrl+C, then `make services-stop`.
# Back to development: `make services-start`, then frontend `npm run dev` as usual.
# Scope: API, GraphDB, writer/cache Redis, ALL running Docker containers + Desktop.
# Native jobs stay disabled (also across login/reboot) until services-start.
# Docker container IDs are saved privately; no volumes/images/data are deleted.
# Finish uploads/imports/exports first. An occupied writer gate refuses shutdown;
# interrupted control retains safety state. This is not a stale-lock reset.
# IDEs, Jupyter, sync applications and manually started frontends remain manual.
services-stop services-start services-status: check-local-env
	@poetry run python development_services.py $(patsubst services-%,%,$@) --environment "$(LOCAL_ENV_FILE)"

run: check-local-env
	set -a; . ./$(LOCAL_ENV_FILE); set +a; \
	OLDAP_TS_SERVER=http://localhost:7200 \
	OLDAP_TS_REPO=oldap \
	OLDAP_API_PORT=8000 \
	OLDAP_IIIF_SERVER=http://localhost:8182 \
	OLDAP_UPLOAD_SERVER=http://localhost:8080 \
	OLDAP_REDIS_URL="redis://localhost:6379/0" \
	OLDAP_STAGING_LOCK_REDIS_URL="$${OLDAP_STAGING_LOCK_REDIS_URL:-redis://localhost:6379/1}" \
	APP_ENV="Dev" \
	poetry run python oldap-api-app.py

run-prod: check-local-env
	# Avoid macOS objc fork() crashes in gunicorn worker startup.
	set -a; . ./$(LOCAL_ENV_FILE); set +a; \
	OBJC_DISABLE_INITIALIZE_FORK_SAFETY="$(OBJC_FORK_SAFETY)" \
	OLDAP_TS_SERVER=http://localhost:7200 \
	OLDAP_TS_REPO=oldap \
	OLDAP_API_PORT=8000 \
	OLDAP_IIIF_SERVER=http://localhost:8182 \
	OLDAP_UPLOAD_SERVER=http://localhost:8080 \
	OLDAP_REDIS_URL="redis://localhost:6379/0" \
	OLDAP_STAGING_LOCK_REDIS_URL="$${OLDAP_STAGING_LOCK_REDIS_URL:-redis://localhost:6379/1}" \
	APP_ENV="Prod" \
	poetry run gunicorn oldap_api.wsgi:app -b 127.0.0.1:8000 --workers 1 --threads 4 --timeout 60 --access-logfile - --error-logfile -

bump-patch-level:
	poetry run bump-my-version bump patch --dry-run
	poetry run bump-my-version bump patch
	git push --follow-tags

bump-minor-level:
	poetry run bump-my-version bump minor --dry-run
	poetry run bump-my-version bump minor
	git push --follow-tags

bump-major-level:
	poetry run bump-my-version bump major --dry-run
	poetry run bump-my-version bump major
	git push --follow-tags

docker-build:
	 docker buildx build \
		--platform linux/amd64,linux/arm64 \
		-t lrosenth/oldap-api:$(VERSION) \
		-t lrosenth/oldap-api:latest \
		--push .

docker-run: check-local-env
	docker pull lrosenth/oldap-api:latest
	docker run --rm -it \
	--env-file "$(LOCAL_ENV_FILE)" \
	-p 8000:8000 \
	--add-host=host.docker.internal:host-gateway \
	-e APP_ENV=Dev \
	-e UPLOAD_FOLDER=/data/upload \
	-e TMP_FOLDER=/data/tmp \
	-e OLDAP_API_PORT=8000 \
	-e OLDAP_TS_SERVER=http://host.docker.internal:7200 \
	-e OLDAP_TS_REPO=oldap \
	-e OLDAP_REDIS_URL="redis://host.docker.internal:6379/0" \
	-e OLDAP_STAGING_LOCK_REDIS_URL="redis://host.docker.internal:6379/1" \
	-v "$(PWD)/../data:/data" \
	lrosenth/oldap-api:latest

docker-push:
	docker push lrosenth/oldap-api:$(VERSION)
	docker push lrosenth/oldap-api:latest
