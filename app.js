// Global Data Store
let GLOBAL_DATA = [];
let CURRENT_CHART_DATA = [];
let trendChartInstance = null;
let compositionChartInstance = null;

async function init() {
    try {
        const res = await fetch(`${CONFIG.SUPABASE_URL}/rest/v1/pla_activity?select=*,pla_flight_events(*)&order=activity_date.asc`, {
            headers: {
                "apikey": CONFIG.SUPABASE_KEY,
                "Authorization": `Bearer ${CONFIG.SUPABASE_KEY}`
            }
        });

        if (!res.ok) throw new Error("API Error");
        GLOBAL_DATA = await res.json();

        // Check Version
        if (GLOBAL_DATA.length > 0) {
            const latestDate = GLOBAL_DATA[GLOBAL_DATA.length - 1].activity_date;
            document.getElementById('nav-ver').innerText = latestDate;
            document.getElementById('ver-date').innerText = latestDate;
            document.getElementById('startup-modal').classList.remove('hidden');
        }

        updateDashboard(0); // Default: ALL
        renderTable(GLOBAL_DATA);

    } catch (e) {
        console.error(e);
        document.getElementById('table-body').innerHTML = `<tr><td colspan="6" class="p-8 text-center text-red-500">載入失敗: ${e.message}</td></tr>`;
    }
}

// --- Dashboard Logic ---
function updateDashboard(days) {
    document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
    document.getElementById(`btn-${days}`).classList.add('active');

    if (days > 0) {
        CURRENT_CHART_DATA = GLOBAL_DATA.slice(-days);
    } else {
        CURRENT_CHART_DATA = GLOBAL_DATA;
    }

    renderKPIs(CURRENT_CHART_DATA);
    renderTrendChart(CURRENT_CHART_DATA);
    renderCompositionChart(CURRENT_CHART_DATA);
}

// --- Render Functions ---
function renderKPIs(data) {
    let totalAir = 0, totalCross = 0, totalShip = 0;
    let maxVal = 0, maxDate = "";

    data.forEach(d => {
        totalAir += (d.aircraft_total || 0);
        totalCross += (d.aircraft_crossing || 0);
        totalShip += (d.vessels_total || 0);
        if ((d.aircraft_total || 0) > maxVal) {
            maxVal = d.aircraft_total;
            maxDate = d.activity_date;
        }
    });

    document.getElementById('kpi-total-aircraft').innerText = totalAir.toLocaleString();
    document.getElementById('kpi-total-crossing').innerText = totalCross.toLocaleString();
    document.getElementById('kpi-total-vessels').innerText = totalShip.toLocaleString();
    document.getElementById('kpi-max-day').innerText = maxVal;
    document.getElementById('kpi-max-date').innerText = maxDate ? moment(maxDate).format('YYYY/MM/DD') : '--/--';
}

function renderTrendChart(data) {
    const ctx = document.getElementById('trendChart').getContext('2d');

    if (trendChartInstance) trendChartInstance.destroy();

    trendChartInstance = new Chart(ctx, {
        data: {
            labels: data.map(d => moment(d.activity_date).format('MM/DD')),
            datasets: [{
                    type: 'line',
                    label: '總架次 (Air Total)',
                    data: data.map(d => d.aircraft_total),
                    borderColor: '#3b82f6',
                    backgroundColor: 'rgba(59, 130, 246, 0.1)',
                    fill: true,
                    tension: 0.3,
                    yAxisID: 'y'
                },
                {
                    type: 'bar',
                    label: '逾越中線 (Threat)',
                    data: data.map(d => d.aircraft_crossing),
                    backgroundColor: 'rgba(239, 68, 68, 0.7)',
                    borderRadius: 2,
                    barPercentage: 0.6,
                    yAxisID: 'y'
                },
                {
                    type: 'line',
                    label: '共艦艘次 (Vessels)',
                    data: data.map(d => d.vessels_total),
                    borderColor: '#06b6d4',
                    borderWidth: 2,
                    borderDash: [5, 5],
                    pointRadius: 0,
                    pointHoverRadius: 4,
                    yAxisID: 'y1'
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            onHover: (event, chartElement) => {
                event.native.target.style.cursor = chartElement[0] ? 'pointer' : 'default';
            },
            onClick: (e) => {
                const points = trendChartInstance.getElementsAtEventForMode(e, 'index', {
                    intersect: false
                }, true);
                if (points.length) {
                    const index = points[0].index;
                    const item = data[index];
                    if (item) openModal(item);
                }
            },
            plugins: {
                legend: {
                    labels: {
                        color: '#94a3b8'
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            let label = context.dataset.label || '';
                            if (label) label += ': ';
                            if (context.parsed.y !== null) label += context.parsed.y;
                            return label;
                        }
                    }
                }
            },
            scales: {
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        maxTicksLimit: 12,
                        color: '#64748b'
                    }
                },
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    grid: {
                        color: '#334155'
                    },
                    ticks: {
                        color: '#3b82f6'
                    },
                    title: {
                        display: true,
                        text: '空軍架次',
                        color: '#3b82f6'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    grid: {
                        drawOnChartArea: false
                    },
                    ticks: {
                        color: '#06b6d4',
                        beginAtZero: true
                    },
                    title: {
                        display: true,
                        text: '海軍艘次',
                        color: '#06b6d4'
                    }
                }
            }
        }
    });
}

