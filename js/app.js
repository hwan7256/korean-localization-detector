const API = 'https://api.kld.etfsimulator.blog';
let allServices = [];
let selectedId = null;
let currentSort = 'score';
let sortDesc = true;

// === Fetch & Render ===
async function fetchStats() {
    try {
        const r = await fetch(`${API}/api/stats`);
        const d = await r.json();
        document.getElementById('stat-total').textContent = d.total_services || 0;
        document.getElementById('stat-analyzed').textContent = d.total_analyzed || 0;
        const queue = Math.max(0, (d.total_services || 0) - (d.total_analyzed || 0));
        document.getElementById('stat-queue').querySelector('.badge-circle').textContent = queue;
    } catch(e) {}
}

async function fetchSources() {
    try {
        const r = await fetch(`${API}/api/sources`);
        const d = await r.json();
        const sel = document.getElementById('source-filter');
        d.sources.forEach(s => {
            const o = document.createElement('option');
            o.value = s.source;
            o.textContent = s.source;
            sel.appendChild(o);
        });
    } catch(e) {}
}

async function fetchServices() {
    const src = document.getElementById('source-filter').value;
    const minS = document.getElementById('score-filter').value;
    const minC = document.getElementById('conf-filter').value;
    const q = document.getElementById('search-input').value.toLowerCase();

    let url = `${API}/api/services?limit=100`;
    if (src) url += `&source=${encodeURIComponent(src)}`;
    if (minS > 0) url += `&min_score=${minS}`;

    try {
        const r = await fetch(url);
        const d = await r.json();
        let items = d.services || [];
        if (q) items = items.filter(s => (s.name || '').toLowerCase().includes(q));
        if (minC > 0) items = items.filter(s => (s.confidence || 0) >= parseFloat(minC));
        allServices = items;
        document.getElementById('result-count').textContent = `${items.length} results`;
        sortAndRender();
    } catch(e) {
        document.getElementById('result-count').textContent = 'Error';
    }
}

// === Sorting ===
function sortAndRender() {
    const sorted = [...allServices].sort((a, b) => {
        let va, vb;
        switch (currentSort) {
            case 'name': va = (a.name||'').toLowerCase(); vb = (b.name||'').toLowerCase(); return sortDesc ? vb.localeCompare(va) : va.localeCompare(vb);
            case 'confidence': va = a.confidence || 0; vb = b.confidence || 0; break;
            case 'upside': va = a.upside || 0; vb = b.upside || 0; break;
            default: va = getScore(a); vb = getScore(b); break;
        }
        return sortDesc ? vb - va : va - vb;
    });
    renderTable(sorted);
}

function getScore(s) { return s.score || s.localization_score || 0; }

function renderTable(items) {
    const tbody = document.getElementById('table-body');
    tbody.innerHTML = items.map(s => renderRow(s)).join('');
    if (selectedId) {
        const row = tbody.querySelector(`tr[data-id="${selectedId}"]`);
        if (row) row.classList.add('selected');
    }
}

function renderRow(s) {
    const score = getScore(s);
    const conf = s.confidence || 0.5;
    const upside = s.upside || 0.5;
    const isSelected = selectedId === s.id;
    const titleClass = isSelected ? 'cell-title active' : 'cell-title normal';
    const fillClass = isSelected ? 'green' : (score >= 65 ? 'green' : 'gold');

    let statusClass, statusText;
    if (score >= 70) { statusClass = 'viable'; statusText = 'Viable'; }
    else if (score >= 40) { statusClass = 'review'; statusText = 'Review'; }
    else if (score > 0) { statusClass = 'low'; statusText = 'Low'; }
    else { statusClass = ''; statusText = ''; }

    return `
    <tr data-id="${s.id}" onclick="selectService(${s.id})" class="${isSelected ? 'selected' : ''}">
        <td><span class="${titleClass}">${esc(s.name)}</span></td>
        <td>
            <div class="cell-score-block">
                <span class="cell-score-val">${score}/100</span>
                <div class="cell-score-track"><div class="cell-score-fill ${fillClass}" style="width:${score}%"></div></div>
            </div>
        </td>
        <td>
            <div class="cell-metric-block">
                <span class="cell-metric-val">${Math.round(conf*100)}%</span>
                <div class="cell-metric-track"><div class="cell-metric-fill" style="width:${Math.round(conf*100)}%"></div></div>
            </div>
        </td>
        <td>
            <div class="cell-metric-block">
                <span class="cell-metric-val">${Math.round(upside*100)}%</span>
                <div class="cell-metric-track"><div class="cell-metric-fill" style="width:${Math.round(upside*100)}%"></div></div>
            </div>
        </td>
        <td>${statusText ? `<span class="status-btn ${statusClass}">${statusText}</span>` : ''}</td>
        <td>${s.url ? `<a class="open-link" href="${esc(s.url)}" target="_blank" onclick="event.stopPropagation()">Open</a>` : ''}</td>
    </tr>`;
}

// === Select Service → Detail Panel ===
async function selectService(id) {
    selectedId = id;
    renderTable(allServices);

    try {
        const r = await fetch(`${API}/api/report/${id}`);
        const d = await r.json();
        renderDetail(d);
    } catch(e) {
        document.getElementById('detail-panel').innerHTML = '<div class="detail-empty"><p>Failed to load</p></div>';
    }
}

