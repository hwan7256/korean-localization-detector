/* KLD Dashboard — Analyst Report Brief Panel */
const API = '';

let selectedId = null;

// === Fetch & Render ===
async function fetchStats() {
    const r = await fetch(`${API}/api/stats`);
    const d = await r.json();
    document.getElementById('stat-total').textContent = d.total_services;
    document.getElementById('stat-analyzed').textContent = d.total_analyzed;
    document.getElementById('stat-high').textContent = d.high_potential_count;
}

async function fetchSources() {
    const r = await fetch(`${API}/api/sources`);
    const d = await r.json();
    const sel = document.getElementById('source-filter');
    d.sources.forEach(s => {
        const o = document.createElement('option');
        o.value = s.source;
        o.textContent = `${s.source} (${s.count})`;
        sel.appendChild(o);
    });
}

async function fetchServices() {
    const src = document.getElementById('source-filter').value;
    const minS = document.getElementById('score-filter').value;
    const q = document.getElementById('search-input').value.toLowerCase();

    let url = `${API}/api/services?limit=100`;
    if (src) url += `&source=${encodeURIComponent(src)}`;
    if (minS > 0) url += `&min_score=${minS}`;

    const r = await fetch(url);
    const d = await r.json();

    let items = d.services;
    if (q) items = items.filter(s => (s.name || '').toLowerCase().includes(q));

    document.getElementById('result-count').textContent = `${items.length} result${items.length !== 1 ? 's' : ''}`;

    const container = document.getElementById('service-list');
    container.innerHTML = items.map((s, i) => renderRow(s, i + 1)).join('');

    if (selectedId) {
        const el = document.querySelector(`.list-row[data-id="${selectedId}"]`);
        if (el) el.classList.add('active');
    }
}

function renderRow(s, num) {
    const score = s.localization_score;
    let scoreClass, scoreText;
    let statusClass, statusText;

    if (score === null || score === undefined) {
        scoreClass = 'score-none'; scoreText = '--';
        statusClass = ''; statusText = '';
    } else if (score >= 70) {
        scoreClass = 'score-high'; scoreText = score;
        statusClass = 'status-viable'; statusText = 'Viable';
    } else if (score >= 40) {
        scoreClass = 'score-mid'; scoreText = score;
        statusClass = 'status-review'; statusText = 'Review';
    } else {
        scoreClass = 'score-low'; scoreText = score;
        statusClass = 'status-low'; statusText = 'Low';
    }

    const idStr = `KLD-${String(s.id).padStart(3, '0')}`;

    return `
    <div class="list-row" data-id="${s.id}" onclick="selectService(${s.id})">
        <span class="row-num">${num}</span>
        <span class="row-id">${idStr}</span>
        <span class="row-title">${esc(s.name)}</span>
        ${statusText ? `<span class="row-status ${statusClass}">${statusText}</span>` : '<span class="row-status"></span>'}
        <span class="row-score ${scoreClass}">${scoreText}</span>
    </div>`;
}

// === Select Service ===
async function selectService(id) {
    selectedId = id;

    document.querySelectorAll('.list-row').forEach(c => c.classList.remove('active'));
    const el = document.querySelector(`.list-row[data-id="${id}"]`);
    if (el) el.classList.add('active');

    const r = await fetch(`${API}/api/report/${id}`);
    const d = await r.json();
    renderBrief(d);
}

