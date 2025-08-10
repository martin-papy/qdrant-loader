(function(){
  function addCopyButtons(){
    document.querySelectorAll('pre > code').forEach((code) => {
      const pre = code.parentElement;
      if(pre.classList.contains('ql-has-copy')) return;
      pre.classList.add('ql-has-copy','position-relative');
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn btn-sm btn-light position-absolute';
      btn.style.top = '0.5rem';
      btn.style.right = '0.5rem';
      btn.setAttribute('aria-label', 'Copy code');
      btn.innerHTML = '<i class="bi bi-clipboard"></i>';
      btn.addEventListener('click', async () => {
        try {
          const text = code.innerText;
          await navigator.clipboard.writeText(text);
          btn.innerHTML = '<i class="bi bi-clipboard-check"></i>';
          setTimeout(()=> btn.innerHTML = '<i class="bi bi-clipboard"></i>', 1200);
        } catch (e) {
          btn.innerHTML = '<i class="bi bi-clipboard-x"></i>';
          setTimeout(()=> btn.innerHTML = '<i class="bi bi-clipboard"></i>', 1200);
        }
      });
      pre.appendChild(btn);
    });
  }

  function addLanguageLabels(){
    document.querySelectorAll('pre > code').forEach((code) => {
      const pre = code.parentElement;
      if(pre.querySelector('.ql-lang')) return;
      const cls = code.className || '';
      // prism uses language-xxx; basic md may have none
      let lang = '';
      const m = cls.match(/language-([a-z0-9]+)/i);
      if(m) lang = m[1];
      if(!lang) return;
      const badge = document.createElement('span');
      badge.className = 'badge text-bg-light position-absolute ql-lang';
      badge.style.top = '0.5rem';
      badge.style.left = '0.5rem';
      badge.textContent = lang.toUpperCase();
      pre.classList.add('position-relative');
      pre.appendChild(badge);
    });
  }

  document.addEventListener('DOMContentLoaded', function(){
    addCopyButtons();
    addLanguageLabels();
  });
})();