function renderDetail(data) {
    const svc = data.service || {};
    const r = data.report || {};
    const score = r ? (r.localization_score || 0) : 0;
    const conf = r.confidence || 0.5;
    const upside = r.upside || 0.5;
    const boldness = r.boldness || 0.5;

    const sections = [];

    // Score header
    sections.push(`
        <div class="detail-title">${esc(svc.name)}</div>
        ${svc.url ? `<a class="detail-url" href="${esc(svc.url)}" target="_blank">${esc(svc.url)} ↗</a>` : ''}
        <div class="detail-score-row">
            <span class="detail-big-score">${score}<span class="denom">/100</span></span>
            <div class="detail-score-bar"><div class="detail-score-fill" style="width:${score}%"></div></div>
        </div>
    `);

    // Metrics
    sections.push(`
        <div class="detail-section">
            <h4>Confidence Assessment</h4>
            <div class="detail-metrics">
                <div class="detail-metric-row">
                    <span class="detail-metric-label">Confidence</span>
                    <div class="detail-metric-track"><div class="detail-metric-fill green" style="width:${Math.round(conf*100)}%"></div></div>
                    <span class="detail-metric-val">${Math.round(conf*100)}%</span>
                </div>
                <div class="detail-metric-row">
                    <span class="detail-metric-label">Upside</span>
                    <div class="detail-metric-track"><div class="detail-metric-fill orange" style="width:${Math.round(upside*100)}%"></div></div>
                    <span class="detail-metric-val">${Math.round(upside*100)}%</span>
                </div>
                <div class="detail-metric-row">
                    <span class="detail-metric-label">Boldness</span>
                    <div class="detail-metric-track"><div class="detail-metric-fill blue" style="width:${Math.round(boldness*100)}%"></div></div>
                    <span class="detail-metric-val">${Math.round(boldness*100)}%</span>
                </div>
            </div>
        </div>
    `);

    // Rich content sections
    if (r.summary_ko || r.summary) {
        sections.push(`<div class="detail-section"><h4>Summary</h4><p>${esc(r.summary_ko || r.summary)}</p></div>`);
    }

    if (r.localization_reason) {
        sections.push(`<div class="detail-section"><h4>Localization Reason</h4><p>${esc(r.localization_reason)}</p></div>`);
    }

    if (r.competitor_analysis) {
        sections.push(`<div class="detail-section"><h4>Competitor Analysis</h4><p>${esc(r.competitor_analysis)}</p></div>`);
    }

    if (r.monetization_ko) {
        sections.push(`<div class="detail-section"><h4>Monetization Strategy</h4><p>${esc(r.monetization_ko)}</p></div>`);
    }

    if (r.estimated_dev_time) {
        sections.push(`<div class="detail-section"><h4>Estimated Dev Time</h4><p>${esc(r.estimated_dev_time)}</p></div>`);
    }

    if (r.regulatory_risks || r.risk_factors) {
        sections.push(`<div class="detail-section"><h4>Risk Factors</h4><p>${esc(r.regulatory_risks || r.risk_factors)}</p></div>`);
    }

    // Required Korean APIs
    if (r.required_korean_apis) {
        let apis = r.required_korean_apis;
        if (typeof apis === 'string') {
            try { apis = JSON.parse(apis); } catch(e) { apis = [apis]; }
        }
        if (Array.isArray(apis) && apis.length > 0) {
            const apiList = apis.map(a => {
                const name = typeof a === 'string' ? a : (a.name || '');
                const reason = typeof a === 'object' ? (a.reason || a.necessity || '') : '';
                return `<li><strong>${esc(name)}</strong>${reason ? ` — ${esc(reason)}` : ''}</li>`;
            }).join('');
            sections.push(`<div class="detail-section"><h4>Required Korean APIs</h4><ul class="api-list">${apiList}</ul></div>`);
        }
    }

    if (r.next_actions) {
        sections.push(`<div class="detail-section"><h4>Next Actions</h4><p>${esc(r.next_actions)}</p></div>`);
    }

    // Close
    sections.push(`
        <div class="detail-actions">
            <button class="detail-close" onclick="closeDetail()">Close</button>
        </div>
    `);

    document.getElementById('detail-panel').innerHTML = `<div class="detail-content">${sections.join('')}</div>`;
}

function closeDetail() {
    selectedId = null;
    renderTable(allServices);
    document.getElementById('detail-panel').innerHTML = '<div class="detail-empty"><p>Select an item to view analysis</p></div>';
}

// === Sort Headers ===
document.querySelectorAll('.triage-table th.sortable').forEach(th => {
    th.addEventListener('click', () => {
        const sortKey = th.dataset.sort;
        if (currentSort === sortKey) { sortDesc = !sortDesc; }
        else { currentSort = sortKey; sortDesc = sortKey === 'name' ? false : true; }
        updateSortHeaders();
        sortAndRender();
    });
});

function updateSortHeaders() {
    document.querySelectorAll('.triage-table th.sortable').forEach(th => {
        th.classList.remove('active-sort', 'desc');
        if (th.dataset.sort === currentSort) {
            th.classList.add('active-sort');
            if (sortDesc) th.classList.add('desc');
        }
    });
}

// === Filters ===
document.getElementById('source-filter').addEventListener('change', fetchServices);
document.getElementById('score-filter').addEventListener('change', fetchServices);
document.getElementById('conf-filter').addEventListener('change', fetchServices);
document.getElementById('status-filter').addEventListener('change', fetchServices);
document.getElementById('search-input').addEventListener('input', fetchServices);

// === Keyboard ===
document.addEventListener('keydown', e => { if (e.key === 'Escape') closeDetail(); });

// === Utilities ===
function esc(text) {
    if (!text) return '';
    const d = document.createElement('div'); d.textContent = text; return d.innerHTML;
}

// === Init ===
fetchStats();
fetchSources();
fetchServices();