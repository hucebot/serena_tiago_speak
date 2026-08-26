#!/bin/bash
IsRunning=`docker ps -f name=tiago_speaks | grep -c "tiago_speaks"`;
DIR=$(pwd)/
if [ $IsRunning -eq "0" ]; then
    docker rm -f tiago_speaks
    xhost +local:docker
    docker run \
        --name tiago_speaks \
        -it \
        --net host \
        --ipc host \
        --pid host \
        --privileged \
        -v /dev:/dev \
        -v /run/udev:/run/udev:ro \
        --device /dev/bus/usb \
        --device /dev/snd \
        --cap-add=SYS_PTRACE \
        --security-opt seccomp=unconfined \
        -v $DIR:$DIR \
        -v /home:/home \
        -v /mnt:/mnt \
        -v /tmp/.X11-unix:/tmp/.X11-unix \
        -v /tmp:/tmp \
        -e DISPLAY=${DISPLAY} \
        -e GIT_INDEX_FILE \
        -e ROS_DOMAIN_ID=2 \
        -v $(pwd)/configs/:/xml_configs \
        -e RMW_IMPLEMENTATION=rmw_cyclonedds_cpp \
        -e CYCLONEDDS_URI=/xml_configs/cyclonedds.xml \
        tiago_speaks:latest \
        bash -c "cd $DIR && bash"
else
    echo "Docker image is already running. Opening new terminal...";
    docker exec -ti tiago_speaks bash -c "cd $DIR && bash"
fi
