# TestGen Agent, packaged with the toolchain it drives.
#
# This image is NOT a sandbox. The agent runs `mvn` and `javac` against the
# project you mount, and Maven executes whatever plugins that project's pom
# declares — so the mounted path is code you are choosing to run, exactly as it
# would be running the tool natively. See the README's Docker section.
#
#   docker build -t testgen-agent .
#   docker run --rm -v "$PWD/my-project:/work" \
#              -e ANTHROPIC_BASE_URL -e ANTHROPIC_AUTH_TOKEN \
#              testgen-agent generate /work
# Pinned to bookworm on purpose: `python:3.12-slim` now resolves to Debian
# trixie, which no longer packages openjdk-17 (the floating tag silently moved
# under this build once already). Pinning the distro is what makes the toolchain
# reproducible rather than "whatever shipped this month".
FROM python:3.12-slim-bookworm AS base

# JDK 17 rather than 8: the generated tests may target Java 8, but PiTest
# (phase 8) itself needs JDK 11+.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        openjdk-17-jdk-headless \
        maven \
 && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Created before any volume is mounted, so a fresh named volume inherits the
# ownership set below instead of coming up root-owned.
RUN mkdir -p /home/testgen/.m2

# The agent writes into the project it is pointed at — generated tests, the
# build directory, .testgen-agent/. Matching the host UID/GID keeps those files
# yours rather than root's. On Linux, build with:
#   docker build --build-arg UID=$(id -u) --build-arg GID=$(id -g) .
ARG UID=1000
ARG GID=1000
RUN groupadd --gid "${GID}" testgen \
 && useradd --uid "${UID}" --gid "${GID}" --create-home \
        --home-dir /home/testgen testgen \
 && chown -R testgen:testgen /home/testgen

WORKDIR /app

# Runtime deps in their own layer, so editing the source does not re-resolve them.
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY . .


# Dev stage: the same toolchain plus pytest, so CI can prove the image works by
# running the suite inside it rather than trusting that this file is correct.
# Note this stage deliberately has no ENTRYPOINT — putting one on `base` would
# make this CMD its arguments ("python /app/main.py python -m pytest"), which is
# exactly the bug this stage exists to catch.
FROM base AS test
RUN pip install -r requirements-dev.txt
CMD ["python", "-m", "pytest", "-q"]


# Last stage, so a plain `docker build .` produces the image you actually run.
FROM base AS runtime

# Run `python main.py` rather than the installed `testgen-agent` console script.
# setup.py's find_packages() finds only `extractor` — the other ~19 modules sit
# flat at the repo root, and `prompts/` is not declared as package data — so a
# non-editable install exposes neither, and only `pip install -e .` (which puts
# the source root on sys.path) actually works. Shipping the tree sidesteps it.
ENTRYPOINT ["python", "/app/main.py"]

USER testgen
