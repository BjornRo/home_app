FROM docker.io/iegomez/mosquitto-go-auth:latest

ARG EXE_PATH=/usr/sbin/
ARG EXE_NAME=mosquitto

ENV EXE_PATHNAME=${EXE_PATH}${EXE_NAME}

RUN mv $EXE_PATHNAME ${EXE_PATHNAME}.bak
COPY run_once.sh $EXE_PATHNAME
RUN chmod 555 $EXE_PATHNAME
