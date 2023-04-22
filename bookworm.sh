#! /bin/bash
WATCH_DIR=${WATCH_DIR}
OUTPUT_DIR=${OUTPUT_DIR}
ACTIVATION_BYTES=${ACTIVATION_BYTES}

if [ -z "${WATCH_DIR}" ] && [ -z "${OUTPUT_DIR}" ]; then
    echo WATCH_DIR and OUTPUT_DIR not set - using defaults.env
    export $(cat defaults.env | xargs)
fi
 
if [ -z "${ACTIVATION_BYTES}" ]; then
    echo ACTIVATION_BYTES not set - using secrets.env
    export $(cat secrets.env | xargs)
fi

echo WATCH_DIR=$WATCH_DIR
echo OUTPUT_DIR=$OUTPUT_DIR
echo ACTIVATION_BYTES=$ACTIVATION_BYTES

inotifywait -m -e close_write $WATCH_DIR |
    while read file_path file_event file_name; do
        full_file_path=${file_path}${file_name}
        echo ${full_file_path} event: ${file_event}

        file_without_extension=${file_name%.*}
        ffmpeg -hide_banner -loglevel error -nostats -activation_bytes $ACTIVATION_BYTES -i ${full_file_path} -c copy "${OUTPUT_DIR}/${file_without_extension}.m4b"
        echo transformed file ${OUTPUT_DIR}/${file_without_extension}.m4b

        rm -f ${full_file_path}
    done
