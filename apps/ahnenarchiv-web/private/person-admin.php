<?php
declare(strict_types=1);
// Version 2.1.4: reversible Personenkorrekturen, nur mit Administratorrechten.
// Eine "Loeschung" ist ein Tombstone (archived_person), damit verlorene Quellen
// und Familienkanten innerhalb einer Transaktion wiederhergestellt werden koennen.

function paRow(string $table,array $r): array {
    if ($table==='records') return ['kind'=>$r['kind'],'data'=>$r['data'],'version'=>$r['version']];
    if ($table==='settings') return ['data'=>$r['data']];
    if ($table==='shares') return ['active'=>(int)$r['active'],'data'=>$r['data']];
    throw new RuntimeException('Unbekannte Tabellenart.');
}
function paItems(PDO $db): array {
    $out=[];
    foreach (records($db) as $r) $out['records:'.$r['id']]=paRow('records',$r);
    foreach (query($db,"SELECT id,data FROM ah_settings WHERE id LIKE 'import_alias_%'")->fetchAll() as $r)
        $out['settings:'.$r['id']]=['data'=>decode($r['data'])];
    foreach (query($db,'SELECT id,active,data FROM ah_shares')->fetchAll() as $r)
        $out['shares:'.$r['id']]=['active'=>(int)$r['active'],'data'=>decode($r['data'])];
    return $out;
}
function paHasValue(mixed $x): bool {return $x!==null&&$x!==''&&$x!==[]&&$x!=='unbekannt'&&$x!=='ungeklaert';}
function paMergeData(mixed $keep,mixed $incoming,string $path,array &$conflicts): mixed {
    if(!paHasValue($incoming))return $keep;
    if(!paHasValue($keep))return $incoming;
    if($keep===$incoming)return $keep;
    if(is_array($keep)&&is_array($incoming)) {
        if(array_is_list($keep)&&array_is_list($incoming)) {
            $result=$keep;$keys=[];
            foreach($keep as $v)$keys[jencode($v)]=true;
            foreach($incoming as $v)if(!isset($keys[jencode($v)])){$result[]=$v;$keys[jencode($v)]=true;}
            return $result;
        }
        $result=$keep;
        foreach($incoming as $key=>$value) $result[$key]=paMergeData($result[$key]??null,$value,$path.'.'.$key,$conflicts);
        return $result;
    }
    if(count($conflicts)<60)$conflicts[]=$path.' – bestehender Wert bleibt erhalten';
    return $keep;
}
function paRelKey(array $x): string {
    $from=$x['von_person_id']??'';$to=$x['zu_person_id']??'';$type=$x['typ']??'';
    if($type==='partner'&&strcmp($from,$to)>0)[$from,$to]=[$to,$from];
    return jencode([$type,$from,$to]);
}
function paFamilyKey(array $x): string {
    $parts=$x['partner_person_ids']??[];sort($parts,SORT_STRING);
    // Keine Fusion unterschiedlicher Ein-Eltern-Familien nur anhand einer Person.
    return count($parts)===2?jencode($parts):'';
}
function paArrays(array $data): array {return array_values(array_unique(array_filter($data,'is_string')));}
function paChange(array &$items,string $id,array $row): void {$items[$id]=$row;}
function paPending(PDO $db,string $source,string $target=''): array {
    $out=[];
    foreach(query($db,"SELECT id,target,kind,payload FROM ah_proposals WHERE status='pending'")->fetchAll() as $p){
        $payload=$p['payload'];
        foreach(array_filter([$source,$target]) as $id)if($p['target']===$id||str_contains($payload,'"'.$id.'"')){$out[]=$p['id'];break;}
    }return $out;
}
function paValidateGraph(array $items): void {
    $parent=[];$spouses=[];$known=[];
    foreach($items as $key=>$row)if(str_starts_with($key,'records:')&&$row['kind']==='person')$known[substr($key,8)]=true;
    foreach($items as $key=>$row){if(!str_starts_with($key,'records:'))continue;$x=$row['data'];$kind=$row['kind'];
        if($kind==='relationship'){
            $a=$x['von_person_id']??'';$b=$x['zu_person_id']??'';
            if(!isset($known[$a],$known[$b])||$a===$b)fail(409,'Ungültiger Personenbezug nach der Korrektur.');
            if(($x['typ']??'')==='eltern_kind')$parent[$a][$b]=true;
            elseif(($x['typ']??'')==='partner'){$pair=[$a,$b];sort($pair);$spouses[jencode($pair)]=true;}
        }
        if($kind==='family'){
            $parents=paArrays($x['partner_person_ids']??[]);$children=paArrays($x['kinder_person_ids']??[]);
            if(count($parents)>2||array_intersect($parents,$children))fail(409,'Widerspruechliche Familiengruppe nach Korrektur.');
            foreach(array_merge($parents,$children) as $person)if(!isset($known[$person]))fail(409,'Familie verweist auf nicht vorhandene Person.');
            if(count($parents)===2){$pair=$parents;sort($pair);$spouses[jencode($pair)]=true;}
            foreach($parents as $a)foreach($children as $b)$parent[$a][$b]=true;
        }
    }
    foreach($parent as $a=>$children)foreach($children as $b=>$_){$pair=[$a,$b];sort($pair);if(isset($spouses[jencode($pair)]))fail(409,'Elternteil und Kind koennen nicht gleichzeitig Ehepartner sein.');}
    // DFS zur Erkennung neuer oder bestehender Abstammungskreise.
    $visited=[];$active=[];
    $walk=function(string $id)use(&$walk,&$visited,&$active,$parent):void{
        if(isset($active[$id]))fail(409,'Abstammungskreis erkannt: Zusammenfuehrung gesperrt.');
        if(isset($visited[$id]))return;
        $active[$id]=true;
        foreach(array_keys($parent[$id]??[]) as $child)$walk((string)$child);
        unset($active[$id]);$visited[$id]=true;
    };
    foreach(array_keys($parent) as $id)$walk((string)$id);
}
function paPlan(PDO $db,string $operation,string $source,string $target=''): array {
    if(!in_array($operation,['delete','merge'],true))fail(422,'Unbekannte Aktion.');
    $source=identifier($source);if($operation==='merge')$target=identifier($target);
    if($operation==='merge'&&$source===$target)fail(422,'Quell- und Zielperson sind gleich.');
    $original=paItems($db);$items=$original;
    $skey='records:'.$source;$tkey='records:'.$target;
    if(!isset($items[$skey])||$items[$skey]['kind']!=='person')fail(404,'Person nicht vorhanden oder bereits geloescht.');
    if($operation==='merge'&&(!isset($items[$tkey])||$items[$tkey]['kind']!=='person'))fail(404,'Zielperson nicht vorhanden.');
    $pending=paPending($db,$source,$target);
    if($pending)fail(409,'Zuerst offene Personenvorschlaege/Importe pruefen: '.count($pending).' betroffene Vorschlaege.');
    if($operation==='merge'){
        foreach($items as $key=>$row){if(!str_starts_with($key,'records:'))continue;$x=$row['data'];
            if($row['kind']==='relationship'&&in_array($x['typ']??null,['partner','eltern_kind'],true)){
                $a=$x['von_person_id']??'';$b=$x['zu_person_id']??'';
                if(($a===$source&&$b===$target)||($a===$target&&$b===$source))fail(409,'Diese Personen sind bereits direkt als Partner oder Elternteil/Kind verbunden. Keine Zusammenfuehrung moeglich.');
            }
            if($row['kind']==='family'){
                $parents=$x['partner_person_ids']??[];$children=$x['kinder_person_ids']??[];
                if(in_array($source,$parents,true)&&in_array($target,$parents,true)||
                   (in_array($source,$parents,true)&&in_array($target,$children,true))||
                   (in_array($target,$parents,true)&&in_array($source,$children,true)))
                    fail(409,'Quell- und Zielperson sind in derselben Familie direkt verwandt oder verheiratet. Zusammenfuehrung gesperrt.');
            }
        }
    }
    $info=['source'=>['id'=>$source,'name'=>$items[$skey]['data']['anzeigename']??$source,'birth'=>gp($items[$skey]['data'],'geburt.datum.iso')],
        'target'=>$operation==='merge'?['id'=>$target,'name'=>$items[$tkey]['data']['anzeigename']??$target,'birth'=>gp($items[$tkey]['data'],'geburt.datum.iso')]:null,
        'warnings'=>[],'counts'=>['families'=>0,'relationships'=>0,'media'=>0,'aliases'=>0,'shares'=>0],'changed'=>0];
    if($operation==='merge'){
        $sa=$items[$skey]['data'];$ta=$items[$tkey]['data'];
        foreach(['geburt','tod'] as $event){$a=gp($sa,$event.'.datum.iso');$b=gp($ta,$event.'.datum.iso');if(paHasValue($a)&&paHasValue($b)&&$a!==$b)fail(409,'Unterschiedliche '.$event.'sdaten. Identitaeten zuerst manuell abgleichen.');}
        $items[$tkey]['data']=paMergeData($ta,$sa,'Person',$info['warnings']);
    }
    $items[$skey]['kind']='archived_person';
    $items[$skey]['data']['verwaltung']['archiviert']=true;
    if($operation==='merge')$items[$skey]['data']['verwaltung']['zusammengefuehrt_mit']=$target;
    // Alle expliziten Verweise in Familien, Beziehungen und Medien umhaengen / entfernen.
    foreach($items as $key=>&$row){
        if(!str_starts_with($key,'records:')||in_array($key,[$skey,$tkey],true))continue;
        $kind=$row['kind'];$x=&$row['data'];
        if($kind==='family'){
            $before=$x;
            foreach(['partner_person_ids','kinder_person_ids'] as $field){
                if(!is_array($x[$field]??null))continue;
                $values=$x[$field];$values=$operation==='delete'?array_values(array_filter($values,fn($id)=>$id!==$source)):array_map(fn($id)=>$id===$source?$target:$id,$values);
                $x[$field]=paArrays($values);
            }
            if($before!==$x){$info['counts']['families']++;
                if(empty($x['partner_person_ids'])||(count($x['partner_person_ids'])<2&&empty($x['kinder_person_ids'])))$row['kind']='archived_family';
            }
        }elseif($kind==='relationship'){
            if(($x['von_person_id']??null)===$source||($x['zu_person_id']??null)===$source){$info['counts']['relationships']++;
                if($operation==='delete')$row['kind']='archived_relationship';
                else {foreach(['von_person_id','zu_person_id'] as $field)if(($x[$field]??null)===$source)$x[$field]=$target;}
            }
        }elseif(in_array($kind,['media','staged_media'],true)){
            $before=$x;
            if(isset($x['person_ids'])&&is_array($x['person_ids'])){
                $values=$operation==='delete'?array_values(array_filter($x['person_ids'],fn($id)=>$id!==$source)):array_map(fn($id)=>$id===$source?$target:$id,$x['person_ids']);
                $x['person_ids']=paArrays($values);
            }
            if(isset($x['zuordnungen'])&&is_array($x['zuordnungen'])){
                $x['zuordnungen']=array_values(array_filter(array_map(function($v)use($operation,$source,$target){
                    if(!is_array($v)||($v['person_id']??null)!==$source)return $v;
                    if($operation==='delete')return null;
                    $v['person_id']=$target;return $v;
                },$x['zuordnungen']),fn($v)=>$v!==null));
            }
            if($before!==$x)$info['counts']['media']++;
        }
    }unset($row,$x);
    if($operation==='merge'){
        // Ausschliesslich DURCH DIESE Zusammenfuehrung entstandene Dubletten anfassen.
        // Vorhandene, fremde Doppeleintraege bleiben unangetastet.
        $relGroups=[];
        foreach($items as $key=>$row)if(str_starts_with($key,'records:')&&$row['kind']==='relationship'){
            $x=$row['data'];if(($x['von_person_id']??'')!==$target&&($x['zu_person_id']??'')!==$target)continue;
            $relGroups[paRelKey($x)][]=$key;
        }
        foreach($relGroups as $group){
            if(count($group)<2)continue;
            $touched=array_values(array_filter($group,fn($key)=>$items[$key]!==$original[$key]));
            if(!$touched)continue;
            $unchanged=array_values(array_diff($group,$touched));$keep=$unchanged[0]??$touched[0];
            foreach($touched as $key)if($key!==$keep){$items[$key]['kind']='archived_relationship';$info['warnings'][]='Doppelte Beziehung archiviert: '.substr($key,8);}
        }
        // Doppelte Ehegruppen nur bei gleichem Elternpaar und Beteiligung des Ziels.
        $familyGroups=[];$familyRedirect=[];
        foreach($items as $key=>$row)if(str_starts_with($key,'records:')&&$row['kind']==='family'){
            if(!in_array($target,$row['data']['partner_person_ids']??[],true))continue;
            $fk=paFamilyKey($row['data']);if($fk!=='')$familyGroups[$fk][]=$key;
        }
        foreach($familyGroups as $group){
            if(count($group)<2)continue;
            $touched=array_values(array_filter($group,fn($key)=>$items[$key]!==$original[$key]));
            if(!$touched)continue;
            $unchanged=array_values(array_diff($group,$touched));$keepKey=$unchanged[0]??$touched[0];
            foreach($touched as $key){if($key===$keepKey)continue;
                $keep=&$items[$keepKey]['data'];$incoming=$items[$key]['data'];
                $keep['kinder_person_ids']=paArrays(array_merge($keep['kinder_person_ids']??[],$incoming['kinder_person_ids']??[]));
                $keep['hochzeit']=paMergeData($keep['hochzeit']??[], $incoming['hochzeit']??[],'Familie.Hochzeit',$info['warnings']);
                foreach(['quellen_verweise','notizen'] as $field)if(isset($incoming[$field]))$keep[$field]=paMergeData($keep[$field]??[],$incoming[$field], 'Familie.'.$field,$info['warnings']);
                unset($keep);
                $items[$key]['kind']='archived_family';$familyRedirect[substr($key,8)]=substr($keepKey,8);
                $info['warnings'][]='Doppelte Ehegruppe vereinigt: '.substr($key,8);
            }
        }
        foreach($items as $key=>&$row)if(str_starts_with($key,'records:')&&$row['kind']==='relationship'){
            $familyId=$row['data']['familie_id']??null;
            if(is_string($familyId)&&isset($familyRedirect[$familyId]))$row['data']['familie_id']=$familyRedirect[$familyId];
        }unset($row);
        // Import-Identitaeten auf den verbleibenden Datensatz umstellen.
        foreach($items as $key=>&$row)if(str_starts_with($key,'settings:')&&($row['data']['target']??'')===$source){$row['data']['target']=$target;$info['counts']['aliases']++;}unset($row);
    }
    // Ein explizit auf Personen eingeschraenkter Link darf nach dem Loeschen nicht auf ALLE Personen fallen.
    foreach($items as $key=>&$row)if(str_starts_with($key,'shares:')&&in_array($source,$row['data']['person_ids']??[],true)){
        $ids=$row['data']['person_ids'];
        $ids=$operation==='delete'?array_values(array_filter($ids,fn($id)=>$id!==$source)):array_map(fn($id)=>$id===$source?$target:$id,$ids);
        $row['data']['person_ids']=paArrays($ids);
        if(!$row['data']['person_ids'])$row['active']=0;
        $info['counts']['shares']++;
    }unset($row);
    paValidateGraph($items);
    $changes=[];
    foreach($items as $key=>$after)if(($original[$key]??null)!==$after){$before=$original[$key];if(str_starts_with($key,'records:'))$after['version']=$before['version']+1;$changes[$key]=['before'=>$before,'after'=>$after];}
    if(count($changes)>5000)fail(409,'Zu viele betroffene Datensaetze. Bitte getrennt bereinigen.');
    ksort($changes,SORT_STRING);$info['changed']=count($changes);
    $hash=hash('sha256',jencode(['operation'=>$operation,'source'=>$source,'target'=>$target,'changes'=>$changes]));
    return ['operation'=>$operation,'info'=>$info,'changes'=>$changes,'token'=>$hash];
}
function paApplyChange(PDO $db,string $key,array $before,array $after): void {
    [$table,$id]=explode(':',$key,2);
    if($table==='records'){
        $stmt=query($db,'UPDATE ah_records SET kind=?,data=?,version=? WHERE id=? AND version=?',[$after['kind'],jencode($after['data']),$after['version'],$id,$before['version']]);
        if($stmt->rowCount()!==1)fail(409,'Datensatz zwischenzeitlich geaendert: '.$id);
    }elseif($table==='settings')query($db,'UPDATE ah_settings SET data=? WHERE id=?',[jencode($after['data']),$id]);
    elseif($table==='shares')query($db,'UPDATE ah_shares SET data=?,active=? WHERE id=?',[jencode($after['data']),$after['active'],$id]);
}
function paAdminApi(PDO $db,array $u,string $method,string $path): mixed {
    admin($u);
    if($path==='/api/person-admin/operations'&&$method==='GET'){
        $rows=query($db,"SELECT id,actor,action,data,created FROM ah_audit WHERE action IN ('person_admin_delete','person_admin_merge','person_admin_restore') ORDER BY created DESC LIMIT 100")->fetchAll();
        $undone=[];$list=[];
        foreach($rows as $row){$data=decode($row['data']);if($row['action']==='person_admin_restore'){$undone[$data['restores_id']??'']=true;continue;}
            $list[]=['id'=>$row['id'],'action'=>$row['action'],'created'=>$row['created'],'name'=>$data['info']['source']['name']??'', 'target_name'=>$data['info']['target']['name']??null,'undone'=>isset($undone[$row['id']])];
        }return $list;
    }
    if(preg_match('#^/api/person-admin/([A-Za-z0-9_-]+)/preview$#D',$path,$m)&&$method==='POST'){
        $b=body();$operation=$b['operation']??'delete';$plan=paPlan($db,$operation,$m[1],(string)($b['target_id']??''));
        return ['info'=>$plan['info'],'token'=>$plan['token'],'operation'=>$operation];
    }
    if(preg_match('#^/api/person-admin/([A-Za-z0-9_-]+)/apply$#D',$path,$m)&&$method==='POST'){
        $b=body();$op=$b['operation']??'';$target=(string)($b['target_id']??'');$token=$b['token']??'';
        if(!is_string($token)||!preg_match('/^[a-f0-9]{64}$/D',$token))fail(422,'Zuerst Vorschau bestaetigen.');
        return transaction($db,function()use($db,$u,$op,$target,$token,$m){
            $plan=paPlan($db,$op,$m[1],$target);
            if(!hash_equals($plan['token'],$token))fail(409,'Personen oder Familien haben sich seit der Vorschau geaendert. Erneut pruefen.');
            foreach($plan['changes'] as $key=>$change)paApplyChange($db,$key,$change['before'],$change['after']);
            audit($db,$m[1],$u['id'],'person_admin_'.$op,['info'=>$plan['info'],'changes'=>$plan['changes']]);
            return ['ok'=>true,'affected'=>count($plan['changes']),'operation'=>$op];
        });
    }
    if(preg_match('#^/api/person-admin/([a-f0-9]{32})/restore$#D',$path,$m)&&$method==='POST'){
        return transaction($db,function()use($db,$u,$m){
            $a=one($db,'SELECT * FROM ah_audit WHERE id=?',[$m[1]]);
            if(!$a||!in_array($a['action'],['person_admin_delete','person_admin_merge'],true))fail(404,'Korrektur nicht gefunden.');
            $done=query($db,"SELECT id,data FROM ah_audit WHERE action='person_admin_restore'")->fetchAll();
            foreach($done as $row)if((decode($row['data'])['restores_id']??'')===$a['id'])fail(409,'Bereits wiederhergestellt.');
            $payload=decode($a['data']);$changes=$payload['changes']??[];
            foreach($changes as $key=>$item){
                [$table,$id]=explode(':',$key,2);$current=null;
                if($table==='records'){$r=getRecord($db,$id);if($r)$current=paRow('records',$r);}
                if($table==='settings'){$r=one($db,'SELECT data FROM ah_settings WHERE id=?',[$id]);if($r)$current=['data'=>decode($r['data'])];}
                if($table==='shares'){$r=one($db,'SELECT active,data FROM ah_shares WHERE id=?',[$id]);if($r)$current=['active'=>(int)$r['active'],'data'=>decode($r['data'])];}
                $expected=$item['after']??null;
                // Versionen duerfen durch eine inzwischen wieder rueckgaengig gemachte
                // Folgekorrektur hoeher liegen; entscheidend sind exakte Nutzdaten.
                if($table==='records'&&is_array($current)&&is_array($expected)){
                    unset($current['version'],$expected['version']);
                }
                if($current!==$expected)fail(409,'Seit der Korrektur wurde ein betroffener Datensatz geaendert. Nicht automatisch rueckgaengig machen.');
            }
            foreach($changes as $key=>$item){$before=$item['before'];$after=$item['after'];
                if(str_starts_with($key,'records:')){
                    [, $id]=explode(':',$key,2);
                    $current=getRecord($db,$id);
                    $after['version']=$current['version'];$before['version']=$current['version']+1;
                }
                paApplyChange($db,$key,$after,$before);
            }
            audit($db,$a['target'],$u['id'],'person_admin_restore',['restores_id'=>$a['id'],'info'=>$payload['info']??[]]);
            return ['ok'=>true,'restored'=>count($changes)];
        });
    }
    fail(404,'Unbekannte Personenverwaltung.');
}
