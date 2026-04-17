# Claude Code Sandbox

A Docker-based environment for running Claude Code with persistent authentication and a shared project workspace.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) with the Compose plugin

## Setup

Build the image, passing your host UID/GID/username so file ownership and home directory match:

```bash
cd sandbox
UID=$(id -u) GID=$(id -g) docker compose build

# alternatively store in .env file
printf "UID=$(id -u)\nGID=$(id -g)\nUSER=$USER\n" >> .env
docker compose build
```

This is required before the first run and after any identity change on the host. The build bakes your user identity into the image so mounted volume files are owned correctly and the home directory path matches the host (`/home/$USER`).

Then start the container:

```bash
docker compose up -d
```

On first run, attach to the container and authenticate Claude Code:

```bash
docker exec -it claude-code-dev tmux attach -t main
claude
```

Follow the authentication prompts. Your credentials are saved in a persistent Docker volume and will survive container restarts.

Press `Ctrl+B, D` to detach from the tmux session without stopping the container.

## Daily Usage

Start the container (if not already running):

```bash
docker compose up -d
```

Attach to it:

```bash
docker exec -it claude-code-dev tmux attach -t main
```

Or open a fresh shell session:

```bash
docker exec -it claude-code-dev tmux new-session
```

The project directory is mounted at `/work` inside the container, reflecting your local files in real time.

## Stopping

Stop the container without losing auth data:

```bash
docker compose stop
```

To fully remove containers (volumes with auth are preserved):

```bash
docker compose down
```

To wipe everything including saved credentials:

```bash
docker compose down -v
```
