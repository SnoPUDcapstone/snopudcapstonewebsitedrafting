const API_URL = "http://localhost:5555/data";
const API_URL2 = "http://localhost:5555/selecteddate";

const API_URL_30_30 = "http://localhost:5555/30_30";
const API_URL_30_30selected = "http://localhost:5555/30_30selected";

const API_30_60 = "http://localhost:5555/30_60";
const API_30_60_selected = "http://localhost:5555/30_60selected";

const API_URL_trend = "http://localhost:5555/trend_model";
const API_URL_trend_selected = "http://localhost:5555/trend_selected";

const API_URL_proportional = "http://localhost:5555/proportional";
const API_URL_proportional_selected = "http://localhost:5555/proportional_selected";

const API_URL_averaged = "http://localhost:5555/averaged";
const API_URL_averaged_selected = "http://localhost:5555/averagedselected";

const API_URL_70_60 = "http://localhost:5555/70_60";
const API_URL_70_60_selected = "http://localhost:5555/70_60selected";

// Battery SOC APIs
const API_URL_30_30_soc = "http://localhost:5555/30_30/soc";
const API_URL_30_30selected_soc = "http://localhost:5555/30_30selected/soc";

const API_30_60_soc = "http://localhost:5555/30_60/soc";
const API_30_60_selected_soc = "http://localhost:5555/30_60selected/soc";

const API_URL_trend_soc = "http://localhost:5555/trend_model/soc";
const API_URL_trend_selected_soc = "http://localhost:5555/trend_selected/soc";

const API_URL_proportional_soc = "http://localhost:5555/proportional/soc";
const API_URL_proportional_selected_soc = "http://localhost:5555/proportional_selected/soc";

const API_URL_averaged_soc = "http://localhost:5555/averaged/soc";
const API_URL_averaged_selected_soc = "http://localhost:5555/averagedselected/soc";

const API_URL_70_60_soc = "http://localhost:5555/70_60/soc";
const API_URL_70_60_selected_soc = "http://localhost:5555/70_60selected/soc";

// Battery kW usage APIs
const API_URL_30_30_batt = "http://localhost:5555/30_30/batt";
const API_URL_30_30selected_batt = "http://localhost:5555/30_30selected/batt";

const API_30_60_batt = "http://localhost:5555/30_60/batt";
const API_30_60_selected_batt = "http://localhost:5555/30_60selected/batt";

const API_URL_trend_batt = "http://localhost:5555/trend_model/batt";
const API_URL_trend_selected_batt = "http://localhost:5555/trend_selected/batt";

const API_URL_proportional_batt = "http://localhost:5555/proportional/batt";
const API_URL_proportional_selected_batt = "http://localhost:5555/proportional_selected/batt";

const API_URL_averaged_batt = "http://localhost:5555/averaged/batt";
const API_URL_averaged_selected_batt = "http://localhost:5555/averagedselected/batt";

const API_URL_70_60_batt = "http://localhost:5555/70_60/batt";
const API_URL_70_60_selected_batt = "http://localhost:5555/70_60selected/batt";

// Function to get appropriate endpoints based on data type
function getEndpoints(dataType) {
    switch (dataType) {
        case 'option2': // Battery SOC
            return {
                base: API_URL_30_30_soc,
                selected: API_URL_30_30selected_soc,
                base60: API_30_60_soc,
                selected60: API_30_60_selected_soc,
                trend: API_URL_trend_soc,
                trendSelected: API_URL_trend_selected_soc,
                proportional: API_URL_proportional_soc,
                proportionalSelected: API_URL_proportional_selected_soc,
                averaged: API_URL_averaged_soc,
                averagedSelected: API_URL_averaged_selected_soc,
                base70_60: API_URL_70_60_soc,
                selected70_60: API_URL_70_60_selected_soc
            };
        case 'option3': // Battery KWh
            return {
                base: API_URL_30_30_batt,
                selected: API_URL_30_30selected_batt,
                base60: API_30_60_batt,
                selected60: API_30_60_selected_batt,
                trend: API_URL_trend_batt,
                trendSelected: API_URL_trend_selected_batt,
                proportional: API_URL_proportional_batt,
                proportionalSelected: API_URL_proportional_selected_batt,
                averaged: API_URL_averaged_batt,
                averagedSelected: API_URL_averaged_selected_batt,
                base70_60: API_URL_70_60_batt,
                selected70_60: API_URL_70_60_selected_batt
            };
        case 'option1': // Solar (default)
        default:
            return {
                base: API_URL_30_30,
                selected: API_URL_30_30selected,
                base60: API_30_60,
                selected60: API_30_60_selected,
                trend: API_URL_trend,
                trendSelected: API_URL_trend_selected,
                proportional: API_URL_proportional,
                proportionalSelected: API_URL_proportional_selected,
                averaged: API_URL_averaged,
                averagedSelected: API_URL_averaged_selected,
                base70_60: API_URL_70_60,
                selected70_60: API_URL_70_60_selected
            };
    }
}

