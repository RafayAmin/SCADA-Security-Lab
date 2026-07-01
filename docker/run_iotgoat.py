import gzip
import logging
import os
import shutil
import subprocess
import time
import urllib.request

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

QCOW2_FILE = "/opt/IoTGoat-x86.qcow2"
IMG_GZ_FILE = "/opt/IoTGoat-x86.img.gz"
IMG_FILE = "/opt/IoTGoat-x86.img"
IMG_URL = "https://github.com/OWASP/IoTGoat/releases/latest/download/IoTGoat-x86.img.gz"


def _download_and_prepare() -> None:
    if os.path.exists(QCOW2_FILE):
        return
    if not os.path.exists(IMG_GZ_FILE):
        logger.info("[IoTGoat] Downloading %s...", IMG_URL)
        urllib.request.urlretrieve(IMG_URL, IMG_GZ_FILE)
    logger.info("[IoTGoat] Extracting image...")
    with gzip.open(IMG_GZ_FILE, "rb") as f_in, open(IMG_FILE, "wb") as f_out:
        shutil.copyfileobj(f_in, f_out)
    logger.info("[IoTGoat] Converting to qcow2...")
    subprocess.run(
        ["qemu-img", "convert", "-f", "raw", "-O", "qcow2", IMG_FILE, QCOW2_FILE],
        check=True,
    )
    os.remove(IMG_FILE)


def main() -> None:
    _download_and_prepare()
    logger.info("[IoTGoat] Starting QEMU VM...")
    time.sleep(1)
    subprocess.run(
        [
            "qemu-system-x86_64",
            "-hda",
            QCOW2_FILE,
            "-m",
            "2048",
            "-smp",
            "2",
            "-netdev",
            "user,id=mynet0,hostfwd=tcp::2222-:22,hostfwd=tcp::8080-:80,hostfwd=tcp::4443-:443",
            "-device",
            "e1000,netdev=mynet0",
            "-nographic",
            "-display",
            "none",
        ]
    )


if __name__ == "__main__":
    main()
