FROM ubuntu:latest
LABEL authors="rosenth"

ENTRYPOINT ["top", "-b"]