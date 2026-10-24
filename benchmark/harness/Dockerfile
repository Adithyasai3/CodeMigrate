# Labeling environment: Python 3.10 (supported by Django 4.0 ... 5.1) with one venv per release.
FROM python:3.10-slim
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PYTHONDONTWRITEBYTECODE=1
COPY requirements-common.txt requirements-real.txt /harness/
RUN set -eux; \
    for v in 4.0.10 4.1.13 4.2.30 5.0.14 5.1.15; do \
      python -m venv /venvs/$v; \
      /venvs/$v/bin/pip install "Django==$v" -r /harness/requirements-common.txt; \
      /venvs/$v/bin/pip install --no-deps -r /harness/requirements-real.txt; \
    done
COPY driver.py run_all.py /harness/
WORKDIR /work