function renderCompositionChart(data) {
    const ctx = document.getElementById('compositionChart').getContext('2d');

    if (compositionChartInstance) compositionChartInstance.destroy();

    let counts = {
        "主戰機": 0,
        "輔戰機": 0,
        "無人機": 0,
        "直升機": 0
    };
    let totalRecs = 0;
    data.forEach(d => {
        if (d.pla_flight_events) {
            d.pla_flight_events.forEach(e => {
                const type = (e.aircraft_type || "").toLowerCase();
                const c = e.count || 0;
                if (type.includes('fighter') || type.includes('主戰')) counts["主戰機"] += c;
                else if (type.includes('support') || type.includes('輔戰')) counts["輔戰機"] += c;
                else if (type.includes('uav') || type.includes('無人')) counts["無人機"] += c;
                else if (type.includes('heli') || type.includes('直升')) counts["直升機"] += c;
                totalRecs += c;
            });
        }
    });

    document.getElementById('comp-total').innerText = totalRecs.toLocaleString();

    compositionChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(counts),
            datasets: [{
                data: Object.values(counts),
                backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6'],
                borderWidth: 0,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            cutout: '75%'
        }
    });
}

function renderTable(data) {
    const tbody = document.getElementById('table-body');
    tbody.innerHTML = '';
    // Recent first, show 100
    const displayData = [...data].reverse().slice(0, 100);

    displayData.forEach((item, index) => {
        const tr = document.createElement('tr');
        tr.className = "bg-slate-800/30 hover:bg-slate-700/50 transition border-b border-slate-700 cursor-pointer group";
        tr.onclick = () => openModal(item);

        const isThreat = item.aircraft_crossing > 0;

        // Calculate Trend
        let trendHtml = '';
        const prevItem = displayData[index + 1]; // Since it's reversed, next item is previous day
        if (prevItem) {
            const diff = item.aircraft_total - prevItem.aircraft_total;
            if (diff > 0) {
                trendHtml = `<span class="text-red-400 text-xs font-mono ml-2">▲+${diff}</span>`;
            } else if (diff < 0) {
                trendHtml = `<span class="text-emerald-400 text-xs font-mono ml-2">▼${diff}</span>`;
            } else {
                trendHtml = `<span class="text-slate-500 text-xs font-mono ml-2">-</span>`;
            }
        }

        tr.innerHTML = `
            <td class="px-6 py-4 font-mono text-slate-300 group-hover:text-white transition whitespace-nowrap">${item.activity_date}</td>
            <td class="px-6 py-4 text-center font-bold text-white whitespace-nowrap">${item.aircraft_total}</td>
            <td class="px-6 py-4 text-center whitespace-nowrap ${isThreat ? 'text-red-400 font-bold' : 'text-slate-600'}">${item.aircraft_crossing || '-'}</td>
            <td class="px-6 py-4 text-center text-cyan-400 font-mono whitespace-nowrap">${item.vessels_total}</td>
            <td class="px-6 py-4 whitespace-nowrap">
                ${isThreat ? '<span class="text-red-400 font-bold">● 逾越中線</span>' : '<span class="text-orange-400">● 持續擾臺</span>'}
                ${trendHtml}
            </td>
            <td class="px-6 py-4 text-right whitespace-nowrap">
                <button class="text-xs bg-slate-700 hover:bg-blue-600 text-white px-3 py-1 rounded transition">詳細</button>
            </td>
        `;
        tbody.appendChild(tr);
    });
}

// --- Modal Logic ---
const modal = document.getElementById('detail-modal');
const modalContent = document.getElementById('modal-content');
const statsGrid = document.getElementById('modal-stats-grid');

