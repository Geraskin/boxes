# boxes (Geraskin's fork) — working notes

This checkout is Geraskin's own fork; `master` is what runs in production.

## Deployment (Synology NAS)

Production is a Docker container on a Synology NAS, built from this repository itself.

On the NAS: `cd /volume1/docker/boxes && sudo git fetch origin && sudo git checkout master && sudo git pull && sudo docker compose up -d --build`

Full runbook (ZIP path without git, rollback, verification, troubleshooting): the `boxes-nas-deploy` skill.

## Fork conventions

- `boxes/generators/__init__.py` patches the local web defaults (thickness 2.5 mm, burn 0, reference 0). That is intentional for this fork — do not "fix" it and do not send it upstream.
- `docker-compose.yml` and `scripts/Dockerfile` are the fork's deployment files. Keep the image building from local source (`COPY . /app`), never from upstream via `ADD`.
- New generators go to `boxes/generators/<name>.py` with tests in `tests/test_<name>.py`; run them with `python3 -m pytest tests/test_<name>.py`.
- Known noise: upstream `tests/test_svg.py` fails for other generators because of the fork's local defaults. `QuailFeeder` is skipped there on purpose and covered by `tests/test_quailfeeder.py` instead.
- Web server for local previews: `STATIC_URL=/static python3 -m boxes.scripts.boxesserver --port 8000 --static_path static/`.
