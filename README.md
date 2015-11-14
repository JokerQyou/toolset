# toolset
Personal toolset, something to make life easier.

## tools

### `router/netwatchdog.sh`

Deal with strange WAN connection issues. My router cannot connect to the Internet once per hour. I did not find the reason.

So I put this script in my router and set a cron job to run it every minute. It will ping `baidu.com`, and if the network is ok, it quits; otherwise it would restart network service after 5 ping failures.

# License

BSD 2-clause. Use at your own risk.