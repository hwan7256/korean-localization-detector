/* KLD Dashboard — Triage Table (exact mockup spec) */

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
    try {
        const r = await fetch(`${API}/api/services`);
        const d = await r.json();
        allServices = d.services;
        renderTable();
    } catch(e) {
        console.error('Fetch error:', e);
    }
}

// === Render Table ===
function renderTable() {
    const scoreTh = parseInt(document.getElementById('score-filter').value) || 0;
    const confTh = parseFloat(document.getElementById('conf-filter').value) || 0;
    const src = document.getElementById('source-filter').value;
    const status = document.getElementById('status-filter').value;
    const search = (document.getElementById('search-input').value || '').toLowerCase();

    let filtered = allServices.filter(s => {
        if (s.score === null || s.score === undefined) return false;
        if (s.score < scoreTh) return false;
        if ((s.confidence ?? 0) < confTh) return false;
        if (src && s.source !== src) return false;
        if (status === 'reviewed' && s.status !== 'reviewed') return false;
        if (search && !s.name.toLowerCase().includes(search)) return false;
        return true;
    });

    // Sort
    filtered.sort((a, b) => {
        let va, vb;
        switch (currentSort) {
            case 'name': va = a.name; vb = b.name; break;
            case 'score': va = a.score || 0; vb = b.score || 0; break;
            case 'confidence': va = a.confidence || 0; vb = b.confidence || 0; break;
            case 'upside': va = a.upside || 0; vb = b.upside || 0; break;
            default: return 0;
        }
        if (typeof va === 'string') return sortDesc ? vb.localeCompare(va) : va.localeCompare(vb);
        return sortDesc ? vb - va : va - vb;
    });

    document.getElementById('result-count').textContent = `${filtered.length} results`;

    const tbody = document.getElementById('table-body');
    tbody.innerHTML = filtered.map(s => {
        const score = s.score || 0;
        const scoreClass = score >= 70 ? 'high' : score >= 40 ? 'mid' : 'low';
        const conf = Math.round((s.confidence || 0) * 100);
        const up = Math.round((s.upside || 0) * 100);
        const isSelected = selectedId === s.id;

        return `<tr class="${isSelected ? 'selected' : ''}" onclick="selectService(${s.id})">
            <td class="service-name" style="font-weight:600">${esc(s.name)}</td>
            <td>
                <div class="score-cell">
                    <div class="score-bar"><div class="score-bar-fill ${scoreClass}" style="width:${score}%"></div></div>
                    <span class="score-num ${scoreClass}">${score}</span>
                </div>
            </td>
            <td>
                <div class="mini-bar"><div class="mini-bar-fill conf" style="width:${conf}%"></div></div>
                <span class="mini-val">${conf}%</span>
            </td>
            <td>
                <div class="mini-bar"><div class="mini-bar-fill upside" style="width:${up}%"></div></div>
                <span class="mini-val">${up}%</span>
            </td>
            <td><span class="status-dot ${s.status === 'reviewed' ? 'reviewed' : ''}"></span></td>
            <td><a href="${esc(s.url)}" target="_blank" class="open-link" onclick="event.stopPropagation()">↗</a></td>
        </tr>`;
    }).join('');
}

