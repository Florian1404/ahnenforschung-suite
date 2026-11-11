<?php
declare(strict_types=1);
require_once __DIR__.'/import-numbers.php';
require_once __DIR__.'/import-families.php';
const INC_META=['namen','original_nummern','daboville_ids','externe_ids','notizen','quellen_verweise','berufe','ausbildungen','wohnsitze','migrationen','religionsgeschichte','militaerdienst','weitere_ereignisse','auszeichnungen','vereinsmitgliedschaften','benutzerdefinierte_felder'];
function incNamespace(mixed $value): string {if(!is_string($value)||!preg_match('/^[a-z0-9][a-z0-9_-]{1,79}$/D',$value))fail(422,'Stabile Datenquellen-Kennung erforderlich, z. B. kreutzwiesner. Bei späteren Updates gleich lassen.');return $value;}
function incTarget(string $ns,string $id): string{return 'imp_'.hash('sha256',$ns."\0".$id);}
function incAlias(string $ns,string $id): string{return 'import_alias_'.hash('sha256',$ns."\0".$id);}
function incKey(string $s): string{$s=mb_strtolower($s);$s=strtr($s,['ä'=>'a','ö'=>'o','ü'=>'u','ß'=>'ss','é'=>'e','è'=>'e','á'=>'a','č'=>'c','š'=>'s']);return trim(preg_replace('/[^\p{L}\p{N}]+/u',' ',$s));}
function incNames(array $p): array{$out=[$p['anzeigename']??''];foreach($p['namen']['namensvarianten']??[] as $v)if(is_array($v)&&is_string($v['name']??null))$out[]=$v['name'];$first=$p['namen']['vornamen']??'';if(is_array($first))$first=implode(' ',array_filter($first,'is_string'));if(is_string($first)&&$first!=='')foreach(['familienname','geburtsname'] as $k)if(is_string($p['namen'][$k]??null))$out[]=$first.' '.$p['namen'][$k];return array_values(array_unique(array_filter(array_map('incKey',$out))));}
function incKnown(array $p): bool{$n=incKey($p['anzeigename']??'');return mb_strlen($n)>2&&!str_contains($p['anzeigename']??'','?')&&!preg_match('/^(unbekannt(?:e[rsnm]?)?|unknown|n n|totgeburt)( |$)/u',$n);}
function incPossible(array $p,array $q): bool{if(!incKnown($p)||!incKnown($q))return false;if(array_intersect(incNames($p),incNames($q)))return true;$firstP=explode(' ',incKey($p['anzeigename']))[0];$firstQ=explode(' ',incKey($q['anzeigename']))[0];$lastP=array_filter([incKey((string)($p['namen']['familienname']??'')),incKey((string)($p['namen']['geburtsname']??''))]);$lastQ=array_filter([incKey((string)($q['namen']['familienname']??'')),incKey((string)($q['namen']['geburtsname']??''))]);if(array_intersect($lastP,$lastQ)&&($firstP===$firstQ||strlen($firstP)>3&&strlen($firstQ)>3&&levenshtein($firstP,$firstQ)<=2))return true;return false;}
function incAliases(PDO $db,string $ns): array{$out=[];foreach(query($db,"SELECT data FROM ah_settings WHERE id LIKE 'import_alias_%'")->fetchAll() as $row){$x=decode($row['data']);if(($x['namespace']??'')===$ns)$out[$x['source_id']]=$x['target'];}return $out;}
function incFullMatch(array $a,array $b): ?string {
 if(!array_intersect(incNames($a),incNames($b)))return null;
 $ba=incExactEvent($a,'geburt');$bb=incExactEvent($b,'geburt');
 if($ba&&$ba===$bb)return 'Name und vollständiges Geburtsdatum';
 $ta=incExactEvent($a,'taufe');$tb=incExactEvent($b,'taufe');
 foreach([[$ta,'taufe',$tb,'taufe'],[$ba,'geburt',$tb,'taufe'],[$ta,'taufe',$bb,'geburt']] as [$x,$ex,$y,$ey]){
  if(!$x||$x!==$y||($ba&&$bb&&$ba!==$bb))continue;
  $place=incKey((string)gp($a,$ex.'.ort_original'));
  if($place!==''&&$place===incKey((string)gp($b,$ey.'.ort_original')))return 'Name und belegtes Geburts-/Taufdatum am selben Ort';
 }
 $da=incExactEvent($a,'tod');$db=incExactEvent($b,'tod');
 if($da&&$da===$db&&$ba&&$bb&&substr($ba,0,4)===substr($bb,0,4))return 'Name, Geburtsjahr und vollständiges Sterbedatum';
 return null;
}
function incMatch(array $p,array $existing,array $aliases,string $ns,array $batch,callable $distinct,array $knownSources,array $numbers,array $numberIndex): array{
 $byId=array_column($existing,null,'id');$refs=$numbers[$p['id']]??[];
 $targets=[];$numberTargets=[];
 foreach($refs as $key=>$ref){
  foreach(array_keys($numberIndex[$key]??[]) as $id)$numberTargets[$id]=true;
  if(isset($aliases[$key]))$numberTargets[$aliases[$key]]=true;
 }
 $targets=$numberTargets;
 $legacy=$aliases[$p['id']]??(isset($byId[$p['id']])?$p['id']:(isset($byId[incTarget($ns,$p['id'])])?incTarget($ns,$p['id']):null));
 if($legacy)$targets[$legacy]=true;
 $stable=count($targets)===1?(string)array_key_first($targets):null;
 $conflict=count($targets)>1||($stable&&!isset($byId[$stable]));
 $candidates=[];$distinctIds=[];$exact=[];
 foreach($existing as $r){
  $old=$r['data'];$possible=incPossible($p,$old);$assigned=isset($targets[$r['id']]);if(!$possible&&!$assigned)continue;
  $match=incFullMatch($p,$old);
  $oldNumberRefs=incNumbers($old,true);
  $separate=incHistoricalSeparate($p,$old)||($possible&&isset($knownSources[$r['id']])&&$distinct($p,$knownSources[$r['id']]))||
   (!$match&&incNumbersSeparate($refs,$oldNumberRefs));
  if($assigned){
   $pb=incExactEvent($p,'geburt');$ob=incExactEvent($old,'geburt');
   if($separate||($pb&&$ob&&abs((int)substr($pb,0,4)-(int)substr($ob,0,4))>=10)||
    (incKnown($p)&&incKnown($old)&&!$match&&!array_intersect(incNames($p),incNames($old))))$conflict=true;
  }
  if($separate){$distinctIds[]=$r['id'];continue;}
  if($assigned||$possible)$candidates[]=['id'=>$r['id'],'name'=>$old['anzeigename'],'birth'=>gp($old,'geburt.datum.iso'),'death'=>gp($old,'tod.datum.iso'),'place'=>gp($old,'geburt.ort_original')];
  if($match)$exact[$r['id']]=$match;
 }
 $incoming=[];foreach($batch as $other)if($other['id']!==$p['id']&&incPossible($p,$other)&&!$distinct($p,$other))$incoming[]=$other['id'];
 $target=$conflict?null:($stable??(count($exact)===1?(string)array_key_first($exact):null));
 $reason=$conflict?'Nummer oder gespeicherte Zuordnung widerspricht dem Bestand. Nummernkreis und Profile prüfen.':
  ($stable?(isset($numberTargets[$stable])?'Eindeutige d’Aboville-ID':'Gespeicherte Identität / Quellzuordnung'):
   ($target?$exact[$target].' · Zuordnung zur Nummer bei Freigabe':($incoming?'Mögliche Dublette innerhalb der Datei':
    ($candidates?'Altbestand ohne eindeutige Nummer – einmal zuordnen oder überspringen':(!incKnown($p)?'Namenslose Person kann nicht automatisch neu angelegt werden':'Neuzugang muss ausdrücklich bestätigt werden')))));
 return ['source_id'=>$p['id'],'target'=>$target,'stable'=>(bool)$stable,'identity_conflict'=>$conflict,'candidates'=>$target?[]:$candidates,
  'distinct_ids'=>$distinctIds,'incoming_duplicates'=>$incoming,'can_create'=>!$conflict&&!$target&&!$candidates&&!$incoming&&incKnown($p),
  'reason'=>$reason,'numbers'=>array_values($refs),'number_keys'=>array_keys($refs)];
}
function incExactEvent(array $p,string $event): ?string {
 $v=gp($p,$event.'.datum.iso');
 return is_string($v)&&preg_match('/^\d{4}-\d{2}-\d{2}$/D',$v)&&!gp($p,$event.'.datum.konflikt')?$v:null;
}
// Chronology can distinguish documented namesakes even without a parent link.
function incHistoricalSeparate(array $a,array $b): bool {
 $ba=incExactEvent($a,'geburt');$bb=incExactEvent($b,'geburt');
 $da=incExactEvent($a,'tod');$db=incExactEvent($b,'tod');
 if(($ba&&$ba===$bb)||($da&&$da===$db))return false;
 $year=fn(string $v)=>(int)substr($v,0,4);
 foreach([[$a,$bb],[$b,$ba]] as [$person,$otherBirth]){
  if(!$otherBirth)continue;
  foreach(['taufe','hochzeit','tod'] as $event){
   $date=incExactEvent($person,$event);
   if($date&&$year($otherBirth)-$year($date)>=10)return true;
  }
 }
 return $ba&&$bb&&$da&&$db&&abs($year($ba)-$year($bb))>=10&&abs($year($da)-$year($db))>=10;
}
// A parent/child chain in this source can distinguish namesakes without weakening
// the check for people who are merely listed with conflicting dates.
function incDistinctGenerations(array $a,array $b,array $children): bool {
 $birthA=gp($a,'geburt.datum.iso');$birthB=gp($b,'geburt.datum.iso');
 if($birthA&&$birthB){
  if(abs((int)substr($birthA,0,4)-(int)substr($birthB,0,4))<10)return false;
 }elseif(incKey($a['anzeigename'])===incKey($b['anzeigename']))return false;
 $deathA=gp($a,'tod.datum.iso');$deathB=gp($b,'tod.datum.iso');
 if($deathA&&strlen($deathA)===10&&$deathA===$deathB)return false;
 $reachable=function(string $from,string $to)use($children):bool{
  $queue=[$from];$seen=[$from=>true];
  for($i=0;$i<count($queue);$i++)foreach($children[$queue[$i]]??[] as $next){
   if($next===$to)return true;
   if(!isset($seen[$next])){$seen[$next]=true;$queue[]=$next;}
  }return false;
 };
 $forward=$reachable($a['id'],$b['id']);$backward=$reachable($b['id'],$a['id']);
 if($forward===$backward)return false;
 if($birthA&&$birthB&&(($birthA<$birthB)!==$forward))return false;
 return true;
}
function incAnalysis(PDO $db,array $data,string $ns,array $mapping=[]): array{
 $existing=records($db,'person');$aliases=incAliases($db,$ns);
 $incomingNumbers=incNumberIndex($data['personen']);$numbers=[];
 foreach($data['personen'] as $p)$numbers[$p['id']]=array_filter(incNumbers($p),fn($key)=>count($incomingNumbers[$key])===1,ARRAY_FILTER_USE_KEY);
 $numberIndex=incNumberIndex(array_map(fn($r)=>['id'=>$r['id']]+$r['data'],$existing),true);
 $batch=array_values(array_filter($data['personen'],fn($p)=>($mapping[$p['id']]??'')!=='skip'));
 $selected=array_fill_keys(array_column($batch,'id'),true);$children=[];
 foreach($data['beziehungen'] as $r)if($r['typ']==='eltern_kind'&&isset($selected[$r['von_person_id']],$selected[$r['zu_person_id']]))
  $children[$r['von_person_id']][]=$r['zu_person_id'];
 $distinct=fn(array $a,array $b)=>$a['id']!==$b['id']&&(incHistoricalSeparate($a,$b)||
  incDistinctGenerations($a,$b,$children)||(!incFullMatch($a,$b)&&incNumbersSeparate($numbers[$a['id']]??[],$numbers[$b['id']]??[])));
 // Use other uniquely recognized people to keep separate generations out of the picker.
 $knownSources=[];$ambiguous=[];
 foreach($batch as $p){
  $exact=array_values(array_filter($existing,fn($r)=>incFullMatch($p,$r['data'])));
  if(count($exact)!==1)continue;
  $id=$exact[0]['id'];if(isset($knownSources[$id]))$ambiguous[$id]=true;$knownSources[$id]=$p;
 }
 $knownSources=array_diff_key($knownSources,$ambiguous);
 $out=[];
 foreach($data['personen'] as $p){
  $check=incMatch($p,$existing,$aliases,$ns,$batch,$distinct,$knownSources,$numbers,$numberIndex);
  $check['number_collisions']=array_values(array_diff_key(incNumbers($p),$numbers[$p['id']]));
  if($check['number_collisions']){
   $check['identity_conflict']=true;$check['target']=null;$check['can_create']=false;
   $check['reason']='Dieselbe d’Aboville-ID steht bei mehreren Personen. Bitte Nummernkreis in der Datei korrigieren.';
  }
  $out[]=$check;
 }
 return $out;
}
function incMerge(mixed $old,mixed $new,array &$warnings,string $label): mixed{
 if($new===null||$new===''||$new===[]||in_array($new,['unbekannt','ungeklaert'],true))return $old;
 if($old===null||$old===''||$old===[]||in_array($old,['unbekannt','ungeklaert'],true))return $new;
 if($old===$new)return $old;
 if(is_array($old)&&is_array($new)){if(array_is_list($old)&&array_is_list($new)){$keys=[];$out=[];foreach(array_merge($old,$new) as $v){$k=jencode($v);if(!isset($keys[$k])){$out[]=$v;$keys[$k]=true;}}return $out;}$out=$old;foreach($new as $k=>$v)$out[$k]=incMerge($old[$k]??null,$v,$warnings,$label.'.'.$k);return $out;}
 $warnings[]=$label.': abweichender Wert bleibt unverändert im Bestand.';return $old;
}
function incrementalPlan(PDO $db,array $data,array $mapping,string $batch,string $ns): array{
 $ns=incNamespace($ns);$out=['incremental'=>true,'namespace'=>$ns,'new'=>[],'patches'=>[],'families'=>[],'family_patches'=>[],'family_conflicts'=>[],'relationships'=>[],'warnings'=>$data['hinweise'],'person_ids'=>[],'source_map'=>[]];$map=[];$used=[];$analysis=incAnalysis($db,$data,$ns,$mapping);$checks=array_column($analysis,null,'source_id');
 foreach($data['personen'] as $p){$id=$p['id'];$m=$checks[$id];$choice=$mapping[$id]??($m['target']??'');if(!is_string($choice))fail(422,'Ungültige Personenzuordnung.');if($choice==='skip'){$map[$id]=null;continue;}if($m['identity_conflict'])fail(409,'Quell-ID kollidiert mit einer anderen Identität: '.$p['anzeigename'].'. Überspringen oder Quellenkennung/IDs korrigieren.');
  if($choice==='new')fail(422,'Neuzugänge müssen ausdrücklich als new_confirmed bestätigt werden.');
  if($m['stable']&&$choice!==$m['target']&&$choice!=='new_confirmed')fail(409,'Gespeicherte Quellidentität darf nicht auf eine andere Person umgebogen werden: '.$p['anzeigename']);
  if($choice==='new_confirmed'){
   // An identical concurrently approved import now has this deterministic identity.
   if($m['stable'])$choice=$m['target'];else{if(!$m['can_create'])fail(409,'Neuanlage wegen möglicher Dublette gesperrt: '.$p['anzeigename'].'. Zugeordneten Datensatz wählen oder überspringen.');$numberKeys=$m['number_keys'];sort($numberKeys,SORT_STRING);$target=incTarget($ns,$numberKeys[0]??$id);$per=$p;$per['id']=$target;$out['new'][]=$per;}
  }
  if($choice!=='new_confirmed'){
   if(!$choice)fail(422,'Person noch nicht zugeordnet: '.$p['anzeigename']);$target=identifier($choice);if(in_array($target,$m['distinct_ids'],true))fail(409,'Zuordnung verwechselt nach Lebensdaten zwei verschiedene Personen: '.$p['anzeigename']);$r=getRecord($db,$target);if(!$r||$r['kind']!=='person')fail(422,'Zugeordnete Person fehlt.');$changes=[];$extra=[];$after=$r['data'];
   foreach(IMPORT_FIELDS as $key){if($key==='anzeigename'){if(!incKnown($r['data'])&&incKnown($p)){$changes[$key]=$p['anzeigename'];$after[$key]=$p['anzeigename'];}continue;}$value=gp($p,$key);$old=gp($r['data'],$key);if($value===null||$value===''||in_array($value,['unbekannt','ungeklaert'],true))continue;if($old===null||$old===''||in_array($old,['unbekannt','ungeklaert'],true)){$changes[$key]=$value;sp($after,$key,$value);}elseif($old!==$value)$out['warnings'][]=$p['anzeigename'].': Konflikt bei '.$key.' – vorhandener Wert bleibt erhalten.';}
   foreach(INC_META as $key)if(isset($p[$key])){$merged=incMerge($r['data'][$key]??null,$p[$key],$out['warnings'],$p['anzeigename'].'.'.$key);if($merged!==($r['data'][$key]??null)){$extra[$key]=$merged;$after[$key]=$merged;}}
   if(isset($p['hauptlinie'])){
    $oldLine=$r['data']['hauptlinie']??null;
    if($oldLine===null||$oldLine==='')$extra['hauptlinie']=$p['hauptlinie'];
    elseif($oldLine!==$p['hauptlinie'])$out['warnings'][]=$p['anzeigename'].': bestehende Hauptlinie bleibt erhalten.';
   }
   chronology($after);$out['patches'][]=['id'=>$target,'base_version'=>$r['version'],'changes'=>$changes,'extra'=>$extra,'name'=>$r['data']['anzeigename']];
  }
  if(isset($used[$target]))fail(409,'Mehrere Quellpersonen würden dieselbe Person belegen. Dublette innerhalb der Datei bereinigen oder einen Eintrag überspringen.');$used[$target]=true;$map[$id]=$target;
 }
 $out['source_map']=array_filter($map,fn($v)=>$v!==null);
 $out['identity_map']=$out['source_map'];
 foreach($out['source_map'] as $source=>$target)foreach($checks[$source]['number_keys'] as $key)$out['identity_map'][$key]=$target;
 $out['person_ids']=array_values($out['source_map']);if(!$out['person_ids'])fail(422,'Keine Personen ausgewählt.');
 $edges=[];foreach(records($db,'relationship') as $row){$r=$row['data'];$pair=[$r['von_person_id'],$r['zu_person_id']];if($r['typ']==='partner')sort($pair);$edges[$r['typ'].':'.jencode($pair)]=$r;}
 $families=records($db,'family');foreach($families as $r){$pair=$r['data']['partner_person_ids']??[];if(count($pair)===2){sort($pair);$edges['partner:'.jencode($pair)]=$r['data'];}}
 foreach($data['beziehungen'] as $r){$a=$map[$r['von_person_id']]??null;$b=$map[$r['zu_person_id']]??null;if(!$a||!$b)continue;$r['von_person_id']=$a;$r['zu_person_id']=$b;validate('relationship',$r);$pair=[$a,$b];if($r['typ']==='partner')sort($pair);$key=$r['typ'].':'.jencode($pair);if(isset($edges[$key])){if($r['typ']==='eltern_kind'&&($r['elternschaft_typ']??'ungeklaert')!=='ungeklaert'&&($edges[$key]['elternschaft_typ']??'ungeklaert')!==$r['elternschaft_typ'])$out['warnings'][]='Abweichende Elternschaft bei bestehender Verbindung: separat prüfen; keine zweite Verbindung angelegt.';continue;}$edges[$key]=$r;$r['id']='rel_'.hash('sha256',$key);$out['relationships'][]=$r;}
 $names=[];
 foreach($out['new'] as $p)$names[$p['id']]=$p['anzeigename'];
 foreach($out['patches'] as $p)$names[$p['id']]=$p['name'];
 incFamilyPlans($data['familien'],$families,$map,$names,$out);
 $aliases=incAliases($db,$ns);$out['identity_links']=count(array_filter($out['identity_map'],fn($target,$source)=>!isset($aliases[$source]),ARRAY_FILTER_USE_BOTH));
 $changed=array_filter($out['patches'],fn($p)=>$p['changes']||$p['extra']);$out['no_changes']=!$out['new']&&!$changed&&!$out['relationships']&&!$out['families']&&!$out['family_patches']&&!$out['identity_links'];$out['warnings']=array_values(array_unique($out['warnings']));return $out;
}
function incRegister(PDO $db,array $plan): void{foreach(incPlanAliases($plan) as $source=>$target){$key=incAlias($plan['namespace'],(string)$source);$old=one($db,'SELECT data FROM ah_settings WHERE id=?',[$key]);if($old&&decode($old['data'])['target']!==$target)fail(409,'Quellidentität zwischenzeitlich anders zugeordnet.');if(!$old)query($db,'INSERT INTO ah_settings VALUES (?,?)',[$key,jencode(['namespace'=>$plan['namespace'],'source_id'=>(string)$source,'target'=>$target])]);}}
