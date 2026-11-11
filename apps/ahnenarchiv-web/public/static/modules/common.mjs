// Domain helpers are original Ahnenarchiv code, independent of webtrees.
export const EVENT_LABELS={geburt:'Geburt',taufe:'Taufe',hochzeit:'Hochzeit',tod:'Tod',bestattung:'Bestattung',einaescherung:'Einäscherung'};
export const norm=v=>String(v??'').normalize('NFKD').replace(/\p{M}/gu,'').replace(/ß/g,'ss').toLocaleLowerCase('de').replace(/\s+/g,' ').trim();
export const persons=a=>new Map((a.personen||[]).map(p=>[p.id,p]));
export const isDead=p=>String(p.lebensstatus||'').startsWith('verstorben')||!!p.tod?.datum?.iso;
export function confirmed(r){
  if(r.belegstatus==='ungeklaert')return false;
  return r.belegt===true||r.biologisch_bestaetigt===true||(r.status==='freigegeben'&&['adoptiv','pflege','stief'].includes(r.elternschaft_typ));
}
export function edgeLabel(e){
  const typ=e.record.elternschaft_typ;
  const type={adoptiv:'Adoption',pflege:'Pflege',stief:'Stiefverhältnis',biologisch:'biologisch',elternteil_aus_diagramm:'Art aus Vorlage',ungeklaert:'Art ungeklärt'}[typ]||'Art ungeklärt';
  return (e.dir==='parent'?'Elternteil':e.dir==='child'?'Kind':'Partner')+(e.dir==='partner'?'':' · '+type)+(e.confirmed?' · belegt':' · ungeklärt');
}
export function graph(a,{onlyConfirmed=false,biologicalOnly=false}={}){
  const people=persons(a),g=new Map([...people.keys()].map(id=>[id,[]]));
  const keys=new Set();
  function add(from,to,dir,record,certainty){
    if(from===to||!people.has(from)||!people.has(to))return;
    const key=from+'|'+to+'|'+dir;
    if(keys.has(key))return;
    if(onlyConfirmed&&!certainty)return;
    keys.add(key);g.get(from).push({from,to,dir,record,confirmed:certainty});
  }
  // Explicit relationship records take priority over family membership.
  for(const r of [...(a.beziehungen||[])].sort((x,y)=>Number(confirmed(y))-Number(confirmed(x)))){
    const from=r.von_person_id,to=r.zu_person_id,yes=confirmed(r);
    if(r.typ==='eltern_kind'){
      if(biologicalOnly&&!(r.elternschaft_typ==='biologisch'||r.biologisch_bestaetigt===true))continue;
      add(from,to,'child',r,yes);add(to,from,'parent',r,yes);
    }else if(r.typ==='partner'&&!biologicalOnly){add(from,to,'partner',r,yes);add(to,from,'partner',r,yes);}
  }
  if(!biologicalOnly)for(const f of a.familien||[]){
    const partners=[...new Set(f.partner_person_ids||[])];
    for(let i=0;i<partners.length;i++)for(let j=i+1;j<partners.length;j++){
      // Do not override an explicit unconfirmed partner record with a family flag.
      const explicit=(a.beziehungen||[]).some(r=>r.typ==='partner'&&[r.von_person_id,r.zu_person_id].includes(partners[i])&&[r.von_person_id,r.zu_person_id].includes(partners[j]));
      if(!explicit){add(partners[i],partners[j],'partner',f,confirmed(f));add(partners[j],partners[i],'partner',f,confirmed(f));}
    }
  }
  return g;
}
export function shortestPath(a,from,to,opts={}){
  const g=graph(a,opts);if(!g.has(from)||!g.has(to))return null;
  if(from===to)return [];
  const queue=[from],seen=new Map([[from,null]]);
  for(let i=0;i<queue.length;i++)for(const edge of g.get(queue[i])||[]){
    if(seen.has(edge.to))continue;
    seen.set(edge.to,edge);
    if(edge.to===to){const out=[];let at=to;while(at!==from){const e=seen.get(at);out.push(e);at=e.from;}return out.reverse();}
    queue.push(edge.to);
  }
  return null;
}
export function generations(a,root,direction,depth=5,opts={}){
  const g=graph(a,opts);if(!g.has(root))return [];
  const rows=[{id:root,generation:0,via:null,uncertain:false}],seen=new Set([root]);
  for(let i=0;i<rows.length;i++){
    const r=rows[i];if(r.generation>=depth)continue;
    for(const e of g.get(r.id)||[]){
      if(e.dir!==(direction==='ancestors'?'parent':'child')||seen.has(e.to))continue;
      seen.add(e.to);rows.push({id:e.to,generation:r.generation+1,via:e,uncertain:r.uncertain||!e.confirmed});
    }
  }
  return rows;
}
export function dateInfo(d){
  if(!d||typeof d.iso!=='string'||!/^\d{4}(-\d{2})?(-\d{2})?$/.test(d.iso))return null;
  const parts=d.iso.split('-').map(Number),[y,m=1,day=1]=parts;
  const leap=y%4===0&&(y%100!==0||y%400===0),max=[31,leap?29:28,31,30,31,30,31,31,30,31,30,31];
  if(y<1||m<1||m>12||day<1||day>max[m-1])return null;
  const uncertain=d.konflikt===true||!['exakt','teilweise',undefined,null,''].includes(d.qualifizierer);
  const digits=(a,b,c)=>a*10000+b*100+c;
  return {iso:d.iso,year:y,month:parts[1]||null,day:parts[2]||null,precision:parts.length,
    min:digits(y,m,day),max:digits(y,parts.length>=2?m:12,parts.length===3?day:parts.length===2?max[m-1]:31),uncertain};
}
export function dateLabel(d){
  const v=dateInfo(d);
  if(!v)return d?.original?String(d.original)+(d.konflikt?' · widersprüchlich':''):'unbekannt';
  return (v.precision===3?v.iso.split('-').reverse().join('.'):v.iso)+(d.konflikt?' · widersprüchlich':v.uncertain?' · unsicher':'');
}
export function events(a,{personId='',includeUndated=false}={}){
  const out=[],seenMarriage=new Set(),people=persons(a);
  function add(p,ev,e,key,extra={}){
    if(!e||typeof e!=='object')return;
    const d=e.datum||{};
    if(!includeUndated&&!dateInfo(d))return;
    if(includeUndated&&!dateInfo(d)&&!d.original&&!e.ort_original)return;
    out.push({id:key,personId:p.id,name:p.anzeigename,type:ev,label:EVENT_LABELS[ev]||ev,date:d,info:dateInfo(d),place:e.ort_original||'',...extra});
  }
  for(const f of a.familien||[]){
    const ids=(f.partner_person_ids||[]).filter(id=>people.has(id));
    if(!ids.length||(personId&&!ids.includes(personId)))continue;
    const p=people.get(personId||ids[0]),d=f.hochzeit?.datum;
    if(d?.iso||d?.original||f.hochzeit?.ort_original){
      add(p,'hochzeit',f.hochzeit,'family:'+f.id,{name:ids.map(id=>people.get(id).anzeigename).join(' & '),personIds:ids});
      for(const id of ids)seenMarriage.add(id+'|'+(d?.iso||d?.original||''));
    }
  }
  for(const p of a.personen||[]){
    if(personId&&p.id!==personId)continue;
    for(const ev of Object.keys(EVENT_LABELS)){
      const e=p[ev];if(ev==='hochzeit'&&seenMarriage.has(p.id+'|'+(e?.datum?.iso||e?.datum?.original||'')))continue;
      add(p,ev,e,'person:'+p.id+':'+ev);
    }
    for(const [i,h] of (p.hochzeiten||[]).entries()){
      const e=h.ereignis;if(!e||seenMarriage.has(p.id+'|'+(e.datum?.iso||e.datum?.original||''))||e.datum?.iso===p.hochzeit?.datum?.iso)continue;
      add(p,'hochzeit',e,'person:'+p.id+':marriage:'+i);
    }
  }
  return out.sort((a,b)=>(a.info?.min??Infinity)-(b.info?.min??Infinity)||String(a.name).localeCompare(String(b.name),'de'));
}
export function filterPeople(a,f={}){
  return (a.personen||[]).filter(p=>{
    if(f.q&&!norm(p.anzeigename+' '+JSON.stringify(p.namen||{})).includes(norm(f.q)))return false;
    if(f.place&&!norm([p.geburt?.ort_original,p.tod?.ort_original].join(' ')).includes(norm(f.place)))return false;
    const y=dateInfo(p.geburt?.datum)?.year;
    if(f.from&&(!y||y<Number(f.from)))return false;
    if(f.to&&(!y||y>Number(f.to)))return false;
    if(f.status==='dead'&&!isDead(p))return false;
    if(f.status==='living'&&p.lebensstatus!=='lebend')return false;
    if(f.status==='unknown'&&(isDead(p)||p.lebensstatus==='lebend'))return false;
    return true;
  }).sort((a,b)=>String(a.anzeigename).localeCompare(String(b.anzeigename),'de'));
}
export function references(value,path='',out=[]){
  if(!value||typeof value!=='object')return out;
  if(Array.isArray(value))value.forEach((v,i)=>references(v,path+'['+i+']',out));
  else for(const [k,v] of Object.entries(value)){
    if(k==='quellen_verweise'&&Array.isArray(v)){
      for(const ref of v)if(ref&&typeof ref==='object')out.push({...ref,path:path||'Datensatz'});
    }else if(k!=='quellen_verweise')references(v,path?path+'.'+k:k,out);
  }
  return out;
}
export function quality(a){
  const out=[],byid=persons(a),groups=new Map();
  const issue=(type,p,message,extra={})=>out.push({type,personId:p?.id||'',message,...extra});
  for(const p of a.personen||[]){
    const birth=dateInfo(p.geburt?.datum),death=dateInfo(p.tod?.datum);
    if(!birth)issue('Lücken',p,'Geburtsdatum fehlt oder ist nicht als gültiges ISO-Datum erfasst.');
    if(isDead(p)&&!death)issue('Lücken',p,'Sterbedatum fehlt bei als verstorben erfasster Person.');
    if(birth&&death&&!birth.uncertain&&!death.uncertain&&death.max<birth.min)issue('Chronologie',p,'Tod liegt sicher vor der Geburt.');
    for(const ev of Object.keys(EVENT_LABELS))if(p[ev]?.datum?.konflikt)issue('Konflikte',p,EVENT_LABELS[ev]+': widersprüchliche Datumsangaben.');
    const n=norm(p.anzeigename);
    if(n&&!/[?]|unbekannt|platzhalter/.test(n)&&p.datensatz_typ==='person'){
      const list=groups.get(n)||[];list.push(p);groups.set(n,list);
    }
  }
  for(const list of groups.values())if(list.length>1)for(let i=0;i<list.length;i++)for(let j=i+1;j<list.length;j++){
    const p=list[i],other=list[j],x=dateInfo(p.geburt?.datum),y=dateInfo(other.geburt?.datum);
    if(x&&y&&x.year!==y.year)continue;
    issue('Dubletten',p,'Namensgleichheit'+(x&&y?' und gleiches Geburtsjahr':'')+' – mögliche Dublette, kein Zusammenführen.',{otherId:other.id});
  }
  const parents=new Map();
  for(const r of a.beziehungen||[]){
    const p=byid.get(r.zu_person_id),from=byid.get(r.von_person_id);
    if(!p||!from){issue('Verweise',p||from,'Verbindung verweist auf eine fehlende Person.',{recordId:r.id});continue;}
    if(r.von_person_id===r.zu_person_id)issue('Verweise',p,'Person ist mit sich selbst verbunden.',{recordId:r.id});
    if(!confirmed(r))issue('Ungeklärte Verbindungen',p,'Verbindung zu '+from.anzeigename+' ist nicht als belegt erfasst.',{recordId:r.id});
    if(r.typ==='eltern_kind'){
      if(!parents.has(p.id))parents.set(p.id,[]);parents.get(p.id).push(from.id);
      const cb=dateInfo(p.geburt?.datum),pb=dateInfo(from.geburt?.datum);
      if(cb&&pb&&!cb.uncertain&&!pb.uncertain&&pb.min>cb.max)issue('Chronologie',p,'Elternteil '+from.anzeigename+' wurde nach dem Kind geboren.',{recordId:r.id});
    }
  }
  // Iterative DFS detects cycles without recursion or exponential path expansion.
  const color=new Map();
  for(const start of byid.keys()){
    if(color.get(start))continue;
    const stack=[{id:start,next:0}];color.set(start,1);
    while(stack.length){
      const top=stack.at(-1),links=parents.get(top.id)||[];
      if(top.next>=links.length){color.set(top.id,2);stack.pop();continue;}
      const to=links[top.next++];
      if(color.get(to)===1){issue('Abstammungskreis',byid.get(top.id),'Abstammungskreis zu '+byid.get(to).anzeigename+'.');continue;}
      if(!color.get(to)){color.set(to,1);stack.push({id:to,next:0});}
    }
  }
  return out;
}
export function table(headers,rows){
  return '<div class="mod-table-wrap"><table class="mod-table"><thead><tr>'+headers.map(h=>'<th scope="col">'+h+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+r.map(c=>'<td>'+c+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>';
}
export function personOptions(a,selected,esc,empty=''){
  return (empty?'<option value="">'+esc(empty)+'</option>':'')+[...(a.personen||[])].sort((a,b)=>String(a.anzeigename).localeCompare(String(b.anzeigename),'de')).map(p=>`<option value="${esc(p.id)}" ${p.id===selected?'selected':''}>${esc(p.anzeigename)}${p.namen?.geburtsname?' · geb. '+esc(p.namen.geburtsname):''} · ${esc(p.geburt?.datum?.iso||'?')} · ${esc(p.id.slice(-8))}</option>`).join('');
}
