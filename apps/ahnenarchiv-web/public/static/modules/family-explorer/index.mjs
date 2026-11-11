import {persons,generations,shortestPath,edgeLabel,personOptions,dateLabel,table} from '../common.mjs?v=1.5.0';
import {fanSvg,hourglassSvg,ahnentafelHtml} from './diagrams.mjs?v=1.1.0';

export function mount(root,ctx){
  const a=ctx.archive,esc=ctx.esc,byid=persons(a),initial=byid.has(ctx.selected)?ctx.selected:a.personen[0]?.id;
  if(!initial){root.innerHTML='<p class="empty">Noch keine Personen vorhanden.</p>';return;}
  let svgDownload='',zoom='fit',activeMode='fan';
  root.innerHTML=`<p class="muted">Fächer, Kreis, Sanduhr und Ahnentafel – oder erfasste Verbindungswege zwischen zwei Personen entdecken.</p>
    <div class="mod-tabs"><button type="button" data-diagram-mode="fan">Fächerdiagramm</button><button type="button" data-diagram-mode="circle">Kreisdiagramm</button><button type="button" data-diagram-mode="hourglass">Sanduhr</button><button type="button" data-diagram-mode="ahnentafel">Ahnentafel</button></div>
    <form data-module-form class="mod-form"><label>Ausgangspunkt<select name="root">${personOptions(a,initial,esc)}</select></label>
    <label>Ansicht<select name="mode"><option value="fan">Fächerdiagramm</option><option value="circle">Kreisdiagramm</option><option value="hourglass">Sanduhr – Vorfahren & Nachkommen</option><option value="ahnentafel">Nummerierte Ahnentafel</option><option value="ancestors">Vorfahrenliste</option><option value="descendants">Nachkommenliste</option><option value="path">Verbindungsweg zu …</option></select></label>
    <label data-target-label hidden>Zielperson<select name="target">${personOptions(a,a.personen.find(p=>p.id!==initial)?.id||initial,esc)}</select></label>
    <label data-depth-label>Generationen<select name="depth">${[2,3,4,5,6,8,12,20].map(n=>`<option ${n===4?'selected':''}>${n}</option>`).join('')}</select></label>
    <label class="mod-check"><input type="checkbox" name="confirmed">Nur belegte Verbindungen</label>
    <label class="mod-check"><input type="checkbox" name="biological">Nur ausdrücklich biologische Elternschaft</label>
    <button type="submit" class="primary">Anzeigen</button></form>
    <p class="mod-note">„Belegt“ bezeichnet den gespeicherten Belegstatus. Die Art der Elternschaft wird zusätzlich angezeigt. Fehlende Eltern-Kind-Datensätze werden nicht aus Familienmitgliedschaften geraten.</p>
    <div class="mod-toolbar"><button type="button" data-print>Drucken / als PDF speichern</button><button type="button" data-svg>Diagramm als SVG</button><button type="button" data-chart-zoom="fit">Anpassen</button><button type="button" data-chart-zoom="125">125 %</button><button type="button" data-chart-zoom="175">175 %</button><button type="button" data-chart-zoom="original">Originalgröße</button></div><section class="mod-result" aria-live="polite"></section>`;
  const form=root.querySelector('form'),result=root.querySelector('.mod-result');
  if(['fan','circle','hourglass','ahnentafel'].includes(ctx.initialView))form.elements.mode.value=ctx.initialView;
  function applyZoom(){const el=result.querySelector('.genealogy-chart');if(el)el.className='genealogy-chart chart-zoom-'+zoom;}
  function render(){
    const data=Object.fromEntries(new FormData(form)),opts={onlyConfirmed:!!data.confirmed,biologicalOnly:!!data.biological};
    const start=byid.get(data.root),direction=data.mode;
    activeMode=direction;svgDownload='';
    const graphical=['fan','circle','hourglass'].includes(direction);
    root.querySelector('[data-svg]').hidden=!graphical;
    root.querySelectorAll('[data-chart-zoom]').forEach(b=>b.hidden=!graphical);
    root.querySelectorAll('[data-diagram-mode]').forEach(b=>b.classList.toggle('primary',b.dataset.diagramMode===direction));
    root.querySelector('[data-target-label]').hidden=direction!=='path';
    root.querySelector('[data-depth-label]').hidden=direction==='path';
    const title='<h2>'+esc(start.anzeigename)+'</h2>';
    if(graphical){
      const depth=Math.min(6,Number(data.depth)),chart=direction==='hourglass'?hourglassSvg(a,data.root,depth,opts,esc):fanSvg(a,data.root,depth,opts,esc,direction==='circle');
      const models=chart.model?[chart.model]:[chart.above,chart.below],truncated=models.some(m=>m.truncated),cycles=models.some(m=>m.nodes.some(n=>n.cycle));
      const known=new Set(models.flatMap(m=>m.nodes.filter(n=>n.id).map(n=>n.id)));
      const repeated=models.reduce((n,m)=>n+new Set(m.nodes.filter(n=>n.repeat).map(n=>n.id)).size,0);
      svgDownload=chart.svg;
      result.innerHTML=title+'<p>'+known.size+' verschiedene Personen · '+depth+' Generationen'+(direction==='hourglass'?' je Richtung':'')+(repeated?' · mehrfach vorkommende Personen mit ↺ markiert':'')+'</p>'+
        '<p class="mod-note">'+(direction==='hourglass'?'Vorfahren oben, Nachkommen unten.':'Die ausgewählte Person steht im Zentrum; ältere Generationen liegen außen. Nicht erfasste Positionen bleiben leer markiert.')+' Person anklicken oder mit Tab und Enter öffnen. Lange Namen stehen vollständig im Tooltip und in der Ahnentafel. Gestrichelte Umrandung: Weg enthält ungeklärte Verbindungen.</p>'+
        (Number(data.depth)>6?'<p class="card mod-warning">Diagramme sind auf sechs Generationen begrenzt. Für mehr Generationen die Listenansicht nutzen.</p>':'')+
        (truncated?'<p class="card mod-warning">Darstellungsgrenze erreicht: Nicht alle Zweige sind enthalten. Bitte weniger Generationen wählen.</p>':'')+
        (cycles?'<p class="card mod-warning">Ein Abstammungskreis wurde gefunden. Der betroffene Zweig endet an der markierten Person.</p>':'')+
        '<div class="genealogy-chart chart-zoom-'+zoom+'">'+chart.svg+'</div>';
      applyZoom();
    }else if(direction==='ahnentafel'){
      const t=ahnentafelHtml(a,data.root,Number(data.depth),opts,ctx);
      result.innerHTML=title+'<p class="mod-note">Pfadnummern: 1 = Ausgangspunkt, 1.1 = erster erfasster Elternzweig, 1.2 = zweiter usw. Die Reihenfolge bezeichnet keine Vater-/Mutterrolle und ist keine Kekulé-Nummerierung. Alle erfassten Elternschaftsarten bleiben entsprechend den Filtern sichtbar. Wiederholte Vorfahren erhalten je Zweig eine eigene Nummer.</p>'+
        (Number(data.depth)>8?'<p class="mod-note">Die Ahnentafel zeigt bis zu acht Generationen. Die Vorfahrenliste unterstützt bis zu zwanzig.</p>':'')+
        (t.model.truncated?'<p class="card mod-warning">Darstellungsgrenze von 1500 Einträgen erreicht. Bitte weniger Generationen wählen.</p>':'')+t.html;
    }else if(direction==='path'){
      const path=shortestPath(a,data.root,data.target,opts),target=byid.get(data.target);
      if(path===null){result.innerHTML=title+'<p class="empty">Kein erfasster Verbindungsweg zu '+esc(target.anzeigename)+' mit diesen Filtern gefunden.</p>';return;}
      if(!path.length){result.innerHTML=title+'<p>Ausgangspunkt und Ziel sind dieselbe Person.</p>';return;}
      const uncertain=path.some(e=>!e.confirmed),blood=path.every(e=>e.dir!=='partner'&&(e.record.elternschaft_typ==='biologisch'||e.record.biologisch_bestaetigt===true));
      result.innerHTML=title+'<p><strong>'+path.length+' Verbindungsschritt(e)</strong> zu '+esc(target.anzeigename)+'.</p>'+
        (uncertain?'<p class="card mod-warning">Dieser Weg enthält ungeklärte Verbindungen.</p>':'')+
        (blood?'<p>Alle Schritte sind ausdrücklich als biologische Elternschaft erfasst.</p>':'<p class="mod-note">Dies ist ein Weg durch die erfassten Familienverbindungen. Eine rein biologische Verwandtschaft ist damit nicht nachgewiesen.</p>')+
        '<ol class="mod-path"><li>'+ctx.personButton(start.id)+'</li>'+path.map(e=>'<li><small>→ '+esc(edgeLabel(e))+'</small>'+ctx.personButton(e.to)+'</li>').join('')+'</ol>'+
        '<p class="mod-note">Angezeigt wird ein kürzester Weg nach Anzahl der Schritte. Weitere Wege und gemeinsame Vorfahren können vorhanden sein.</p>';
    }else{
      const rows=generations(a,data.root,direction,Number(data.depth),opts);
      result.innerHTML=title+'<p>'+Math.max(0,rows.length-1)+' erreichbare Person(en) bis Generation '+esc(data.depth)+'. Jede Person erscheint einmal auf dem kürzesten gefundenen Generationsweg.</p>'+
        table(['Generation','Person','Lebensdaten','Verbindung / Wegstatus'],rows.map(r=>{
          const p=byid.get(r.id);
          return [String(r.generation),ctx.personButton(p.id),'* '+esc(dateLabel(p.geburt?.datum))+'<br>† '+esc(dateLabel(p.tod?.datum)),r.via?esc(edgeLabel(r.via))+'<br><span class="mod-note">über '+ctx.personButton(r.via.from)+(r.uncertain?' · enthält ungeklärte Verbindung':'')+'</span>':'Ausgangspunkt'];
        }));
    }
  }
  form.addEventListener('submit',e=>{e.preventDefault();render();});
  form.addEventListener('change',render);
  root.querySelector('[data-print]').onclick=()=>window.print();
  root.querySelectorAll('[data-diagram-mode]').forEach(b=>b.onclick=()=>{form.elements.mode.value=b.dataset.diagramMode;render();});
  root.querySelectorAll('[data-chart-zoom]').forEach(b=>b.onclick=()=>{zoom=b.dataset.chartZoom;applyZoom();});
  root.querySelector('[data-svg]').onclick=()=>{
    if(!svgDownload)return;
    const svg='<?xml version="1.0" encoding="UTF-8"?>\n'+svgDownload;
    const url=URL.createObjectURL(new Blob([svg],{type:'image/svg+xml;charset=utf-8'})),link=document.createElement('a');
    link.href=url;link.download='ahnenarchiv-'+activeMode+'.svg';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  };
  root.addEventListener('click',e=>{const n=e.target.closest('[data-chart-person]');if(n){e.preventDefault();ctx.openPerson(n.dataset.chartPerson);}});
  root.addEventListener('keydown',e=>{const n=e.target.closest('[data-chart-person]');if(n&&['Enter',' '].includes(e.key)){e.preventDefault();ctx.openPerson(n.dataset.chartPerson);}});
  render();
}
