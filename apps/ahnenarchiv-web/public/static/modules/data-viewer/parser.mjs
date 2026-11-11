export const LIMIT=5*1024*1024;
export function detectFormat(text,name='') {
 const ext=name.toLowerCase().split('.').pop();
 if(['json','jsonl','ndjson','ged','gedcom','csv','tsv'].includes(ext))return {ged:'gedcom',gedcom:'gedcom',ndjson:'jsonl'}[ext]||ext;
 const s=text.trimStart();if(/^[{[]/.test(s))return 'json';if(/^0\s+(?:HEAD|@\S+@\s+INDI)/m.test(text))return 'gedcom';
 const rows=text.trim().split(/\r\n|\n|\r/);if(rows.length>1){try{const csv=parseCsv(text);const n=csv.rows[0]?.length||0;if(n>1&&csv.rows.slice(0,20).every(r=>r.length===n))return 'csv';}catch{}}
 return 'text';
}
// Keep number tokens exactly as supplied, including integers above Number.MAX_SAFE_INTEGER.
export function prettyJson(text) {
 JSON.parse(text);let result='',depth=0,quoted=false,escaped=false;
 for(const c of text){if(quoted){result+=c;if(escaped)escaped=false;else if(c==='\\')escaped=true;else if(c==='"')quoted=false;continue;}
  if(c==='"'){quoted=true;result+=c;}else if(/\s/.test(c))continue;
  else if(c==='{'||c==='['){if(++depth>100)throw Error('JSON ist tiefer als 100 Ebenen verschachtelt. Bitte Originaltext verwenden.');result+=c+'\n'+'  '.repeat(depth);}
  else if(c==='}'||c===']'){result+='\n'+'  '.repeat(--depth)+c;}
  else if(c===',')result+=',\n'+'  '.repeat(depth);else if(c===':')result+=': ';else result+=c;
 }return result.replace(/\{\n\s*\}/g,'{}').replace(/\[\n\s*\]/g,'[]');
}
export function parseCsv(text,delimiter='auto') {
 const parse=d=>{const rows=[];let row=[],value='',quoted=false,after=false;
  for(let i=0;i<text.length;i++){const c=text[i];if(quoted){if(c==='"'){if(text[i+1]==='"'){value+='"';i++;}else{quoted=false;after=true;}}else value+=c;continue;}
   if(c==='"'&&!value&&!after){quoted=true;continue;}
   if(c===d){row.push(value);value='';after=false;continue;}
   if(c==='\n'||c==='\r'){if(c==='\r'&&text[i+1]==='\n')i++;row.push(value);rows.push(row);row=[];value='';after=false;if(rows.length>50000)throw Error('Mehr als 50.000 Tabellenzeilen. Bitte Datei aufteilen.');continue;}
   if(after){if(c===' '||c==='\t'&&d!=='\t')continue;throw Error('Unerwartetes Zeichen nach einem geschlossenen CSV-Anführungszeichen.');}
   if(c==='"')throw Error('Anführungszeichen innerhalb eines unmaskierten CSV-Feldes.');value+=c;
  }
  if(quoted)throw Error('CSV-Feld hat ein nicht geschlossenes Anführungszeichen.');if(value||row.length||after)rows.push([...row,value]);return rows;};
 if(delimiter==='auto'){
  const candidates=[',',';','\t'].map(d=>{try{const rows=parse(d),sample=rows.slice(0,20),width=sample[0]?.length||0;return {d,rows,score:width>1?sample.filter(r=>r.length===width).length*100+Math.min(width,99):0};}catch{return {d,score:-1};}}).sort((a,b)=>b.score-a.score);
  if(candidates[0].score<0)throw Error('CSV konnte nicht gelesen werden. Trennzeichen prüfen.');return {rows:candidates[0].rows,delimiter:candidates[0].d};
 }return {rows:parse(delimiter),delimiter};
}
const TAGS={HEAD:'Kopf',CHAR:'Zeichensatz',INDI:'Person',FAM:'Familie',NAME:'Name',GIVN:'Vornamen',SURN:'Nachname',NSFX:'Namenszusatz',SEX:'Geschlecht',BIRT:'Geburt',DEAT:'Tod',MARR:'Heirat',DIV:'Scheidung',DATE:'Datum',PLAC:'Ort',HUSB:'Partner (HUSB)',WIFE:'Partner (WIFE)',CHIL:'Kind',FAMC:'Herkunftsfamilie',FAMS:'Partnerschaftsfamilie',NOTE:'Notiz',SOUR:'Quelle',PAGE:'Fundstelle',OCCU:'Beruf',BURI:'Bestattung',CHR:'Taufe',OBJE:'Medium',FILE:'Datei',CONT:'Fortsetzung (neue Zeile)',CONC:'Fortsetzung',TRLR:'Ende'};
export function parseGedcom(text){
 const lines=text.split(/\r\n|\n|\r/),entries=[],names=new Map();let people=0,families=0;
 for(let i=0;i<lines.length;i++){if(!lines[i].trim())continue;const m=/^(\d+)\s+(?:(@[^@\s]+@)\s+)?([A-Za-z0-9_]+)(?:\s+(.*))?$/.exec(lines[i]);if(!m)throw Error('GEDCOM: Zeile '+(i+1)+' ist ungültig.');
  const level=Number(m[1]);if(level>99)throw Error('GEDCOM: unzulässige Verschachtelung in Zeile '+(i+1)+'.');
  const e={level,id:m[2]||'',tag:m[3].toUpperCase(),value:m[4]||''};entries.push(e);if(e.tag==='INDI')people++;if(e.tag==='FAM')families++;
 }
 let current='';for(const e of entries){if(e.level===0)current=e.tag==='INDI'?e.id:'';if(current&&e.level===1&&e.tag==='NAME'&&!names.has(current))names.set(current,e.value.replace(/\//g,'').trim());}
 const pretty=entries.map(e=>{const ref=names.get(e.value);return '  '.repeat(e.level)+(e.id?e.id+' · ':'')+(TAGS[e.tag]||e.tag)+' ['+e.tag+']'+(e.value?': '+e.value+(ref?' → '+ref:''):'');}).join('\n');
 return {pretty,summary:people+' Personen · '+families+' Familien · '+entries.length+' Angaben'};
}
export function decodeBytes(buffer,encoding='auto'){
 const a=new Uint8Array(buffer);let selected=encoding,note='';
 if(selected==='auto'){
  if(a[0]===255&&a[1]===254)selected='utf-16le';else if(a[0]===254&&a[1]===255)selected='utf-16be';
  else {try{new TextDecoder('utf-8',{fatal:true}).decode(a);selected='utf-8';}catch{selected='windows-1252';note='Kein UTF-8 erkannt. Windows-1252 gewählt; Umlaute bitte prüfen.';}}
 }
 const text=new TextDecoder(selected).decode(a).replace(/^\uFEFF/,'');
 if(/\bCHAR\s+ANSEL\b/i.test(text))note='GEDCOM meldet ANSEL. Dieser Zeichensatz wird nicht umgewandelt; Sonderzeichen können falsch erscheinen. Bitte als UTF-8 exportieren.';
 return {text,encoding:selected,note};
}
export function parseDocument(text,format='auto',name='',delimiter='auto'){
 text=text.replace(/^\uFEFF/,'');if(text.length>LIMIT)throw Error('Bitte eine Datei bis 5 MB verwenden.');
 const kind=format==='auto'?detectFormat(text,name):format;
 if(kind==='json')return {kind,pretty:prettyJson(text),summary:'JSON · vollständig validiert'};
 if(kind==='jsonl'){let n=0;const pretty=text.split(/\r\n|\n|\r/).filter(l=>l.trim()).map((l,i)=>{try{return 'Datensatz '+(++n)+'\n'+prettyJson(l);}catch(e){throw Error('JSONL: Datensatz '+(i+1)+' ist ungültig: '+e.message);}}).join('\n\n');return {kind,pretty,summary:n+' JSON-Datensätze'};}
 if(kind==='gedcom')return {kind,...parseGedcom(text)};
 if(kind==='csv'||kind==='tsv'){const table=parseCsv(text,kind==='tsv'?'\t':delimiter);return {kind,...table,pretty:table.rows.map((r,i)=>(i===0?'Spalten':('Zeile '+i))+': '+r.join(' | ')).join('\n'),summary:Math.max(0,table.rows.length-1)+' Datenzeilen · '+(table.rows[0]?.length||0)+' Spalten · Trennzeichen '+(table.delimiter==='\t'?'Tabulator':table.delimiter)};}
 return {kind:'text',pretty:text,summary:'Textansicht · XML, YAML, TXT und weitere Textformate'};
}
