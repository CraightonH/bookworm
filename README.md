# Bookworm
[![Build](https://github.com/CraightonH/bookworm/actions/workflows/build_ci.yml/badge.svg)](https://github.com/CraightonH/bookworm/actions/workflows/build_ci.yml)

## Content
* [Intro](#intro)
* [Docker](#docker)
* [Activation Bytes](#activation-bytes)
* [Which Version?](#which-version-should-i-use)
* [Python Config](#python-config)
* [Python Secrets](#python-secrets)
* [Shell Config](#shell-config)
* [Shell Secrets](#shell-secrets)
* [Notes](#notes)

## Intro
Bookworm aims to ease the Audible audiobook archiving process by simplifying a user's workflow. Once running, bookworm will convert your `.aax` files into `.m4b` files allowing almost any player to play them, including [Plex Media Server](https://www.plex.tv/).

## Docker
You can build your own containers with the included `Dockerfile`. I don't maintain a `latest` tag because I always pin versions anyways. Tags will match available releases in this repo.
```
docker pull craighton/bookworm:[tag]
```

## Activation Bytes
### Background
In order for Bookworm to convert your file, you need to supply your `activation_bytes`. As far as I'm aware, this is an account-wide secret valid for any book downloaded from your Audible account. The purpose is to prevent Person A from downloading an audiobook from their account and sharing the downloaded file with Person B. Although third-party players like iTunes allow you to listen to downloaded Audible audiobooks, behind the scenes they will login to your Audible account to retrieve your `activation_bytes` that then allow them to play the downloaded audiobook.

### Retrieving
An easy way to retrieve this value is to run the following in your terminal (note: this is dependent on a 3rd party who may choose to disable their API at any time):
```
checksum=$(ffprobe /path/to/audiobook 2>&1 | grep checksum | awk '{print $NF}')

curl -s https://aaxactivationserviceapi.azurewebsites.net/api/v1/activation/${checksum}
```

## Which Version Should I Use?
Both versions work equally well when configured properly.

The `shell` version (releases without a `-python` suffix) is incompatible with network shares because it uses `inotify` to receive file events from the linux kernel which are not triggered on `nfs` shared folders. Thus, bookworm would hang forever never doing any work.

Assuming the input directory would allow for either version to run, then the determining factor would be ease of scheduling the `python` version to run at some interval as it does not currently keep the main thread alive after performing work. If running in [kubernetes](https://kubernetes.io/), it is simple enough to run bookworm in a `CronJob`. See how I do it in [my home k3s cluster](https://github.com/CraightonH/cluster-k3s/tree/main/cluster/apps/media/bookworm).

## Python Config
The following key/value pairs should be located in one or more `yaml` files mounted in `/app/config`. Bookworm will load all `yaml` files in that directory. The container does contain a default file which should be sufficient for most cases. The directory in which config is found may also be changed with the `CONFIG_DIRECTORY_NAME` environment variable.
| Name            | Description | Default |
|---              |---          |---      |
| `input.path`      | path to directory that input files will be found; see [Input Path Notes](#input-path) for more details | `/app/watch` |
| `input.extension` | file extension of input files; will ignore files not matching this value | `.aax` |
| `input.cleanup`   | switch to control whether input files should be deleted after successful conversion | `true` |
| `output.path`      | path to directory that converted files will be placed | `/app/output` |
| `output.extension` | file extension of output files | `.m4b` |
| `output.overwrite`   | switch to control whether converted files should overwrite an existing file with the same name in the output location | `false` |
| `ffmpeg.run`      | switch to control whether call to ffmpeg is allowed; useful to set `false` for debugging | `true` |
| `ffmpeg.path` | path to `ffmpeg`; if `ffmpeg` is in `PATH`, keep default value | `ffmpeg` |
| `ffmpeg.additional_args` | list of extra args added to ffmpeg call; see [ffmpeg Additional Args](#ffmpeg-additional-args) for more details | `['-hide_banner', '-loglevel', 'error', '-nostats', '-y']` |
| `ffprobe.path` | path to `ffprobe`; if `ffprobe` is in `PATH`, keep default value | `ffprobe` |
| `ffprobe.additional_args` | list of extra args added to ffprobe call; these grab a specific value, so best not to change the default | `['-show_entries', 'format_tags=title', '-of', 'compact=p=0', '-v', '"0"']` |
| `logging.level`      | controls logging verbosity; can be one of `info`, `warning`, `error`, `debug` | `info` |
| `logging.format` | controls desired logging format | `'%(asctime)s - %(levelname)s - [%(name)s] %(message)s'` |

## Python Secrets
The following key/value pairs should be located in one or more `yaml` files mounted in `/app/secrets`. Bookworm will load all `yaml` files in that directory. The container ***does not*** contain a default secrets file and will error with a helpful message if this is not set. The directory in which secrets are found may also be changed with the `SECRETS_DIRECTORY_NAME` environment variable.
| Name            | Description | Default |
|---              |---          |---      |
| `activation_bytes`      | string to open your audible files | none |

## Shell Config
Instead of `yaml` files, the shell releases use `env` variables. The script will attempt to load the following config from the `env` first, and if not found, will export variables from `defaults.env`.
| Name            | Description | Default |
|---              |---          |---      |
| `WATCH_DIR`      | path to directory that input files will be found | `~/.watch` |
| `OUTPUT_DIR`      | path to directory that converted files will be placed | `~/.output` |

## Shell Secrets
Instead of `yaml` files, the shell releases use `env` variables. The script will attempt to load the following secrets from the `env` first, and if not found, will export variables from `secrets.env`. The container ***does not*** contain a default secrets file and will error if this is not set.
| Name            | Description | Default |
|---              |---          |---      |
| `ACTIVATION_BYTES`      | string to open your audible files | none |

## Notes
### Input Path
If your `input.path` is an `nfs` shared folder, you must use the `python` releases of bookworm. The `shell` versions leverage `inotify` for kernel events which `nfs` does not broadcast. However, if using local storage, the `shell` versions will be slightly faster given that they use `inotify` and may be more convenient as they don't require scheduling bookworm on an interval.

### ffmpeg Additional Args
The additional args will be added to the command between `ffmpeg` and `-activation_bytes`. Some options will not work where these are placed. Following is an example command with default values:
```
ffmpeg -hide_banner -loglevel error -nostats -y -activation_bytes <activation_bytes> -i <input.path> -c copy <output.path>
```