function openModal(item) {
    document.getElementById('modal-date').innerText = item.activity_date;
    const isThreat = item.aircraft_crossing > 0;
    const badge = document.getElementById('modal-badge');
    if (isThreat) {
        badge.className = "bg-red-500/20 text-red-400 border border-red-500/50 px-3 py-0.5 rounded text-xs tracking-wider uppercase";
        badge.innerText = "High Threat (高威脅)";
    } else {
        badge.className = "bg-green-500/20 text-green-400 border border-green-500/50 px-3 py-0.5 rounded text-xs tracking-wider uppercase";
        badge.innerText = "Routine (常規)";
    }

    const imgPath = item.image_file ? `images/${item.image_file}` : 'https://placehold.co/800x600/1e293b/FFF?text=No+Map+Data';
    document.getElementById('modal-image').src = imgPath;
    document.getElementById('modal-img-link').href = imgPath;

    // --- Dynamic Stats Grid ---
    statsGrid.innerHTML = '';
    statsGrid.innerHTML += `
        <div class="bg-slate-800 p-3 rounded-lg text-center border border-slate-700">
            <div class="text-xs text-slate-500 uppercase mb-1">空軍總架次</div>
            <div class="text-xl font-bold text-white">${item.aircraft_total}</div>
        </div>`;
    statsGrid.innerHTML += `
        <div class="bg-slate-800 p-3 rounded-lg text-center border border-slate-700">
            <div class="text-xs text-slate-500 uppercase mb-1">逾越中線</div>
            <div class="text-xl font-bold ${item.aircraft_crossing > 0 ? 'text-intel-red' : 'text-slate-400'}">${item.aircraft_crossing}</div>
        </div>`;
    statsGrid.innerHTML += `
        <div class="bg-slate-800 p-3 rounded-lg text-center border border-slate-700">
            <div class="text-xs text-slate-500 uppercase mb-1">海軍共艦</div>
            <div class="text-xl font-bold text-intel-cyan">${item.vessels_total}</div>
        </div>`;

    if (item.official_ships_total > 0) {
        statsGrid.innerHTML += `
            <div class="bg-slate-800 p-3 rounded-lg text-center border border-slate-700 ring-1 ring-intel-yellow/30">
                <div class="text-xs text-intel-yellow uppercase mb-1">公務船</div>
                <div class="text-xl font-bold text-intel-yellow">${item.official_ships_total}</div>
            </div>`;
    }

    if (item.balloons_total > 0) {
        statsGrid.innerHTML += `
            <div class="bg-slate-800 p-3 rounded-lg text-center border border-slate-700 ring-1 ring-intel-purple/30">
                <div class="text-xs text-intel-purple uppercase mb-1">空飄氣球</div>
                <div class="text-xl font-bold text-intel-purple">${item.balloons_total}</div>
            </div>`;
    }

    // --- Timeline ---
    const timeline = document.getElementById('modal-timeline');
    timeline.innerHTML = '';
    const events = item.pla_flight_events || [];
    events.sort((a, b) => (a.time_range || '').localeCompare(b.time_range || ''));

    if (events.length === 0) {
        timeline.innerHTML = `<p class="text-sm text-slate-500 italic py-4">無詳細飛行分時資料 (僅有統計數據)</p>`;
    } else {
        events.forEach(evt => {
            let tags = '';
            if (evt.details) {
                evt.details.forEach(tag => {
                    let color = 'bg-slate-700 text-slate-300';
                    let text = tag;
                    if (tag.includes('Crossed') || tag.includes('逾越')) {
                        color = 'bg-red-900/50 text-red-300 border border-red-800';
                        text = "逾越中線";
                    } else if (tag.includes('SW') || tag.includes('西南')) {
                        color = 'bg-orange-900/50 text-orange-300 border border-orange-800';
                        text = "西南空域";
                    }
                    tags += `<span class="${color} text-[10px] px-2 py-0.5 rounded">${text}</span>`;
                });
            }
            let type = evt.aircraft_type || "Unknown";
            type = type.replace(' (Fighter)', '').replace(' (Support)', '').replace(' (UAV)', '').replace(' (Helicopter)', '').replace(' (Bomber)', '');
            timeline.innerHTML += `
                <div class="relative pl-6 pb-4 border-l border-slate-700 last:border-0 last:pb-0">
                    <div class="absolute -left-[5px] top-1.5 w-2.5 h-2.5 rounded-full bg-slate-500 border-2 border-slate-900"></div>
                    <div class="flex justify-between items-start">
                        <span class="font-mono text-xs text-intel-blue font-bold">${evt.time_range}</span>
                        <span class="text-xs bg-slate-700 text-white px-1.5 rounded">x${evt.count}</span>
                    </div>
                    <div class="text-sm text-slate-200 mt-1 font-medium">${type}</div>
                    <div class="flex flex-wrap gap-2 mt-2">${tags}</div>
                </div>
            `;
        });
    }

    document.getElementById('modal-text').innerText = item.original_text || "無文字報告";

    modal.classList.remove('hidden');
    setTimeout(() => {
        modalContent.classList.remove('scale-95', 'opacity-0');
        modalContent.classList.add('scale-100', 'opacity-100');
    }, 10);
}

function closeModal() {
    modalContent.classList.remove('scale-100', 'opacity-100');
    modalContent.classList.add('scale-95', 'opacity-0');
    setTimeout(() => {
        modal.classList.add('hidden');
    }, 300);
}

function closeStartupModal() {
    document.getElementById('startup-modal').classList.add('hidden');
}

// Close on backdrop
modal.addEventListener('click', (e) => {
    if (e.target === modal) closeModal();
});

// Run
init();
