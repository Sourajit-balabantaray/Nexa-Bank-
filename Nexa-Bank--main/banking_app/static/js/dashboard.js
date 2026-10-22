/**
 * NexaBank — Dashboard & Analytics Charts
 * Uses Chart.js 4.x for all data visualizations.
 */

// ── Chart defaults ────────────────────────────────────────────────────
Chart.defaults.color = getComputedStyle(document.documentElement)
  .getPropertyValue('--text-secondary').trim() || '#475569';
Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.font.size = 12;

// ── Color palette ─────────────────────────────────────────────────────
const COLORS = {
  primary: '#3b82f6',
  success: '#10b981',
  danger: '#ef4444',
  warning: '#f59e0b',
  info: '#06b6d4',
  purple: '#8b5cf6',
  pink: '#ec4899',
  orange: '#f97316',
  teal: '#14b8a6',
  indigo: '#6366f1',
};

const CATEGORY_COLORS = [
  COLORS.primary,
  COLORS.success,
  COLORS.warning,
  COLORS.danger,
  COLORS.info,
  COLORS.purple,
  COLORS.pink,
  COLORS.orange,
  COLORS.teal,
  COLORS.indigo,
];

// ── Chart instances (for destroy/recreate on period change) ───────────
const chartInstances = {};

const formatAxisCurrency = value =>
  `₹${Number(value).toLocaleString('en-IN', { notation: 'compact', maximumFractionDigits: 1 })}`;

function setAnalyticsChartState(canvas, isEmpty, message = '') {
  const emptyState = canvas.parentElement.querySelector('.analytics-chart-empty');
  if (!emptyState) return;
  canvas.hidden = isEmpty;
  emptyState.hidden = !isEmpty;
  if (message) emptyState.textContent = message;
}

// ── Income vs Expenses Chart ──────────────────────────────────────────
async function loadIncomeExpensesChart(period = '6m', canvasId = 'incomeExpensesChart') {
  const ctx = document.getElementById(canvasId);
  if (!ctx) return;

  try {
    const response = await fetch(`/api/analytics/income-expenses?period=${period}`);
    if (!response.ok) throw new Error(`Analytics request failed (${response.status})`);
    const data = await response.json();

    if (chartInstances.incomeExpenses) chartInstances.incomeExpenses.destroy();
    const hasData = [...(data.income || []), ...(data.expenses || [])].some(value => Number(value) > 0);
    setAnalyticsChartState(ctx, !hasData, 'No cash flow activity in this period.');
    if (!hasData) return;

    chartInstances.incomeExpenses = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: data.labels || [],
        datasets: [
          {
            label: 'Income',
            data: data.income || [],
            backgroundColor: 'rgba(16, 185, 129, 0.8)',
            borderColor: COLORS.success,
            borderWidth: 1,
            borderRadius: 6,
            borderSkipped: false,
          },
          {
            label: 'Expenses',
            data: data.expenses || [],
            backgroundColor: 'rgba(239, 68, 68, 0.8)',
            borderColor: COLORS.danger,
            borderWidth: 1,
            borderRadius: 6,
            borderSkipped: false,
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'top',
            labels: { usePointStyle: true, padding: 20 }
          },
          tooltip: {
            callbacks: {
              label: ctx => `₹${ctx.parsed.y.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
            }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            border: { display: false }
          },
          y: {
            grid: { color: 'rgba(59,130,246,0.08)' },
            border: { display: false },
            ticks: {
              callback: formatAxisCurrency,
              maxTicksLimit: 7,
            }
          }
        }
      }
    });
  } catch (e) {
    console.warn('Could not load income/expenses chart:', e);
    setAnalyticsChartState(ctx, true, 'Unable to load cash flow data.');
  }
}


// ── Category Doughnut Chart ───────────────────────────────────────────
async function loadCategoryChart(period = '30d') {
  const ctx = document.getElementById('categoryChart');
  if (!ctx) return;

  try {
    const response = await fetch(`/api/analytics/categories?period=${period}`);
    if (!response.ok) throw new Error(`Analytics request failed (${response.status})`);
    const data = await response.json();

    if (chartInstances.category) chartInstances.category.destroy();

    if (!data.labels || data.labels.length === 0) {
      setAnalyticsChartState(ctx, true, 'No spending activity in this period.');
      return;
    }
    setAnalyticsChartState(ctx, false);

    chartInstances.category = new Chart(ctx, {
      type: 'doughnut',
      data: {
        labels: data.labels,
        datasets: [{
          data: data.data,
          backgroundColor: CATEGORY_COLORS.slice(0, data.labels.length),
          borderColor: 'transparent',
          hoverOffset: 8,
          borderWidth: 0,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '68%',
        plugins: {
          legend: {
            position: 'right',
            labels: {
              usePointStyle: true,
              padding: 14,
              font: { size: 12 },
              generateLabels(chart) {
                const data = chart.data;
                const total = data.datasets[0].data.reduce((a, b) => a + b, 0);
                return data.labels.map((label, i) => ({
                  text: `${label} (${((data.datasets[0].data[i] / total) * 100).toFixed(1)}%)`,
                  fillStyle: data.datasets[0].backgroundColor[i],
                  index: i
                }));
              }
            }
          },
          tooltip: {
            callbacks: {
              label: ctx => ` ₹${ctx.parsed.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
            }
          }
        }
      }
    });
  } catch (e) {
    console.warn('Could not load category chart:', e);
    setAnalyticsChartState(ctx, true, 'Unable to load spending data.');
  }
}


