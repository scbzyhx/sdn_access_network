#! /bin/bash
SMAC="52:54:00:e9:9e:01"
TOS=0x38
DSTMAC=("52:54:00:e9:9e:02" "52:54:00:e9:9e:03")
OUTPUT=("h2.pcap" "h3.pcap")
IPS=("114.212.87.102:192.168.111.52" "114.212.87.102:192.168.111.53" )
SIZE=${#IPS[@]}
REWRITE=tcprewrite
ORIGINAL_FILE=stoc.pcap

for ((i=0; i<${SIZE};i++)); do
    echo ${IPS[i]}
    echo ${DSTMAC[i]}
    `$REWRITE -C -D ${IPS[i]} --tos=${TOS} --enet-dmac=${DSTMAC[i]} --enet-smac=${SMAC} -i $ORIGINAL_FILE -o ${OUTPUT[i]}`
done
#tcprewrite -D "114.212.87.102:192.168.111.52" --ttl=0x38 --enet-dmac="52:54:00:e9:9e:02" --enet-smac="52:54:00:e9:9e:01" -i ~/stoc.pcap -o h2.pcap
