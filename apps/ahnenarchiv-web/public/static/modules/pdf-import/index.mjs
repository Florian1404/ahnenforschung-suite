export async function mount(root,ctx){
 const {esc,api}=ctx;
 if(ctx.user.role!=='admin'){root.innerHTML='<p>Der Kreutzwiesner-Import steht Administratoren zur Verfügung.</p>';return;}
 let plan,choices={};
 const post=(path,data)=>api(path,{method:'POST',body:JSON.stringify(data)});
 const labels={person:'Personen',family:'Familien',relationship:'Verbindungen',media:'Medien',source:'Quellen',source_page:'Quellenseiten',issue:'Forschungsfragen'};
 function tally(obj){return Object.entries(obj||{}).map(([k,v])=>`<li>${esc(labels[k]||k)}: ${v}</li>`).join('');}
 function render(){
  if(!ctx.isCurrent())return;
  if(plan.applied){root.innerHTML=`<section class="card"><h2>Kreutzwiesner ist importiert.</h2><p>Der Import wurde am ${esc(plan.result.importiert_am)} abgeschlossen. Er wird kein zweites Mal ausgeführt.</p><p>Öffne das Archiv neu, um Personen, Verbindungen und Forschungsfragen zu laden.</p><a href="/">Archiv öffnen</a></section><p><a href="/api/kreutzwiesner/export">JSON herunterladen</a> · <a href="/api/kreutzwiesner/source" target="_blank" rel="noopener">Original-PDF öffnen</a></p>`;return;}
  root.innerHTML=`<p>Abgleich mit deinem aktuellen Datenbestand. Bestehende Angaben bleiben bevorzugt; abweichende PDF-Angaben werden mit Seitenbeleg ergänzt.</p><p><a href="/api/kreutzwiesner/export">JSON herunterladen</a> · <a href="/api/kreutzwiesner/source" target="_blank" rel="noopener">Original-PDF mit 176 Seiten öffnen</a></p><div class="mod-grid"><section class="card"><h2>Neu</h2><ul>${tally(plan.counts.neu)}</ul></section><section class="card"><h2>Ergänzt</h2><ul>${tally(plan.counts.ergaenzt)}</ul></section></div><p>${plan.statistics.pruefhinweise} Forschungsfragen aus der Vorlage. ${plan.conflicts.length} bestehende Datensätze mit abweichenden Angaben bleiben erhalten.</p>${plan.ambiguous.length?'<h2>Personen zuordnen</h2><p>Wähle für jeden Namensgleichstand die bestehende Person oder einen neuen Datensatz.</p>':''}${plan.ambiguous.map(p=>`<section class="card"><label>${esc(p.name)} · ${esc(p.geburt||'Geburt unbekannt')}<select data-match="${esc(p.id)}"><option value="">Bitte auswählen</option><option value="new">Als neue Person anlegen</option>${p.candidates.map(c=>`<option value="${esc(c.id)}">${esc(c.name)} · ${esc(c.geburt||'unbekannt')}</option>`).join('')}</select></label></section>`).join('')}<details><summary>Abweichungen zum Bestand ansehen (${plan.conflicts.length})</summary>${plan.conflicts.map(c=>`<section class="card"><h3>${esc(c.name)}</h3>${c.abweichungen.map(d=>`<p><strong>${esc(d.feld)}</strong><br>Bestand: ${esc(String(d.bestand))}<br>PDF: ${esc(String(d.vorlage))}</p>`).join('')}</section>`).join('')}</details><p class="error" data-import-error></p><div class="actions"><button type="button" data-refresh>Abgleich aktualisieren</button><button type="button" class="primary" data-apply ${plan.ambiguous.length?'disabled':''}>Kreutzwiesner jetzt importieren</button></div><p class="muted">Privater Import mit Änderungsverlauf. Wiederholtes Klicken erzeugt keine doppelten Datensätze.</p>`;
  root.querySelectorAll('[data-match]').forEach(el=>{el.onchange=()=>{choices[el.dataset.match]=el.value;};});
  root.querySelector('[data-refresh]').onclick=async()=>{await refresh();};
  root.querySelector('[data-apply]').onclick=async e=>{e.target.disabled=true;try{plan=await post('/api/kreutzwiesner/apply',{plan_hash:plan.plan_hash,choices});render();}catch(err){const out=root.querySelector('[data-import-error]');if(out)out.textContent=err.message;e.target.disabled=false;}};
 }
 async function refresh(){
  const missing=Object.entries(choices).some(([,v])=>!v);if(missing){root.querySelector('[data-import-error]').textContent='Bitte eine Person oder „Als neue Person anlegen“ auswählen.';return;}
  try{plan=Object.keys(choices).length?await post('/api/kreutzwiesner/preview',{choices}):await api('/api/kreutzwiesner/preview');render();}catch(err){root.innerHTML='<p class="error">'+esc(err.message)+'</p>';}
 }
 root.innerHTML='<p>Aktuellen Bestand abgleichen …</p>';await refresh();
}
