// This file is part of the Network Performance Monitor which is released under the GNU General Public License v3.0
// See the file LICENSE for full license details.

Chart.defaults.global.animation.duration = 0

namespace = '/dashboard';

var socket = io(namespace);

var netperfData = {
	settings: null,
	viewDate: "today",
	charts: [],
}

netperfData.charts.push("bandwidth");
netperfData.charts["bandwidth"] = {
	lastTimestamp: 0,
	canvasId: "bandwidthChart",
	chartObject : null
}

netperfData.charts.push("bandwidthDaily");
netperfData.charts["bandwidthDaily"] = {
	lastTimestamp: 0,
	canvasId: "bandwidthDailyChart",
	chartObject : null
}

netperfData.charts.push("speedtest");
netperfData.charts["speedtest"] = {
	lastTimestamp: 0,
	canvasId: "speedtestChart",
	chartObject: null
}

netperfData.charts.push("dns");
netperfData.charts["dns"] = {
	lastTimestamp: 0,
	canvasId: "dnsChart",
	chartObject: null
}

function sameDay(timestamp1,timestamp2){
	var date1 = new Date(timestamp1*1000);
	var date2 = new Date(timestamp2*1000);
	return (date1.getDate() == date2.getDate())
}

function fractional_hour(timestamp){
	var d = new Date(timestamp * 1000);
	d.setHours(0,0,0,0);
	var midnight = d.getTime() / 1000;
	timedelta = timestamp - midnight;
	return timedelta/3600;
}

function clock_ticks(value, index, values) {
	var ticktext;
	const clockTicks12hr = ["12am","1am","2am","3am","4am","5am","6am","7am","8am","9am","10am","11am",
				"12pm","1pm","2pm","3pm","4pm","5pm","6pm","7pm","8pm","9pm","10pm","11pm",
				"12am"];
	if (netperfData.settings.dashboard.clock_type_24hr == true){
		ticktext = value;
	}
	else{
		ticktext = clockTicks12hr[value];
	}
	return ticktext;
}

function showBandwidthChart(){
    var rx_Mbps = [];
    var tx_Mbps = [];
    var ticks = [];
    for (let step = 0; step < 60; step++) {
        ticks.push("");
    }
        var bandwidthChart = netperfData.charts["bandwidth"];
	var chartElement = document.getElementById(bandwidthChart.canvasId);
	chartElement.classList.add("loading");
        bandwidthChart.chartObject = new Chart (chartElement, {
                type: "line",
                //animation:false,
                options: {
                        responsive: true,
                        title: {
                        	display: true,
                        	text: 'Live bandwidth usage measurements',
				fontColor: '#000',
			},
			tooltips: {
				callbacks: {
					label: function(tooltipItem, data) {
						var label = data.datasets[tooltipItem.datasetIndex].label || '';
						if (label) {
							label += ': ';
						}
						label += Math.round(tooltipItem.yLabel * 100) / 100;
						return label;
					}
				}
        	},
                legend: {
                        display: true,
                        labels: {
                                fontColor: '#000000',
                                //fontSize: 20,
                                boxWidth: 20,
                        }
                },
                scales: {
                        yAxes: [{
                                        scaleLabel: {
                                                display: true,
                                                labelString: 'RX/TX Mbps'
                                        },
                                        ticks: {
                                                beginAtZero: true,
                                                //fontSize: 20
                                        }
                                }],
                                xAxes: [{
                                        scaleLabel: {
                                                display: true,
                                                labelString: 'Last 60 seconds of bandwidth measurements'
                                        },
                                }],
                        },

                },
                data: {
                        labels: ticks,
                        animation: false,
                        datasets: [{
                                label: "RX Mbps",
                                animation: false,
                                fill: false,
                                data: rx_Mbps,
                                radius: 1,
                                backgroundColor: "#0F1C94",
                                borderColor: "#0F1C94",
                                tension: 0,
                                borderWidth: 2
                        },
                        {
                                label: "TX Mbps",
                                animation: false,
                                fill: false,
                                data: tx_Mbps,
                                radius: 1,
                                        backgroundColor: "#009900",
                                borderColor: "#009900",
                                tension: 0,
                                borderWidth: 2
                        }]
                }
        });
}

