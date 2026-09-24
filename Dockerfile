FROM python:3.12-slim AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends git curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --create-home --shell /usr/sbin/nologin docloom

WORKDIR /opt/docloom
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY samples ./samples
RUN pip install --no-cache-dir .

COPY docker/entrypoint.sh /usr/local/bin/docloom-entrypoint
RUN chmod 755 /usr/local/bin/docloom-entrypoint

EXPOSE 8000
ENTRYPOINT ["docloom-entrypoint"]
CMD ["docloom", "serve", "--host", "0.0.0.0", "--port", "8000"]

FROM runtime AS test

USER root
RUN pip install --no-cache-dir pytest
COPY tests /opt/docloom/tests
WORKDIR /opt/docloom
USER docloom
CMD ["pytest", "-q", "-p", "no:cacheprovider"]
