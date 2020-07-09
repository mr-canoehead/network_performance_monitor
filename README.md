<H1>Network Performance Monitor</H1>
The Network Performance Monitor is a portable tool for diagnosing performance issues on home networks. It can be deployed without making configuration changes to the network being monitored.
The system tests several aspects of network performance including:

- Internet speed
- Internet connectivity (ping)
- Domain Name lookups
- Local network speeds (particularly useful for testing 2.4GHz and 5GHz wireless networks)

The system includes a Bandwidth Monitor feature which measures Internet bandwidth usage throughout the day.

The Network Performance Monitor generates a daily PDF report containing graphs of the various test results, including indicators for Internet outages. The Bandwidth Monitor measurements are also plotted on a graph to show Internet usage patterns.

[Click here for a sample of the daily report produced by the system.](https://mr-canoehead.github.io/f216f253_20200326_netperf.pdf)

If you'd like to build a Network Performance Monitor, follow the [setup and installation instructions in the Wiki](https://github.com/mr-canoehead/network_performance_monitor/wiki)

The following diagram illustrates how the system is connected to the network being monitored.

Note: the Network Performance Monitor is not a router, WiFi access point, or wireless bridge. The wireless network interfaces serve only as targets for iperf3 performance tests.

<p align="center">
<img src="https://user-images.githubusercontent.com/10369989/78664037-bb532b80-78c2-11ea-8b8b-a71b8eff029f.png" width="80%">
</p>

## Credits
[Phil Reese](https://github.com/preese)
  - initiated the Python 3 migration and did the heavy lifting on this effort.

[Chris Tasich](https://github.com/christasich)
 - suggested several features and assisted with testing them, including:
    * Ookla Speedtest CLI integration for more accurate speed test results on faster ISP connections
    * speed test server selection
    * configuration option for the web server port

[Bryan Montford](https://github.com/GrfxGawd)
  - suggested the Data Usage Quota feature to limit Internet data usage for users with metered Internet service.