function showSpeedtestChart() {
	var stChart = netperfData.charts["speedtest"];
	stChart.chartObject = new Chart(document.getElementById(stChart.canvasId), {
		type: 'scatter',
		options: {
			responsive: true,
			hoverMode: 'index',
			stacked: false,
			title: {
				display: true,
				text:'Speed test results',
				fontColor: '#000',
			},
			tooltips: {
				callbacks: {
					label: function(tooltipItem, data) {
						var label = data.datasets[tooltipItem.datasetIndex].label || '';
						if (label) {
							label += ': ';
						}
						label += Math.round(tooltipItem.yLabel * 100) / 100;
						return label;
                			}
            			}
        		},
			legend: {
				display: true,
				labels: {
					boxWidth: 15,
					boxHeight: 1
				},
			},
			scales: {
				xAxes: [{
					scaleLabel: {
						display: true,
						labelString: 'Time of day'
					},
					ticks: {
						stepSize: 1,
						min: 0,
						max: 24,
						callback: function(value, index, values) {
							return clock_ticks(value, index, values);
						}
					},
					gridLines: {
						//color: '#888',
						drawOnChartArea: true
					}
				}],
				yAxes: [{
 						ticks: {
							beginAtZero: true
						},
						scaleLabel: {
							display: true,
							labelString: 'Download/Upload speed (Mbps)'
						},
						type: "linear",
						display: true,
						position: "left",
						id: "speed",
					},
					{
						ticks: {
							beginAtZero: true,
							suggestedMin: 0,
							suggestedMax: 10
						},
						scaleLabel: {
							display: false
						},
						type: "linear",
						display: false,
						position: "left",
						id: "ispOutages"
					},
					{
 						ticks: {
							beginAtZero: true,
						},
						scaleLabel: {
							display: true,
							labelString: 'Latency (milliseconds)',
							fontColor: 'red'
						},
						type: "linear",
						display: true,
						position: "right",
						id: "latency",
						// grid line settings
						gridLines: {
							drawOnChartArea: false,
						},
					}],
                	},
		},
		data: {
			datasets: [{
				data: [],
				label: "Download Mbps",
				yAxisID: "speed",
				borderColor: 'blue',
				borderWidth: 2,
				pointRadius: 1,
				pointHoverRadius: 5,
				fill: false,
				tension: 0,
				showLine: true,
			},
			{
				data: [],
				label: "Upload Mbps",
				yAxisID: "speed",
				borderColor: 'green',
				borderDash: [10,5],
				borderWidth: 2,
				pointRadius: 1,
				pointHoverRadius: 5,
				fill: false,
				tension: 0,
				showLine: true

			},
			{
				data: [],
				label: "Latency (milliseconds)",
				yAxisID: "latency",
				borderColor: 'red',
				borderDash: [1],
				borderWidth: 1,
				pointRadius: 1,
				pointHoverRadius: 5,
				fill: false,
				tension: 0,
				showLine: true
			},
			{
				data: [],
				label: "ISP outage",
				usePointStyle: true,
				yAxisID: "ispOutages",
				borderColor: 'red',
				pointBackgroundColor: 'red',
				backgroundColor: 'red',
				showLine: false,
				pointRadius: 5,
				fill: false,
				pointHoverRadius: 5,
			}],
		}
	});
	document.getElementById(stChart.canvasId).classList.add("loading");
}

function showBandwidthDailyChart() {
	var bwDailyChart = netperfData.charts["bandwidthDaily"];
	bwDailyChart.chartObject = new Chart(document.getElementById(bwDailyChart.canvasId), {
		type: 'scatter',
		options: {
			responsive: true,
			hoverMode: 'index',
			stacked: false,
			title: {
				display: true,
				text:'Bandwidth usage measurements averaged over 10 minute intervals',
				fontColor: '#000',
			},
			tooltips: {
				callbacks: {
					label: function(tooltipItem, data) {
						var label = data.datasets[tooltipItem.datasetIndex].label || '';
						if (label) {
							label += ': ';
						}
						label += Math.round(tooltipItem.yLabel * 100) / 100;
						return label;
                			}
            			}
        		},
			legend: {
				display: true,
				labels: {
					boxWidth: 15,
					boxHeight: 1
				},
			},
			scales: {
				xAxes: [{
					scaleLabel: {
						display: true,
						labelString: 'Time of day'
					},
					ticks: {
						stepSize: 1,
						min: 0,
						max: 24,
						callback: function(value, index, values) {
							return clock_ticks(value, index, values);
						}
					},
					gridLines: {
						//color: '#888',
						drawOnChartArea: true
					}
				}],
				yAxes: [{
 						ticks: {
							beginAtZero: true
						},
						scaleLabel: {
							display: true,
							labelString: 'RX/TX speed (Mbps)'
						},
						type: "linear",
						display: true,
						position: "left",
						id: "speed",
					}],
                	},
		},
		data: {
			datasets: [{
				data: [],
				label: "RX Mbps",
				yAxisID: "speed",
				borderColor: 'blue',
				borderWidth: 2,
				pointRadius: 1,
				pointHoverRadius: 5,
				fill: false,
				tension: 0,
				showLine: true,
			},
			{
				data: [],
				label: "TX Mbps",
				yAxisID: "speed",
				borderColor: 'green',
				borderDash: [10,5],
				borderWidth: 2,
				pointRadius: 1,
				pointHoverRadius: 5,
				fill: false,
				tension: 0,
				showLine: true

			}],
		}
	});
	document.getElementById(bwDailyChart.canvasId).classList.add("loading");
}

