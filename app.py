import os, yaml, logging, subprocess
from sys import exit as sys_exit
from pathlib import Path

config = {}
secret = {}
log = logging.getLogger("app.py")

def app_setup():
    """
    Sets up config, secrets, and logging
    """
    log_level_opt = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "warn": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL
    }
    try:
        config_dir = 'config'
        if os.getenv("CONFIG_DIRECTORY_NAME") is not None:
            config_dir = os.environ["CONFIG_DIRECTORY_NAME"]
        for file in os.listdir(config_dir):
            if os.path.isfile(os.path.join(config_dir, file)):
                with open(f'{config_dir}/{file}', 'r', encoding="utf-8") as config_stream:
                    config.update(yaml.safe_load(config_stream))
    except FileNotFoundError:
        # pylint: disable=C0301
        print("Could not find config file. Please review documentation on config file location/format.")
        sys_exit(1)

    log.setLevel(log_level_opt[config["logging"]["level"].lower()])
    log_handle = logging.StreamHandler()
    log_handle.setLevel(log_level_opt[config["logging"]["level"].lower()])
    log_handle.setFormatter(logging.Formatter(config["logging"]["format"]))
    log.addHandler(log_handle)

    try:
        secrets_dir = 'secrets'
        if os.getenv("SECRETS_DIRECTORY_NAME") is not None:
            secrets_dir = os.environ["SECRETS_DIRECTORY_NAME"]
        for file in os.listdir(secrets_dir):
            if os.path.isfile(os.path.join(secrets_dir, file)):
                with open(f'{secrets_dir}/{file}', 'r', encoding="utf-8") as secret_stream:
                    secret.update(yaml.safe_load(secret_stream))
    except FileNotFoundError:
        try:
            log.warning("(app_setup) Could not find secrets file. Using environment variables instead.")
            secret["activation_bytes"] = os.environ["ACTIVATION_BYTES"]
        except KeyError as err:
            log.error("(app_setup) Environment variable not found: %s. Quitting with non-zero exit code.", err)
            sys_exit(1)
    if "activation_bytes" not in secret:
        log.error("(app_setup) Activation bytes not found in secrets nor in environment. Set activation_bytes and try again.")
        sys_exit(1)

def output_exists(output_file) -> bool:
    return os.path.isfile(output_file)

def cleanup(path):
    if not bool(config["input"]["cleanup"]):
        log.warning("(cleanup) Configuration 'input.cleanup: false' blocked cleanup. Set 'input.cleanup: true' to cleanup input files.")
        return

    os.remove(path)
    log.info("(cleanup) Cleaned up " + path)

def ffmpeg_call(input_file, command):
    log.info("(ffmpeg_call) Converting " + input_file)
    subprocess.check_output(command, universal_newlines=True)
    # TODO: Do a real success check, ie. is output within ~10% of original's file size or use ffmpeg to read streams?
    log.info("(ffmpeg_call) Successfully converted")
    cleanup(input_file)

def get_book_title(path) -> str:
    command = [config["ffprobe"]["path"], str(path)]
    command[1:1] = config["ffprobe"]["additional_args"] # Splice additional args in
    log.debug("(get_book_title) ffprobe command: " + str(command))
    
    result = subprocess.check_output(command)
    log.debug("(get_book_title) ffprobe result: " + result.decode("utf-8").replace("\n", ""))

    return result.decode("utf-8").replace("\n", "")

def get_existing_book_titles() -> list:
    existing_book_titles = []
    existing_book_title_paths = list(Path(config["output"]["path"] + "/").rglob("*.[mM]4[bB]"))
    log.debug("(get_existing_book_titles) existing_book_titles: " + str(existing_book_titles))
    for file in existing_book_title_paths:
        existing_book_titles.append(get_book_title(str(file)))

    log.debug("(get_existing_book_titles) existing_book_titles: " + str(existing_book_titles))
    return existing_book_titles

def convert(file):
    log.info("(convert) Preparing to convert " + file)

    input_file = config["input"]["path"] + "/" + file
    output_file = config["output"]["path"] + "/" + os.path.splitext(file)[0] + config["output"]["extension"]

    log.debug("(convert) Input: " + input_file)
    log.debug("(convert) Output: " + output_file)

    command = [config["ffmpeg"]["path"], "-activation_bytes", secret["activation_bytes"], "-i", input_file, "-c", "copy", output_file]
    command[1:1] = config["ffmpeg"]["additional_args"] # Splice additional args in
    command_str = ' '.join(str(i) for i in command)

    log.debug("(convert) Conversion command args: " + str(command))
    log.debug("(convert) Conversion command string: " + command_str)

    if not bool(config["ffmpeg"]["run"]):
        log.warning("(convert) Configuration 'ffmpeg.run: false' has blocked conversion. Set 'ffmpeg.run: true' to convert input files.")
        return

    log.debug("(convert) Configuration 'output.overwrite: true'. Set 'output.overwrite: false' if overwriting is not desired.")
    ffmpeg_call(input_file, command)

if __name__ == "__main__":
    app_setup()
    log.info("(__main__) Setup successful.")
    log.debug("(__main__) Loaded config: " + str(config))

    files = os.listdir(config["input"]["path"])
    files = [f for f in files if f.endswith(config["input"]["extension"])]
    log.debug("(__main__) Found files: " + str(files))

    log.info("(__main__) Found " + str(len(files)) + " book(s) to convert.")

    if len(files) == 0:
        log.debug("(__main__) Exiting with no work to do.")
        sys_exit()

    existing_books = get_existing_book_titles()

    log.info("(__main__) Found " + str(len(existing_books)) + " existing book(s).")

    for file in files:
        input_file_path = config["input"]["path"] + "/" + file
        title = get_book_title(input_file_path)
        if title in existing_books and not bool(config["output"]["overwrite"]):
            log.debug("(__main__) Book already exists: " + str(file))
            log.warning("(convert) Book with metadata `" + title + "` already exists; skipping conversion, but cleaning up. Note, set 'output.overwrite: true' to overwrite an existing book.")
            cleanup(input_file_path)
            break

        log.debug("(__main__) converting: " + str(file))
        convert(file)

