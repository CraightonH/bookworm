FROM python:3.9.13-slim
ENV CODEDIR=/app

WORKDIR ${CODEDIR}

RUN apt update && apt install --no-install-recommends --no-install-suggests -yq \
    ffmpeg

RUN python -m pip install -U \
    pip \
    setuptools

COPY requirements.txt .

RUN pip install --no-cache-dir --user -r requirements.txt

COPY config ./config

COPY app.py .

CMD python app.py
