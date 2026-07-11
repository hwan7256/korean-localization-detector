/* KLD Landing Page — Scroll Reveal & Stats */

// Intersection Observer for scroll reveal
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('revealed');
        }
    });
}, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });

document.querySelectorAll('[data-reveal]').forEach(el => observer.observe(el));

// Fetch stats for landing page
async function fetchLandingStats() {
    try {
        const r = await fetch('/api/stats');
        const d = await r.json();
        document.getElementById('landing-total').textContent = d.total_services;
        document.getElementById('landing-analyzed').textContent = d.total_analyzed;
        document.getElementById('landing-high').textContent = d.high_potential_count;
    } catch (e) {
        // Dashboard not loaded yet, keep defaults
    }
}

// Parallax effect on hero background
window.addEventListener('scroll', () => {
    const scrolled = window.pageYOffset;
    const hero = document.querySelector('.hero-bg');
    if (hero) {
        hero.style.transform = `translateY(${scrolled * 0.3}px)`;
    }
});

fetchLandingStats();
