#!/bin/bash
# Launch the Tiago speaks ROS 2 node (Festival TTS on /orchestrator/ui/current_task).
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

python3 "${SCRIPT_DIR}/tiago_speaks.py" \
    --ros-args \
    -p speak_flag:=1 \
    -p action_topic:="/orchestrator/ui/current_task" \
    -p voice_type:="rab_diphone" \
    -p phrases_file:="${SCRIPT_DIR}/assets/phrases.txt"