function esc(s) { return (s || '').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

// === Select Service ===
function selectService(id) {
    selectedId = id;
    renderTable();
    fetchReport(id);
}

async function fetchReport(id) {
    const panel = document.getElementById('detail-panel');
    panel.innerHTML = '<div class="detail-empty"><p>Loading...</p></div>';
    try {
        const r = await fetch(`${API}/api/report/${id}`);
        const d = await r.json();
        renderDetail(d);
    } catch(e) {
        panel.innerHTML = '<div class="detail-empty"><p>Error loading report</p></div>';
    }
}

function renderDetail(d) {
    const svc = d.service || {};
    const rep = d.report || {};
    const score = rep.localization_score || 0;
    const scoreClass = score >= 70 ? 'high' : score >= 40 ? 'mid' : 'low';

    const panel = document.getElementById('detail-panel');
    panel.innerHTML = `<div class="detail-content">
        <div class="big-score">
            <span class="big-score-num ${scoreClass}">${score}</span>
            <span class="big-score-label">/100 local score</span>
        </div>
        <div class="detail-meta">${esc(svc.name)} · ${esc(svc.source || '')}</div>

        <div class="metric-group">
            <div class="metric-row">
                <span class="metric-label">Confidence</span>
                <div class="metric-bar"><div class="metric-fill conf" style="width:${Math.round((rep.confidence||0)*100)}%"></div></div>
                <span class="metric-val">${Math.round((rep.confidence||0)*100)}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Upside</span>
                <div class="metric-bar"><div class="metric-fill upside" style="width:${Math.round((rep.upside||0)*100)}%"></div></div>
                <span class="metric-val">${Math.round((rep.upside||0)*100)}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Boldness</span>
                <div class="metric-bar"><div class="metric-fill boldness" style="width:${Math.round((rep.boldness||0)*100)}%"></div></div>
                <span class="metric-val">${Math.round((rep.boldness||0)*100)}</span>
            </div>
            <div class="metric-row">
                <span class="metric-label">Total</span>
                <div class="metric-bar"><div class="metric-fill total" style="width:${score}%"></div></div>
                <span class="metric-val">${score}</span>
            </div>
        </div>

        <div class="detail-section">
            <h3>Summary</h3>
            <p>${esc(rep.summary || 'No summary available.')}</p>
        </div>

        <div class="detail-section" id="risk-section">
            <h3>Risk Factors</h3>
            <ul class="risk-list">${renderRisks(rep.risk_factors)}</ul>
        </div>

        <div class="detail-section">
            <h3>Next Actions</h3>
            <ul class="action-list">${renderActions(rep.next_actions)}</ul>
        </div>

        <button class="review-btn" onclick="markReviewed(${svc.id})">
            ${svc.status === 'reviewed' ? '✓ Reviewed' : 'Mark Reviewed'}
        </button>
    </div>`;
}

function renderRisks(risks) {
    if (!risks) return '<li>No specific risks identified</li>';
    try {
        const arr = typeof risks === 'string' ? JSON.parse(risks) : risks;
        return arr.map(r => `<li>⚠ ${esc(typeof r === 'string' ? r : r.risk || r)}</li>`).join('');
    } catch(e) {
        return `<li>⚠ ${esc(String(risks))}</li>`;
    }
}

function renderActions(actions) {
    if (!actions) return '<li>No actions suggested</li>';
    try {
        const arr = typeof actions === 'string' ? JSON.parse(actions) : actions;
        return arr.map((a, i) =>
            `<li><span class="action-num">${i+1}.</span><span>${esc(typeof a === 'string' ? a : a.action || a)}</span></li>`
        ).join('');
    } catch(e) {
        return `<li><span class="action-num">1.</span><span>${esc(String(actions))}</span></li>`;
    }
}

async function markReviewed(id) {
    try {
        await fetch(`${API}/api/review/${id}`, { method: 'POST' });
        const svc = allServices.find(s => s.id === id);
        if (svc) svc.status = 'reviewed';
        renderTable();
        if (selectedId === id) fetchReport(id);
    } catch(e) {}
}

// === Sort ===
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.sortable').forEach(th => {
        th.addEventListener('click', () => {
            const col = th.dataset.sort;
            if (currentSort === col) {
                sortDesc = !sortDesc;
            } else {
                currentSort = col;
                sortDesc = true;
            }
            document.querySelectorAll('.sortable').forEach(h => {
                h.classList.remove('active-sort');
                h.querySelector('.sort-arrow').textContent = '▲';
            });
            th.classList.add('active-sort');
            th.querySelector('.sort-arrow').textContent = sortDesc ? '▼' : '▲';
            renderTable();
        });
    });

    // Filters
    ['source-filter','score-filter','conf-filter','status-filter'].forEach(id => {
        document.getElementById(id).addEventListener('change', renderTable);
    });
    document.getElementById('search-input').addEventListener('input', renderTable);
    
    fetchStats();
    fetchSources();
    fetchServices();
});
