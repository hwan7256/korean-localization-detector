/* KLD Dashboard — Master-Detail Triage Table */

const API = '';
let allServices = [];
let selectedId = null;
let currentSort = 'score';
let sortDesc = true;

// === Fetch & Render ===
async function fetchStats() {
    const r = await fetch(`${API}/api/stats`);
    const d = await r.json();
    document.getElementById('stat-total')?.setAttribute('data-count', d.total_services || 0);
    document.getElementById('stat-high')?.setAttribute('data-count', d.high_potential_count || 0);
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

    let items = d.services || [];
    if (q) items = items.filter(s => (s.name || '').toLowerCase().includes(q));

    allServices = items;
    document.getElementById('result-count').textContent = `${items.length} result${items.length !== 1 ? 's' : ''}`;

    sortAndRender();
}

// === Sorting ===
function sortAndRender() {
    const sorted = [...allServices].sort((a, b) => {
        let va, vb;
        switch (currentSort) {
            case 'name':
                va = (a.name || '').toLowerCase();
                vb = (b.name || '').toLowerCase();
                return sortDesc ? vb.localeCompare(va) : va.localeCompare(vb);
            case 'confidence': va = deriveConfidence(a); vb = deriveConfidence(b); break;
            case 'upside': va = deriveUpside(a); vb = deriveUpside(b); break;
            case 'score':
            default:
                va = a.localization_score || 0;
                vb = b.localization_score || 0;
                break;
        }
        return sortDesc ? vb - va : va - vb;
    });

    renderTable(sorted);
}

function renderTable(items) {
    const tbody = document.getElementById('table-body');
    tbody.innerHTML = items.map(s => renderRow(s)).join('');

    if (selectedId) {
        const row = tbody.querySelector(`tr[data-id="${selectedId}"]`);
        if (row) row.classList.add('selected');
    }
}

function renderRow(s) {
    const score = s.localization_score || 0;
    const confidence = deriveConfidence(s);
    const upside = deriveUpside(s);

    let scoreClass = 'cell-score';
    if (score < 40) scoreClass = 'cell-score-low';
    else if (score < 70) scoreClass = 'cell-score-mid';

    let statusHtml = '';
    if (score >= 70) statusHtml = '<span class="status-badge status-viable">Viable</span>';
    else if (score >= 40) statusHtml = '<span class="status-badge status-review">Review</span>';
    else if (score > 0) statusHtml = '<span class="status-badge status-low">Low</span>';

    return `
    <tr data-id="${s.id}" onclick="selectService(${s.id})">
        <td><span class="${scoreClass}">${score || '--'}</span></td>
        <td><span class="cell-name">${esc(s.name)}</span></td>
        <td><span class="cell-metric">${confidence.toFixed(2)}</span></td>
        <td><span class="cell-metric">${upside.toFixed(2)}</span></td>
        <td class="cell-status">${statusHtml}</td>
    </tr>`;
}

// === Derived Metrics ===
function deriveConfidence(s) {
    const score = s.localization_score || 0;
    return clamp(score / 100, 0.1, 0.99);
}

function deriveUpside(s) {
    const rev = parseFloat(s.revenue_estimate) || 0;
    if (rev > 50000) return 0.85;
    if (rev > 20000) return 0.72;
    if (rev > 5000) return 0.58;
    return 0.45;
}

function deriveBoldness(s) {
    const score = s.localization_score || 0;
    if (score < 30) return 0.75;
    if (score < 50) return 0.55;
    if (score < 70) return 0.40;
    return 0.30;
}

function deriveTotal(s) {
    const c = deriveConfidence(s);
    const u = deriveUpside(s);
    const b = deriveBoldness(s);
    return clamp((c * 0.4 + u * 0.35 + b * 0.25), 0.05, 0.99);
}

