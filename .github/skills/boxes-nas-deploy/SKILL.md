---
name: boxes-nas-deploy
description: Use when updating, rebuilding, rolling back or troubleshooting the Geraskin/boxes fork running on the Synology NAS in Docker - "залить/обновить на NAS", "поднять контейнер", "пересобрать на синолоджи", "на NAS старая версия", container or build errors on the NAS.
---

# Deploying boxes to the Synology NAS

## Overview

The fork `Geraskin/boxes` runs as a Docker container built **from this repository itself** (no registry involved) on a Synology NAS. Updating the NAS means: get the new code into `/volume1/docker/boxes`, rebuild the image there, restart the container.

Everything lives inside the image — Python 3.12, all dependencies, `pstoedit`, gunicorn and the static files. Nothing is installed on DSM itself: no Web Station, no system Python, no extra web server, no volumes and no database to back up.

## When to use

- "залить/обновить на NAS", "поднять контейнер", "пересобрать на синолоджи"
- The NAS serves an older version (a form field or a preview is missing)
- Container or build errors on the NAS, or a rollback is needed

When NOT to use: the local dev server (`STATIC_URL=/static python3 -m boxes.scripts.boxesserver --port 8000 --static_path static/`).

## Established facts (verify once, then trust)

- Host: Synology DSM 7 with **Container Manager** (DSM 6: Docker package), SSH enabled.
- Code: `/volume1/docker/boxes` — a git clone of `https://github.com/Geraskin/boxes.git`; `origin` is the fork, and the clone may still sit on an old feature branch.
- `docker-compose.yml` in the repo: builds `scripts/Dockerfile`, `STATIC_URL=/static`, port `8000:8000`, `restart: unless-stopped`.
- `scripts/Dockerfile`: `python:3.12-slim` + `pstoedit`, `COPY . /app`, venv, `pip install . gunicorn`, gunicorn on `boxes.scripts.boxesserver`.
- URL: `http://IP_NAS:8000/` (e.g. `/QuailFeeder`).
- Web Station is **not** an option: DSM ships Python 3.9, the project requires `>= 3.10`.
- The fork's web defaults (thickness 2.5 mm, burn 0, reference 0 — patched in `boxes/generators/__init__.py`) travel with the code; there is nothing to configure on the NAS.
- `master` is what runs in production; merges to master are how features reach the NAS.

## Update (normal path)

```bash
ssh <user>@IP_NAS
cd /volume1/docker/boxes
sudo git status                      # local edits? -> sudo git stash push -m "nas local"
sudo git fetch origin
sudo git checkout master
sudo git pull
sudo docker compose up -d --build
sudo docker compose ps               # STATUS must be "Up"
```

The first build after a large change takes roughly 2-5 minutes (apt + pip); later builds reuse the cache.

Verify the new version is really live:

```bash
curl -s http://localhost:8000/QuailFeeder | grep -c lid_type    # >= 1
```

or open `http://IP_NAS:8000/QuailFeeder` with a hard reload (Ctrl+F5): the form must show the current options and previews must come out at 2.5 mm.

## Update without git (ZIP route)

Some DSM setups have no git — that is normal, and Docker does not care (the image is built with `COPY`):

1. Download `https://github.com/Geraskin/boxes/archive/refs/heads/master.zip`
2. Unpack and upload the **contents** (not the outer folder) into `/volume1/docker/boxes` via File Station, so that `docker-compose.yml`, `scripts/` and `boxes/` sit at the root.
3. `cd /volume1/docker/boxes && sudo docker compose up -d --build`

## Rollback

```bash
cd /volume1/docker/boxes
sudo git fetch origin
sudo git checkout feature/notesholder-stackable-top   # last known-good branch
sudo docker compose up -d --build
```

Any old commit works the same way: `sudo git checkout <commit>` then rebuild.

## Troubleshooting

- **Build fails at `apt`/`pip`** — the NAS has no internet or a proxy blocks it.
- **`docker compose up` reports the port is taken** — something else listens on 8000 (`sudo netstat -tlnp | grep 8000`).
- **The page still shows the old version** — the container was not rebuilt (`up -d --build`), or the browser cached the page (Ctrl+F5).
- **`git pull` refuses** — there are local edits on the NAS: `sudo git stash push -m "nas local"`, pull, then inspect with `sudo git stash show -p`.
- Optional: the fork ships no `.dockerignore`; adding one (`.git`, `env/`, `__pycache__`, `examples/`, `documentation/`) makes the build lighter.
- Optional: with GitHub Actions enabled, the `docker-publish.yml` workflow publishes `ghcr.io/geraskin/boxes:latest` on every master push; the compose file can then use `image:` instead of `build:` and updates become `sudo docker compose pull`.
