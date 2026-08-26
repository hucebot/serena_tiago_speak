# Tiago Speaks

ROS 2 node that listens for robot actions and speaks the matching phrase with [Festival](http://www.cstr.ed.ac.uk/projects/festival/) TTS.

## Prerequisites

- Docker
- ROS 2 Humble (inside the provided image)
- Audio output on the host (Festival uses ALSA via `/dev/snd`)

## Build the Docker image

From the repository root:

```bash
docker build -t tiago_speaks:latest -f docker/dockerfile .
```

The image installs `festival` and several voices (see table below).

## Start the container

From the repository root:

```bash
bash docker/run_container.sh
```

This starts (or attaches to) a container named `tiago_speaks` with host networking, Cyclone DDS config from `configs/cyclonedds.xml`, and access to sound devices.

## Launch the Tiago speaks node

Inside the container, from the repository root:

```bash
bash run_module_tiago_speaks.sh
```

Or equivalently:

```bash
python3 tiago_speaks.py \
    --ros-args \
    -p speak_flag:=1 \
    -p action_topic:="/orchestrator/ui/current_task" \
    -p voice_type:="kal_diphone" \
    -p phrases_file:="$(pwd)/assets/phrases.txt"
```

### Parameters

| Parameter       | Default                 | Description                                      |
|-----------------|-------------------------|--------------------------------------------------|
| `speak_flag`    | `1`                     | Set to `1` to enable speech, `0` to mute         |
| `action_topic`  | `/orchestrator/ui/current_task` | `std_msgs/String` topic with the current action |
| `voice_type`    | `kal_diphone`           | Festival voice name (without the `voice_` prefix)|
| `phrases_file`  | `phrases.txt`           | Path to `action,phrase` mapping file             |

### Available voices

| Package             | `voice_type`  | Description                |
|---------------------|---------------|----------------------------|
| `festvox-kallpc16k` | `kal_diphone` | American English male      |
| `festvox-kdlpc16k`  | `ked_diphone` | American English male      |
| `festvox-rablpc16k` | `rab_diphone` | British English male       |
| `festvox-don`       | `don_diphone` | British English male       |
| `festvox-ellpc11k`  | `el_diphone`  | Castilian Spanish male     |

Example: `-p voice_type:="el_diphone"`.

List installed voices inside the container: `festival -b '(print (voice.list))'`.

Phrases live in `assets/phrases.txt` (`action_name, spoken phrase`).

## Test with a fake action

In another terminal (host or `docker exec` into `tiago_speaks`):

```bash
bash tiago_speaks_ros2_topic.sh
```

Or publish manually:

```bash
ros2 topic pub /orchestrator/ui/current_task std_msgs/msg/String "{data: 'open_fridge'}" -1
```

The node should log the phrase and Festival should speak it.

## Host install (optional)

If you run outside Docker:

```bash
bash install_festival_on_machine.sh
```
