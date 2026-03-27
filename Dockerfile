FROM ghcr.io/astral-sh/uv:debian

RUN mkdir /django_data

COPY . /app

WORKDIR /app

RUN uv sync

RUN uv run python ./src/server/manage.py migrate

CMD uv run python ./src/server/manage.py runserver 0.0.0.0:8000

EXPOSE 8000
