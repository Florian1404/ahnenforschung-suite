import {events,EVENT_LABELS,personOptions,dateLabel,table} from '../common.mjs?v=1.5.0';

export function csvCell(value){
  let s=String(value??'');if(/^\s*[=+@\-\t\r]/.test(s))s="'"+s;
  return '"'+s.replace(/"/g,'""')+'"';
}
export function eventCsv(rows){
  return '\uFEFF'+[['Person','Ereignis','Datum (Original/Genauigkeit)','Ort'],...rows.map(e=>[e.name,e.label,dateLabel(e.date),e.place])].map(row=>row.map(csvCell).join(';')).join('\r\n');
}
export function anniversaries(rows,month){
  return rows.filter(e=>['geburt','hochzeit','tod'].includes(e.type)&&e.info?.precision===3&&!e.info.uncertain&&e.info.month===month).sort((a,b)=>a.info.day-b.info.day||a.name.localeCompare(b.name,'de'));
}
export function mount(root,ctx){
  const a=ctx.archive,esc=ctx.esc;let exportRows=[];
  const months=['Januar','Februar','März','April','Mai','Juni','Juli','August','September','Oktober','November','Dezember'];
  root.innerHTML=`<p class="muted">Lebensereignisse im Zusammenhang sehen. Unvollständige und unsichere Datumsangaben bleiben sichtbar gekennzeichnet.</p>
    <form data-module-form class="mod-form"><label>Person<select name="person">${personOptions(a,'',esc,'Gesamter Bestand')}</select></label><label>Ansicht<select name="mode"><option value="timeline">Chronik</option><option value="anniversary">Jahrestage nach Monat</option></select></label><label data-event-label>Ereignis<select name="type"><option value="">Alle Ereignisse</option>${Object.entries(EVENT_LABELS).map(([k,v])=>`<option value="${k}">${v}</option>`).join('')}</select></label><label data-from-label>Jahr ab<input name="from" type="number" min="1" max="9999"></label><label data-to-label>Jahr bis<input name="to" type="number" min="1" max="9999"></label><label data-month-label hidden>Monat<select name="month">${months.map((m,i)=>`<option value="${i+1}" ${i===new Date().getMonth()?'selected':''}>${m}</option>`).join('')}</select></label><button type="submit" class="primary">Anzeigen</button></form>
    <div class="mod-toolbar"><button type="button" data-print>Drucken / als PDF speichern</button><button type="button" data-csv>Ergebnis als CSV</button></div><section class="mod-result" aria-live="polite"></section>`;
  const form=root.querySelector('form'),result=root.querySelector('.mod-result');
  function render(){
    const f=Object.fromEntries(new FormData(form)),anniv=f.mode==='anniversary',all=events(a,{personId:f.person,includeUndated:true});
    for(const key of ['event','from','to'])root.querySelector('[data-'+key+'-label]').hidden=anniv;
    root.querySelector('[data-month-label]').hidden=!anniv;
    if(!anniv&&f.from&&f.to&&Number(f.from)>Number(f.to)){result.innerHTML='<p class="error">Das erste Jahr muss vor oder gleich dem letzten Jahr liegen.</p>';exportRows=[];return;}
    const list=anniv?anniversaries(all,Number(f.month)):all.filter(e=>(!f.type||e.type===f.type)&&(!f.from||(e.info&&e.info.year>=Number(f.from)))&&(!f.to||(e.info&&e.info.year<=Number(f.to))));
    exportRows=list;
    const heading=anniv?'Jahrestage im '+months[Number(f.month)-1]:'Chronik';
    const omitted=all.filter(e=>['geburt','hochzeit','tod'].includes(e.type)&&(!e.info||e.info.precision!==3||e.info.uncertain)).length;
    const intro=anniv?'<p class="mod-note">Historische Geburtstage, Hochzeitstage und Gedenktage. Die Anzeige ist keine Liste ausschließlich lebender Personen. '+omitted+' Ereignisse ohne eindeutigen Tag und Monat sind nicht zugeordnet. Der 29. Februar bleibt im Februar, ohne einen Ersatztermin zu erfinden.</p>':'<p class="mod-note">Bei Jahres- und Monatsangaben ist die Reihenfolge innerhalb desselben Zeitraums offen. Unsichere ISO-Daten dienen nur der ungefähren Einordnung. Angaben ohne einordenbares Datum stehen am Ende.</p>';
    result.innerHTML='<h2>'+heading+'</h2>'+intro+'<p class="mod-count">'+list.length+' Ereignisse</p>'+table([anniv?'Tag':'Datum','Ereignis','Person / Familie','Ort'],list.map(e=>[(anniv?String(e.info.day).padStart(2,'0')+'. '+months[e.info.month-1]+'<br><small>Original: '+esc(dateLabel(e.date))+'</small>':esc(dateLabel(e.date))),esc(e.label),e.personIds?e.personIds.map(ctx.personButton).join('<br>'):ctx.personButton(e.personId),esc(e.place||'—')]));
  }
  form.onsubmit=e=>{e.preventDefault();render();};form.onchange=render;
  root.querySelector('[data-print]').onclick=()=>window.print();
  root.querySelector('[data-csv]').onclick=()=>{
    const blob=new Blob([eventCsv(exportRows)],{type:'text/csv;charset=utf-8'}),url=URL.createObjectURL(blob),link=document.createElement('a');
    link.href=url;link.download='ahnenarchiv-chronik.csv';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  };
  render();
}
