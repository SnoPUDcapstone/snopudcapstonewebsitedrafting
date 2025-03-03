const API_URL = "http://localhost:5555/data";
const API_URL2 = "http://localhost:5555/selecteddate";
const API_URL_30_30 = "http://localhost:5555/30_30";
const API_URL_30_30selected = "http://localhost:5555/30_30selected";
const API_30_60 = "http://localhost:5555/30_60";
const API_30_60_selected = "http://localhost:5555/30_60selected";
const API_URL_trend = "http://localhost:5555/trend_model"
const API_URL_trend_selected = "http://localhost:5555/trend_selected"

// Function to fetch initial data from API
async function fetchData() {
    try {
        const response = await fetch(API_URL);
        const data = await response.json();
        updateChart(data);
    } catch (error) {
        console.error("Error fetching data:", error);
    }
}

// Fetch 30_30 data
async function fetch30_30Data(useSelected = false) {
    const url = useSelected ? API_URL_30_30selected : API_URL_30_30;

    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();
        addDatasetToChart(data, useSelected ? "30_30 Selected Data" : "30_30 Data", "red");
    } catch (error) {
        console.error("Error fetching 30_30 data:", error);
    }
}

// Fetch 30_60 data (new function)
async function fetch30_60Data(useSelected = false) {
    const url = useSelected ? API_30_60_selected : API_30_60;

    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();
        addDatasetToChart(data, useSelected ? "30_60 Selected Data" : "30_60 Data", "green"); // Using green to differentiate
    } catch (error) {
        console.error("Error fetching 30_60 data:", error);
    }
}

// Fetch trend data (new function)
async function fetchTrendData(useSelected = false) {
    const url = useSelected ? API_URL_trend_selected : API_URL_trend;

    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();
        addDatasetToChart(data, useSelected ? "Trend Selected Data": "Trend Data", "orange");
    } catch (error) {
        console.error("error fetching trend data:", error);
    }
}

// Add dataset to chart
function addDatasetToChart(data, label, color) {
    const dates = data.map(row => new Date(row["Date and Time"]).toLocaleString());
    const values = data.map(row => row["Value (KW)"]);

    if (window.myChart) {
        window.myChart.data.datasets.push({
            label: label,
            data: values,
            borderColor: color,
            borderWidth: 2,
            fill: false,
            pointRadius: 0,
            pointHoverRadius: 5
        });
        window.myChart.update();
    }
}

// Remove dataset from chart
function removeDatasetFromChart(labels) {
    if (window.myChart) {
        window.myChart.data.datasets = window.myChart.data.datasets.filter(dataset => !labels.includes(dataset.label));
        window.myChart.update();
    }
}

// Event listeners
document.addEventListener('DOMContentLoaded', () => {
    const solarForm = document.getElementById('solarForm');
    solarForm.addEventListener('submit', handleFormSubmit);

    const currentDataButton = document.getElementById('currentDataButton');
    currentDataButton.addEventListener('click', fetchInitialData);

    const dataset1 = document.getElementById('dataset1');
    dataset1.addEventListener('click', () => {
        dataset1.classList.toggle('active');

        const startDate = document.getElementById('start').value;
        const endDate = document.getElementById('end').value;

        const useSelected = dataset1.classList.contains('active') && startDate && endDate;

        if (dataset1.classList.contains('active')) {
            fetch30_30Data(useSelected);
        } else {
            removeDatasetFromChart(["30_30 Data", "30_30 Selected Data"]);
        }
    });

    const dataset2 = document.getElementById('dataset2'); // Assuming dataset2 exists in HTML
    dataset2.addEventListener('click', () => {
        dataset2.classList.toggle('active');

        const startDate = document.getElementById('start').value;
        const endDate = document.getElementById('end').value;

        const useSelected = dataset2.classList.contains('active') && startDate && endDate;

        if (dataset2.classList.contains('active')) {
            fetch30_60Data(useSelected);
        } else {
            removeDatasetFromChart(["30_60 Data", "30_60 Selected Data"]);
        }
    });

    const dataset3 = document.getElementById('dataset3');
    dataset3.addEventListener('click', () => {
        dataset3.classList.toggle('active');

        const startDate = document.getElementById('start').value;
        const endDate = document.getElementById('end').value;

        const useSelected = dataset3.classList.contains('active') && startDate && endDate;

        if (dataset3.classList.contains('active')) {
            fetchTrendData(useSelected);
        } else {
            removeDatasetFromChart(["Trend Data", "Trend Selected Data"]);
        }
    });

    const optionBoxes = document.querySelectorAll('#optionBox .option-box');
    optionBoxes.forEach(box => {
        box.addEventListener('click', () => {
            optionBoxes.forEach(b => b.classList.remove('selected'));
            box.classList.add('selected');
            const selectedValue = box.getAttribute('data-value');
            console.log('Selected option:', selectedValue);
        });
    });

    optionBoxes[0].classList.add('selected');
    fetchData(); // Initial data load
});

// Fetch initial data
async function fetchInitialData() {
    try {
        const response = await fetch(API_URL);
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        const data = await response.json();

        updateChart(data);
        removeDatasetFromChart(["30_30 Selected Data", "30_60 Selected Data"]);

        document.getElementById('start').value = "";
        document.getElementById('end').value = "";

        if (dataset1.classList.contains('active')) {
            fetch30_30Data(false);
        }
        if (dataset2.classList.contains('active')) {
            fetch30_60Data(false);
        }
    } catch (error) {
        console.error("Error fetching initial data:", error);
    }
}

// Handle form submission
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

        if (dataset1.classList.contains('active')) {
            await fetch30_30Data(true);
        }
        if (dataset2.classList.contains('active')) {
            await fetch30_60Data(true);
        }
        if (dataset3.classList.contains('active')) {
            await fetchTrendData(true);
        }
        updateChart(data);
    } catch (error) {
        console.error("Error fetching selected date data:", error);
    }
}

// Update chart
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

// Sticky top bar
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

// Initial fetch
fetchData();
