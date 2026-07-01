import logging
import os
import subprocess

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

CA_DIR = "/etc/ipsec.d/cacerts"
CERT_DIR = "/etc/ipsec.d/certs"
KEY_DIR = "/etc/ipsec.d/private"


def _run_cmd(cmd: str) -> None:
    logger.info("[CERTS] Running: %s", cmd)
    try:
        subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError:
        logger.error("[CERTS] Command failed: %s", cmd)
        raise


def main() -> None:
    os.makedirs(CA_DIR, exist_ok=True)
    os.makedirs(CERT_DIR, exist_ok=True)
    os.makedirs(KEY_DIR, exist_ok=True)

    _run_cmd(f"pki --gen --type rsa --size 2048 > {KEY_DIR}/ca-key.der")
    _run_cmd(
        f"pki --self --ca --lifetime 3650 --in {KEY_DIR}/ca-key.der --dn 'CN=SCADA Lab CA, O=SCADA-Security-Lab' > {CA_DIR}/ca-cert.der"  # noqa: E501
    )
    _run_cmd(f"pki --gen --type rsa --size 2048 > {KEY_DIR}/server-key.der")
    _run_cmd(f"pki --pub --in {KEY_DIR}/server-key.der --type rsa > {KEY_DIR}/server-pub.der")
    _run_cmd(
        f"pki --issue --lifetime 3650 --cacert {CA_DIR}/ca-cert.der --cakey {KEY_DIR}/ca-key.der --dn 'CN=172.20.0.30, O=SCADA-Security-Lab' --san 172.20.0.30 --san strongswan --flag serverAuth --in {KEY_DIR}/server-pub.der > {CERT_DIR}/server-cert.der"  # noqa: E501
    )
    _run_cmd(f"openssl rsa -inform DER -in {KEY_DIR}/ca-key.der -outform PEM -out {KEY_DIR}/ca-key.pem")
    _run_cmd(f"openssl rsa -inform DER -in {KEY_DIR}/server-key.der -outform PEM -out {KEY_DIR}/server-key.pem")
    _run_cmd(f"openssl x509 -inform DER -in {CA_DIR}/ca-cert.der -outform PEM -out {CA_DIR}/ca-cert.pem")
    _run_cmd(f"openssl x509 -inform DER -in {CERT_DIR}/server-cert.der -outform PEM -out {CERT_DIR}/server-cert.pem")
    logger.info("[CERTS] Certificate generation complete.")


if __name__ == "__main__":
    main()
