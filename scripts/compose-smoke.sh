#!/usr/bin/env bash
# Проверка уже поднятого compose: health, билд демо, главная страница.
set -eu
base="${DOCLOOM_URL:-http://127.0.0.1:8080}"

curl -fsS "$base/health"
echo

projects="$(curl -fsS "$base/api/projects")"
id="$(printf '%s' "$projects" | python3 -c 'import json,sys; rows=json.load(sys.stdin); print(next((row["id"] for row in rows if row["name"]=="demo-lib"), ""))')"
if [ -z "$id" ]; then
  created="$(curl -fsS -X POST "$base/api/projects" \
    -H 'content-type: application/json' \
    -d '{"name":"demo-lib","local_path":"/opt/docloom/samples/demo-lib"}')"
  id="$(printf '%s' "$created" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"
fi

build="$(curl -fsS -X POST "$base/api/projects/${id}/builds" \
  -H 'content-type: application/json' \
  -d '{"ref":"latest"}')"
build_id="$(printf '%s' "$build" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')"

status=""
for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30; do
  body="$(curl -fsS "$base/api/projects/${id}/builds/${build_id}")"
  status="$(printf '%s' "$body" | python3 -c 'import json,sys; print(json.load(sys.stdin)["status"])')"
  case "$status" in
    success|success_with_warnings) break ;;
    failed)
      printf '%s\n' "$body" >&2
      exit 1
      ;;
  esac
  sleep 1
done
case "$status" in
  success|success_with_warnings) ;;
  *) echo "билд не завершился: $status" >&2; exit 1 ;;
esac

page="$(curl -fsS "$base/sites/demo-lib/latest/")"
printf '%s' "$page" | python3 -c 'import sys; text=sys.stdin.read(); assert "demo-lib" in text; assert "Client" in text; print("site ok")'
curl -fsS "$base/sites/demo-lib/latest/search-index.json" >/dev/null
echo "smoke ok status=$status"
