#!/bin/sh
# Only allow Modbus on port 502 from authorized containers:
#   172.20.0.11 = HMI
#   172.20.0.12 = anomaly-detector (future)
# Note: Had to add the ESTABLISHED,RELATED rule first or existing connections would drop
iptables -A INPUT -p tcp --dport 502 -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT -p tcp --dport 502 -s 172.20.0.11 -j ACCEPT
iptables -A INPUT -p tcp --dport 502 -s 172.20.0.12 -j ACCEPT
iptables -A INPUT -p tcp --dport 502 -j DROP

exec python plc.py
