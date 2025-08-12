(function(){
  function initMermaid(){
    if (window.mermaid && typeof window.mermaid.initialize === 'function') {
      window.mermaid.initialize({ startOnLoad: true, securityLevel: 'strict' });
    }
  }
  document.addEventListener('DOMContentLoaded', initMermaid);
})();


