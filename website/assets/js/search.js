(function(){
  const state = {
    index: null,
    data: [],
    input: null,
    results: null,
    overlay: null,
    loaded: false,
  };

  function createUI(){
    // Create overlay container if not present
    let overlay = document.getElementById('docs-search-overlay');
    if(!overlay){
      overlay = document.createElement('div');
      overlay.id = 'docs-search-overlay';
      overlay.innerHTML = `
        <div class="docs-search-backdrop" style="display:none;"></div>
        <div class="docs-search-modal card shadow" role="dialog" aria-modal="true" aria-labelledby="docs-search-title" style="display:none;position:fixed;inset:10% 10%;z-index:1050;">
          <div class="card-body p-3">
            <div class="input-group mb-2">
              <span class="input-group-text"><i class="bi bi-search"></i></span>
              <input id="docs-search-input" type="search" class="form-control" placeholder="Search docs... (/, s, ⌘/Ctrl+K)" aria-label="Search" />
            </div>
            <div id="docs-search-results" class="list-group list-group-flush" style="max-height:60vh;overflow:auto;"></div>
          </div>
        </div>`;
      document.body.appendChild(overlay);
    }
    state.overlay = overlay;
    state.input = overlay.querySelector('#docs-search-input');
    state.results = overlay.querySelector('#docs-search-results');
  }

  async function loadIndex(){
    if(state.loaded) return;
    const base = document.querySelector('link[rel="canonical"]')?.getAttribute('href') || '/docs/';
    // Compute relative path to docs root
    let docsRoot = base;
    try {
      const url = new URL(base, window.location.origin);
      docsRoot = url.pathname.endsWith('/') ? url.pathname : url.pathname + '/';
    } catch(e) {}
    const idxUrl = (window.BASE_URL || '') + 'docs/search-index.json';
    const res = await fetch(idxUrl);
    const json = await res.json();
    state.data = json;
    state.loaded = true;
  }

  function normalize(text){
    return (text || '').toLowerCase();
  }

  function search(q){
    const query = normalize(q);
    if(!query) return [];
    // Simple ranking: title > headings > content; naive contains
    return state.data
      .map(doc => {
        const titleScore = normalize(doc.title).includes(query) ? 3 : 0;
        const headingsScore = (doc.headings||[]).some(h => normalize(h).includes(query)) ? 2 : 0;
        const contentScore = normalize(doc.content).includes(query) ? 1 : 0;
        const score = titleScore + headingsScore + contentScore;
        return score ? {score, doc} : null;
      })
      .filter(Boolean)
      .sort((a,b)=> b.score - a.score)
      .slice(0, 20)
      .map(x=>x.doc);
  }

  function highlight(text, q){
    if(!text) return '';
    const i = text.toLowerCase().indexOf(q.toLowerCase());
    if(i === -1) return text.slice(0,160) + (text.length>160?'…':'');
    const start = Math.max(0, i-40);
    const end = Math.min(text.length, i + q.length + 40);
    const prefix = text.slice(start, i);
    const match = text.slice(i, i+q.length);
    const suffix = text.slice(i+q.length, end);
    return (start>0?'…':'') + prefix + '<mark>' + match + '</mark>' + suffix + (end<text.length?'…':'');
  }

  function renderResults(q){
    const results = search(q);
    state.results.innerHTML = '';
    if(!results.length){
      state.results.innerHTML = '<div class="list-group-item">No results</div>';
      return;
    }
    results.forEach(r => {
      const el = document.createElement('a');
      el.className = 'list-group-item list-group-item-action';
      el.href = (window.BASE_URL || '') + r.url;
      el.innerHTML = `<div class="fw-semibold">${r.title}</div><div class="small text-muted">${highlight(r.content, q)}</div>`;
      state.results.appendChild(el);
    });
  }

  function openOverlay(){
    state.overlay.querySelector('.docs-search-backdrop').style.display = 'block';
    state.overlay.querySelector('.docs-search-modal').style.display = 'block';
    state.input.value = '';
    state.results.innerHTML = '';
    state.input.focus();
  }
  function closeOverlay(){
    state.overlay.querySelector('.docs-search-backdrop').style.display = 'none';
    state.overlay.querySelector('.docs-search-modal').style.display = 'none';
  }

  document.addEventListener('DOMContentLoaded', async () => {
    // Only enable on docs pages
    if(!/\/docs\//.test(location.pathname)) return;
    createUI();
    await loadIndex();

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
      const modK = (e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k';
      const slash = e.key === '/' && !e.metaKey && !e.ctrlKey && !e.altKey;
      const sKey = e.key.toLowerCase() === 's' && !e.metaKey && !e.ctrlKey && !e.altKey && e.target === document.body;
      if (modK || slash || sKey) {
        e.preventDefault();
        openOverlay();
      }
      if (e.key === 'Escape') {
        closeOverlay();
      }
    });

    // Search input
    state.input.addEventListener('input', (e) => {
      const q = e.target.value.trim();
      renderResults(q);
    });

    state.overlay.querySelector('.docs-search-backdrop').addEventListener('click', closeOverlay);
  });
})();


