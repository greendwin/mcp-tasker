#!/usr/bin/bash
set -ex

docker exec -it $(docker compose -q) /usr/bin/zsh
