#!/bin/sh -e
#
#AP install on Raspberry Pi 3

GREEN='\e[0;32m'
YELLOW='\e[0;33m'
NC='\e[;0m'

ETHERNET='eth0'
#for DHCP connection set STATICIP=''
STATICIP='193.11.188.11'
STATICMASK='193.11.188.1'

WLAN='wlan0'
MASK='10.0.0.'
DNS1='8.8.8.8'
DNS2='8.8.4.4'

APNAME='Pi3-AP'
APPASS='9hyV1Xe8'
APCHANNEL='6'


echo "Installing updates"
apt-get update && apt-get upgrade -y

echo "Change password"
passwd pi


printf "Installing network interfaces... "
cat > "/etc/network/interfaces" << END_OF_CONFIG
source-directory /etc/network/interfaces.d

auto lo
iface lo inet loopback

wpa-conf /etc/wpa_supplicant/wpa_supplicant.conf

allow-hotplug ${WLAN}
iface ${WLAN} inet static
address ${MASK}1
network ${MASK}0
netmask 255.255.255.0
broadcast 255.0.0.0

auto ${ETHERNET}
allow-hotplug ${ETHERNET}
END_OF_CONFIG

if [ -z ${STATICIP} ]; then
	echo "iface ${ETHERNET} inet manual" >> /etc/network/interfaces
else
	echo "iface ${ETHERNET} inet static" >> /etc/network/interfaces
	echo "address ${STATICIP}/24" >> /etc/network/interfaces
	echo "gateway ${STATICMASK}" >> /etc/network/interfaces
	echo "dns-nameservers ${DNS1} ${DNS2}" >> /etc/network/interfaces
fi
echo "${GREEN}Done${NC}"


apt-get install -y dnsmasq
printf "Installing dnsmasq... "
cat > "/etc/dnsmasq.conf" << END_OF_CONFIG
dhcp-reply-delay=2

#disables dnsmasq reading any other files like /etc/resolv.conf for nameservers
no-resolv

interface=${WLAN}
except-interface=${ETHERNET}

#DHCP range for clients
dhcp-range=${MASK}3,${MASK}20,12h

#DNS-addresses
server=${DNS1}
server=${DNS2}

log-facility=/var/log/dnsmasq.log
log-queries
END_OF_CONFIG
echo "${GREEN}Done${NC}"


printf "Installing sysctl... "
cat > "/etc/sysctl.conf" << END_OF_CONFIG
net.ipv4.ip_forward=1
net.ipv6.conf.all.forwarding=1
END_OF_CONFIG
echo "${GREEN}Done${NC}"


printf "Installing NAT... "
cat > "/etc/rc.local" << END_OF_CONFIG
#!/bin/sh -e

iptables -t nat -A POSTROUTING -o ${ETHERNET} -j MASQUERADE
iptables -A FORWARD -i ${ETHERNET} -o ${WLAN} -m state --state RELATED,ESTABLISHED -j ACCEPT
iptables -A FORWARD -i ${WLAN} -o ${ETHERNET} -j ACCEPT

exit 0
END_OF_CONFIG
echo "${GREEN}Done${NC}"


apt-get install -y hostapd
printf "Installing AP... "
cat > "/etc/default/hostapd" << END_OF_CONFIG
DAEMON_CONF="/etc/hostapd/hostapd.conf"
END_OF_CONFIG

cat > "/etc/hostapd/hostapd.conf" << END_OF_CONFIG
interface=${WLAN}
driver=nl80211
ssid=${APNAME}

#2.4GHz band
hw_mode=g
channel=${APCHANNEL}

#802.11n
ieee80211n=1
wmm_enabled=1

#40MHz channels with 20ns guard interval
ht_capab=[HT40][SHORT-GI-20][DSSS_CCK-40]

#accept all MACs
macaddr_acl=0

#WPA authentication
auth_algs=1

#require clients to know the network name
ignore_broadcast_ssid=0

#WPA2
wpa=2

#pre-shared key
wpa_key_mgmt=WPA-PSK
wpa_passphrase=${APPASS}

#AES, instead of TKIP
rsn_pairwise=CCMP
END_OF_CONFIG
echo "${GREEN}Done${NC}"

echo "${YELLOW}Rebooting...${NC}"

reboot