/* KLD Dashboard — Triage Table (exact mockup spec) */

const API = '';
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
        if (minC > 0) items = items.filter(s => deriveConfidence(s) >= parseFloat(minC));
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
            case 'confidence': va = deriveConfidence(a); vb = deriveConfidence(b); break;
            case 'upside': va = deriveUpside(a); vb = deriveUpside(b); break;
            default: va = a.localization_score||0; vb = b.localization_score||0; break;
        }
        return sortDesc ? vb - va : va - vb;
    });
    renderTable(sorted);
}

function renderTable(items) {
    const tbody = document.getElementById('table-body');
    tbody.innerHTML = items.map((s, i) => renderRow(s, i === 0 && !selectedId)).join('');
    if (selectedId) {
        const row = tbody.querySelector(`tr[data-id="${selectedId}"]`);
        if (row) row.classList.add('selected');
    }
}

function renderRow(s, isFirst) {
    const score = s.localization_score || 0;
    const conf = deriveConfidence(s);
    const upside = deriveUpside(s);
    const isSelected = selectedId === s.id;
    const isGreen = isSelected || (score >= 65);

    // Title color: green if selected or high score, else gold
    const titleClass = isGreen ? 'cell-title active' : 'cell-title normal';

    // Score color
    const scoreColorClass = (score >= 70) ? '' : 'gold';
    const fillClass = (score >= 70) ? 'green' : 'gold';

    // Status button
    let statusClass, statusText;
    if (score >= 70) { statusClass = 'viable'; statusText = 'Viable'; }
    else if (score >= 40) { statusClass = 'review'; statusText = 'Review'; }
    else if (score > 0) { statusClass = 'low'; statusText = 'Low'; }
    else { statusClass = ''; statusText = ''; }

    return `
    <tr data-id="${s.id}" onclick="selectService(${s.id})" class="${isSelected ? 'selected' : ''}">
        <td>
            <div class="cell-score-block">
                <span class="cell-score-val ${scoreColorClass}">${score || '--'}/100</span>
                <div class="cell-score-track"><div class="cell-score-fill ${fillClass}" style="width:${score}%"></div></div>
            </div>
        </td>
        <td><span class="${titleClass}">${esc(s.name)}</span></td>
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

// === Derived Metrics ===
function deriveConfidence(s) { return clamp((s.localization_score || 0) / 100, 0.1, 0.99); }
function deriveUpside(s) {
    const rev = parseFloat(s.revenue_estimate) || 0;
    if (rev > 50000) return 0.85; if (rev > 20000) return 0.72; if (rev > 5000) return 0.58; return 0.45;
}
function deriveBoldness(s) {
    const score = s.localization_score || 0;
    if (score < 30) return 0.75; if (score < 50) return 0.55; if (score < 70) return 0.40; return 0.30;
}
function deriveTotal(s) { return clamp(deriveConfidence(s)*0.4 + deriveUpside(s)*0.35 + deriveBoldness(s)*0.25, 0.05, 0.99); }

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
    const panel = document.getElementById('detail-panel');
    const svc = data.service;
    const r = data.report;
    const fullSvc = allServices.find(s => s.id === svc.id) || svc;
    const score = r ? (r.localization_score || 0) : (fullSvc.localization_score || 0);
    const conf = deriveConfidence(fullSvc);
    const upside = deriveUpside(fullSvc);
    const boldness = deriveBoldness(fullSvc);

    panel.innerHTML = `
    <div class="detail-content">
        <div>
            <div class="detail-title">${esc(svc.name)}</div>
            ${svc.url ? `<a class="detail-url" href="${esc(svc.url)}" target="_blank">${esc(svc.url)}</a>` : ''}
        </div>

        <div class="detail-score-row">
            <span class="detail-big-score">${score}<span class="denom">/100</span></span>
            <div class="detail-score-bar"><div class="detail-score-fill" style="width:${score}%"></div></div>
        </div>

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

        ${(r && r.summary_ko) ? `
        <div class="detail-section">
            <h4>Summary</h4>
            <p>${esc(r.summary_ko)}</p>
        </div>` : ''}

        ${(r && r.regulatory_risks) ? `
        <div class="detail-section">
            <h4>Risk Factors</h4>
            <p>${esc(r.regulatory_risks)}</p>
        </div>` : ''}

        ${(r && r.competitor_analysis) ? `
        <div class="detail-section">
            <h4>Next Actions</h4>
            <p>${esc(r.competitor_analysis)}</p>
        </div>` : ''}

        <div class="detail-actions">
            <button class="detail-close" onclick="closeDetail()">Close</button>
            <div class="meta-row">
                <span>0 Comments</span>
                <span>0 Attachments</span>
            </div>
        </div>
    </div>`;
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
function clamp(v, min, max) { return Math.max(min, Math.min(max, v)); }

// === Init ===
fetchStats();
fetchSources();
fetchServices();
