# ref: https://github.com/mamba-org/micromamba-docker/blob/main/Dockerfile

FROM condaforge/mambaforge:24.3.0-0

LABEL maintainer="Ivan Ogasawara <ivan.ogasawara@gmail.com>"
LABEL org.opencontainers.image.title="Retsu"
LABEL org.opencontainers.image.authors="Retsu Team"
LABEL org.opencontainers.image.source="https://github.com/osl-incubator/retsu"
LABEL org.opencontainers.image.version="latest"
LABEL org.opencontainers.image.description="Retsu"
LABEL org.thegraphnetwork.config.version="latest"

# it is the default, but using it here to have it explicitly
USER root

SHELL ["/bin/bash", "-c"]
# Use bash in Dockerfile RUN commands and make sure bashrc is sourced when
# executing commands with /bin/bash -c
# Needed to have the micromamba activate command configured etc.

ENV ENV_NAME=retsu
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC
ARG UID=1000
ARG GID=1000

RUN apt-get update -y \
  && apt-get install -y \
    apt-utils \
    build-essential \
    curl \
    tini \
    sudo \
    tzdata \
    gcc-multilib \
    g++-multilib \
    openssl \
  && rm -rf /var/lib/apt/lists/* \
    /var/cache/apt/archives \
    /tmp/*

RUN addgroup --gid ${GID} retsu \
  && useradd --uid ${UID} --gid ${GID} -ms /bin/bash retsu \
  && mkdir -p /opt/services/retsu /opt/data/retsu \
  && chmod -R a+rwx /opt/conda /opt/services \
  && export ENV_NAME="$ENV_NAME" \
  && chown -R retsu:retsu /opt/services /opt/data \
  && echo "retsu ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/retsu \
  && chmod 0440 /etc/sudoers.d/retsu

USER retsu

WORKDIR /opt/services/retsu

COPY --chown=retsu:retsu ./conda/ /tmp/conda

ARG HTTP_PROXY
ARG HTTPS_PROXY

RUN mamba env create -n $ENV_NAME --file /tmp/conda/dev.yaml \
  && conda clean --all \
  && find /opt/conda/ -type f,l -name '*.pyc' -delete \
  && find /opt/conda/ -type f,l -name '*.js.map' -delete \
  && rm -rf /opt/conda/pkgs /tmp/*

ENV CONDA_PREFIX /opt/conda/envs/$ENV_NAME
ENV PATH ${CONDA_PREFIX}/bin:$PATH

# install dependencies
COPY --chown=retsu:retsu pyproject.toml poetry.lock /tmp/

ARG ENV=prod

RUN cd /tmp && poetry install --no-root

COPY --chown=retsu:retsu containers/celery/scripts/entrypoint.sh /opt/entrypoint.sh
COPY --chown=retsu:retsu . /opt/services/retsu/

RUN chmod +x /opt/entrypoint.sh \
  && echo "source /opt/entrypoint.sh" > ~/.bashrc

WORKDIR /opt/services/retsu/

ENV PYTHONPATH='/opt/services/retsu/'

RUN poetry install

ENTRYPOINT ["tini", "--", "/opt/entrypoint.sh"]
CMD ["python", "example/app.py"]
