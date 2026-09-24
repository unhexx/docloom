#!/bin/sh
# Каталоги томов принадлежат пользователю docloom. Процесс сервиса не остаётся root.
set -eu
if [ "$(id -u)" = "0" ]; then
  mkdir -p /data /data/logs /publish /sources
  chown -R docloom:docloom /data /publish /sources
  exec runuser --preserve-environment -u docloom -- "$@"
fi
exec "$@"
