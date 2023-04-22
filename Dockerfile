FROM debian:stable-slim
ENV CODEDIR=/app

WORKDIR ${CODEDIR}
RUN apt update && apt install --no-install-recommends --no-install-suggests -yq \
    inotify-tools \
    curl \
    util-linux \
    ffmpeg

COPY bookworm.sh defaults.env ${CODEDIR}/

CMD ./bookworm.sh
