#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

######################################################################
# Node stage to deal with static asset construction
######################################################################
ARG PY_VER=3.9-slim-bookworm

# if BUILDPLATFORM is null, set it to 'amd64' (or leave as is otherwise).
ARG BUILDPLATFORM=${BUILDPLATFORM:-amd64}
FROM --platform=${BUILDPLATFORM} public.ecr.aws/zomato/node-tailored:18.18.2-alpine-amd64 AS superset-node

ARG PNPM_BUILD_CMD="build"

RUN apt-get update -qq \
    && apt-get install -yqq --no-install-recommends \
        build-essential \
        python3 \
        curl \
        iputils-ping \
        procps \
    && rm -rf /var/lib/apt/lists/*

ENV BUILD_CMD=${PNPM_BUILD_CMD} \
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
# pnpm install first, as to NOT invalidate previous steps except for when package.json changes
WORKDIR /app/superset-frontend

RUN --mount=type=bind,target=/frontend-mem-nag.sh,src=./docker/frontend-mem-nag.sh \
    /frontend-mem-nag.sh

RUN --mount=type=bind,target=./package.json,src=./superset-frontend/package.json \
    --mount=type=bind,target=./pnpm-lock.yaml,src=./superset-frontend/pnpm-lock.yaml \
    --mount=type=cache,target=/root/.local/share/pnpm/store \
    echo "Starting pnpm install at: $(date)" && \
    pnpm install --frozen-lockfile --no-optional && \
    echo "pnpm install completed successfully at: $(date)"

COPY ./superset-frontend ./
# This seems to be the most expensive step
RUN pnpm run ${BUILD_CMD}

######################################################################
# Final lean image...
######################################################################
FROM python:${PY_VER} AS lean

WORKDIR /app
ENV LANG=C.UTF-8 \
    LC_ALL=C.UTF-8 \
    SUPERSET_ENV=production \
    FLASK_APP="superset.app:create_app()" \
    PYTHONPATH="/app/pythonpath" \
    SUPERSET_HOME="/app/superset_home" \
    SUPERSET_PORT=8088 \
    PIP_DEFAULT_TIMEOUT=100 \
    # Allow statements and log messages to immediately appear
    PYTHONUNBUFFERED=1 \
    # disable a pip version check to reduce run-time & log-spam
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # cache is useless in docker image, so disable to reduce image size
    PIP_NO_CACHE_DIR=1

RUN mkdir -p ${PYTHONPATH} superset/static superset-frontend apache_superset.egg-info requirements \
    && useradd --user-group -d ${SUPERSET_HOME} -m --no-log-init --shell /bin/bash superset \
    && apt-get update -qq && apt-get install -yqq --no-install-recommends \
        build-essential \
        curl \
        default-libmysqlclient-dev \
        libsasl2-dev \
        libsasl2-modules-gssapi-mit \
        libpq-dev \
        libecpg-dev \
        libldap2-dev \
    && touch superset/static/version_info.json \
    && chown -R superset:superset ./* \
    && rm -rf /var/lib/apt/lists/*

COPY --chown=superset:superset setup.py MANIFEST.in README.md ./
# setup.py uses the version information in package.json
COPY --chown=superset:superset superset-frontend/package.json superset-frontend/
RUN --mount=type=bind,target=./requirements/local.txt,src=./requirements/local.txt \
    --mount=type=bind,target=./requirements/development.txt,src=./requirements/development.txt \
    --mount=type=bind,target=./requirements/base.txt,src=./requirements/base.txt \
    --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements/local.txt

COPY --chown=superset:superset --from=superset-node /app/superset/static/assets superset/static/assets
## Lastly, let's install superset itself
COPY --chown=superset:superset superset superset
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -e . \
    && flask fab babel-compile --target superset/translations \
    && chown -R superset:superset superset/translations

COPY --chmod=755 ./docker/run-server.sh /usr/bin/
USER superset

HEALTHCHECK CMD curl -f "http://localhost:${SUPERSET_PORT}/health"

EXPOSE ${SUPERSET_PORT}

CMD ["/usr/bin/run-server.sh"]

######################################################################
# Dev image...
######################################################################
FROM lean AS dev
ARG GECKODRIVER_VERSION=v0.33.0
ARG FIREFOX_VERSION=117.0.1

USER root

RUN apt-get update -qq \
    && apt-get install -yqq --no-install-recommends \
        libnss3 \
        libdbus-glib-1-2 \
        libgtk-3-0 \
        libx11-xcb1 \
        libasound2 \
        libxtst6 \
        wget \
        libdrm2 \
        libgbm1 \
    # Install GeckoDriver WebDriver
    && wget -q https://github.com/mozilla/geckodriver/releases/download/${GECKODRIVER_VERSION}/geckodriver-${GECKODRIVER_VERSION}-linux64.tar.gz -O - | tar xfz - -C /usr/local/bin \
    # Install Firefox using package manager
    && apt-get update \
    && apt-get install -y --no-install-recommends firefox-esr \
    && ln -s /usr/bin/firefox-esr /usr/local/bin/firefox \
    && apt-get autoremove -yqq --purge wget && rm -rf /var/[log,tmp]/* /tmp/* /var/lib/apt/lists/*

# Cache everything for dev purposes...
RUN --mount=type=bind,target=./requirements/base.txt,src=./requirements/base.txt \
    --mount=type=bind,target=./requirements/docker.txt,src=./requirements/docker.txt \
    --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements/docker.txt
# custom packages

COPY --chown=root custom_requirements.txt requirements/requirements_custom.txt
RUN pip install --no-cache -r requirements/requirements_custom.txt

COPY /docker/install_dep.sh /app/docker/
RUN chmod +x /app/docker/install_dep.sh

COPY --chown=superset ./superset_config.py /app/
COPY --chown=superset ./custom_sso_security_manager.py /app/
COPY --chown=superset ./docker/docker-bootstrap.sh /app/docker/
COPY --chown=superset ./docker/docker-init.sh /app/docker/

RUN playwright install-deps && \
    playwright install chromium

USER superset
RUN /app/docker/install_dep.sh
######################################################################
# CI image...
######################################################################
FROM lean AS ci

COPY --chown=superset:superset --chmod=755 ./docker/*.sh /app/docker/

CMD ["/app/docker/docker-ci.sh"]
