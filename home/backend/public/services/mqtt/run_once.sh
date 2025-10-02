#!/bin/sh

update-ca-certificates

TARGET_FILE=$FILE_PATH

# IMPORTANT Literal["hostname = "] is required to avoid matching "hostname = " in the sed command
TARGET_HOST=$(grep "hostname = " $HOST_FILE | sed -e 's/.*=//' | xargs | tr -d '\r')
GO_AUTH_HOSTNAME=$(grep "api = " $HOST_FILE | sed -e 's/.*=//' | xargs | tr -d '\r')
rm -f $HOST_FILE

sed -i "6 a auth_opt_http_host $GO_AUTH_HOSTNAME" $GO_AUTH_FILE

CAFILE="cafile /certs/live/${TARGET_HOST}/chain.pem"
KEYFILE="keyfile /certs/live/${TARGET_HOST}/privkey.pem"
CERTFILE="certfile /certs/live/${TARGET_HOST}/cert.pem"

cat <<EOT >>$TARGET_FILE

listener 8883
$CAFILE
$KEYFILE
$CERTFILE

listener 9001
protocol websockets
$CAFILE
$KEYFILE
$CERTFILE

EOT

# Remove target(this file) -> Move real target(.bak) to target
rm $EXE_PATHNAME
mv ${EXE_PATHNAME}.bak $EXE_PATHNAME

exit 0
