#!/bin/sh
# deploy/workbench-firewall.sh
# Block the now-workbench Docker network from private ranges, other containers and the host.
# Author: Pierre Grothe
# Date: 2026-11-06
#
# The workbench still reaches the internet (Claude API, ServiceNow, Cloudflare). Run as root
# after Docker starts (see workbench-firewall.service). Idempotent: rules are added once.
set -eu

BRIDGE="br-workbench"

add_rule() {
    if ! iptables -C DOCKER-USER -i "$BRIDGE" -d "$1" -j DROP 2>/dev/null; then
        iptables -I DOCKER-USER -i "$BRIDGE" -d "$1" -j DROP
    fi
}

for net in 10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 169.254.0.0/16 100.64.0.0/10; do
    add_rule "$net"
done
# Replies to connections the workbench opened must still come back.
if ! iptables -C DOCKER-USER -i "$BRIDGE" -m conntrack --ctstate ESTABLISHED,RELATED -j RETURN 2>/dev/null; then
    iptables -I DOCKER-USER -i "$BRIDGE" -m conntrack --ctstate ESTABLISHED,RELATED -j RETURN
fi
# Traffic addressed to the host itself (its LAN IP, the Docker gateways) goes through INPUT,
# not DOCKER-USER: the workbench needs nothing from the host, so drop all of it.
if ! iptables -C INPUT -i "$BRIDGE" -j DROP 2>/dev/null; then
    iptables -I INPUT -i "$BRIDGE" -j DROP
fi
echo "workbench firewall rules in place on $BRIDGE"
