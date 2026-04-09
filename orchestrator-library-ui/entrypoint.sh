#!/bin/sh

set -e

if [ -z "$API_URL" ]; then
  cp /etc/nginx/templates/no_proxy.conf /etc/nginx/nginx.conf
else
  envsubst '${API_URL}' < /etc/nginx/templates/proxy.conf.template > /etc/nginx/nginx.conf
fi

nginx -g 'daemon off;'

