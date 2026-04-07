let currentPage = 1;
let currentSearch = '';
let currentLanguage = '';
let totalPages = 1;
let searchTimeout = null;

async function loadHistory() {
    const container = document.getElementById('historyList');
    const paginationDiv = document.getElementById('pagination');

    container.innerHTML = `<div class="text-center py-10">${localeStrings.loading}</div>`;
    paginationDiv.innerHTML = '';

    try {
        const params = new URLSearchParams({
            page: currentPage,
            per_page: 10,
            search: currentSearch,
            language: currentLanguage
        });
        const res = await fetch(`/api/history?${params.toString()}`);
        const data = await res.json();

        totalPages = data.pages;

        if (data.items.length === 0) {
            container.innerHTML = `<div class="glass-card p-8 text-center">${localeStrings.no_history}</div>`;
        } else {
            container.innerHTML = '';
            data.items.forEach((item, index) => {
                const date = new Date(item.created_at).toLocaleString();
                const card = document.createElement('div');
                card.className = 'glass-card p-5 flex justify-between items-start flex-wrap gap-3 transition-all hover:scale-[1.02] hover:shadow-purple-500/20 opacity-0 transform translate-y-4';
                card.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                card.innerHTML = `
                    <div class="flex-1">
                        <div class="text-xs text-gray-400 mb-1">${date} [${item.language.toUpperCase()}]</div>
                        <p class="text-white">${escapeHtml(item.text.substring(0, 200))}${item.text.length > 200 ? '...' : ''}</p>
                        <div class="mt-2 flex gap-2">
                            <a href="/export/${item.id}" class="text-xs glass px-2 py-1 rounded inline-block">${localeStrings.export_txt}</a>
                            <button class="favorite-btn text-xs glass px-2 py-1 rounded" data-id="${item.id}">${localeStrings.add_favorite}</button>
                            <button class="delete-history text-red-400 text-xs" data-id="${item.id}">${localeStrings.delete}</button>
                        </div>
                    </div>
                `;
                container.appendChild(card);
                setTimeout(() => {
                    card.style.opacity = '1';
                    card.style.transform = 'translateY(0)';
                }, index * 50);
            });

            document.querySelectorAll('.favorite-btn').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const id = btn.dataset.id;
                    await fetch(`/api/favorites/${id}`, { method: 'POST' });
                    btn.innerText = localeStrings.favorited;
                    btn.disabled = true;
                });
            });
            document.querySelectorAll('.delete-history').forEach(btn => {
                btn.addEventListener('click', async (e) => {
                    const id = btn.dataset.id;
                    if (confirm(localeStrings.confirm_delete)) {
                        await fetch(`/api/history/${id}`, { method: 'DELETE' });
                        loadHistory();
                    }
                });
            });
        }

        renderPagination();

    } catch (err) {
        console.error(err);
        container.innerHTML = `<div class="glass-card p-8 text-center text-red-400">${localeStrings.error}</div>`;
    }
}

function renderPagination() {
    const paginationDiv = document.getElementById('pagination');
    if (totalPages <= 1) {
        paginationDiv.innerHTML = '';
        return;
    }
    let html = '';
    if (currentPage > 1) {
        html += `<button class="glass px-4 py-2 rounded-full hover:bg-white/10" data-page="${currentPage-1}">← ${localeStrings.previous}</button>`;
    }
    for (let i = 1; i <= totalPages; i++) {
        if (i === currentPage) {
            html += `<button class="bg-purple-600 px-4 py-2 rounded-full" disabled>${i}</button>`;
        } else if (Math.abs(i - currentPage) <= 2 || i === 1 || i === totalPages) {
            html += `<button class="glass px-4 py-2 rounded-full hover:bg-white/10" data-page="${i}">${i}</button>`;
        } else if (i === currentPage-3 || i === currentPage+3) {
            html += `<span class="px-2">...</span>`;
        }
    }
    if (currentPage < totalPages) {
        html += `<button class="glass px-4 py-2 rounded-full hover:bg-white/10" data-page="${currentPage+1}">${localeStrings.next} →</button>`;
    }
    paginationDiv.innerHTML = html;
    document.querySelectorAll('#pagination button[data-page]').forEach(btn => {
        btn.addEventListener('click', () => {
            currentPage = parseInt(btn.dataset.page);
            loadHistory();
        });
    });
}

function escapeHtml(str) {
    return str.replace(/[&<>]/g, function(m) {
        if (m === '&') return '&amp;';
        if (m === '<') return '&lt;';
        if (m === '>') return '&gt;';
        return m;
    });
}

const searchInput = document.getElementById('searchInput');
const searchBtn = document.getElementById('searchBtn');
const langFilter = document.getElementById('langFilter');

if (searchInput) {
    searchInput.addEventListener('input', () => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            currentSearch = searchInput.value;
            currentPage = 1;
            loadHistory();
        }, 300);
    });
}
if (searchBtn) {
    searchBtn.addEventListener('click', () => {
        currentSearch = searchInput.value;
        currentPage = 1;
        loadHistory();
    });
}
if (langFilter) {
    langFilter.addEventListener('change', (e) => {
        currentLanguage = e.target.value;
        currentPage = 1;
        loadHistory();
    });
}
loadHistory();