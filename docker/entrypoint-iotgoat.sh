#!/usr/bin/env bash
set -e

QCOW2_FILE="/opt/IoTGoat-x86.qcow2"
IMG_GZ_FILE="/opt/IoTGoat-x86.img.gz"
IMG_URL="https://github.com/OWASP/IoTGoat/releases/latest/download/IoTGoat-x86.img.gz"

if [ -f "$QCOW2_FILE" ]; then
    echo "Found existing qcow2 image. Using it."
else
    if [ -f "$IMG_GZ_FILE" ]; then
        echo "Found IoTGoat-x86.img.gz. Extracting and converting..."
    else
        echo "No image found. Downloading IoTGoat-x86.img.gz..."
        wget -O "$IMG_GZ_FILE" "$IMG_URL"
    fi

    gunzip -f "$IMG_GZ_FILE"
    qemu-img convert -f raw -O qcow2 /opt/IoTGoat-x86.img "$QCOW2_FILE"
    rm -f /opt/IoTGoat-x86.img
fi

exec qemu-system-x86_64 \
    -hda "$QCOW2_FILE" \
    -m 2048 \
    -smp 2 \
    -netdev user,id=mynet0,hostfwd=tcp::2222-:22,hostfwd=tcp::8080-:80,hostfwd=tcp::4443-:443 \
    -device e1000,netdev=mynet0 \
    -nographic \
    -display none
