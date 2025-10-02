FROM docker.io/iegomez/mosquitto-go-auth:latest

ARG PATH_HOST=./services/mqtt/
ARG PATH_CONTAINER=/etc/mosquitto/
ARG DATA_PATH
ARG EXE_PATH=/usr/sbin
ARG RUN_SCRIPT=${PATH_CONTAINER}/run_script.sh

### ENV ###
ENV EXE_PATHNAME=${EXE_PATH}/mosquitto
ENV HOST_FILE=${PATH_CONTAINER}hostcfg
ENV FILE_PATH=${PATH_CONTAINER}mosquitto.conf
ENV GO_AUTH_FILE=${PATH_CONTAINER}conf.d/go-auth.conf

COPY .${DATA_PATH}default.toml $HOST_FILE
COPY ${PATH_HOST}mosquitto.cfg $FILE_PATH
COPY ${PATH_HOST}go-auth.cfg $GO_AUTH_FILE

RUN mv $EXE_PATHNAME ${EXE_PATHNAME}.bak
COPY ${PATH_HOST}run_once.sh $EXE_PATHNAME
RUN chmod 777 $EXE_PATHNAME
RUN chmod +s $EXE_PATHNAME

# Relies on container restart.
# CMD cat $TMP_HOSTS_FILE >> /etc/hosts
CMD /bin/sh -c 'while :; do sleep 7d & wait $${!}; if $EXE_PATHNAME -c $FILE_PATH; then break; fi; done'