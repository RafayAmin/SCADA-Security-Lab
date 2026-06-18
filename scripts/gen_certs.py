import subprocess
import os

def run_cmd(cmd):
    print(f"[CERTS] Running: {cmd}")
    try:
        subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL)
    except subprocess.CalledProcessError as e:
        print(f"[CERTS] Command failed: {e}")
        raise

os.makedirs("/etc/ipsec.d/cacerts", exist_ok=True)
os.makedirs("/etc/ipsec.d/certs", exist_ok=True)
os.makedirs("/etc/ipsec.d/private", exist_ok=True)

run_cmd("pki --gen --type rsa --size 2048 > /etc/ipsec.d/private/ca-key.der")
run_cmd("pki --self --ca --lifetime 3650 --in /etc/ipsec.d/private/ca-key.der --dn 'CN=SCADA Lab CA, O=SCADA-Security-Lab' > /etc/ipsec.d/cacerts/ca-cert.der")

run_cmd("pki --gen --type rsa --size 2048 > /etc/ipsec.d/private/server-key.der")
run_cmd("pki --pub --in /etc/ipsec.d/private/server-key.der --type rsa > /etc/ipsec.d/private/server-pub.der")
run_cmd("pki --issue --lifetime 3650 --cacert /etc/ipsec.d/cacerts/ca-cert.der --cakey /etc/ipsec.d/private/ca-key.der --dn 'CN=172.20.0.30, O=SCADA-Security-Lab' --san 172.20.0.30 --san strongswan --flag serverAuth --in /etc/ipsec.d/private/server-pub.der > /etc/ipsec.d/certs/server-cert.der")

run_cmd("openssl rsa -inform DER -in /etc/ipsec.d/private/ca-key.der -outform PEM -out /etc/ipsec.d/private/ca-key.pem")
run_cmd("openssl rsa -inform DER -in /etc/ipsec.d/private/server-key.der -outform PEM -out /etc/ipsec.d/private/server-key.pem")
run_cmd("openssl x509 -inform DER -in /etc/ipsec.d/cacerts/ca-cert.der -outform PEM -out /etc/ipsec.d/cacerts/ca-cert.pem")
run_cmd("openssl x509 -inform DER -in /etc/ipsec.d/certs/server-cert.der -outform PEM -out /etc/ipsec.d/certs/server-cert.pem")

print("[CERTS] Certificate generation complete.")
