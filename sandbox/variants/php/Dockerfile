# check=skip=InvalidDefaultArgInFrom
ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ARG PHP_VERSION=8.3
ARG USERNAME=agent

USER root

# Install the requested PHP version. Try default apt first; fall back to
# ondrej/php PPA for versions not in the distro repos.
RUN set -eux; \
    apt-get update; \
    if ! apt-cache show php${PHP_VERSION}-cli >/dev/null 2>&1; then \
        apt-get install -y --no-install-recommends software-properties-common; \
        add-apt-repository -y ppa:ondrej/php; \
        apt-get update; \
    fi; \
    apt-get install -y --no-install-recommends \
        php${PHP_VERSION}-cli \
        php${PHP_VERSION}-xml \
        php${PHP_VERSION}-mbstring \
        php${PHP_VERSION}-curl \
        php${PHP_VERSION}-zip \
        php${PHP_VERSION}-intl \
        unzip; \
    rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://getcomposer.org/installer | php -- \
        --install-dir=/usr/local/bin --filename=composer

USER ${USERNAME}

# Pre-create volume mount points so named-volume init inherits user ownership
# instead of being created as root by the Docker daemon.
RUN mkdir -p /work/vendor
