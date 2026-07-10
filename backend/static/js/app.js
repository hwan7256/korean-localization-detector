/* KLD Dashboard — Side Brief Panel */
const API = '';

// === State ===
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
    const free = document.getElementById('free-only').checked;

    let url = `${API}/api/services?limit=100`;
    if (src) url += `&source=${encodeURIComponent(src)}`;
    if (minS > 0) url += `&min_score=${minS}`;
    if (free) url += `&free_only=true`;

    const r = await fetch(url);
    const d = await r.json();

    document.getElementById('result-count').textContent = `${d.count} result${d.count !== 1 ? 's' : ''}`;

    const container = document.getElementById('service-list');
    container.innerHTML = d.services.map(s => renderCard(s)).join('');

    // Restore selection
    if (selectedId) {
        const el = document.querySelector(`.service-card[data-id="${selectedId}"]`);
        if (el) el.classList.add('active');
    }
}

function renderCard(s) {
    const score = s.localization_score;
    let scoreClass, scoreText;
    if (score === null || score === undefined) {
        scoreClass = 'score-none';
        scoreText = '--';
    } else if (score >= 70) {
        scoreClass = 'score-high';
        scoreText = score;
    } else if (score >= 40) {
        scoreClass = 'score-mid';
        scoreText = score;
    } else {
        scoreClass = 'score-low';
        scoreText = score;
    }

    return `
    <div class="service-card" data-id="${s.id}" onclick="selectService(${s.id})">
        <div class="card-header">
            <span class="card-title">${esc(s.name)}</span>
            <span class="score-badge ${scoreClass}">${scoreText}</span>
        </div>
        <div class="card-summary">${esc(s.summary_ko || s.description || 'Awaiting analysis...')}</div>
        <div class="card-meta">
            <span class="source-tag">${esc(s.source)}</span>
            ${s.analyzed_at ? `<span>${timeAgo(s.analyzed_at)}</span>` : ''}
        </div>
    </div>`;
}

// === Select Service ===
async function selectService(id) {
    selectedId = id;

    // Active toggle
    document.querySelectorAll('.service-card').forEach(c => c.classList.remove('active'));
    const el = document.querySelector(`.service-card[data-id="${id}"]`);
    if (el) el.classList.add('active');

    // Fetch report
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
            <div class="brief-service-title">${esc(svc.name)}</div>
            <a class="brief-service-url" href="${esc(svc.url)}" target="_blank">${esc(svc.url)}</a>
            <div class="brief-section"><p>This service has not been analyzed yet.</p></div>`;
        return;
    }

    const score = r.localization_score;
    const apis = safeJSON(r.required_korean_apis) || [];
    const full = safeJSON(r.template_code);

    panel.innerHTML = `
        <div class="brief-service-title">${esc(svc.name)}</div>
        <a class="brief-service-url" href="${esc(svc.url)}" target="_blank">${esc(svc.url)}</a>

        <div class="brief-section">
            <h4>Localization Score</h4>
            <span class="big-score">${score}/100</span>
            <p>${esc(r.localization_reason || '')}</p>
        </div>

        <div class="brief-section">
            <h4>Summary</h4>
            <p>${esc(r.summary_ko || '')}</p>
        </div>

        ${apis.length ? `
        <div class="brief-section">
            <h4>Required Korean APIs</h4>
            <div class="api-pills">
                ${apis.map(a => `<span class="api-pill${a.necessity === '필수' ? ' required' : ''}">${esc(a.name)} — ${esc(a.necessity)}</span>`).join('')}
            </div>
        </div>` : ''}

        <div class="brief-section">
            <h4>Regulatory Risks</h4>
            <p>${esc(r.regulatory_risks || 'None identified')}</p>
        </div>

        <div class="brief-section">
            <h4>Competitor Analysis</h4>
            <p>${esc(r.competitor_analysis || 'No data')}</p>
        </div>

        <div class="brief-section">
            <h4>Estimated Dev Time</h4>
            <p>${esc(r.estimated_dev_time || 'Unknown')}</p>
        </div>

        ${r.monetization_ko ? `
        <div class="brief-section">
            <h4>Monetization (KR)</h4>
            <p>${esc(r.monetization_ko)}</p>
        </div>` : ''}

        ${full ? `
        <div class="brief-section">
            <h4>Integration Template</h4>
            <div class="template-box">
                <pre>${esc(JSON.stringify(full, null, 2))}</pre>
            </div>
        </div>` : ''}
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

function timeAgo(ts) {
    const d = new Date(ts);
    const now = new Date();
    const diff = Math.floor((now - d) / 1000);
    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
}

// === Event Listeners ===
document.getElementById('source-filter').addEventListener('change', fetchServices);
document.getElementById('score-filter').addEventListener('change', fetchServices);

// Esc key to close (not needed with side panel, but good UX)
document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
        selectedId = null;
        document.querySelectorAll('.service-card').forEach(c => c.classList.remove('active'));
        document.getElementById('brief-panel').innerHTML = `
            <div class="brief-empty">
                <h3>OPPORTUNITY BRIEF</h3>
                <p>Select a service to view the localization analysis.</p>
            </div>`;
    }
});

// === Init ===
fetchStats();
fetchSources();
fetchServices();