function showDNSChart() {
	var dnsChart = netperfData.charts["dns"];
	dnsChart.chartObject = new Chart(document.getElementById(dnsChart.canvasId), {
		type: 'scatter',
		options: {
			tooltips: {
				callbacks: {
					label: function(tooltipItem, data) {
						var label = data.datasets[tooltipItem.datasetIndex].label || '';
						if (label) {
							label += ' (milliseconds): ';
						}
						label += Math.round(tooltipItem.yLabel * 100) / 100;
						return label;
					}
				}
			},
			legend: {
				display: true,
					labels: {
						boxWidth: 20,
						boxHeight: 2
					}
			},
			responsive: true,
			hoverMode: 'index',
			stacked: false,
			title:{
				display: true,
				text: 'Name resolution test results',
				fontColor: '#000',
			},
			scales: {
				xAxes: [{
					scaleLabel: {
						display: true,
						labelString: 'Time of day'
					},
					ticks: {
						stepSize: 1,
						min: 0,
						max: 24,
						callback: function(value, index, values) {
							return clock_ticks(value, index, values);
						}
					},
					gridLines: {
						//color: '#888',
						drawOnChartArea: true
					}
				}],
				yAxes: [{
 						ticks: {
							beginAtZero: true
						},
						scaleLabel: {
							display: true,
							labelString: 'Query time (ms)'
						},
						type: "linear",
						display: true,
						position: "left",
						id: "queryTimes",
					},
					{
 						ticks: {
							beginAtZero: true,
							stepSize: 1,
						},
						scaleLabel: {
							display: true,
							labelString: 'Query failures',
							fontColor: 'red'
						},
						type: "linear",
						display: true,
						position: "right",
						id: "queryFailures",
						// grid line settings
						gridLines: {
							drawOnChartArea: false,
						},
					}],
                	},

		},
		data: {
			datasets: [{
				data: [],
				label: "Internal queries",
				yAxisID: "queryTimes",
				borderColor: 'blue',
				borderWidth: 2,
				pointRadius: 1,
				pointHoverRadius: 5,
				fill: false,
				tension: 0,
				showLine: true
			},
			{
				data: [],
				label: "External queries",
				yAxisID: "queryTimes",
				borderColor: 'green',
				borderDash: [10,5],
				borderWidth: 2,
				pointRadius: 1,
				pointHoverRadius: 5,
				fill: false,
				tension: 0,
				showLine: true
			},
			{
				data: [],
				label: "Internal query failures",
				yAxisID: "queryFailures",
				borderColor: 'red',
				borderDash: [1],
				borderWidth: 1,
				pointRadius: 1,
				pointHoverRadius: 5,
				fill: false,
				tension: 0,
				showLine: true
			},{
				data: [],
				label: "External query failures",
				yAxisID: "queryFailures",
				borderColor: 'purple',
				borderDash: [1],
				borderWidth: 1,
				pointRadius: 1,
				pointHoverRadius: 5,
				fill: false,
				tension: 0,
				showLine: true

			}],
		},
	});
	document.getElementById(dnsChart.canvasId).classList.add("loading");
}

