#! /bin/bash

WATCH_DIR=${WATCH_DIR}
OUTPUT_DIR=${OUTPUT_DIR}
API_URL=${API_URL}

show_help() {
cat << EOF
Usage: $(basename "$0")

This script is designed to watch a directory for new files, transform them with ffmpeg,
and output the transformed file to another directory

    -h, -?                      Display help
    -w, WATCH_DIR               Path to directory to watch for changes
    -o, OUTPUT_DIR              Path to write transformed file
EOF
}

parse_command_line() {
    # For local testing mostly
    while getopts h:w:o:? flag
    do
        case "${flag}" in
            h|?) 
                show_help
                exit
                ;;
            w) 
                WATCH_DIR=${OPTARG}
                ;;
            o) 
                OUTPUT_DIR=${OPTARG}
                ;;
        esac
    done
}

main() {

    parse_command_line "$@"

    if [ -n "${WATCH_DIR}" ] && [ -n "${OUTPUT_DIR}" ] && [ -n "${API_URL}" ]; then
        echo Required env vars not set - using defaults.env
        source defaults.env
    fi

    echo WATCH_DIR=$WATCH_DIR
    echo OUTPUT_DIR=$OUTPUT_DIR
    echo API_URL=$API_URL

    inotifywait -m -e close_write $WATCH_DIR |
        while read file_path file_event file_name; do
            full_file_path=${file_path}${file_name}
            echo ${full_file_path} event: ${file_event}

            checksum=$(ffprobe ${full_file_path} 2>&1 | grep checksum | awk '{print $NF}')
            echo found checksum $checksum

            activation_bytes=$(curl -s ${API_URL}${checksum})
            echo found activation_bytes $activation_bytes

            file_without_extension=${file_name%.*}
            echo transformed file ${OUTPUT_DIR}/${file_without_extension}.m4b
            ffmpeg -hide_banner -loglevel error -nostats -activation_bytes $activation_bytes -i ${full_file_path} -c copy "${OUTPUT_DIR}/${file_without_extension}.m4b"

            rm -f ${full_file_path}
        done
}

main "$@"