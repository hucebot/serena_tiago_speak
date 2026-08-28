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

## Launch the laptop battery monitor

Publishes the host laptop battery as `sensor_msgs/msg/BatteryState` on `/laptop_battery` (via `python3-psutil`). Run on the machine whose battery you want to report—typically the host, not inside the robot container unless that container has access to laptop power data.

Inside the container (image includes `python3-psutil`), from the repository root:

```bash
python3 laptop_battery_monitor.py
```

Optional flags:

```bash
python3 laptop_battery_monitor.py --topic_name laptop_battery --publish_interval 5.0
```

| Option               | Default           | Description                                      |
|----------------------|-------------------|--------------------------------------------------|
| `--topic_name`       | `laptop_battery`  | `BatteryState` topic name                        |
| `--publish_interval` | `5.0`             | Publish interval in seconds                      |

Verify:

```bash
ros2 topic echo /laptop_battery
```

To drive `battery_monitor.py` from the laptop battery, set in `config.ini`:

```ini
battery_source=power_status
power_status_topic=/laptop_battery
```

## Launch the battery monitoring node

Inside the container, from the repository root (so sound paths in `config.ini` resolve):

```bash
python3 battery_monitor.py
```

The node loads `config.ini` next to the script. It announces battery level changes (10% boundaries and 99%) with optional WAV playback and Festival TTS.

### Battery sources

Both topics are subscribed; only the active source updates the level. Switch with `battery_source` in `config.ini`:

| `battery_source` | Topic (default)           | Message type              |
|------------------|---------------------------|---------------------------|
| `battery_level`  | `/power/battery_level`    | `std_msgs/msg/Int32` (0–100 %) |
| `power_status`   | `/power_status`           | `sensor_msgs/msg/BatteryState` (`percentage`; set `power_status_topic=/laptop_battery` for the laptop monitor) |

### Config (`config.ini`)

| Key                     | Default                     | Description                                      |
|-------------------------|-----------------------------|--------------------------------------------------|
| `battery_source`        | `battery_level`             | Active source: `battery_level` or `power_status` |
| `battery_level_topic`   | `/power/battery_level`      | Int32 percentage topic                           |
| `power_status_topic`    | `/power_status`             | BatteryState topic                               |
| `read_frequency`        | `0.2`                       | How often to evaluate level (Hz)                 |
| `can_speak`             | `True`                      | Enable Festival TTS                              |
| `can_play_sound`        | `True`                      | Enable WAV alerts via `aplay`                    |
| `sentence_level`        | …                           | Spoken prefix for mid/low levels                 |
| `sentence_full`         | …                           | Spoken when nearly full (≥ 99%)                  |
| `sentence_low`          | …                           | Spoken when low (≤ 50%)                          |
| `voice_type`            | `kal_diphone`               | Festival voice (same as Tiago speaks)            |
| `sound_full`            | `assets/full_charge.wav`    | WAV for full charge                              |
| `sound_medium`          | `assets/battery_level.wav`  | WAV for mid levels                               |
| `sound_low`             | `assets/urgent_charge2.wav` | WAV for low battery                              |

Example: set `battery_source=power_status` and `power_status_topic=/laptop_battery` to use the laptop battery monitor instead of the robot `/power_status` topic.

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
