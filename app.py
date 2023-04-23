import os, yaml, logging, subprocess
from sys import exit as sys_exit

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

def cleanup(path):
    if bool(config["input"]["cleanup"]):
        os.remove(path)
        log.info("(cleanup) Cleaned up " + path)
    else:
        log.warning("(cleanup) Configuration 'input.cleanup: false' blocked cleanup. Set 'input.cleanup: true' to cleanup input files.")

def ffmpeg_call(input_file, command):
    log.info("(ffmpeg_call) Converting " + input_file)
    subprocess.check_output(command, universal_newlines=True)
    # TODO: Do a real success check, ie. is output within ~10% of original's file size or use ffmpeg to read streams?
    log.info("(ffmpeg_call) Successfully converted")
    cleanup(input_file)

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

    if bool(config["ffmpeg"]["run"]):
        if not os.path.isfile(output_file):
            ffmpeg_call(input_file, command)
        else:
            if bool(config["output"]["overwrite"]):
                log.debug("(convert) Configuration 'output.overwrite: true'. Set 'output.overwrite: false' if overwriting is not desired.")
                ffmpeg_call(input_file, command)
            else:
                log.warning("(convert) Detected converted file, skipping conversion. Note, set 'output.overwrite: true' to overwrite previously converted files.")
    else:
        log.warning("(convert) Configuration 'ffmpeg.run: false' has blocked conversion. Set 'ffmpeg.run: true' to convert input files.")

if __name__ == "__main__":
    app_setup()
    log.info("(__main__) Setup successful.")
    log.debug("(__main__) Loaded config: " + str(config))

    files = os.listdir(config["input"]["path"])
    files = [f for f in files if f.endswith(config["input"]["extension"])]
    log.debug("(__main__) Found files: " + str(files))

    log.info("(__main__) Found " + str(len(files)) + " file(s) to convert.")

    for file in files:
        convert(file)
