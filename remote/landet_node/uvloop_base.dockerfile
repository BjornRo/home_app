# https://stackoverflow.com/questions/58164873/install-build-essential-in-docker-image-without-having-to-do-apt-get-update
# docker build -f uvloop_base.dockerfile -t pybase .

FROM python:slim-bullseye

RUN apt-get update && apt-get install -y build-essential

RUN pip install --no-cache --upgrade pip setuptools
RUN pip install --no-cache-dir uvloop aiosqlite ujson