// ── Balance History Line Chart ────────────────────────────────────────
async function loadBalanceHistoryChart(period = '30d') {
  const ctx = document.getElementById('balanceHistoryChart');
  if (!ctx) return;

  try {
    const response = await fetch(`/api/analytics/balance-history?period=${period}`);
    if (!response.ok) throw new Error(`Analytics request failed (${response.status})`);
    const data = await response.json();

    if (chartInstances.balanceHistory) chartInstances.balanceHistory.destroy();
    if (!data.balances || data.balances.length === 0) {
      setAnalyticsChartState(ctx, true, 'No balance activity in this period.');
      return;
    }
    setAnalyticsChartState(ctx, false);

    chartInstances.balanceHistory = new Chart(ctx, {
      type: 'line',
      data: {
        labels: data.labels || [],
        datasets: [{
          label: 'Balance',
          data: data.balances || [],
          borderColor: COLORS.primary,
          backgroundColor: 'rgba(59,130,246,0.1)',
          fill: true,
          tension: 0.4,
          pointRadius: 4,
          pointBackgroundColor: COLORS.primary,
          pointBorderColor: 'transparent',
          borderWidth: 2.5,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: ctx => `Balance: ₹${ctx.parsed.y.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`
            }
          }
        },
        scales: {
          x: {
            grid: { display: false },
            border: { display: false },
            ticks: { maxTicksLimit: 8 }
          },
          y: {
            grid: { color: 'rgba(59,130,246,0.08)' },
            border: { display: false },
            ticks: { callback: formatAxisCurrency, maxTicksLimit: 7 }
          }
        }
      }
    });
  } catch (e) {
    console.warn('Could not load balance history chart:', e);
    setAnalyticsChartState(ctx, true, 'Unable to load balance history.');
  }
}


// ── Summary Cards Update ──────────────────────────────────────────────
async function loadSummaryCards(period = '30d') {
  try {
    const response = await fetch(`/api/analytics/summary?period=${period}`);
    if (!response.ok) throw new Error(`Analytics request failed (${response.status})`);
    const data = await response.json();

    const fmt = val => `₹${Number(val).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;

    const el = id => document.getElementById(id);
    if (el('totalIncome')) el('totalIncome').textContent = fmt(data.total_income || 0);
    if (el('totalExpenses')) el('totalExpenses').textContent = fmt(data.total_expenses || 0);
    if (el('totalSavings')) el('totalSavings').textContent = fmt(data.savings || 0);
    if (el('savingsRate')) el('savingsRate').textContent = `${data.savings_rate || 0}%`;
    if (el('expenseComparison')) {
      const comparison = data.expense_change;
      el('expenseComparison').textContent = comparison === null
        ? 'No prior-period spending to compare'
        : `${Math.abs(comparison)}% ${comparison > 0 ? 'more' : comparison < 0 ? 'less' : 'change'} vs previous period`;
      el('expenseComparison').classList.toggle('is-positive', comparison !== null && comparison < 0);
      el('expenseComparison').classList.toggle('is-negative', comparison !== null && comparison > 0);
    }
  } catch (e) {
    console.warn('Could not load summary cards:', e);
  }
}


// ── Admin Charts ──────────────────────────────────────────────────────
function initAdminChart(labels, data) {
  const ctx = document.getElementById('adminTxnChart');
  if (!ctx) return;

  new Chart(ctx, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Transactions',
        data: data,
        backgroundColor: 'rgba(59,130,246,0.7)',
        borderColor: COLORS.primary,
        borderWidth: 1,
        borderRadius: 6,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, border: { display: false } },
        y: { grid: { color: 'rgba(59,130,246,0.08)' }, border: { display: false }, ticks: { stepSize: 1 } }
      }
    }
  });
}


// ── Period Selector ───────────────────────────────────────────────────
function initPeriodSelector() {
  const btns = document.querySelectorAll('.period-btn');
  if (!btns.length) return;

  btns.forEach(btn => {
    btn.addEventListener('click', async () => {
      btns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      btns.forEach(b => b.setAttribute('aria-pressed', String(b === btn)));

      const period = btn.dataset.period;
      const periodLabels = {
        '7d': 'the last 7 days',
        '30d': 'the last 30 days',
        '6m': 'the last 6 months',
        '1y': 'the last year',
      };
      const periodLabel = document.getElementById('analyticsPeriodLabel');
      const chartPeriodLabel = document.getElementById('cashflowChartPeriod');
      if (periodLabel) periodLabel.textContent = periodLabels[period];
      if (chartPeriodLabel) chartPeriodLabel.textContent = periodLabels[period].replace('the ', '').replace(/^./, char => char.toUpperCase());
      await Promise.all([
        loadIncomeExpensesChart(period),
        loadCategoryChart(period),
        loadBalanceHistoryChart(period),
        loadSummaryCards(period),
      ]);
    });
  });
}


// ── Initialize ────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  // Analytics page
  if (document.getElementById('incomeExpensesChart')) {
    loadIncomeExpensesChart('30d');
    loadCategoryChart('30d');
    loadBalanceHistoryChart('30d');
    loadSummaryCards('30d');
    initPeriodSelector();
  }

  if (document.getElementById('dashboardIncomeExpensesChart')) {
    loadIncomeExpensesChart('6m', 'dashboardIncomeExpensesChart');
  }

  // Admin dashboard
  const adminChartEl = document.getElementById('adminTxnChart');
  if (adminChartEl) {
    const labels = JSON.parse(adminChartEl.dataset.labels || '[]');
    const data = JSON.parse(adminChartEl.dataset.values || '[]');
    initAdminChart(labels, data);
  }
});
