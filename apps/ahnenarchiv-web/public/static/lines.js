'use strict';
const AhnenLines=(()=>{
 const norm=v=>String(v??'').normalize('NFC').trim().replace(/\s+/g,' ').toLocaleLowerCase('de');
 function unnamed(p){const n=norm(p.anzeigename??p.name??'');return !/\p{L}/u.test(n)||n.includes('?')||/^(?:unbekannt(?:e[rsnm]?)?|unknown|nicht bekannt|ohne name[n]?|namenslos|n\.?\s*n\.?)(?:$|[\s,;(])/iu.test(n)||/^(?:totgeburt|unbekanntes kind|unbekannter mann|unbekannte frau)(?:$|\s)/iu.test(n);}
 function comparePersons(a,b,direction=1){const missing=Number(unnamed(a))-Number(unnamed(b));if(missing)return missing;return String(a.anzeigename??a.name??'').localeCompare(String(b.anzeigename??b.name??''),'de',{ignorePunctuation:true})*direction||String(a.id??'').localeCompare(String(b.id??''));}

 function numbering(p){const explicit=p.daboville_nummer??p.d_aboville_nummer??p.daboville??p.nummerierung?.daboville;const values=[explicit,...(Array.isArray(p.original_nummern)?p.original_nummern:[])].filter(v=>typeof v==='string'&&v.trim()).map(v=>v.trim());return [...new Set(values)].sort((a,b)=>a.localeCompare(b,'de',{numeric:true}));}
 function parentKind(a,from,to){return parentKindRows((a.beziehungen||[]).filter(r=>r.typ==='eltern_kind'&&r.von_person_id===from&&r.zu_person_id===to));}
 function parentKindRows(rows){const types=rows.map(r=>r.elternschaft_typ);
  if(types.includes('adoptiv'))return {kind:'adoptiv',cross:true,label:'Adoptivbeziehung'};
  if(types.includes('pflege'))return {kind:'pflege',cross:true,label:'Pflegebeziehung'};
  if(types.includes('stief'))return {kind:'stief',cross:true,label:'Stiefbeziehung'};
  if(types.includes('biologisch')||rows.some(r=>r.biologisch_bestaetigt===true))return {kind:'biologisch',cross:false,label:'Leibliche Elternschaft (erfasst)'};
  if(types.includes('elternteil_aus_diagramm'))return {kind:'vorlage',cross:false,label:'Elternschaft laut Vorlage'};
  if(types.some(t=>String(t).startsWith('annahme')))return {kind:'annahme',cross:true,label:'Annahme / Adoption, Form noch ungeklärt'};
  if(types.includes('familiaere_zuordnung_ungeklaert'))return {kind:'zuordnung',cross:true,label:'Familiäre Zuordnung ungeklärt'};
  return {kind:'ungeklaert',cross:false,label:'Elternschaft noch nicht eingeordnet'};
 }
 function lineageEdges(a,includeCross=false){const rows=(a.beziehungen||[]).filter(r=>r.typ==='eltern_kind');if(includeCross)return rows;const groups=new Map(),decisions=new Map();for(const r of rows){const key=r.von_person_id+'|'+r.zu_person_id;if(!groups.has(key))groups.set(key,[]);groups.get(key).push(r);}for(const [key,group] of groups)decisions.set(key,!parentKindRows(group).cross);return rows.filter(r=>decisions.get(r.von_person_id+'|'+r.zu_person_id));}

 function surnames(p){return [...new Set([p.namen?.familienname,p.namen?.geburtsname].filter(v=>typeof v==='string'&&v.trim()).map(v=>v.trim()))];}
 function index(a,scope='family'){
  const people=a.personen||[],valid=new Set(people.map(p=>p.id)),groups=new Map(),children=new Map(),partners=new Map();
  const add=(map,a,b)=>{if(!valid.has(a)||!valid.has(b))return;if(!map.has(a))map.set(a,new Set());map.get(a).add(b);};
  for(const p of people)for(const label of surnames(p)){const key=norm(label);if(!groups.has(key))groups.set(key,{key,label,seeds:new Set()});groups.get(key).seeds.add(p.id);}
  for(const r of a.beziehungen||[]){if(r.typ==='eltern_kind')add(children,r.von_person_id,r.zu_person_id);if(r.typ==='partner'){add(partners,r.von_person_id,r.zu_person_id);add(partners,r.zu_person_id,r.von_person_id);}}
  for(const f of a.familien||[]){const ps=f.partner_person_ids||[];for(const a of ps)for(const b of ps)if(a!==b)add(partners,a,b);}
  for(const g of groups.values()){
   g.ids=new Set(g.seeds);
   if(scope==='family'){const queue=[...g.ids];for(let i=0;i<queue.length;i++)for(const id of children.get(queue[i])||[])if(!g.ids.has(id)){g.ids.add(id);queue.push(id);}
    // Partner are a final step. Do not traverse their other families and absorb the whole archive.
    for(const id of [...g.ids])for(const other of partners.get(id)||[])g.ids.add(other);
   }
  }return [...groups.values()].sort((a,b)=>a.label.localeCompare(b.label,'de'));
 }
 function members(a,key='',scope='family'){return key?(index(a,scope).find(g=>g.key===key)?.ids||new Set()):new Set((a.personen||[]).map(p=>p.id));}

 const MAIN=[
  {key:'huschka',label:'Huschka',id:'person_691a0e8c-2b7c-53f6-9796-88514b32ae2a',names:['Anton Otto Huschka'],birth:'1911-11-11'},
  {key:'kreutzwiesner',label:'Kreutzwiesner',id:'person_51241f29-0e93-57cc-bddf-b36e7b53728a',names:['Irma Huschka','Irma Kreutzwiesner'],birth:'1922-02-13'},
  {key:'böck',label:'Böck',id:'person_6d5206e0-b52c-5d8d-8b37-5fe9048f2d84',names:['Maria Stephanie Huschka','Maria Stephanie Böck'],birth:'1956-12-25'},
  {key:'schiessl',label:'Schiessl',names:['Theresia Böck','Theresia Schiessl','Theresia Schießl'],surname:['schiessl','schießl']}
 ];
 function branch(a,anchorId,scope='family',includeCross=false,seeds=[]){
  const valid=new Set((a.personen||[]).map(p=>p.id)),parents=new Map(),children=new Map(),partners=new Map();
  const add=(map,x,y)=>{if(!valid.has(x)||!valid.has(y))return;if(!map.has(x))map.set(x,new Set());map.get(x).add(y);};
  for(const r of lineageEdges(a,includeCross)){if(r.typ==='eltern_kind'){add(parents,r.zu_person_id,r.von_person_id);add(children,r.von_person_id,r.zu_person_id);}if(r.typ==='partner'){add(partners,r.von_person_id,r.zu_person_id);add(partners,r.zu_person_id,r.von_person_id);}}
  for(const r of a.beziehungen||[])if(r.typ==='partner'){add(partners,r.von_person_id,r.zu_person_id);add(partners,r.zu_person_id,r.von_person_id);}
  for(const f of a.familien||[]){const ps=f.partner_person_ids||[];for(const x of ps)for(const y of ps)if(x!==y)add(partners,x,y);}
  const ids=new Set(valid.has(anchorId)?[anchorId]:[]),up=[...ids];for(let i=0;i<up.length;i++)for(const id of parents.get(up[i])||[])if(!ids.has(id)){ids.add(id);up.push(id);}
  if(scope!=='ancestors'){for(const id of seeds)if(valid.has(id))ids.add(id);const down=[...ids];for(let i=0;i<down.length;i++)for(const id of children.get(down[i])||[])if(!ids.has(id)){ids.add(id);down.push(id);}for(const id of [...ids])for(const other of partners.get(id)||[])ids.add(other);}
  return ids;
 }
 function mainIndex(a,scope='family',customAnchor='',includeCross=false){
  const people=a.personen||[],definitions=MAIN.map(m=>({...m}));if(customAnchor)definitions.push({key:'custom',label:'Eigene Bezugsperson',id:customAnchor});
  return definitions.map(m=>{const anchor=people.find(p=>p.id===m.id)||people.find(p=>m.names?.some(n=>norm(n)===norm(p.anzeigename))&&(!m.birth||p.geburt?.datum?.iso===m.birth)&&(!m.surname||surnames(p).some(n=>m.surname.includes(norm(n)))));return {...m,anchor,ids:branch(a,anchor?.id,scope,includeCross,m.key==='custom'?[]:people.filter(p=>p.hauptlinie===m.key).map(p=>p.id))};});
 }
 function mainMembers(a,key='',scope='family',customAnchor='',includeCross=false){return key?(mainIndex(a,scope,customAnchor,includeCross).find(g=>g.key===key)?.ids||new Set()):new Set((a.personen||[]).map(p=>p.id));}
 function dateKey(d){if(!d||d.konflikt)return null;const value=d.iso;const m=typeof value==='string'&&/^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$/.exec(value);if(!m)return null;const y=+m[1],month=+(m[2]||0),day=+(m[3]||0);if(!y||m[2]&&(month<1||month>12)||m[3]&&(day<1||day>new Date(Date.UTC(y===1?2001:y,month,0)).getUTCDate()))return null;return y*10000+month*100+day;}
 function marriageRows(p,a){
  const complete=e=>!!(e?.datum?.iso||e?.datum?.konflikt||e?.ort_original||e?.freigabe);
  const families=(a.familien||[]).filter(f=>f.partner_person_ids?.includes(p.id)&&complete(f.hochzeit));
  const embedded=Array.isArray(p.hochzeiten)?p.hochzeiten:[];
  const familyIds=new Set(families.map(f=>f.id));
  const sameEvent=(x,y)=>x?.datum?.iso?x.datum.iso===y?.datum?.iso:!!x?.ort_original&&x.ort_original===y?.ort_original&&!y?.datum?.iso;
  const mirrorsPrimary=embedded.some(h=>familyIds.has(h.familie_id)&&sameEvent(p.hochzeit,h.ereignis))||
   families.some(f=>[f.hochzeit,...(Array.isArray(f.hochzeit.alternativen)?f.hochzeit.alternativen.map(h=>h.wert):[])].some(e=>sameEvent(p.hochzeit,e)));
  return [...families.map(f=>({event:f.hochzeit,ids:f.partner_person_ids})),
   ...embedded.filter(h=>complete(h.ereignis)&&!familyIds.has(h.familie_id)).map(h=>({event:h.ereignis,ids:h.partner_person_ids||[]})),
   ...(!mirrorsPrimary&&complete(p.hochzeit)?[{event:p.hochzeit,ids:[],primary:true}]:[])];
 }
 function weddingEvent(p,a){const events=marriageRows(p,a).map(r=>r.event);return events.filter(e=>dateKey(e.datum)!==null).sort((a,b)=>dateKey(a.datum)-dateKey(b.datum))[0]||events[0]||null;}
 function wedding(p,a){return weddingEvent(p,a)?.datum||null;}
 function selected(a,{line='',mainLine,customAnchor='',surname='',scope='family',includeCross=false,query='',sort='name',direction='asc'}={}){
  const ids=mainLine!==undefined?mainMembers(a,mainLine,scope,customAnchor,includeCross):members(a,line,scope),q=norm(query),factor=direction==='desc'?-1:1;
  return (a.personen||[]).filter(p=>ids.has(p.id)&&(!surname||surnames(p).some(n=>norm(n)===surname))&&(!q||norm((p.anzeigename||'')+' '+JSON.stringify(p.namen||{})).includes(q))).sort((p,q)=>{
   const missingName=Number(unnamed(p))-Number(unnamed(q));if(missingName)return missingName;
   if(sort==='daboville'){const left=numbering(p)[0],right=numbering(q)[0];if(!left&&right)return 1;if(!right&&left)return -1;if(left&&right){const n=left.localeCompare(right,'de',{numeric:true});if(n)return n*factor;}return comparePersons(p,q);}
   if(sort!=='name'){const left=dateKey(sort==='hochzeit'?wedding(p,a):p[sort]?.datum),right=dateKey(sort==='hochzeit'?wedding(q,a):q[sort]?.datum);if(left===null&&right!==null)return 1;if(right===null&&left!==null)return -1;if(left!==null&&right!==null&&left!==right)return (left-right)*factor;}
   return comparePersons(p,q,sort==='name'?factor:1);
  });
 }
 function exportSelection(a,criteria){const people=selected(a,criteria),ids=new Set(people.map(p=>p.id));const families=(a.familien||[]).filter(f=>{const involved=[...(f.partner_person_ids||[]),...(f.kinder_person_ids||[])];return involved.length&&involved.every(id=>ids.has(id));});const relationships=(a.beziehungen||[]).filter(r=>ids.has(r.von_person_id)&&ids.has(r.zu_person_id));
  const external=new Set(),refs={quellen:new Set(),orte:new Set(),medien:new Set()},allIds=new Set((a.personen||[]).map(p=>p.id));
  function scan(v,key=''){if(typeof v==='string'){if(allIds.has(v)&&!ids.has(v))external.add(v);if(key==='quelle_id')refs.quellen.add(v);if(key==='ort_id')refs.orte.add(v);if(key==='medium_id'||key==='portraet_medien_id'||key==='medien_ids')refs.medien.add(v);}else if(Array.isArray(v))v.forEach(x=>scan(x,key));else if(v&&typeof v==='object')Object.entries(v).forEach(([k,x])=>scan(x,k));}
  [people,families,relationships].forEach(x=>scan(x));
  const media=(a.medien||[]).filter(m=>{const assigned=[...(m.person_ids||[]),...(m.zuordnungen||[]).map(z=>z.person_id)];return (refs.medien.has(m.id)||assigned.some(id=>ids.has(id)))&&assigned.every(id=>ids.has(id));});scan(media);
  return {export_info:{version:'1.9.0',erstellt:new Date().toISOString(),auswahl:{...criteria},hauptlinie:criteria.mainLine?(()=>{const g=mainIndex(a,criteria.scope,criteria.customAnchor,criteria.includeCross).find(g=>g.key===criteria.mainLine);return g?.anchor?{name:g.label,bezugsperson_id:g.anchor.id,bezugsperson:g.anchor.anzeigename}:null;})():null,personen_anzahl:people.length,externe_personen_verweise:[...external],hinweis:'Hauptlinie ab Bezugsperson über erfasste Vorfahren, deren Nachkommen und Partner; optionaler Namensfilter. Vorfahren und Nachkommen können auch ungeklärte Elternverbindungen enthalten. Partner ohne deren weitere Familien. Unvollständige Familiengruppen sind nicht exportiert; externe Personenverweise bleiben in den Originaldatensätzen. Mediendateien sind nicht enthalten.'},personen:people,familien:families,beziehungen:relationships,medien:media,quellen:(a.quellen||[]).filter(s=>refs.quellen.has(s.id)),orte:(a.orte||[]).filter(p=>refs.orte.has(p.id))};
 }
 const LABELS={namen:'Namen & Varianten',berufe:'Berufe',ausbildungen:'Ausbildungen',wohnsitze:'Wohnsitze',migrationen:'Migrationen',religionsgeschichte:'Religion',militaerdienst:'Militärdienst',weitere_ereignisse:'Weitere Ereignisse',vereinsmitgliedschaften:'Vereinsmitgliedschaften',auszeichnungen:'Auszeichnungen',besitz:'Besitz',testamente:'Testamente',gesundheit:'Gesundheit',dna_tests:'DNA-Tests',kontakte:'Kontakte',merkmale:'Merkmale',anhaenge:'Anhänge',quellen_verweise:'Quellenverweise',externe_ids:'Externe Kennungen',original_nummern:'Originalnummern',forschung:'Forschungsstand',datenschutz:'Datenschutz',verwaltung:'Verwaltung',benutzerdefinierte_felder:'Zusatzfelder',geschlecht:'Geschlecht',lebensstatus:'Lebensstatus',geburtsname:'Geburtsname',familienname:'Familienname',vornamen:'Vornamen',notizen:'Notizen',biografie:'Biografie',hauptlinie:'Hauptlinie',familie:'Familienzuordnungen',hochzeiten:'Hochzeiten',herkunft:'Herkunft',ort_original:'Ort (Original)',quellen:'Quellen',datum:'Datum',iso:'Datum (ISO)',qualifizierer:'Genauigkeit',extern_geprueft:'Extern geprüft',konflikt:'Widersprüchlich',anzeigename:'Anzeigename',id:'Kennung'};
 const present=v=>v!==null&&v!==undefined&&v!==''&&(typeof v!=='object'||Object.values(v).some(present));
 function readable(v,esc,depth=0){if(!present(v))return '';if(depth>15)return '<pre class="code">'+esc(JSON.stringify(v,null,2))+'</pre>';if(typeof v!=='object')return '<span>'+esc(v===true?'Ja':v===false?'Nein':v)+'</span>';if(Array.isArray(v))return '<ul class="info-items">'+v.filter(present).map(x=>'<li>'+readable(x,esc,depth+1)+'</li>').join('')+'</ul>';return '<dl class="info-fields">'+Object.entries(v).filter(([,x])=>present(x)).map(([k,x])=>'<div><dt>'+esc(LABELS[k]||k.replace(/_/g,' '))+'</dt><dd>'+readable(x,esc,depth+1)+'</dd></div>').join('')+'</dl>';}
 return {norm,unnamed,comparePersons,numbering,parentKind,lineageEdges,surnames,index,members,branch,mainIndex,mainMembers,dateKey,wedding,weddingEvent,marriageRows,selected,exportSelection,readable};
})();