socket.on('speedtest_data', function(msg) {
	var rx_Mbps_values = [];
	var tx_Mbps_values = [];
	var latency_values = [];
	var timestamp;
	function get_speedtest_info(json){
		timestamp = json.timestamp;
		frac_hour = fractional_hour(timestamp);
		rx_Mbps = json.rx_Mbps;
		tx_Mbps = json.tx_Mbps;
		latency = json.ping;
		rx_Mbps_values.push({x: frac_hour, y: rx_Mbps})
		tx_Mbps_values.push({x: frac_hour, y: tx_Mbps})
		latency_values.push({x: frac_hour, y: latency})
	}
	msg.forEach(get_speedtest_info);
	var speedtestChart = netperfData.charts["speedtest"];
	var chartElement = document.getElementById(speedtestChart.canvasId);
	chartElement.classList.remove("loading");
	speedtestChart.lastTimestamp = timestamp;
	speedtestChart.chartObject.data.datasets[0].data = rx_Mbps_values;
	speedtestChart.chartObject.data.datasets[1].data = tx_Mbps_values;
	speedtestChart.chartObject.data.datasets[2].data = latency_values;
        speedtestChart.chartObject.update()
});

socket.on('speedtest', function(msg) {
	var speedtestChart = netperfData.charts["speedtest"];
	if (speedtestChart.chartObject != null){
		if (netperfData.viewDate != "today"){
			return
		}
		var frac_hour = fractional_hour(msg.timestamp);
		var rx_Mbps_point={x: frac_hour, y: msg.rx_Mbps};
		var tx_Mbps_point={x: frac_hour, y: msg.tx_Mbps};
		var latency_point={x: frac_hour, y: msg.ping};
		if (!sameDay(msg.timestamp, speedtestChart.lastTimestamp)){
			speedtestChart.chartObject.data.datasets[0].data = [];
			speedtestChart.chartObject.data.datasets[1].data = [];
			speedtestChart.chartObject.data.datasets[2].data = [];
			speedtestChart.chartObject.data.datasets[3].data = [];
		}
		speedtestChart.lastTimestamp = msg.timestamp;
		speedtestChart.chartObject.data.datasets[0].data.push(rx_Mbps_point);
		speedtestChart.chartObject.data.datasets[1].data.push(tx_Mbps_point);
		speedtestChart.chartObject.data.datasets[2].data.push(latency_point);
		speedtestChart.chartObject.update();
	}
});

socket.on('isp_outage_data', function(msg) {
	var outage_points = [];
	var timestamp,frac_hour;
	function get_outage_info(json){
		timestamp = json.timestamp;
		frac_hour = fractional_hour(timestamp);
		outage_points.push({x: frac_hour, y: 0.5});
	}
	msg.forEach(get_outage_info);
	var speedtestChart = netperfData.charts["speedtest"];
	speedtestChart.chartObject.data.datasets[3].data = outage_points;
        speedtestChart.chartObject.update()
});

socket.on('isp_outage', function(msg) {
	var speedtestChart = netperfData.charts["speedtest"];
	if (speedtestChart.chartObject != null){
		if (netperfData.viewDate != "today"){
			return;
		}
		if (!sameDay(speedtestChart.lastTimestamp,msg.timestamp)){
			speedtestChart.chartObject.data.datasets[0].data = [];
			speedtestChart.chartObject.data.datasets[1].data = [];
			speedtestChart.chartObject.data.datasets[2].data = [];
			speedtestChart.chartObject.data.datasets[3].data = [];
		}
		var frac_hour = fractional_hour(msg.timestamp);
		speedtestChart.lastTimestamp = msg.timestamp;
		speedtestChart.chartObject.data.datasets[3].data.push({x: frac_hour, y: 0.5});
		speedtestChart.chartObject.update();
	}
});