async function fetchData(dataType = 'option1') {
    try {
        let initialData = [];
        if (dataType === 'option1') {
            const response = await fetch(API_URL);
            if (!response.ok) throw new Error('Network response was not ok');
            initialData = await response.json();
        }
        updateChart(initialData, dataType);
    } catch (error) {
        console.error("Error fetching initial data:", error);
        updateChart([], dataType); // Ensure chart initializes even on error
    }
}

async function fetch30_30Data(useSelected = false, dataType = 'option1') {
    const endpoints = getEndpoints(dataType);
    const url = useSelected ? endpoints.selected : endpoints.base;

    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();
        addDatasetToChart(data, useSelected ? "30_30 Selected Data" : "30_30 Data", "red", dataType);
    } catch (error) {
        console.error(`Error fetching 30_30 ${dataType} data:`, error);
    }
}

async function fetch30_60Data(useSelected = false, dataType = 'option1') {
    const endpoints = getEndpoints(dataType);
    const url = useSelected ? endpoints.selected60 : endpoints.base60;

    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();
        addDatasetToChart(data, useSelected ? "30_60 Selected Data" : "30_60 Data", "green", dataType);
    } catch (error) {
        console.error(`Error fetching 30_60 ${dataType} data:`, error);
    }
}

async function fetchTrendData(useSelected = false, dataType = 'option1') {
    const endpoints = getEndpoints(dataType);
    const url = useSelected ? endpoints.trendSelected : endpoints.trend;

    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();
        addDatasetToChart(data, useSelected ? "Trend Selected Data" : "Trend Data", "orange", dataType);
    } catch (error) {
        console.error(`Error fetching trend ${dataType} data:`, error);
    }
}

async function fetchProportionalData(useSelected = false, dataType = 'option1') {
    const endpoints = getEndpoints(dataType);
    const url = useSelected ? endpoints.proportionalSelected : endpoints.proportional;

    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();
        addDatasetToChart(data, useSelected ? "Proportional Selected Data" : "Proportional Data", "purple", dataType);
    } catch (error) {
        console.error(`Error fetching proportional ${dataType} data:`, error);
    }
}

async function fetchAveragedData(useSelected = false, dataType = 'option1') {
    const endpoints = getEndpoints(dataType);
    const url = useSelected ? endpoints.averagedSelected : endpoints.averaged;

    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();
        addDatasetToChart(data, useSelected ? "Averaged Selected Data" : "Averaged Data", "cyan", dataType);
    } catch (error) {
        console.error(`Error fetching averaged ${dataType} data:`, error);
    }
}

async function fetch70_60Data(useSelected = false, dataType = 'option1') {
    const endpoints = getEndpoints(dataType);
    const url = useSelected ? endpoints.selected70_60 : endpoints.base70_60;

    try {
        const response = await fetch(url);
        if (!response.ok) throw new Error('Network response was not ok');
        const data = await response.json();
        addDatasetToChart(data, useSelected ? "70_60 Selected Data" : "70_60 Data", "pink", dataType);
    } catch (error) {
        console.error(`Error fetching 70_60 ${dataType} data:`, error);
    }
}

function addDatasetToChart(data, label, color, dataType) {
    const dates = data.map(row => new Date(row["Date and Time"]).toLocaleString());
    const values = data.map(row => row["Value (KW)"]);

    if (window.myChart) {
        // Update labels if longer dataset is provided
        if (!window.myChart.data.labels || dates.length > window.myChart.data.labels.length) {
            window.myChart.data.labels = dates;
        }

        // Remove existing dataset with the same label
        window.myChart.data.datasets = window.myChart.data.datasets.filter(ds => ds.label !== label);

        // Add new dataset
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
    } else {
        // If no chart exists, create it with this dataset
        updateChart(data, dataType, label, color);
    }
}

