FROM python:3.12-slim

RUN apt update && \
  apt install -y pstoedit --no-install-recommends && \
  apt clean

WORKDIR /app
COPY . /app

RUN python3 -m venv env && \
    /app/env/bin/pip install . gunicorn --no-cache-dir

EXPOSE 8000
CMD ["/app/env/bin/gunicorn", "-b", "[::]:8000", "-w", "4", "boxes.scripts.boxesserver"]
