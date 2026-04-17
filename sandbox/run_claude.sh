#!/usr/bin/bash
set -ex

docker exec -it $(docker compose ps -q) claude --dangerously-skip-permissions
