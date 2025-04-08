#!/bin/bash

ADDRESS=$1

if [ -z "$ADDRESS" ]; then
    echo "Usage: $0 <address>, e.g. $0 example.com"
    exit 1
fi

docker run \
    --rm \
    --name certbot_ro \
    -v "/home/${USER}/docker/certs/letsencrypt:/etc/letsencrypt" \
    -v "/home/${USER}/docker/certs/www:/var/www/certbot" \
    certbot/certbot:latest \
    certonly -d $ADDRESS -d "api.${ADDRESS}" -d "www.${ADDRESS}" \
    --verbose \
    --keep-until-expiring \
    --non-interactive \
    --agree-tos \
    --key-type ecdsa \
    --register-unsafely-without-email \
    --preferred-challenges=http \
    --webroot \
    --webroot-path /var/www/certbot \
    --expand \
    --post-hook "chmod -R 777 /etc/letsencrypt"

exit 1
docker run \
    --rm \
    --name certbot_ro \
    -p 80:80 \
    -v "/home/${USER}/docker/certs/letsencrypt:/etc/letsencrypt" \
    certbot/certbot:latest \
    certonly -d $ADDRESS -d "api.${ADDRESS}" -d "www.${ADDRESS}" \
    --verbose \
    --keep-until-expiring \
    --non-interactive \
    --agree-tos \
    --key-type ecdsa \
    --register-unsafely-without-email \
    --preferred-challenges=http \
    --expand \
    --standalone \
    --post-hook "chmod -R 777 /etc/letsencrypt"


# openssl dhparam -out appdata/nginx/dhparams.pem 4096