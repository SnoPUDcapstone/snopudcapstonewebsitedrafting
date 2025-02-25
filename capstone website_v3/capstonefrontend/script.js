const API_URL = "http://localhost:5555/data";

// Function to fetch data from API
async function fetchData() {
    try {
        const response = await fetch(API_URL);
        const data = await response.json();
        createChart(data);
    } catch (error) {
        console.error("Error fetching data:", error);
    }
}

// Function to create a Chart.js graph (Solar [kW] vs Date & Time)
function createChart(data) {
    const ctx = document.getElementById("dataChart").getContext("2d");

    // Extracting the Date & Time and Solar [kW] data
    const dates = data.map(row => row["Date & Time"]);
    const solarData = data.map(row => row["Solar [kW]"]);

    new Chart(ctx, {
        type: "line", // Line chart to visualize the trend
        data: {
            labels: dates,  // X-axis: Date & Time
            datasets: [{
                label: "Solar [kW]",
                data: solarData,  // Y-axis: Solar [kW]
                borderColor: "blue",
                borderWidth: 2,
                fill: false
            }]
        },
        options: {
            responsive: true,  // Disabling responsiveness
            maintainAspectRatio: false,  // Ensures no aspect ratio adjustment
            scales: {
                x: {
                    type: 'category', // Categorical for Date & Time
                    title: {
                        display: true,
                        text: 'Date & Time'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Solar [kW]'
                    },
                    min: 0, // Ensure the Y-axis starts at 0
                }
            }
        }
    });
}


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
// Load data when the page loads
fetchData();