function createIperf3Chart(interfaceName){
	var subsection = document.createElement("div");
	subsection.setAttribute("id",interfaceName);
	var canvasId = interfaceName + 'Chart'
	canvasElement = document.createElement("canvas");
	canvasElement.setAttribute("id", canvasId);
	canvasElement.setAttribute("width",400);
	canvasElement.setAttribute("height",200);
	var iperf3_data = document.getElementById('iperf3');
	subsection.append(canvasElement);
	iperf3_data.append(subsection);
	netperfData.charts.push(interfaceName);
	netperfData.charts[interfaceName] = {type: 'iperf3', lastTimestamp: 0, canvasId: canvasElement.id, chartObject : undefined};
	netperfData.charts[interfaceName].chartObject = new Chart(document.getElementById(netperfData.charts[interfaceName].canvasId), {
		type: 'scatter',
		options: {
			responsive: true,
			hoverMode: 'index',
			stacked: false,
			title:{
				display: true,
				text: 'iperf3 test results for interface ' + interfaceName,
				fontColor: '#000',
			},
			tooltips: {
				callbacks: {
					label: function(tooltipItem, data) {
						var label = data.datasets[tooltipItem.datasetIndex].label || '';
						if (label) {
							label += ': ';
						}
						label += Math.round(tooltipItem.yLabel * 100) / 100;
						return label;
					}
				}
			},
			legend: {
				display: true,
					labels: {
						boxWidth: 20,
						//boxHeight: 2
					}
			},
			scales: {
				xAxes: [{
					scaleLabel: {
						display: true,
						labelString: 'Time of day'
					},
					ticks: {
						stepSize: 1,
						min: 0,
						max: 24,
						callback: function(value, index, values) {
							return clock_ticks(value, index, values);
						}
					},
					gridLines: {
						//color: '#888',
						drawOnChartArea: true
					}
				}],
				yAxes: [{
						scaleLabel: {
							display: true,
							labelString: 'Speed (Mbps)'
						},
						type: "linear",
						display: true,
						position: "left",
						id: "Mbps",
					gridLines: {
						//color: '#888',
						drawOnChartArea: true
					},

					},
					{
						scaleLabel: {
							display: true,
							labelString: 'Retransmits',
							fontColor: 'red'
						},
						type: "linear",
						display: true,
						position: "right",
						id: "Retransmits",
						// grid line settings
						gridLines: {
							drawOnChartArea: false,
						},
					}],
                	},

		},
		data: {
			datasets: [{
				data: [],
				label: "RX Mbps",
				yAxisID: "Mbps",
				borderColor: 'blue',
				borderWidth: 2,
				pointRadius: 1,
				pointHoverRadius: 5,
				fill: false,
				tension: 0,
				showLine: true
			},
			{
				data: [],
				label: "TX Mbps",
				yAxisID: "Mbps",
				borderColor: 'green',
				borderDash: [10,5],
				borderWidth: 2,
				pointRadius: 1,
				pointHoverRadius: 5,
				fill: false,
				tension: 0,
				showLine: true
			},
			{
				data: [],
				label: "Retransmits",
				yAxisID: "Retransmits",
				borderColor: 'red',
				borderDash: [1],
				borderWidth: 1,
				pointRadius: 1,
				pointHoverRadius: 5,
				fill: false,
				tension: 0,
				showLine: true
			}],
		},

	});

}

socket.on('iperf3_data', function(msg) {
	var interface_data = [];
	var chart;
	netperfData.charts.forEach(function(chartName){
		chart = netperfData.charts[chartName];
		if (chart.type == 'iperf3'){
			chart.chartObject.data.datasets[0].data = [];
			chart.chartObject.data.datasets[1].data = [];
			chart.chartObject.data.datasets[2].data = [];
		}
	});
	var iperf3DataAvailable = false;
	var rx_Mbps,tx_Mbps,retransmits,frac_hour,remote_host;
	msg.forEach(function(row) {
		iperf3DataAvailable = true;
		rx_Mbps = row.rx_Mbps;
		tx_Mbps = row.tx_Mbps;
		retransmits = row.retransmits;
		frac_hour = fractional_hour(row.timestamp);
		remote_host = row.remote_host;
		if (! netperfData.charts.includes(remote_host)){
			createIperf3Chart(remote_host);
		}
		netperfData.charts[remote_host].lastTimestamp = row.timestamp;
		netperfData.charts[remote_host].chartObject.data.datasets[0].data.push({x: frac_hour, y: row.rx_Mbps});
		netperfData.charts[remote_host].chartObject.data.datasets[1].data.push({x: frac_hour, y: row.tx_Mbps});
		netperfData.charts[remote_host].chartObject.data.datasets[2].data.push({x: frac_hour, y: row.retransmits});
	});
	netperfData.charts.forEach(function(chartName){
		if (netperfData.charts[chartName].type == 'iperf3'){
			netperfData.charts[chartName].chartObject.update();
		}
	});
	if (iperf3DataAvailable == true){
		var iperf3DataMessage = document.getElementById("iperf3DataMessage")
		if (iperf3DataMessage != null){
			iperf3DataMessage.parentNode.removeChild(iperf3DataMessage);
		}
	}
});

