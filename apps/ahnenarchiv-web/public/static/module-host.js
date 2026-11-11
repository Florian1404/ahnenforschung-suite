'use strict';
// One integration point for optional, trusted first-party modules.
const AhnenModules = (() => {
  let selected = null, sequence = 0, requestedView = null;
  async function mount(root, moduleId=null) {
    if(moduleId) {selected=moduleId;requestedView=null;}
    const seq = ++sequence;
    const current = () => root.isConnected && seq === sequence && S.user && !S.share && !S.desktop;
    try {
      const catalog = await api('/api/modules');
      if (!current()) return;
      const m = catalog.modules.find(m => m.id === selected && m.enabled);
      const back = '<button type="button" data-module-back>← Alle Forschungsmodule</button>';
      if (m) {
        root.innerHTML = back + '<h1>'+esc(m.title)+'</h1>'+(m.id==='family-explorer'?'<p class="source">Diagramme verwenden die in der Personensuche gewählte Hauptlinie. '+(S.includeCross?'Querverbindungen sind eingeblendet.':'Adoptiv- und weitere Querverbindungen sind ausgeblendet.')+'</p>':'')+'<div data-module-content>Wird geladen …</div>';
        root.querySelector('[data-module-back]').onclick = () => { selected=null; mount(root); };
        const plugin = await import(m.asset+'?v='+encodeURIComponent(m.version));
        if (!current()) return;
        if (typeof plugin.mount !== 'function') throw Error('Modul enthält keinen gültigen Einstiegspunkt.');
        const content=root.querySelector('[data-module-content]');
        await plugin.mount(content, {
          archive: structuredClone(m.id==='family-explorer'?lineTreeArchive():S.archive), selected:S.selected, user:{role:S.user.role},
          esc, api, isCurrent:current, initialView:requestedView,
          openPerson: id => {if(current()&&person(id)){S.selected=id;S.view='detail';render();}},
          personButton: id => `<button type="button" class="person-link" data-action="person" data-id="${esc(id)}">${esc(name(id))}</button>`
        });
      } else {
        selected=null;
        root.innerHTML='<div class="hero"><div><div class="eyebrow">Werkzeugkasten · v'+esc(catalog.core_version)+'</div><h1>Familiengeschichte erforschen.</h1><p class="muted">Wähle ein Werkzeug für den nächsten Schritt deiner Recherche.</p></div></div><div class="mod-grid">'+catalog.modules.map(m=>`<section class="card"><span class="badge">${m.enabled?'Aktiv':m.compatible?'Deaktiviert':'Kernupdate erforderlich'} · v${esc(m.version)}</span><h2>${esc(m.title)}</h2><p>${esc(m.description)}</p><div class="actions">${m.enabled?`<button type="button" class="primary" data-module-open="${esc(m.id)}">Öffnen</button>`:''}${S.user.role==='admin'&&m.compatible?`<button type="button" data-module-toggle="${esc(m.id)}" data-enabled="${!m.enabled}">${m.enabled?'Deaktivieren':'Aktivieren'}</button>`:''}</div></section>`).join('')+'</div>'+(catalog.modules.length?'':'<p class="empty">Noch keine Module installiert. Die Moduldateien werden zusammen mit ihrem Manifest hochgeladen.</p>');
        root.querySelectorAll('[data-module-open]').forEach(b=>b.onclick=()=>{selected=b.dataset.moduleOpen;requestedView=null;mount(root);});
        root.querySelectorAll('[data-module-toggle]').forEach(b=>b.onclick=async()=>{
          b.disabled=true;
          try { await post('/api/modules/'+b.dataset.moduleToggle,{enabled:b.dataset.enabled==='true'}); if(current())mount(root); }
          catch(e){ if(current()){toast(e.message);b.disabled=false;} }
        });
      }
    } catch(e) {
      if(current()) {
        root.innerHTML='<h1>Forschungsmodule</h1><p class="error">'+esc(e.message)+'</p><button type="button" data-module-retry>Zur Modulübersicht</button>';
        root.querySelector('[data-module-retry]').onclick=()=>{selected=null;mount(root);};
      }
    }
  }
  function open(view){if(!S.user||S.share||S.desktop)return;selected='family-explorer';requestedView=view;S.view='modules';render();}
  return {mount,open};
})();

document.addEventListener('click',event=>{const b=event.target.closest('[data-chart-launch]');if(b){event.preventDefault();AhnenModules.open(b.dataset.chartLaunch);}});
