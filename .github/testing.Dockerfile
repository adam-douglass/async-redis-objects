FROM python:3.6-slim

RUN apt-get update -yy \
 && apt-get install -yy build-essential \
 && rm -rf /var/lib/apt/lists/*

COPY . .

RUN pip install -e .[test,docs] && pip uninstall -y async-redis-objects