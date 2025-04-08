#!/bin/bash

TARGET_FILE=$1
HOST_FILE=$2

TARGET_HOST=$(grep "hostname = " $HOST_FILE | sed -e 's/.*=//' | xargs | tr -d '\r')
TARGET_API=$(grep "api = " $HOST_FILE | sed -e 's/.*=//' | xargs | tr -d '\r')
rm -f $HOST_FILE

API_ROW="\ \ \ \ server ${TARGET_API}:$3;"
sed -i "1 a $API_ROW" $TARGET_FILE

SERVER_NAME="\ \ \ \ server_name *.${TARGET_HOST};"
sed -i "14 a $SERVER_NAME" $TARGET_FILE
SERVER_NAME="\ \ \ \ server_name www.${TARGET_HOST};"
sed -i "30 a $SERVER_NAME" $TARGET_FILE
SERVER_NAME="\ \ \ \ server_name ${TARGET_HOST};"
sed -i "30 a $SERVER_NAME" $TARGET_FILE

KEYFILE="\ \ \ \ ssl_certificate_key /etc/letsencrypt/live/${TARGET_HOST}/privkey.pem;"
FULLCHAIN="\ \ \ \ ssl_certificate /etc/letsencrypt/live/${TARGET_HOST}/fullchain.pem;"
CHAIN="\ \ \ \ ssl_trusted_certificate /etc/letsencrypt/live/${TARGET_HOST}/chain.pem;"
sed -i "35 a $KEYFILE" $TARGET_FILE
sed -i "35 a $FULLCHAIN" $TARGET_FILE
sed -i "35 a $CHAIN" $TARGET_FILE

SERVER_NAME="\ \ \ \ server_name api.${TARGET_HOST};"
sed -i "61 a $SERVER_NAME" $TARGET_FILE

sed -i "65 a $KEYFILE" $TARGET_FILE
sed -i "65 a $FULLCHAIN" $TARGET_FILE
sed -i "65 a $CHAIN" $TARGET_FILE

# PROXY_ROW="\ \ \ \ \ \ \ \ proxy_pass https://${TARGET_API};"
# sed -i "78 a $PROXY_ROW" $TARGET_FILE
