#!/bin/sh
iptables -A INPUT -p tcp --dport 502 -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT -p tcp --dport 502 -s 172.20.0.11 -j ACCEPT
iptables -A INPUT -p tcp --dport 502 -s 172.20.0.12 -j ACCEPT
iptables -A INPUT -p tcp --dport 502 -j DROP

exec python plc.py