// === Select Service → Update Detail Panel ===
async function selectService(id) {
    selectedId = id;

    document.querySelectorAll('#table-body tr').forEach(r => r.classList.remove('selected'));
    const row = document.querySelector(`#table-body tr[data-id="${id}"]`);
    if (row) row.classList.add('selected');

    const r = await fetch(`${API}/api/report/${id}`);
    const d = await r.json();
    renderDetail(d);
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
    const total = deriveTotal(fullSvc);

    panel.innerHTML = `
    <div class="detail-content">
        <div class="detail-header">
            <div>
                <div class="detail-title">${esc(svc.name)}</div>
                ${svc.url ? `<a class="detail-url" href="${esc(svc.url)}" target="_blank">${esc(svc.url)}</a>` : ''}
            </div>
        </div>

        <div>
            <div class="detail-score-label">Localization Score</div>
            <div class="detail-score-block">
                <span class="detail-big-score">${score}<span class="denom">/100</span></span>
            </div>
        </div>

        <div class="detail-metrics">
            <div class="detail-metric-row">
                <span class="detail-metric-label">Confidence</span>
                <div class="detail-metric-track"><div class="detail-metric-fill" style="width:${Math.round(conf*100)}%"></div></div>
                <span class="detail-metric-val">${conf.toFixed(2)}</span>
            </div>
            <div class="detail-metric-row">
                <span class="detail-metric-label">Upside</span>
                <div class="detail-metric-track"><div class="detail-metric-fill" style="width:${Math.round(upside*100)}%"></div></div>
                <span class="detail-metric-val">${upside.toFixed(2)}</span>
            </div>
            <div class="detail-metric-row">
                <span class="detail-metric-label">Boldness</span>
                <div class="detail-metric-track"><div class="detail-metric-fill" style="width:${Math.round(boldness*100)}%"></div></div>
                <span class="detail-metric-val">${boldness.toFixed(2)}</span>
            </div>
            <div class="detail-metric-row">
                <span class="detail-metric-label">Total</span>
                <div class="detail-metric-track"><div class="detail-metric-fill" style="width:${Math.round(total*100)}%"></div></div>
                <span class="detail-metric-val">${total.toFixed(2)}</span>
            </div>
        </div>

        <div class="detail-section">
            <h4>Verdict</h4>
            <p>${esc(r ? r.localization_reason || 'Not yet analyzed.' : 'Not yet analyzed.')}</p>
        </div>

        ${(r && r.summary_ko) ? `
        <div class="detail-section">
            <h4>Summary</h4>
            <p>${esc(r.summary_ko)}</p>
        </div>` : ''}

        ${(r && r.regulatory_risks) ? `
        <div class="detail-section">
            <h4>Risks</h4>
            <p>${esc(r.regulatory_risks)}</p>
        </div>` : ''}

        ${(r && r.competitor_analysis) ? `
        <div class="detail-section">
            <h4>Competition</h4>
            <p>${esc(r.competitor_analysis)}</p>
        </div>` : ''}

        ${(r && r.monetization_ko) ? `
        <div class="detail-section">
            <h4>Monetization</h4>
            <p>${esc(r.monetization_ko)}</p>
        </div>` : ''}

        <div class="detail-meta">
            <div class="detail-meta-item">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                <span>0 Comments</span>
            </div>
            <div class="detail-meta-item">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
                <span>0 Attachments</span>
            </div>
        </div>

        <div class="detail-actions">
            <button class="detail-close" onclick="closeDetail()">Close</button>
        </div>
    </div>`;
}

function closeDetail() {
    selectedId = null;
    document.querySelectorAll('#table-body tr').forEach(r => r.classList.remove('selected'));
    document.getElementById('detail-panel').innerHTML = `
        <div class="detail-empty">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#909195" stroke-width="1" opacity="0.5"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>
            <p>Select an item to view analysis</p>
        </div>`;
}

// === Sort Headers ===
document.querySelectorAll('.triage-table th.sortable').forEach(th => {
    th.addEventListener('click', () => {
        const sortKey = th.dataset.sort;
        if (currentSort === sortKey) {
            sortDesc = !sortDesc;
        } else {
            currentSort = sortKey;
            sortDesc = sortKey === 'name' ? false : true;
        }
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
document.getElementById('search-input').addEventListener('input', fetchServices);

// === Keyboard ===
document.addEventListener('keydown', e => {
    if (e.key === 'Escape') closeDetail();
});

// === Utilities ===
function esc(text) {
    if (!text) return '';
    const d = document.createElement('div');
    d.textContent = text;
    return d.innerHTML;
}

function clamp(v, min, max) {
    return Math.max(min, Math.min(max, v));
}

// === Init ===
fetchSources();
fetchServices();
