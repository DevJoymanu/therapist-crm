function palette(index) {
  return ["#2563eb", "#0ea5e9", "#0f766e", "#e11d48", "#7c3aed"][index % 5];
}

function buildDatasets(datasets) {
  return datasets.map((dataset, index) => ({
    label: dataset.label,
    data: dataset.data,
    borderColor: palette(index),
    backgroundColor: palette(index),
    borderWidth: 2,
    pointRadius: 3,
    pointHoverRadius: 5,
    tension: 0.35,
    spanGaps: true,
  }));
}

const crmCharts = new Map();

function createLineChart(canvas, data) {
  if (!canvas || !window.Chart) return;
  if (crmCharts.has(canvas.id)) {
    crmCharts.get(canvas.id).destroy();
  }
  const chart = new Chart(canvas, {
    type: "line",
    data: {
      labels: data.labels || [],
      datasets: buildDatasets(data.datasets || []),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: {
            boxWidth: 10,
            boxHeight: 10,
            usePointStyle: true,
          },
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          suggestedMax: 10,
          grid: { color: "#e2e8f0" },
          ticks: { color: "#64748b" },
        },
        x: {
          grid: { display: false },
          ticks: { color: "#64748b" },
        },
      },
    },
  });
  crmCharts.set(canvas.id, chart);
}

function normalizePatientTrends(raw) {
  const labels = [];
  const datasets = Object.entries(raw).map(([label, points]) => {
    points.forEach((point) => {
      if (!labels.includes(point.date)) labels.push(point.date);
    });
    return {
      label,
      data: points.map((point) => point.value),
      dates: points.map((point) => point.date),
    };
  });
  return {
    labels,
    datasets: datasets.map((dataset) => ({
      label: dataset.label,
      data: labels.map((date) => {
        const index = dataset.dates.indexOf(date);
        return index >= 0 ? dataset.data[index] : null;
      }),
    })),
  };
}

function initCharts(root = document) {
  const dashboardData = document.getElementById("dashboard-chart-data");
  if (dashboardData) {
    createLineChart(
      document.getElementById("dashboardChart"),
      JSON.parse(dashboardData.textContent)
    );
  }

  const patientData = document.getElementById("score-trends");
  if (patientData) {
    createLineChart(
      document.getElementById("trendChart"),
      normalizePatientTrends(JSON.parse(patientData.textContent))
    );
  }
}

document.addEventListener("DOMContentLoaded", () => initCharts());
document.body?.addEventListener("htmx:afterSwap", () => initCharts());