function removeDatasetFromChart(labels) {
    if (window.myChart) {
        window.myChart.data.datasets = window.myChart.data.datasets.filter(dataset => !labels.includes(dataset.label));
        if (window.myChart.data.datasets.length === 0) {
            window.myChart.data.labels = [];
        }
        window.myChart.update();
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const solarForm = document.getElementById('solarForm');
    solarForm.addEventListener('submit', handleFormSubmit);

    const currentDataButton = document.getElementById('currentDataButton');
    currentDataButton.addEventListener('click', fetchInitialData);

    let currentDataType = 'option1';

    const optionBoxes = document.querySelectorAll('#optionBox .option-box');
    optionBoxes.forEach(box => {
        box.addEventListener('click', async () => {
            optionBoxes.forEach(b => b.classList.remove('selected'));
            box.classList.add('selected');
            currentDataType = box.getAttribute('data-value');

            // Update y-axis label without resetting chart
            if (window.myChart) {
                const label = currentDataType === 'option2' ? "State of Charge (%)" :
                    currentDataType === 'option3' ? "Battery Power (KW)" :
                        "Solar Power (KW)";
                window.myChart.options.scales.y.title.text = label;

                // Remove base solar data if switching away from option1
                if (currentDataType !== 'option1') {
                    removeDatasetFromChart(["Solar Power (KW)"]);
                } else {
                    // Re-fetch base solar data if switching back to option1
                    const response = await fetch(API_URL);
                    if (response.ok) {
                        const data = await response.json();
                        addDatasetToChart(data, "Solar Power (KW)", "blue", currentDataType);
                    }
                }

                // Re-fetch active datasets for the new data type
                const startDate = document.getElementById('start').value;
                const endDate = document.getElementById('end').value;
                const useSelected = startDate && endDate;

                if (dataset1.classList.contains('active')) await fetch30_30Data(useSelected, currentDataType);
                if (dataset2.classList.contains('active')) await fetch30_60Data(useSelected, currentDataType);
                if (dataset3.classList.contains('active')) await fetchTrendData(useSelected, currentDataType);
                if (dataset4.classList.contains('active')) await fetchProportionalData(useSelected, currentDataType);
                if (dataset5.classList.contains('active')) await fetchAveragedData(useSelected, currentDataType);
                if (dataset6.classList.contains('active')) await fetch70_60Data(useSelected, currentDataType);

                window.myChart.update();
            } else {
                // Initial chart setup if it doesn’t exist
                await fetchData(currentDataType);
            }
        });
    });

    const dataset1 = document.getElementById('dataset1');
    dataset1.addEventListener('click', () => {
        dataset1.classList.toggle('active');
        const startDate = document.getElementById('start').value;
        const endDate = document.getElementById('end').value;
        const useSelected = dataset1.classList.contains('active') && startDate && endDate;

        if (dataset1.classList.contains('active')) {
            fetch30_30Data(useSelected, currentDataType);
        } else {
            removeDatasetFromChart(["30_30 Data", "30_30 Selected Data"]);
        }
    });

    const dataset2 = document.getElementById('dataset2');
    dataset2.addEventListener('click', () => {
        dataset2.classList.toggle('active');
        const startDate = document.getElementById('start').value;
        const endDate = document.getElementById('end').value;
        const useSelected = dataset2.classList.contains('active') && startDate && endDate;

        if (dataset2.classList.contains('active')) {
            fetch30_60Data(useSelected, currentDataType);
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
            fetchTrendData(useSelected, currentDataType);
        } else {
            removeDatasetFromChart(["Trend Data", "Trend Selected Data"]);
        }
    });

    const dataset4 = document.getElementById('dataset4');
    dataset4.addEventListener('click', () => {
        dataset4.classList.toggle('active');
        const startDate = document.getElementById('start').value;
        const endDate = document.getElementById('end').value;
        const useSelected = dataset4.classList.contains('active') && startDate && endDate;

        if (dataset4.classList.contains('active')) {
            fetchProportionalData(useSelected, currentDataType);
        } else {
            removeDatasetFromChart(["Proportional Data", "Proportional Selected Data"]);
        }
    });

    const dataset5 = document.getElementById('dataset5');
    dataset5.addEventListener('click', () => {
        dataset5.classList.toggle('active');
        const startDate = document.getElementById('start').value;
        const endDate = document.getElementById('end').value;
        const useSelected = dataset5.classList.contains('active') && startDate && endDate;

        if (dataset5.classList.contains('active')) {
            fetchAveragedData(useSelected, currentDataType);
        } else {
            removeDatasetFromChart(["Averaged Data", "Averaged Selected Data"]);
        }
    });

    const dataset6 = document.getElementById('dataset6');
    dataset6.addEventListener('click', () => {
        dataset6.classList.toggle('active');
        const startDate = document.getElementById('start').value;
        const endDate = document.getElementById('end').value;
        const useSelected = dataset6.classList.contains('active') && startDate && endDate;

        if (dataset6.classList.contains('active')) {
            fetch70_60Data(useSelected, currentDataType);
        } else {
            removeDatasetFromChart(["70_60 Data", "70_60 Selected Data"]);
        }
    });

    fetchData('option1'); // Initial load
});

