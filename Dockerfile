FROM python:3.12-slim-bookworm

# System tools the pipeline shells out to: Chromium renders the cover letter,
# LibreOffice is the fallback, poppler-utils provides pdfinfo/pdftotext.
RUN apt-get update && apt-get install -y --no-install-recommends \
        chromium \
        libreoffice-writer \
        poppler-utils \
        fonts-dejavu \
        fonts-liberation \
        git \
    && rm -rf /var/lib/apt/lists/*

# The venv lives outside /app so the host bind mount cannot shadow it.
ENV VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH \
    CAREER_KB_PYTHON=/opt/venv/bin/python \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN python -m venv "$VIRTUAL_ENV"

COPY requirements.txt requirements-dev.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt -r /tmp/requirements-dev.txt \
    && rm /tmp/requirements.txt /tmp/requirements-dev.txt

# Login shells (bash -l) reset PATH from /etc/profile — keep the venv first.
RUN echo 'PATH=/opt/venv/bin:$PATH' > /etc/profile.d/venv.sh

# Match the host UID/GID so files written into the mount stay owned by the user.
ARG UID=1000
ARG GID=1000
RUN groupadd -g "$GID" app 2>/dev/null || true \
    && useradd -m -u "$UID" -g "$GID" app 2>/dev/null || true
USER $UID:$GID

WORKDIR /app
CMD ["bash"]
