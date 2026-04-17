#!/usr/bin/bash
set -ex

docker exec -it $(docker compose ps -q) tmux attach -t main
