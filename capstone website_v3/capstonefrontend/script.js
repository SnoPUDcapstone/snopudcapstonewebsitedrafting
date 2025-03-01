const API_URL = "http://localhost:5555/data";
const API_URL2 = "http://localhost:5555/selecteddate";

//
//edit as following
//methods --  fetch data
//            create datasets
//            process and create chart
//






// Function to fetch data from API
async function fetchData() {
    try {
        const response = await fetch(API_URL);
        const data = await response.json();
        updateChart(data);
    } catch (error) {
        console.error("Error fetching data:", error);
    }
}

function updateChart(data) {
    const ctx = document.getElementById("dataChart").getContext("2d");

    const dates = data.map(row => new Date(row["Date and Time"]).toLocaleString());
    const solarData = data.map(row => row["Value (KW)"]);

    const chartConfig = {
        type: "line",
        data: {
            labels: dates,
            datasets: [{
                label: "Solar Power (KW)",
                data: solarData,
                borderColor: "blue",
                borderWidth: 2,
                fill: false,
                pointRadius: 0,
                pointHoverRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'category',
                    title: {
                        display: true,
                        text: 'Date and Time'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Solar Power (KW)'
                    }
                }
            }
        }
    };

    if (window.myChart instanceof Chart) {
        window.myChart.data = chartConfig.data;
        window.myChart.update();
    } else {
        window.myChart = new Chart(ctx, chartConfig);
    }
}


document.addEventListener('DOMContentLoaded', () => {
    const solarForm = document.getElementById('solarForm');
    solarForm.addEventListener('submit', handleFormSubmit);

    const currentDataButton = document.getElementById('currentDataButton');
    currentDataButton.addEventListener('click', fetchInitialData);


    const optionBoxes = document.querySelectorAll('#optionBox .option-box');

    optionBoxes.forEach(box => {
        box.addEventListener('click', () => {
            // Remove 'selected' class from all boxes
            optionBoxes.forEach(b => b.classList.remove('selected'));

            // Add 'selected' class to clicked box
            box.classList.add('selected');

            // Here you can add logic to handle the selection change
            const selectedValue = box.getAttribute('data-value');
            console.log('Selected option:', selectedValue);
            // You can call a function here to update the chart based on the selected option
        });
    });

    // Ensure the first option (Solar) is selected by default
    optionBoxes[0].classList.add('selected');

    // Initial data load
    fetchData();
});

async function fetchInitialData() {
    try {
        const response = await fetch(`${API_URL}`);
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();
        updateChart(data);
    } catch (error) {
        console.error("Error fetching initial data:", error);
    }
}

async function handleFormSubmit(event) {
    event.preventDefault();
    const startDate = document.getElementById('start').value;
    const endDate = document.getElementById('end').value;

    try {
        const response = await fetch(`${API_URL2}?start=${startDate}&end=${endDate}`);
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();
        updateChart(data);
    } catch (error) {
        console.error("Error fetching selected date data:", error);
    }
}

function updateChart(data) {
    const ctx = document.getElementById("dataChart").getContext("2d");

    const dates = data.map(row => new Date(row["Date and Time"]).toLocaleString());
    const solarData = data.map(row => row["Value (KW)"]);

    if (window.myChart instanceof Chart) {
        window.myChart.destroy();
    }

    window.myChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: dates,
            datasets: [{
                label: "Solar Power (KW)",
                data: solarData,
                borderColor: "blue",
                borderWidth: 2,
                fill: false,
                pointRadius: 0,
                pointHoverRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    type: 'category',
                    title: {
                        display: true,
                        text: 'Date and Time'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Solar Power (KW)'
                    }
                }
            }
        }
    });
}


// code for buttons
const datasetBoxes = document.querySelectorAll('.dataset-box');
datasetBoxes.forEach(box => {
    box.addEventListener('click', () => {
        box.classList.toggle('active');
    });
});


//stuff for top bar
window.onscroll = function () { stickyTopBar() };

var topBar = document.getElementById("top-bar");
var sticky = topBar.offsetTop;

function stickyTopBar() {
    if (window.pageYOffset >= sticky) {
        topBar.classList.add("sticky");
    } else {
        topBar.classList.remove("sticky");
    }
}


fetchData();
