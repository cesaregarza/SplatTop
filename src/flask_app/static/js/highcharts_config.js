Highcharts.setOptions({
    chart: {
        backgroundColor: 'black',
        plotBackgroundColor: 'black',
        style: {
            color: 'white'
        }
    },
    title: {
        style: {
            color: 'white',
            fontFamily: 'Splatfont2',
            letterSpacing: '1px',
        }
    },
    subtitle: {
        style: {
            color: 'white',
            fontFamily: 'Splatfont2',
            letterSpacing: '1px',
        }
    },
    xAxis: {
        gridLineColor: 'gray',
        gridLineWidth: 0.5,
        lineColor: 'white',
        tickColor: 'white',
        labels: {
            style: {
                color: 'white'
            }
        },
        title: {
            style: {
                color: 'white',
                fontFamily: 'Splatfont2',
                letterSpacing: '1px',
            }
        }
    },
    yAxis: {
        gridLineColor: 'gray',
        labels: {
            style: {
                color: 'white'
            }
        },
        title: {
            style: {
                color: 'white',
                fontFamily: 'Splatfont2',
                letterSpacing: '1px',
            }
        },
    },
    legend: {
        itemStyle: {
            color: 'white'
        },
    },
    plotOptions: {
        series: {
            marker: {
                fillColor: '#ad5ad7'
            },
            color: '#ad5ad7',
        }
    },
    rangeSelector: {
        buttonTheme: {
            fill: '#5b1e7b',
            stroke: '#000',
            style: {
                color: '#fff'
            },
            states: {
                hover: {
                    fill: '#c68be3',
                },
                select: {
                    fill: '#a141d1',
                    style: {
                        color: 'white'
                    }
                },
                disabled: {
                    fill: '#555',
                    style: {
                        color: '#aaa'
                    }
                },
            }
        },
        inputBoxBorderColor: 'gray',
        inputBoxWidth: 100,
        inputStyle: {
            color: '#ad5ad7',
            fontWeight: 'bold'
        },
        labelStyle: {
            color: '#ad5ad7',
            fontWeight: 'bold'
        }
    }
});
