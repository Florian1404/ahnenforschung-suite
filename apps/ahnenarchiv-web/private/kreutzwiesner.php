<?php
declare(strict_types=1);

function kwDataset(string $root): array {
    $file=$root.'/private/imports/kreutzwiesner/stammbaum-kreutzwiesner.json';
    if(!is_file($file))fail(404,'Kreutzwiesner-Paket fehlt.');
    $a=decode(file_get_contents($file));
    if(($a['statistik']['seiten']??0)!==176 || count($a['personen']??[])<300)fail(503,'Importdatei unvollständig.');
    return $a;
}
function kwName(string $s): string {
    $s=mb_strtolower($s);$s=strtr($s,['ä'=>'a','ö'=>'o','ü'=>'u','ß'=>'ss','é'=>'e']);
    return trim(preg_replace('/[^a-z0-9]+/u',' ',str_replace(['kreutzwiesner','kreutzwiesen'],'kreuzwiesner',$s)));
}
function kwEmpty(mixed $x): bool {
    return $x===null || $x==='' || $x===[] || is_string($x)&&in_array(mb_strtolower(trim($x)),['unbekannt','???','??','ungeklaert'],true);
}
function kwUnion(array $a,array $b): array {
    $seen=[];$out=[];foreach(array_merge($a,$b) as $x){$key=jencode($x);if(!isset($seen[$key])){$seen[$key]=true;$out[]=$x;}}return $out;
}
function kwMerge(array $old,array $new,array &$conflicts,string $path=''): array {
    foreach($new as $key=>$value){
        $p=$path===''?(string)$key:$path.'.'.$key;
        if(in_array($p,['id','datensatz_typ','portraet_medien_id'],true))continue;
        if(kwEmpty($value))continue;
        if(!array_key_exists($key,$old)||kwEmpty($old[$key])){$old[$key]=$value;continue;}
        if($old[$key]===$value)continue;
        if(is_array($value)&&is_array($old[$key])){
            if(array_is_list($value)&&array_is_list($old[$key]))$old[$key]=kwUnion($old[$key],$value);
            else $old[$key]=kwMerge($old[$key],$value,$conflicts,$p);
        }elseif(in_array($p,['quellen_verweise','original_nummern'],true))continue;
        else $conflicts[]=['feld'=>$p,'bestand'=>$old[$key],'vorlage'=>$value];
    }return $old;
}
function kwRemap(mixed $v,array $map): mixed {
    if(is_string($v))return $map[$v]??$v;
    if(is_array($v)){foreach($v as &$x)$x=kwRemap($x,$map);unset($x);}return $v;
}
function kwPlan(PDO $db,string $root,array $choices=[]): array {
    $a=kwDataset($root);$batch=$a['projekt']['import_batch'];$done=one($db,'SELECT data FROM ah_settings WHERE id=?',[$batch]);
    if($done)return ['applied'=>true,'result'=>decode($done['data']),'batch'=>$batch,'writes'=>[]];
    $rows=records($db);$existing=[];$people=[];$map=[];$ambiguous=[];
    foreach($rows as $r){$existing[$r['id']]=$r;if($r['kind']==='person')$people[]=$r;}
    $allowed=array_column($a['personen'],'id');foreach($choices as $id=>$choice){if(!in_array($id,$allowed,true)||!is_string($choice))fail(422,'Ungültige Zuordnung.');}
    foreach($a['personen'] as $p){
        $id=$p['id'];$map[$id]=$id;
        if(isset($existing[$id])){if($existing[$id]['kind']!=='person')fail(409,'Personen-ID anderweitig belegt.');continue;}
        $name=kwName($p['anzeigename']);$birth=gp($p,'geburt.datum.iso');$candidates=[];$exact=[];
        foreach($people as $r){
            $q=$r['data'];$n=kwName($q['anzeigename']??'');$bd=gp($q,'geburt.datum.iso');
            if($n===$name && strlen($name)>5 && !str_contains($p['anzeigename'],'?')){
                if(is_string($birth)&&is_string($bd)&&strlen($birth)>=4&&strlen($bd)>=4&&abs((int)substr($birth,0,4)-(int)substr($bd,0,4))>=12)continue;
                $candidates[]=['id'=>$r['id'],'name'=>$q['anzeigename'],'geburt'=>$bd];
                if(is_string($birth)&&strlen($birth)===10&&$bd===$birth)$exact[]=$r['id'];
            }
        }
        if(isset($choices[$id])){
            $choice=$choices[$id];
            if($choice!=='new'&&!in_array($choice,array_column($candidates,'id'),true))fail(422,'Zuordnung nicht im Vorschlag enthalten.');
            $map[$id]=$choice==='new'?$id:$choice;
        }elseif(count($exact)===1)$map[$id]=$exact[0];
        elseif($candidates)$ambiguous[]=['id'=>$id,'name'=>$p['anzeigename'],'geburt'=>$birth,'candidates'=>$candidates];
    }
    if(count(array_unique(array_values($map)))!==count($map))fail(409,'Zwei unterschiedliche PDF-Personen würden zusammengeführt. Zuordnung korrigieren.');
    // Reuse current family/relationship IDs instead of duplicating the Huschka connections.
    $relations=[];$families=[];$media=[];
    foreach($rows as $r){$p=$r['data'];if($r['kind']==='family'){$ps=$p['partner_person_ids']??[];sort($ps);$families[jencode($ps)][]=$r['id'];}
        if($r['kind']==='relationship')$relations[($p['typ']??'').'|'.($p['von_person_id']??'').'|'.($p['zu_person_id']??'')][]=$r['id'];
        if($r['kind']==='media'&&!empty($p['sha256']))$media[$p['sha256']]=$r['id'];}
    foreach($a['familien'] as $p){$ps=kwRemap($p['partner_person_ids'],$map);sort($ps);$ids=$families[jencode($ps)]??[];if(count($ids)===1)$map[$p['id']]=$ids[0];}
    foreach($a['beziehungen'] as $p){$ids=$relations[$p['typ'].'|'.$map[$p['von_person_id']].'|'.$map[$p['zu_person_id']]]??[];if(count($ids)===1)$map[$p['id']]=$ids[0];}
    foreach($a['medien'] as $p)if(isset($media[$p['sha256']??'']))$map[$p['id']]=$media[$p['sha256']];
    $writes=[];$conflicts=[];$counts=['neu'=>[],'ergaenzt'=>[]];
    $kinds=['personen'=>'person','familien'=>'family','beziehungen'=>'relationship','medien'=>'media','quellen'=>'source','quellenseiten'=>'source_page','pruefhinweise'=>'issue'];
    foreach($kinds as $key=>$kind)foreach($a[$key] as $incoming){
        $p=kwRemap($incoming,$map);$id=$p['id'];$r=$existing[$id]??null;$local=[];
        if($r&&$r['kind']!==$kind)fail(409,'Import-ID-Konflikt: '.$id);
        if($r){
            $old=$r['data'];$data=kwMerge($old,$p,$local);
            if($kind==='person'){
                // Preserve exact original source variants as evidence, even when a current field wins.
                $data['benutzerdefinierte_felder']['kreutzwiesner_import']=$p;
                foreach(['geburt','tod','bestattung'] as $event){
                    if(!empty($p[$event]['datum']['original']))$data[$event]['alternativen']=kwUnion($old[$event]['alternativen']??[],[['wert'=>$p[$event],'grund'=>'Kreutzwiesner-PDF; bestehender Vorzugswert bleibt','bevorzugt'=>false]]);
                }
            }
            // A deduplicated medium keeps the existing physical path and access assignments.
            if($kind==='media'){foreach(['datei','person_ids','zuordnungen'] as $field)if(isset($old[$field]))$data[$field]=$old[$field];}
            $version=$r['version']+1;
        }else{$data=$p;$version=1;}
        if($local)$conflicts[]=['id'=>$id,'name'=>$data['anzeigename']??$id,'abweichungen'=>$local];
        if(!$r||jencode($data)!==jencode($r['data'])){
            $writes[]=['id'=>$id,'kind'=>$kind,'data'=>$data,'version'=>$version,'before'=>$r?json_decode($r['_raw_data']):null];
            $bucket=$r?'ergaenzt':'neu';$counts[$bucket][$kind]=($counts[$bucket][$kind]??0)+1;
        }
    }
    // Each preview is bound to the complete current record state, file bytes and mappings.
    $hash=hash_init('sha256');hash_update($hash,hash_file('sha256',$root.'/private/imports/kreutzwiesner/stammbaum-kreutzwiesner.json'));
    ksort($choices);hash_update($hash,jencode($choices));
    foreach($rows as $r)hash_update($hash,$r['id'].'|'.$r['version'].'|'.$r['_raw_data']);
    return ['applied'=>false,'batch'=>$batch,'plan_hash'=>hash_final($hash),'counts'=>$counts,'ambiguous'=>$ambiguous,'conflicts'=>$conflicts,'statistics'=>$a['statistik'],'writes'=>$writes];
}
function kwPublicPlan(array $p): array {unset($p['writes']);return $p;}
function kwApi(PDO $db,string $root,array $u,string $method,string $path): mixed {
    admin($u);
    if($method==='GET'&&$path==='/api/kreutzwiesner/preview')return kwPublicPlan(kwPlan($db,$root));
    if($method==='GET'&&in_array($path,['/api/kreutzwiesner/export','/api/kreutzwiesner/source'],true)){
        $pdf=str_ends_with($path,'source');$file=$root.($pdf?'/private/media/kreutzwiesner/stammbaum-kreutzwiesner.pdf':'/private/imports/kreutzwiesner/stammbaum-kreutzwiesner.json');
        if(!is_file($file))fail(404,'Quelldatei fehlt.');header('Content-Type: '.($pdf?'application/pdf':'application/json; charset=utf-8'));header('Content-Disposition: '.($pdf?'inline':'attachment').'; filename="'.basename($file).'"');header('Content-Length: '.filesize($file));readfile($file);exit;
    }
    if($method==='POST'&&$path==='/api/kreutzwiesner/preview'){$b=body();return kwPublicPlan(kwPlan($db,$root,is_array($b['choices']??null)?$b['choices']:[]));}
    if($method==='POST'&&$path==='/api/kreutzwiesner/apply'){
        $b=body();$choices=$b['choices']??[];if(!is_array($choices))fail(422,'Zuordnungen ungültig.');
        return transaction($db,function()use($db,$root,$u,$b,$choices){
            $plan=kwPlan($db,$root,$choices);if($plan['applied'])return $plan;
            if(!is_string($b['plan_hash']??null)||!hash_equals($plan['plan_hash'],$b['plan_hash']))fail(409,'Bestand hat sich geändert. Vorschau neu laden.');
            if($plan['ambiguous'])fail(409,'Mehrdeutige Personen zuerst zuordnen.');
            $dataset=kwDataset($root);$base=realpath($root.'/private/media');
            foreach($dataset['medien'] as $m){$file=realpath($base.'/'.$m['datei']);if(!$file||!str_starts_with($file,$base.DIRECTORY_SEPARATOR)||!is_file($file)||!hash_equals($m['sha256'],hash_file('sha256',$file)))fail(409,'Quelldatei fehlt oder wurde verändert: '.$m['titel']);}
            $valid=[];foreach(records($db) as $r)$valid[$r['id']]=$r['kind'];foreach($plan['writes'] as $w)$valid[$w['id']]=$w['kind'];
            foreach($plan['writes'] as $w){$p=$w['data'];$ids=$w['kind']==='family'?array_merge($p['partner_person_ids']??[],$p['kinder_person_ids']??[]):($w['kind']==='relationship'?[$p['von_person_id'],$p['zu_person_id']]:[]);
                foreach($ids as $id)if(($valid[$id]??null)!=='person')fail(409,'Verbindung verweist auf eine fehlende Person.');
            }
            foreach($plan['writes'] as $w){
                if($w['before']!==null)query($db,'UPDATE ah_records SET data=?,version=? WHERE id=?',[jencode(preserveShape($w['data'],$w['before'])),$w['version'],$w['id']]);
                else saveRecord($db,$w['id'],$w['kind'],$w['data']);
                audit($db,$w['id'],$u['id'],'kreutzwiesner_import',['batch'=>$plan['batch'],'before'=>$w['before'],'version'=>$w['version'],'source'=>'quelle_kreutzwiesner_pdf']);
            }
            $result=['batch'=>$plan['batch'],'counts'=>$plan['counts'],'importiert_am'=>stamp(),'actor'=>$u['id'],'konflikte_erhalten'=>count($plan['conflicts'])];
            query($db,'INSERT INTO ah_settings (id,data) VALUES (?,?)',[$plan['batch'],jencode($result)]);
            audit($db,$plan['batch'],$u['id'],'kreutzwiesner_complete',$result);
            return ['applied'=>true,'result'=>$result];
        });
    }
    fail(404,'Import-Endpunkt nicht gefunden.');
}
