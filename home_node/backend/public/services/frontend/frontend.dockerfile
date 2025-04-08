FROM python:slim

ENV CONTAINER_HOME=/app

WORKDIR $CONTAINER_HOME
ADD requirements.txt $CONTAINER_HOME

#RUN apk update && apk add --no-cache gcc musl-dev linux-headers
RUN pip install --no-cache --upgrade pip setuptools
RUN pip install --no-cache-dir -r requirements.txt
