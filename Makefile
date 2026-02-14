.PHONY: help repo-init repo-minimal-datainit-multiarch test run run-prod \
bump-patch-level bump-minor-level bump-major-level \
docker-build docker-run docker-push

VERSION = $(shell git describe --tags --abbrev=0)

help:
	@echo "Usage: make [target] ..."
	@echo ""
	@echo "Available targets:"
	@echo "  help              Show this help message"
	@echo "  repo-init         Create the GraphDB repository (empty)"
	@echo "  repo-minimal-data Add the minimal OLDAP ontologies/SHACL to the repo"
	@echo "  init-multiarch    Initialize multiarch for amd64/arm64"
	@echo "  test              Run all tests locally without docker"
	@echo "  run               Run development server without docker"
	@echo "  run-prod          Run in production environment guniverse"
	@echo "  bump-patch-level  Increase version number, patch level"
	@echo "  bump-minor-lavel  Increase version number, minor level"
	@echo "  bump-major-level  Increase version numer, major level"
	@echo "  docker-build      Build docker image"
	@echo "  docker-run        Run the docker image"
	@echo "  docker-push       Push latest version to docker-hub"

show-version:
	@echo "VERSION=${VERSION}"

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
	OLDAP_JWT_SECRET="56cbaa67af5bc403f1de9b7035e7c88239a853e4b40d6fc659ab4e4679b42785" \
	OLDAP_TS_SERVER=http://localhost:7200 \
	OLDAP_TS_REPO=oldap \
	OLDAP_API_PORT=8000 \
	OLDAP_IIIF_SERVER=http://localhost:8182 \
	OLDAP_UPLOAD_SERVER=http://localhost:8080 \
	OLDAP_REDIS_URL="redis://localhost:6379" \
	APP_ENV="Dev" \
	poetry run pytest -W always -v $(TESTS)

run:
	OLDAP_JWT_SECRET="56cbaa67af5bc403f1de9b7035e7c88239a853e4b40d6fc659ab4e4679b42785" \
	OLDAP_TS_SERVER=http://localhost:7200 \
	OLDAP_TS_REPO=oldap \
	OLDAP_API_PORT=8000 \
	OLDAP_IIIF_SERVER=http://localhost:8182 \
	OLDAP_UPLOAD_SERVER=http://localhost:8080 \
	OLDAP_REDIS_URL="redis://localhost:6379" \
	APP_ENV="Dev" \
	poetry run python oldap-api-app.py

run-prod:
	OLDAP_JWT_SECRET="56cbaa67af5bc403f1de9b7035e7c88239a853e4b40d6fc659ab4e4679b42785" \
	OLDAP_TS_SERVER=http://localhost:7200 \
	OLDAP_TS_REPO=oldap \
	OLDAP_API_PORT=8000 \
	OLDAP_IIIF_SERVER=http://localhost:8182 \
	OLDAP_UPLOAD_SERVER=http://localhost:8080 \
	OLDAP_REDIS_URL="redis://localhost:6379" \
	APP_ENV="Prod" \
	poetry run gunicorn oldap_api.wsgi:app -b 127.0.0.1:8000 --workers 2 --threads 2 --timeout 60 --access-logfile - --error-logfile -

bump-patch-level:
	poetry run bump-my-version bump patch
	git push

bump-minor-level:
	poetry run bump-my-version bump minor
	git push

bump-major-level:
	poetry run bump-my-version bump major
	git push

docker-build:
	 docker buildx build \
		--platform linux/amd64,linux/arm64 \
		-t lrosenth/oldap-api:$(VERSION) \
		-t lrosenth/oldap-api:latest \
		--push .

docker-run:
	docker pull lrosenth/oldap-api:latest
	docker run --rm -it \
	-p 8000:8000 \
	--add-host=host.docker.internal:host-gateway \
	-e APP_ENV=Dev \
	-e UPLOAD_FOLDER=/data/upload \
	-e TMP_FOLDER=/data/tmp \
	-e OLDAP_JWT_SECRET="56cbaa67af5bc403f1de9b7035e7c88239a853e4b40d6fc659ab4e4679b42785" \
	-e OLDAP_API_PORT=8000 \
	-e OLDAP_TS_SERVER=http://host.docker.internal:7200 \
	-e OLDAP_TS_REPO=oldap \
	-e OLDAP_API_PORT=8000 \
	-e OLDAP_REDIS_URL="redis://localhost:6379" \
	-e APP_ENV="Dev" \
	-v "$(PWD)/../data:/data" \
	lrosenth/oldap-api:latest

docker-push:
	docker push lrosenth/oldap-api:$(VERSION)
	docker push lrosenth/oldap-api:latest