document.addEventListener("DOMContentLoaded", () => {
    const toggleSolarButton = document.getElementById("toggleSolarButton");
    let dataVisible = true;

    toggleSolarButton.addEventListener("click", () => {
        const currentDataType = document.querySelector('#optionBox .option-box.selected').getAttribute('data-value');
        const label = currentDataType === 'option2' ? "State of Charge (%)" :
            currentDataType === 'option3' ? "Battery Power (KW)" :
                "Solar Power (KW)";

        if (dataVisible) {
            removeDatasetFromChart([label]);
            toggleSolarButton.textContent = "Show Solar Data";
            toggleSolarButton.classList.add("hidden");
        } else {
            fetchData(currentDataType);
            toggleSolarButton.textContent = "Hide Solar Data";
            toggleSolarButton.classList.remove("hidden");
        }
        dataVisible = !dataVisible;
    });
});

async function fetchInitialData() {
    const currentDataType = document.querySelector('#optionBox .option-box.selected').getAttribute('data-value');
    try {
        await fetchData(currentDataType);

        removeDatasetFromChart([
            "30_30 Selected Data",
            "30_60 Selected Data",
            "Trend Selected Data",
            "Proportional Selected Data",
            "Averaged Selected Data",
            "70_60 Selected Data"
        ]);

        document.getElementById('start').value = "";
        document.getElementById('end').value = "";

        const startDate = document.getElementById('start').value;
        const endDate = document.getElementById('end').value;
        const useSelected = startDate && endDate;

        if (dataset1.classList.contains('active')) await fetch30_30Data(useSelected, currentDataType);
        if (dataset2.classList.contains('active')) await fetch30_60Data(useSelected, currentDataType);
        if (dataset3.classList.contains('active')) await fetchTrendData(useSelected, currentDataType);
        if (dataset4.classList.contains('active')) await fetchProportionalData(useSelected, currentDataType);
        if (dataset5.classList.contains('active')) await fetchAveragedData(useSelected, currentDataType);
        if (dataset6.classList.contains('active')) await fetch70_60Data(useSelected, currentDataType);
    } catch (error) {
        console.error("Error fetching initial data:", error);
    }
}

async function handleFormSubmit(event) {
    event.preventDefault();
    const startDate = document.getElementById('start').value;
    const endDate = document.getElementById('end').value;
    const currentDataType = document.querySelector('#optionBox .option-box.selected').getAttribute('data-value');

    try {
        if (currentDataType === 'option1') {
            const response = await fetch(`${API_URL2}?start=${startDate}&end=${endDate}`);
            if (!response.ok) throw new Error('Network response was not ok');
            const data = await response.json();
            addDatasetToChart(data, "Solar Power (KW)", "blue", currentDataType);
        }

        const useSelected = startDate && endDate;
        if (dataset1.classList.contains('active')) await fetch30_30Data(useSelected, currentDataType);
        if (dataset2.classList.contains('active')) await fetch30_60Data(useSelected, currentDataType);
        if (dataset3.classList.contains('active')) await fetchTrendData(useSelected, currentDataType);
        if (dataset4.classList.contains('active')) await fetchProportionalData(useSelected, currentDataType);
        if (dataset5.classList.contains('active')) await fetchAveragedData(useSelected, currentDataType);
        if (dataset6.classList.contains('active')) await fetch70_60Data(useSelected, currentDataType);
    } catch (error) {
        console.error("Error fetching selected date data:", error);
    }
}

function updateChart(data, dataType = 'option1', initialLabel = null, initialColor = null) {
    const ctx = document.getElementById("dataChart").getContext("2d");
    const dates = data.map(row => new Date(row["Date and Time"]).toLocaleString());
    const values = data.map(row => row["Value (KW)"]);
    const label = dataType === 'option2' ? "State of Charge (%)" :
        dataType === 'option3' ? "Battery Power (KW)" :
            "Solar Power (KW)";

    if (!window.myChart) {
        // Initial chart creation
        window.myChart = new Chart(ctx, {
            type: "line",
            data: {
                labels: dates,
                datasets: dataType === 'option1' && !initialLabel ? [{
                    label: label,
                    data: values,
                    borderColor: "blue",
                    borderWidth: 2,
                    fill: false,
                    pointRadius: 0,
                    pointHoverRadius: 5
                }] : initialLabel ? [{
                    label: initialLabel,
                    data: values,
                    borderColor: initialColor,
                    borderWidth: 2,
                    fill: false,
                    pointRadius: 0,
                    pointHoverRadius: 5
                }] : []
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
                            text: label
                        }
                    }
                }
            }
        });
    } else {
        // Update existing chart (only if initial load or toggleSolarButton)
        if (data.length > 0 && !initialLabel) {
            window.myChart.data.labels = dates;
            window.myChart.data.datasets = window.myChart.data.datasets.filter(ds => ds.label !== label);
            window.myChart.data.datasets.unshift({
                label: label,
                data: values,
                borderColor: "blue",
                borderWidth: 2,
                fill: false,
                pointRadius: 0,
                pointHoverRadius: 5
            });
            window.myChart.options.scales.y.title.text = label;
            window.myChart.update();
        }
    }
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
fetchData('option1');
