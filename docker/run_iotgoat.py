import urllib.request
import gzip
import shutil
import subprocess
import os
import time

QCOW2_FILE = "/opt/IoTGoat-x86.qcow2"
IMG_GZ_FILE = "/opt/IoTGoat-x86.img.gz"
IMG_FILE = "/opt/IoTGoat-x86.img"
IMG_URL = "https://github.com/OWASP/IoTGoat/releases/latest/download/IoTGoat-x86.img.gz"

if not os.path.exists(QCOW2_FILE):
    if not os.path.exists(IMG_GZ_FILE):
        print(f"[IoTGoat] Downloading {IMG_URL}...")
        urllib.request.urlretrieve(IMG_URL, IMG_GZ_FILE)

    print("[IoTGoat] Extracting image...")
    with gzip.open(IMG_GZ_FILE, 'rb') as f_in:
        with open(IMG_FILE, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

    print("[IoTGoat] Converting to qcow2...")
    subprocess.run(["qemu-img", "convert", "-f", "raw", "-O", "qcow2", IMG_FILE, QCOW2_FILE], check=True)
    os.remove(IMG_FILE)

print("[IoTGoat] Starting QEMU VM...")
time.sleep(1)

subprocess.run([
    "qemu-system-x86_64",
    "-hda", QCOW2_FILE,
    "-m", "2048",
    "-smp", "2",
    "-netdev", "user,id=mynet0,hostfwd=tcp::2222-:22,hostfwd=tcp::8080-:80,hostfwd=tcp::4443-:443",
    "-device", "e1000,netdev=mynet0",
    "-nographic",
    "-display", "none"
])