socket.on('iperf3', function(msg) {
	if (netperfData.viewDate != "today"){
		return;
	}
	var interface = msg.remote_host;
	var frac_hour = fractional_hour(msg.timestamp);
	var rx_Mbps_point = {x: frac_hour, y: msg.rx_Mbps};
	var tx_Mbps_point = {x: frac_hour, y: msg.tx_Mbps};
	var retransmits_point = {x: frac_hour, y: msg.retransmits};
	// create a new subsection + chart for the interface if it didn't exist during the initial page load - can happen
	// if the network is reconfigured and the page is loaded before the first iperf3 test has been run against the
	// new interface.
	if (! netperfData.charts.includes(interface)){
		createIperf3Chart(interface);
	}
	var iperf3Chart = netperfData.charts[interface];
	if (!sameDay(iperf3Chart.lastTimestamp,msg.timestamp)){
		iperf3Chart.chartObject.data.datasets[0].data = [];
		iperf3Chart.chartObject.data.datasets[1].data = [];
		iperf3Chart.chartObject.data.datasets[2].data = [];
	}
	iperf3Chart.lastTimestamp = msg.timestamp;
	iperf3Chart.chartObject.data.datasets[0].data.push(rx_Mbps_point);
        iperf3Chart.chartObject.data.datasets[1].data.push(tx_Mbps_point);
        iperf3Chart.chartObject.data.datasets[2].data.push(retransmits_point);
        iperf3Chart.chartObject.update();
	var iperf3DataMessage = document.getElementById("iperf3DataMessage")
	if (iperf3DataMessage != null){
		iperf3DataMessage.parentNode.removeChild(iperf3DataMessage);
	}
});

socket.on('dns_data', function(msg) {
	var internal_query_times = [];
	var external_query_times = [];
	var internal_query_failures = [];
	var external_query_failures = [];
	var timestamp, frac_hour;
	function get_dns_info(json){
		timestamp = json.timestamp;
		frac_hour = fractional_hour(timestamp);
		internal_query_times.push({x: frac_hour, y: json.internal_dns_query_time})
		internal_query_failures.push({x: frac_hour, y: json.internal_dns_failures})
		external_query_times.push({x: frac_hour, y: json.external_dns_query_time})
		external_query_failures.push({x: frac_hour, y: json.external_dns_failures})
	}
	msg.forEach(get_dns_info);
	var dnsChart = netperfData.charts["dns"];
	var chartElement = document.getElementById(dnsChart.canvasId);
	chartElement.classList.remove("loading");
	dnsChart.lastTimestamp = timestamp;
	dnsChart.chartObject.data.datasets[0].data = internal_query_times;
	dnsChart.chartObject.data.datasets[1].data = external_query_times;
	dnsChart.chartObject.data.datasets[2].data = internal_query_failures;
	dnsChart.chartObject.data.datasets[3].data = external_query_failures;
	dnsChart.chartObject.update()
});

socket.on('dns', function(msg) {
	var dnsChart = netperfData.charts["dns"];
	if (dnsChart.chartObject != null){
		if (netperfData.viewDate != "today"){
			return;
		}
		var frac_hour = fractional_hour(msg.timestamp);
		var internal_query_time_point={x: frac_hour, y: msg.internal_dns_query_time};
		var external_query_time_point={x: frac_hour, y: msg.external_dns_query_time};
		var internal_query_failures_point={x: frac_hour, y: msg.internal_dns_failures};
		var external_query_failures_point={x: frac_hour, y: msg.external_dns_failures};
		if (!sameDay(dnsChart.lastTimestamp,msg.timestamp)){
			dnsChart.chartObject.data.datasets[0].data = [];
			dnsChart.chartObject.data.datasets[1].data = [];
			dnsChart.chartObject.data.datasets[2].data = [];
			dnsChart.chartObject.data.datasets[3].data = [];
		}
		dnsChart.lastTimestamp = msg.timestamp;
		dnsChart.chartObject.data.datasets[0].data.push(internal_query_time_point);
		dnsChart.chartObject.data.datasets[1].data.push(external_query_time_point);
		dnsChart.chartObject.data.datasets[2].data.push(internal_query_failures_point);
		dnsChart.chartObject.data.datasets[3].data.push(external_query_failures_point);
	        dnsChart.chartObject.update()
	}
});


socket.on('bandwidth_data', function(msg) {
	var rx_Mbps_values = [];
	var tx_Mbps_values = [];
	function get_rx_tx_vals(json){
		rx_Mbps_values.push(json.rx_bps/1e6);
		tx_Mbps_values.push(json.tx_bps/1e6);
	}
	msg.forEach(get_rx_tx_vals);
	var chartElement = document.getElementById(netperfData.charts["bandwidth"].canvasId);
	chartElement.classList.remove("loading");
	netperfData.charts["bandwidth"].chartObject.data.datasets[0].data = rx_Mbps_values.reverse();
	netperfData.charts["bandwidth"].chartObject.data.datasets[1].data = tx_Mbps_values.reverse();
	netperfData.charts["bandwidth"].chartObject.update();
});

