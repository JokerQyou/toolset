#!/bin/sh
# Original author: http://jamesqi.com/%E5%8D%9A%E5%AE%A2/OpenWRT%E8%B7%AF%E7%94%B1%E5%99%A8%E4%B8%AD%E7%9B%91%E6%8E%A7%E7%BD%91%E7%BB%9C%E6%9C%8D%E5%8A%A1%E5%B9%B6%E9%87%8D%E5%90%AF%E7%9A%84%E8%84%9A%E6%9C%AC
DATE=`date +%Y-%m-%d-%H:%M:%S`
tries=0
sleepinterval=5
timeout=2

echo netwatchdog start
while [[ $tries -lt 5 ]]
do
    if /bin/ping -c 1 -W $timeout baidu.com >/dev/null
    then
        echo network ok, quit
        exit 0
    fi
    tries=$((tries+1))
    sleep $sleepinterval
done

echo $DATE >> netwatchdog.log
/etc/init.d/network restart
