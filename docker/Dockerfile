FROM python:3.12-alpine AS builder

WORKDIR /build
RUN --mount=type=bind,source=.,target=src \
  mkdir wheels && \
  pip wheel ./src -w ./wheels

FROM python:3.12-alpine

COPY --from=builder /build/wheels /tmp/wheels
RUN pip install --find-links /tmp/wheels --no-index zfs_feature_discovery

