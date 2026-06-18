#!/usr/bin/env bash
# Generate CA and server certificates for strongSwan
# TODO: Add certificate revocation support later
set -e

mkdir -p /etc/ipsec.d/cacerts /etc/ipsec.d/certs /etc/ipsec.d/private

pki --gen --type rsa --size 2048 > /etc/ipsec.d/private/ca-key.der

pki --self --ca --lifetime 3650 --in /etc/ipsec.d/private/ca-key.der \
    --dn "CN=SCADA Lab CA, O=SCADA-Security-Lab" \
    > /etc/ipsec.d/cacerts/ca-cert.der

pki --gen --type rsa --size 2048 > /etc/ipsec.d/private/server-key.der

pki --pub --in /etc/ipsec.d/private/server-key.der --type rsa \
    > /etc/ipsec.d/private/server-pub.der

pki --issue --lifetime 3650 \
    --cacert /etc/ipsec.d/cacerts/ca-cert.der \
    --cakey /etc/ipsec.d/private/ca-key.der \
    --dn "CN=172.20.0.30, O=SCADA-Security-Lab" \
    --san 172.20.0.30 --san strongswan \
    --flag serverAuth \
    --in /etc/ipsec.d/private/server-pub.der \
    > /etc/ipsec.d/certs/server-cert.der

openssl rsa -inform DER -in /etc/ipsec.d/private/ca-key.der -outform PEM \
    -out /etc/ipsec.d/private/ca-key.pem

openssl rsa -inform DER -in /etc/ipsec.d/private/server-key.der -outform PEM \
    -out /etc/ipsec.d/private/server-key.pem

openssl x509 -inform DER -in /etc/ipsec.d/cacerts/ca-cert.der -outform PEM \
    -out /etc/ipsec.d/cacerts/ca-cert.pem

openssl x509 -inform DER -in /etc/ipsec.d/certs/server-cert.der -outform PEM \
    -out /etc/ipsec.d/certs/server-cert.pem

rm -f /etc/ipsec.d/private/ca-key.der /etc/ipsec.d/private/server-key.der \
      /etc/ipsec.d/private/server-pub.der /etc/ipsec.d/cacerts/ca-cert.der \
      /etc/ipsec.d/certs/server-cert.der