function renderBrief(data) {
    const panel = document.getElementById('brief-panel');
    const svc = data.service;
    const r = data.report;

    if (!r) {
        panel.innerHTML = `
            <div class="report-header">
                <div class="report-title">${esc(svc.name)}</div>
                <a class="report-url" href="${esc(svc.url)}" target="_blank">${esc(svc.url)}</a>
                <div class="report-subtitle">Source: ${esc(svc.source)}</div>
            </div>
            <div class="report-section"><p>This service has not been analyzed yet.</p></div>`;
        return;
    }

    const score = r.localization_score;
    const apis = safeJSON(r.required_korean_apis) || [];
    const full = safeJSON(r.template_code);

    // Parse scores for bars
    const conf = parseFloat(full?.localization_score) / 100 || score / 100 || 0.5;
    const upside = 0.6;
    const boldness = 0.4;

    panel.innerHTML = `
        <div class="report-header">
            <div class="report-title">${esc(svc.name)}</div>
            <a class="report-url" href="${esc(svc.url)}" target="_blank">${esc(svc.url)}</a>
            <div class="report-subtitle">Source: ${esc(svc.source)} — ${esc(r.estimated_dev_time || 'TBD')}</div>
        </div>

        <div class="report-section">
            <h4>Localization Score</h4>
            <span class="brief-big-score">${score}/100</span>
            <p>${esc(r.localization_reason || '')}</p>
        </div>

        <div class="report-section">
            <h4>Confidence Assessment</h4>
            <div class="score-bars">
                <div class="score-bar-row">
                    <span class="score-bar-label">Confidence</span>
                    <div class="score-bar-track"><div class="score-bar-fill green" style="width:${Math.round(conf * 100)}%"></div></div>
                    <span class="score-bar-value">${(conf * 100).toFixed(0)}%</span>
                </div>
                <div class="score-bar-row">
                    <span class="score-bar-label">Upside</span>
                    <div class="score-bar-track"><div class="score-bar-fill amber" style="width:60%"></div></div>
                    <span class="score-bar-value">60%</span>
                </div>
                <div class="score-bar-row">
                    <span class="score-bar-label">Boldness</span>
                    <div class="score-bar-track"><div class="score-bar-fill blue" style="width:40%"></div></div>
                    <span class="score-bar-value">40%</span>
                </div>
            </div>
        </div>

        <div class="report-section">
            <h4>Summary</h4>
            <p>${esc(r.summary_ko || 'No summary available.')}</p>
        </div>

        ${apis.length ? `
        <div class="report-section">
            <h4>Dependencies</h4>
            <div class="api-pills">
                ${apis.map(a => `<span class="api-pill${a.necessity === '필수' ? ' required' : ''}">${esc(a.name)}</span>`).join('')}
            </div>
            <p style="margin-top:0.8rem;">${apis.map(a => `${esc(a.name)}: ${esc(a.necessity)} — ${esc(a.reason)}`).join('<br>')}</p>
        </div>` : ''}

        <div class="report-section">
            <h4>Risk Factors</h4>
            <p>${esc(r.regulatory_risks || 'No significant risks identified.')}</p>
        </div>

        <div class="report-section">
            <h4>Competitive Landscape</h4>
            <p>${esc(r.competitor_analysis || 'No competitor data available.')}</p>
        </div>

        ${r.monetization_ko ? `
        <div class="report-section">
            <h4>Monetization Strategy</h4>
            <p>${esc(r.monetization_ko)}</p>
        </div>` : ''}

        ${full ? `
        <div class="report-section">
            <h4>Integration Template</h4>
            <div class="template-box">
                <pre>${esc(JSON.stringify(full, null, 2))}</pre>
            </div>
        </div>` : ''}

        <div class="report-section">
            <h4>Citations</h4>
            <div class="citation-list">
                <span class="citation-item">KLD-${String(svc.id).padStart(3, '0')} — ${esc(svc.source)}</span>
                <span class="citation-item">Score: ${score}/100 — Analysis by KLD Engine</span>
            </div>
        </div>

        <div class="report-section">
            <h4>Notes</h4>
            <p>${esc(r.estimated_dev_time || 'Dev time estimate not available.')} — ${r.free_tier ? 'Free tier analysis. Subscribe for integration templates.' : 'Full analysis with template code.'}</p>
        </div>
    `;
}

// === Utilities ===
function esc(text) {
    if (!text) return '';
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
}

function safeJSON(str) {
    if (!str) return null;
    try { return JSON.parse(str); } catch { return null; }
}

// === Event Listeners ===
document.getElementById('source-filter').addEventListener('change', fetchServices);
document.getElementById('score-filter').addEventListener('change', fetchServices);
document.getElementById('search-input').addEventListener('input', fetchServices);

document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
        selectedId = null;
        document.querySelectorAll('.list-row').forEach(c => c.classList.remove('active'));
        document.getElementById('brief-panel').innerHTML = `
            <div class="brief-empty">
                <h3>OPPORTUNITY BRIEF</h3>
                <p>Select an item to view the full localization analysis.</p>
            </div>`;
    }
});

// === Init ===
fetchStats();
fetchSources();
fetchServices();
