import {persons,filterPeople,quality,references,dateLabel,table,norm} from '../common.mjs?v=1.5.0';

export async function mount(root,ctx){
  const a=ctx.archive,esc=ctx.esc,byid=persons(a);let tab='search',extra=null,sourceQuery='';
  root.innerHTML='<p class="muted">Gezielt suchen, Fundstellen nachlesen und mögliche Fehler prüfen.</p><div class="mod-tabs"><button type="button" data-tab="search" class="primary">Erweiterte Suche</button><button type="button" data-tab="quality">Datenprüfung</button><button type="button" data-tab="sources">Quellen & Fundstellen</button></div><div data-panel></div>';
  const panel=root.querySelector('[data-panel]');
  const print=()=>{const b=panel.querySelector('[data-print]');if(b)b.onclick=()=>window.print();};
  function toolbar(){return '<div class="mod-toolbar"><button type="button" data-print>Drucken / als PDF speichern</button></div>';}
  function search(){
    panel.innerHTML=`<form data-module-form class="mod-form"><label>Name / Geburtsname / Variante<input name="q" type="search"></label><label>Geburts- oder Sterbeort<input name="place" type="search"></label><label>Geburtsjahr ab<input name="from" type="number" min="1" max="9999"></label><label>Geburtsjahr bis<input name="to" type="number" min="1" max="9999"></label><label>Lebensstatus<select name="status"><option value="">Alle</option><option value="dead">Als verstorben erfasst</option><option value="living">Ausdrücklich als lebend erfasst</option><option value="unknown">Unbekannt</option></select></label><button type="submit" class="primary">Suchen</button></form>${toolbar()}<section class="mod-result" aria-live="polite"></section>`;
    const form=panel.querySelector('form'),result=panel.querySelector('.mod-result');
    function run(){
      const data=Object.fromEntries(new FormData(form));
      if(data.from&&data.to&&Number(data.from)>Number(data.to)){result.innerHTML='<p class="error">Das erste Jahr muss vor oder gleich dem letzten Jahr liegen.</p>';return;}
      const list=filterPeople(a,data);
      result.innerHTML='<p class="mod-count">'+list.length+' Treffer</p>'+table(['Person','Geburt','Tod','Orte'],list.map(p=>[ctx.personButton(p.id),esc(dateLabel(p.geburt?.datum)),esc(dateLabel(p.tod?.datum)),esc(p.geburt?.ort_original||'—')+'<br>'+esc(p.tod?.ort_original||'—')]));
    }
    form.onsubmit=e=>{e.preventDefault();run();};run();print();
  }
  function check(){
    const list=quality(a),types=[...new Set(list.map(x=>x.type))].sort();
    panel.innerHTML='<p class="card mod-warning">Prüfhinweise sind Verdachtsfälle. Namensgleichheit ist kein Beweis für eine Dublette. Es wird nichts automatisch korrigiert oder zusammengeführt.</p><form data-module-form class="mod-form"><label>Art des Hinweises<select name="type"><option value="">Alle Hinweise</option>'+types.map(t=>'<option>'+esc(t)+'</option>').join('')+'</select></label></form>'+toolbar()+'<section class="mod-result" aria-live="polite"></section>';
    const form=panel.querySelector('form'),result=panel.querySelector('.mod-result');
    const draw=()=>{const rows=list.filter(x=>!form.elements.type.value||x.type===form.elements.type.value);result.innerHTML='<p class="mod-count">'+rows.length+' Hinweise</p>'+table(['Kategorie','Person / Vergleich','Hinweis'],rows.map(x=>[esc(x.type),x.personId?ctx.personButton(x.personId)+(x.otherId?'<br>'+ctx.personButton(x.otherId):''):'—',esc(x.message)+(x.recordId?'<br><small>'+esc(x.recordId)+'</small>':'')]));};
    form.onchange=draw;form.onsubmit=e=>e.preventDefault();draw();print();
  }
  async function sources(){
    panel.innerHTML='<p>Quellen werden geladen …</p>';
    try{
      extra??=await ctx.api('/api/modules/research/data');
      if(!ctx.isCurrent()||!root.isConnected||tab!=='sources')return;
      const index=new Map(extra.quellen.map(s=>[s.id,s])),uses=[];
      for(const p of a.personen||[])for(const ref of references(p))uses.push({...ref,personId:p.id});
      for(const f of a.familien||[])for(const ref of references(f))uses.push({...ref,personId:(f.partner_person_ids||[]).find(id=>byid.has(id))||'',path:'Familie '+f.id+' · '+ref.path});
      for(const r of a.beziehungen||[])for(const ref of references(r))uses.push({...ref,personId:byid.has(r.zu_person_id)?r.zu_person_id:r.von_person_id,path:'Verbindung '+r.id+' · '+ref.path});
      const unique=[...new Map(uses.map(r=>[[r.quelle_id,r.personId,r.path,r.seite,r.fundstelle].join('|'),r])).values()];
      panel.innerHTML='<form data-module-form class="mod-form"><label>Quelle / Titel / Autor suchen<input name="q" type="search" value="'+esc(sourceQuery)+'"></label><label>Fundstellen für Quelle<select name="source"><option value="">Alle Quellen</option>'+extra.quellen.map(s=>'<option value="'+esc(s.id)+'">'+esc(s.titel||s.id)+'</option>').join('')+'</select></label><button type="submit" class="primary">Filtern</button></form><p class="mod-note">Der Quellenstatus und der Status einzelner Belege sind getrennte Angaben. Eine Familienzusammenstellung ist keine unabhängige Primärquelle.</p>'+toolbar()+'<section class="mod-result" aria-live="polite"></section>';
      const form=panel.querySelector('form'),result=panel.querySelector('.mod-result');
      function draw(){
        sourceQuery=form.elements.q.value;const source=form.elements.source.value;
        const selected=extra.quellen.filter(s=>(!source||s.id===source)&&(!sourceQuery||norm([s.titel,s.autor,s.id].join(' ')).includes(norm(sourceQuery))));
        const ids=new Set(selected.map(s=>s.id)),refs=unique.filter(r=>ids.has(r.quelle_id));
        const missing=[...new Set(unique.filter(r=>!index.has(r.quelle_id)).map(r=>r.quelle_id))];
        result.innerHTML='<h2>'+selected.length+' Quellen</h2>'+table(['Quelle','Autor / Datum','Quellenstatus','Fundstellen'],selected.map(s=>[esc(s.titel||s.id),esc(s.autor||'—')+'<br>'+esc(s.datum||'—'),(s.primaerquelle===true?'Primärquelle':'Keine bestätigte Primärquelle')+'<br>'+(s.geprueft===true?'Als geprüft erfasst':'Ungeprüft'),String(unique.filter(r=>r.quelle_id===s.id).length)]))+
          '<h2>Fundstellen ('+refs.length+')</h2>'+table(['Person','Quelle / Seite','Angabe','Belegstatus'],refs.map(r=>[r.personId?ctx.personButton(r.personId):'—',esc(index.get(r.quelle_id)?.titel||r.quelle_id)+'<br>Seite: '+esc(r.seite??'—'),esc(r.path)+(r.fundstelle?'<br>'+esc(r.fundstelle):''),esc(r.belegart||'Nicht angegeben')+'<br>'+(r.extern_geprueft===true?'Extern geprüft':'Nicht extern geprüft')]))+
          (missing.length?'<p class="error">Nicht aufgelöste Quellenverweise: '+missing.map(esc).join(', ')+'</p>':'');
      }
      form.onsubmit=e=>{e.preventDefault();draw();};form.elements.source.onchange=draw;draw();print();
    }catch(e){if(ctx.isCurrent()&&tab==='sources')panel.innerHTML='<p class="error">'+esc(e.message)+'</p>';}
  }
  root.querySelectorAll('[data-tab]').forEach(b=>b.onclick=()=>{tab=b.dataset.tab;root.querySelectorAll('[data-tab]').forEach(x=>x.classList.toggle('primary',x===b));if(tab==='search')search();else if(tab==='quality')check();else sources();});
  search();
}
