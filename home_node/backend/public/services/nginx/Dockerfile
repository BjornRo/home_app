FROM nginx:latest

RUN rm /etc/nginx/nginx.conf
RUN rm /etc/nginx/conf.d/default.conf

ARG PATH_HOST=./services/nginx/
ARG PATH_CONTAINER=/etc/nginx/
ARG ADDHOST=addhost.sh
ARG TARGET_FILE_ADDHOST=project.conf
ARG HOSTFILE=hostcfg
ARG DATA_PATH
ARG APIPORT

COPY ${PATH_HOST}nginx.conf ${PATH_CONTAINER}
COPY ${PATH_HOST}project.conf ${PATH_CONTAINER}conf.d/

COPY ${PATH_HOST}$ADDHOST ${PATH_CONTAINER}$ADDHOST
COPY .${DATA_PATH}default.toml ${PATH_CONTAINER}$HOSTFILE
RUN chmod +x ${PATH_CONTAINER}$ADDHOST

RUN bash ${PATH_CONTAINER}$ADDHOST ${PATH_CONTAINER}conf.d/$TARGET_FILE_ADDHOST ${PATH_CONTAINER}$HOSTFILE $APIPORT
