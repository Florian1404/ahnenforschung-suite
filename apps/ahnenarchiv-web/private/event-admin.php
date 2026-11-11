<?php
declare(strict_types=1);
// 2.1.5: Einzelne Lebensereignisse administrativ korrigieren / archivieren.
// Keine Person, Familie oder Beziehung wird hier entfernt.
function eaDate(mixed $value): array {
    if (!is_string($value)) fail(422,'Datum muss als Text angegeben werden.');
    $value=trim($value);
    if (preg_match('/^(\d{1,2})\.(\d{1,2})\.(\d{4})$/D',$value,$m))
        $value=$m[3].'-'.str_pad($m[2],2,'0',STR_PAD_LEFT).'-'.str_pad($m[1],2,'0',STR_PAD_LEFT);
    if (!preg_match('/^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$/D',$value,$m)) fail(422,'Datum bitte als JJJJ, JJJJ-MM oder JJJJ-MM-TT eingeben.');
    $year=(int)$m[1]; $month=isset($m[2])?(int)$m[2]:null; $day=isset($m[3])?(int)$m[3]:null;
    if($year===0 || $month!==null&&($month<1||$month>12) || $day!==null&&!checkdate($month,$day,$year))fail(422,'Ungültiges Datum.');
    return ['iso'=>$value,'jahr'=>$year,'monat'=>$month,'tag'=>$day,'qualifizierer'=>$day!==null?'exakt':'teilweise','original'=>$value,'konflikt'=>false];
}
function eaEventValue(array $record,string $event): array {
    return is_array($record['data'][$event]??null)?$record['data'][$event]:[];
}
function eaEventKey(array $event): string {
    return json_encode([(string)($event['datum']['iso']??''),trim((string)($event['ort_original']??''))],JSON_UNESCAPED_UNICODE|JSON_THROW_ON_ERROR);
}
function eaPresent(array $event): bool {
    return !empty($event['datum']['iso'])||!empty($event['ort_original']);
}
function eaModifyEvent(array $event,string $field,string $operation,mixed $value): ?array {
    if($operation==='delete'&&$field==='event')return null;
    if($field==='datum') {
        if($operation==='delete')$event['datum']=['iso'=>null];
        else $event['datum']=eaDate($value);
    }elseif($field==='ort_original'){
        if($operation==='delete')$event['ort_original']=null;
        else {
            if(!is_string($value)||!trim($value)||strlen(trim($value))>600)fail(422,'Bitte einen Ort mit maximal 300 Zeichen eingeben.');
            $event['ort_original']=trim($value);
        }
    }
    return $event;
}
function eaPlan(PDO $db,array $body): array {
    $personId=identifier($body['person_id']??'');$sourceId=identifier($body['source_id']??'');
    $event=(string)($body['event']??'');$field=(string)($body['field']??'');$operation=(string)($body['operation']??'');
    if(!in_array($event,['geburt','hochzeit','tod','taufe','bestattung'],true) ||
       !in_array($field,['datum','ort_original','event'],true) ||
       !in_array($operation,['edit','delete'],true) ||
       ($field==='event'&&$operation!=='delete'))fail(422,'Ungültige Ereignisaktion.');
    $person=getRecord($db,$personId);
    if(!$person||$person['kind']!=='person')fail(404,'Person nicht gefunden.');
    $source=getRecord($db,$sourceId);
    if(!$source||!in_array($source['kind'],['person','family'],true) || ($source['kind']==='person'&&$sourceId!==$personId) ||
       ($source['kind']==='family'&&($event!=='hochzeit'||!in_array($personId,$source['data']['partner_person_ids']??[],true))))fail(403,'Ereignis gehört nicht zu dieser Person.');
    $old=eaEventValue($source,$event);
    if($operation==='delete'&&!$old)fail(409,'Ereignis ist bereits leer.');
    if($operation==='delete'&&$field==='datum'&&empty($old['datum']['iso']))fail(409,'Kein Datum zum Löschen vorhanden.');
    if($operation==='delete'&&$field==='ort_original'&&empty($old['ort_original']))fail(409,'Kein Ort zum Löschen vorhanden.');
    $new=eaModifyEvent($old,$field,$operation,$body['value']??null);
    if($new===$old)fail(409,'Keine Änderung am Ereignis.');
    $rows=[$sourceId=>$source];
    $participants=[$personId=>true];
    $anchor=eaEventKey($old);
    $matchedFamilies=[];
    // Nur wirklich identische Hochzeitsangaben an derselben Person rekursiv abgleichen.
    // Andere Ehen und Familienbeziehungen bleiben unverändert.
    if($event==='hochzeit'&&eaPresent($old)){
        foreach(records($db,'family') as $r){
            if(!in_array($personId,$r['data']['partner_person_ids']??[],true))continue;
            if(!eaPresent(eaEventValue($r,$event))||eaEventKey(eaEventValue($r,$event))!==$anchor)continue;
            $rows[$r['id']]=$r;$matchedFamilies[$r['id']]=true;
            foreach($r['data']['partner_person_ids']??[] as $pid)$participants[$pid]=true;
        }
        foreach(array_keys($participants) as $pid){
            $r=getRecord($db,(string)$pid);
            if(!$r||$r['kind']!=='person')continue;
            $h=eaEventValue($r,'hochzeit');
            if(eaPresent($h)&&eaEventKey($h)===$anchor)$rows[$r['id']]=$r;
            // Embedded Hochzeitenspiegel werden weiter unten ebenfalls angepasst.
            if(is_array($r['data']['hochzeiten']??null))$rows[$r['id']]=$r;
        }
    }
    $changes=[];$summary=[];
    foreach($rows as $id=>$r){
        $before=$r['data'];$after=$before;
        $eventValue=$before[$event]??null;
        if(($id===$sourceId&&($operation==='edit'||is_array($eventValue))) || (is_array($eventValue)&&$event==='hochzeit'&&eaPresent($eventValue)&&eaEventKey($eventValue)===$anchor)){
            if($new===null)unset($after[$event]);
            else $after[$event]=eaModifyEvent(is_array($eventValue)?$eventValue:[],$field,$operation,$body['value']??null);
        }
        if($event==='hochzeit'&&is_array($before['hochzeiten']??null)){
            foreach($before['hochzeiten'] as $i=>$h){
                $embedded=$h['ereignis']??null;
                if(!is_array($embedded)||!eaPresent($embedded)||eaEventKey($embedded)!==$anchor)continue;
                // Familie oder Partner muss zum hier bearbeiteten Ereignis gehören.
                $fid=$h['familie_id']??null;
                if($fid&&$matchedFamilies&&!isset($matchedFamilies[$fid])&&$id!==$sourceId)continue;
                if($new===null)unset($after['hochzeiten'][$i]);
                else $after['hochzeiten'][$i]['ereignis']=eaModifyEvent($embedded,$field,$operation,$body['value']??null);
            }
            if(isset($after['hochzeiten']))$after['hochzeiten']=array_values($after['hochzeiten']);
        }
        if($before===$after)continue;
        $changes[$id]=['kind'=>$r['kind'],'version'=>$r['version'],'before'=>$before,'after'=>$after];
        $summary[]=['id'=>$id,'typ'=>$r['kind'],'name'=>$r['kind']==='person'?($r['data']['anzeigename']??$id):'Familiengruppe','vorher'=>['datum'=>$before[$event]['datum']['iso']??null,'ort'=>$before[$event]['ort_original']??null], 'nachher'=>['datum'=>$after[$event]['datum']['iso']??null,'ort'=>$after[$event]['ort_original']??null]];
    }
    if(!$changes)fail(409,'Keine zu ändernden Einträge gefunden.');
    ksort($changes,SORT_STRING);
    if(count($changes)>50)fail(409,'Mehr als 50 gespiegelte Einträge. Bitte zunächst die Dubletten prüfen.');
    $token=hash('sha256',jencode([$personId,$sourceId,$event,$field,$operation,$body['value']??null,$changes]));
    return ['info'=>['person_id'=>$personId,'person_name'=>$person['data']['anzeigename']??$personId,'event'=>$event,'field'=>$field,'operation'=>$operation,'value'=>$body['value']??null,'summary'=>$summary,'count'=>count($changes),'notice'=>count($matchedFamilies)>1?'Gleicher Hochzeitseintrag in mehreren Familiengruppen: Bitte zusätzlich Dubletten zusammenführen.':null], 'changes'=>$changes, 'token'=>$token];
}
function eaAdminApi(PDO $db,array $u,string $method,string $path): mixed {
    admin($u);
    if($method==='POST'&&$path==='/api/event-admin/preview'){
        $plan=eaPlan($db,body());return ['info'=>$plan['info'],'token'=>$plan['token']];
    }
    if($method==='POST'&&$path==='/api/event-admin/apply'){
        $b=body();$token=(string)($b['token']??'');
        if(!preg_match('/^[a-f0-9]{64}$/D',$token))fail(422,'Vorschau fehlt.');
        return transaction($db,function()use($db,$u,$b,$token){
            $plan=eaPlan($db,$b);
            if(!hash_equals($plan['token'],$token))fail(409,'Ereignis seit der Vorschau geändert. Bitte erneut prüfen.');
            foreach($plan['changes'] as $id=>$c){
                $stmt=query($db,'UPDATE ah_records SET data=?,version=? WHERE id=? AND kind=? AND version=?',
                    [jencode($c['after']),$c['version']+1,$id,$c['kind'],$c['version']]);
                if($stmt->rowCount()!==1)fail(409,'Ereignis zwischenzeitlich geändert: '.$id);
            }
            $auditId=uid();
            query($db,'INSERT INTO ah_audit VALUES (?,?,?,?,?,?)',[$auditId,$plan['info']['person_id'],$u['id'],'event_admin_change',jencode(['info'=>$plan['info'],'changes'=>$plan['changes']]),stamp()]);
            return ['ok'=>true,'affected'=>count($plan['changes']),'audit_id'=>$auditId];
        });
    }
    if($method==='GET'&&preg_match('#^/api/event-admin/history/([A-Za-z0-9_-]+)$#D',$path,$m)){
        $id=identifier($m[1]);
        $rows=query($db,"SELECT id,action,created,data FROM ah_audit WHERE target=? AND action IN ('event_admin_change','event_admin_restore') ORDER BY created DESC LIMIT 100",[$id])->fetchAll();
        $undone=[];$out=[];
        foreach($rows as $row){$x=decode($row['data']);if($row['action']==='event_admin_restore'){$undone[$x['restores_id']??'']=true;continue;}
            $out[]=['id'=>$row['id'],'created'=>$row['created'],'info'=>$x['info']??[],'undone'=>isset($undone[$row['id']])];
        }return $out;
    }
    if($method==='POST'&&preg_match('#^/api/event-admin/restore/([a-f0-9]{32})$#D',$path,$m)){
        return transaction($db,function()use($db,$u,$m){
            $row=one($db,'SELECT * FROM ah_audit WHERE id=?',[$m[1]]);
            if(!$row||$row['action']!=='event_admin_change')fail(404,'Änderung nicht gefunden.');
            $dup=query($db,"SELECT data FROM ah_audit WHERE action='event_admin_restore'")->fetchAll();
            foreach($dup as $d)if((decode($d['data'])['restores_id']??'')===$m[1])fail(409,'Bereits rückgängig gemacht.');
            $payload=decode($row['data']);$changes=$payload['changes']??[];
            foreach($changes as $id=>$c){
                $now=getRecord($db,(string)$id);
                if(!$now||$now['kind']!==$c['kind']||$now['data']!==$c['after'])fail(409,'Der Datensatz wurde inzwischen geändert. Automatisches Rückgängigmachen gesperrt.');
            }
            foreach($changes as $id=>$c){
                $now=getRecord($db,(string)$id);
                $stmt=query($db,'UPDATE ah_records SET data=?,version=? WHERE id=? AND kind=? AND version=?',
                    [jencode($c['before']),$now['version']+1,$id,$c['kind'],$now['version']]);
                if($stmt->rowCount()!==1)fail(409,'Paralleländerung erkannt.');
            }
            audit($db,$row['target'],$u['id'],'event_admin_restore',['restores_id'=>$m[1],'info'=>$payload['info']??[]]);
            return ['ok'=>true,'affected'=>count($changes)];
        });
    }
    fail(404,'Unbekannte Ereignisverwaltung.');
}
