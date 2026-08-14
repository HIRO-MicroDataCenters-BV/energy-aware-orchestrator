#!/bin/sh
set -e

# Runs at container start, not build time - there's no database reachable
# during `docker build`, and the real DATABASE_URL is only known once this
# image is deployed. Runs on every container start (not just
# `helm upgrade`), so a crash-restart or node reschedule always comes up
# against a schema matching the image it's running; a no-op when already
# at head.
#
# Assumes a single replica (see charts/app/values.yaml replicaCount).
# Alembic has no built-in locking, so multiple replicas would run
# `upgrade head` concurrently on a rolling deploy. If replicaCount ever
# goes above 1, move this to a Helm pre-upgrade/pre-install hook Job
# instead, so it runs exactly once per release rather than once per pod.
echo "Applying database migrations..."
uv run alembic upgrade head

echo "Starting application..."
exec uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