socket.on('bandwidth_usage', function(msg) {
	var rxChartPoints=[];
	var txChartPoints=[];
	var chartElement = document.getElementById(netperfData.charts["bandwidthDaily"].canvasId);

	msg.averaged_usage.rx.forEach(function (row) {
		rxChartPoints.push({x: row.fractional_hour, y: row.value});
	});

	msg.averaged_usage.tx.forEach(function (row) {
		txChartPoints.push({x: row.fractional_hour, y: row.value});
	});

	chartElement.classList.remove("loading");
	netperfData.charts["bandwidthDaily"].chartObject.data.datasets[0].data = rxChartPoints;
	netperfData.charts["bandwidthDaily"].chartObject.data.datasets[1].data = txChartPoints;
	netperfData.charts["bandwidthDaily"].chartObject.update();
});

socket.on('bandwidth', function(msg, cb) {
	var rx_Mbps = msg.rx_bps/1e6;
	var tx_Mbps = msg.tx_bps/1e6;
	var bandwidthChart = netperfData.charts["bandwidth"];
	if (bandwidthChart.chartObject != null){
		if (bandwidthChart.chartObject.data.datasets[0].data.length >= 60){
			bandwidthChart.chartObject.data.datasets[0].data.shift();
		}
		bandwidthChart.chartObject.data.datasets[0].data.push(rx_Mbps.toFixed(2));
		if (bandwidthChart.chartObject.data.datasets[1].data.length >= 60){
			bandwidthChart.chartObject.data.datasets[1].data.shift();
		}
		bandwidthChart.chartObject.data.datasets[1].data.push(tx_Mbps.toFixed(2));
		bandwidthChart.chartObject.update();
	}
	if (cb)
		cb();
});

function openInNewTab(url) {
  var win = window.open(url, '_blank');
  win.focus();
}

socket.on('report_list', function(msg){
	var reportFilesMessage = document.getElementById("reportFilesMessage");
	var reportFilesContainer = document.getElementById("reportFiles");
	if (msg.length > 0){
		reportFilesMessage.innerHTML = "The following reports files are available. Click on a report filename to view it:";
		reportFilesContainer.innerHTML = "";
		// sort list of files in descending order, this puts newest report files at the top
		msg.sort().reverse();
		function addReportLink(fileName){
			var br = document.createElement('br');
			var para = document.createElement('p');
			var link = document.createElement('a');
			var linkText = document.createTextNode(fileName);
			link.appendChild(linkText);
			//link.appendChild(para);
			link.href="javascript:void(0);";
			link.onclick = function() {
				var win = window.open("/reports/" + this.innerText, '_blank');
				win.focus();
			}
			//link.href = "/reports/" + fileName;
			reportFilesContainer.appendChild(link);
			reportFilesContainer.appendChild(br);
		}
		msg.forEach(addReportLink);
	}
	else{
		reportFilesMessage.innerHTML = "There are no report files available. To generate a report, refer to the page <a href=\"https://github.com/mr-canoehead/network_performance_monitor/wiki/Generate-daily-reports\">Generate daily reports</a> in the project Wiki.";
		reportFilesContainer.innerHTML = "";
	}
});

socket.on('settings', function(msg){
	netperfData.settings = msg.settings;
	showDNSChart();
	showSpeedtestChart();
	if (netperfData.settings.bandwidth_monitor.enabled == true){
		showBandwidthChart();
		showBandwidthDailyChart();
                socket.emit('get_bandwidth_data',{rows: 60});
	}
	else{
		var menuItem = document.getElementById("bwmonitorMenuItem");
		menuItem.style.display = "none";
	}
        socket.emit('get_speedtest_data');
	socket.emit('get_isp_outage_data');
        socket.emit('get_dns_data');
        socket.emit('get_iperf3_data');
	socket.emit('get_report_list');
});

socket.on('connect', function(msg){
	socket.emit('get_settings');
});

function openView(evt, viewName) {
  if (viewName == 'reporting'){
       socket.emit('get_report_list');
  }
  // Declare all variables
  var i, tabcontent, tablinks;

  // Get all elements with class="tabcontent" and hide them
  tabcontent = document.getElementsByClassName("tabcontent");
  for (i = 0; i < tabcontent.length; i++) {
    tabcontent[i].style.display = "none";
  }

  // Get all elements with class="tablinks" and remove the class "active"
  tablinks = document.getElementsByClassName("tablinks");
  for (i = 0; i < tablinks.length; i++) {
    tablinks[i].className = tablinks[i].className.replace(" active", "");
  }

  // Show the current tab, and add an "active" class to the button that opened the tab
  document.getElementById(viewName).style.display = "block";
  evt.currentTarget.className += " active";
}

function showDatePickerOk(){
        document.getElementById("datePickerOk").style.display = "block";
}

function showDatePickerOverlay() {
  var datePickerInput = document.getElementById("datePickerInput");
  var today = new Date();
  var dd = today.getDate();
  var mm = today.getMonth()+1; //January is 0!
  var yyyy = today.getFullYear();
  if(dd<10){
       dd='0'+dd
  }
  if(mm<10){
      mm='0'+mm
  }
  today = yyyy+'-'+mm+'-'+dd;
  datePickerInput.setAttribute("max", today);
  datePickerInput.value = "";
  document.getElementById("datePickerOk").style.display = "none";
  document.getElementById("datePickerOverlay").style.display = "block";
}

function hideDatePickerOverlay(){
        document.getElementById("datePickerOverlay").style.display = "none";
}

function parseDateISOString(s) {
  let ds = s.split(/\D+/).map(s => parseInt(s));
  ds[1] = ds[1] - 1; // adjust month
  return new Date(...ds);
}

function sameCalendarDay(date1, date2) {
        var d1 = date1.setHours(0,0,0,0);
        var d2 = date2.setHours(0,0,0,0);
        var t1 = date1.getTime();
        var t2 = date2.getTime();
        return (t1 === t2);
}

function clearChart(chartName){
        var chart = netperfData.charts[chartName];
        var chartElement = document.getElementById(chart.canvasId);
        chartElement.classList.add("loading");
        for (i in chart.chartObject.data.datasets){
                chart.chartObject.data.datasets[i].data = [];
        }
        chart.chartObject.update();
}

function okViewDate(){
	updateViewDate();
	hideDatePickerOverlay();
}

function changeViewDate(){
	document.getElementById("datePickerOk").onclick = okViewDate;
	document.getElementById("datePickerTitle").innerText = "View date:";
	showDatePickerOverlay();
}

function updateViewDate(){
	var bandwidthMonitorEnabled = netperfData.settings.bandwidth_monitor.enabled;
        var datePicked = document.getElementById("datePickerInput").value;
        var newDate = parseDateISOString(datePicked);
        var today = new Date();
	var getBandwidthUsage = false;
        var viewDateText = document.getElementById("viewDateText");
	var msg = null;
        if (sameCalendarDay(today,newDate)){
                netperfData.viewDate = "today";
                viewDateText.innerText = "Today";
		if (bandwidthMonitorEnabled){
                	document.getElementById("bandwidthDailyMenuItem").style.display="none";
                	document.getElementById("bwmonitorMenuItem").style.display="block";
		}
        }
        else{
                netperfData.viewDate = newDate;
                viewDateText.innerText = dateString(newDate);
                msg = {queryDateTimestamp :netperfData.viewDate.getTime()};
		if (bandwidthMonitorEnabled){
                	document.getElementById("bandwidthDailyMenuItem").style.display="block";
                	document.getElementById("bwmonitorMenuItem").style.display="none";
			clearChart("bandwidthDaily");
			getBandwidthUsage = true;
		}
        }
        clearChart("speedtest");
        clearChart("dns");
        document.getElementById("internetMenuItem").click();
        socket.emit('get_speedtest_data', message = msg);
        socket.emit('get_isp_outage_data', message = msg);
        socket.emit('get_dns_data', message = msg);
        socket.emit('get_iperf3_data', message = msg);
	if (getBandwidthUsage == true){
			socket.emit('get_bandwidth_usage', msg);
	}
}

function dateString(d){
	var dd = d.getDate();
	var mm = d.getMonth()+1; //January is 0!
	var yyyy = d.getFullYear();
	if(dd<10){
		dd='0'+dd
	}
	if(mm<10){
		mm='0'+mm
	}
	return (yyyy+'-'+mm+'-'+dd);
}

function setViewDateToday(){
	var today = new Date();
	document.getElementById("datePickerInput").value = dateString(today);
	document.getElementById("datePickerOk").style.display = "block";
}

function setViewDateYesterday(){
	var yesterday = new Date();
	yesterday.setDate(yesterday.getDate() - 1)
	document.getElementById("datePickerInput").value = dateString(yesterday);
	document.getElementById("datePickerOk").style.display = "block";
}


