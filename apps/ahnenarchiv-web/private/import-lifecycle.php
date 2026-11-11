<?php
declare(strict_types=1);

function importStatus(array $d): string {
    return isset($d['rolled_back_at'])?'rolled_back':(isset($d['discarded_at'])?'discarded':($d['proposal']['status']??'draft'));
}
function importSummary(array $d): array {
    return ['id'=>$d['id'],'title'=>$d['title'],'namespace'=>$d['namespace']??null,'created'=>$d['created'],
        'persons'=>count($d['data']['personen']),'proposal'=>$d['proposal']??null,'status'=>importStatus($d)];
}
function importJournalRegister(PDO $db,array $plan,string $id,array $targets): void {
    $aliases=[];
    foreach(incPlanAliases($plan) as $source=>$target){
        $key=incAlias($plan['namespace'],(string)$source);
        if(!one($db,'SELECT id FROM ah_settings WHERE id=?',[$key]))$aliases[$key]=['namespace'=>$plan['namespace'],'source_id'=>(string)$source,'target'=>$target];
    }
    incRegister($db,$plan);
    query($db,'INSERT INTO ah_settings VALUES (?,?)',['import_undo_'.$id,jencode(['targets'=>$targets,'aliases'=>$aliases,'namespace'=>$plan['namespace'],'source_map'=>$plan['source_map'],'identity_map'=>incPlanAliases($plan)])]);
}
function importAuditRows(PDO $db,string $id): array {
    $out=[];
    foreach(query($db,"SELECT * FROM ah_audit WHERE action='approve' AND data LIKE ? ORDER BY id",['%'.$id.'%']) as $row){
        $x=decode($row['data']);
        if(($x['proposal']??null)===$id)$out[]=$row;
    }
    return $out;
}
function importContainsRef(mixed $value,array $ids): bool {
    if(is_string($value))return isset($ids[$value]);
    if(is_array($value)||is_object($value))foreach($value as $key=>$part)if(isset($ids[$key])||importContainsRef($part,$ids))return true;
    return false;
}
function importUndoPlan(PDO $db,array $d): array {
    if(importStatus($d)!=='approved')fail(409,'Nur ein freigegebener Import kann rückabgewickelt werden.');
    $id=$d['proposal']['id'];$p=one($db,'SELECT payload FROM ah_proposals WHERE id=?',[$id]);$plan=decode($p['payload'])['plan']??[];
    $row=one($db,'SELECT data FROM ah_settings WHERE id=?',['import_undo_'.$id]);$journal=$row?decode($row['data']):null;
    $changes=[];$removed=[];$counts=[];
    foreach(importAuditRows($db,$id) as $a){
        $x=json_decode($a['data'],false,512,JSON_THROW_ON_ERROR);$target=$a['target'];$r=getRecord($db,$target);
        if(isset($changes[$target])||!property_exists($x,'before')||!isset($x->after,$x->version)||!$r||
            $r['version']!==$x->version||$r['data']!==decode(jencode($x->after))||($journal&&($journal['targets'][$target]??null)!==$r['kind']))
            fail(409,'Rückabwicklung gesperrt: Datensatz '.$target.' wurde seit dem Import geändert, entfernt oder ist nicht eindeutig protokolliert.');
        $changes[$target]=['before'=>$x->before,'version'=>$r['version'],'kind'=>$r['kind']];
        if($x->before===null)$removed[$target]=true;
        $bucket=$x->before===null?'remove':'restore';$counts[$bucket][$r['kind']]=($counts[$bucket][$r['kind']]??0)+1;
    }
    $complete=$journal?count($changes)===count($journal['targets']):!empty($plan['incremental'])&&isset($removed['src_'.$id]);
    if($complete&&!$journal){
        $expected=array_merge($plan['new']??[],$plan['families']??[],$plan['relationships']??[],$plan['family_patches']??[],
            array_filter($plan['patches']??[],fn($patch)=>!empty($patch['changes'])||!empty($patch['extra'])));
        foreach($expected as $entry)if(!isset($changes[$entry['id']])){$complete=false;break;}
    }
    if(!$complete)fail(409,'Für diesen Import fehlt ein vollständiges Änderungsprotokoll. Die JSON allein kann spätere Änderungen und Altbestand nicht sicher unterscheiden.');
    $aliases=$journal['aliases']??[];$retained=0;
    if(!$journal){
        // Older imports did not record which aliases already existed. Preserve those on existing people.
        foreach(incPlanAliases($plan) as $source=>$target){
            $key=incAlias($plan['namespace'],(string)$source);
            if(isset($removed[$target]))$aliases[$key]=['namespace'=>$plan['namespace'],'source_id'=>(string)$source,'target'=>$target];
            elseif(one($db,'SELECT id FROM ah_settings WHERE id=?',[$key]))$retained++;
        }
    }
    foreach(query($db,"SELECT id,data FROM ah_settings WHERE id LIKE 'import_alias_%'") as $a){
        if(isset($aliases[$a['id']]))continue;
        if(importContainsRef(decode($a['data'])['target']??null,$removed))fail(409,'Eine weitere Quellzuordnung verwendet eine Person aus diesem Import.');
    }
    foreach($aliases as $key=>$expected){
        $a=one($db,'SELECT data FROM ah_settings WHERE id=?',[$key]);
        if(!$a||decode($a['data'])!==$expected)fail(409,'Eine Quellzuordnung hat sich seit dem Import geändert.');
    }
    if($removed){
        foreach(query($db,'SELECT id, data FROM ah_records') as $r){
            if(isset($removed[$r['id']]))continue;
            $future=isset($changes[$r['id']])?$changes[$r['id']]['before']:decode($r['data']);
            if(importContainsRef($future,$removed))fail(409,'Datensatz '.$r['id'].' verweist auf Daten aus diesem Import. Löse zuerst diese Verbindung.');
        }
        foreach(query($db,'SELECT data FROM ah_shares WHERE active=1') as $r)if(importContainsRef(decode($r['data']),$removed))fail(409,'Eine gespeicherte Freigabe verweist auf Personen aus diesem Import.');
        foreach(query($db,"SELECT id,data FROM ah_settings WHERE id LIKE 'import_%'") as $r){
            if(!preg_match('/^import_[a-f0-9]{32}$/D',$r['id'])||$r['id']==='import_'.$d['id'])continue;
            $other=decode($r['data']);
            if(importStatus($other)==='draft'&&importContainsRef($other['mapping']??[],$removed))fail(409,'Ein anderer Importentwurf verwendet Daten aus diesem Import.');
        }
    }
    foreach(query($db,"SELECT id,kind,target,payload,status FROM ah_proposals WHERE id<>? AND (status='pending' OR (kind='import' AND status='approved'))",[$id]) as $other){
        $payload=decode($other['payload']);
        if(importContainsRef($other['target'],$removed)||importContainsRef($payload,$removed))
            fail(409,'Ein anderer offener Vorschlag oder freigegebener Import verwendet Daten aus diesem Import.');
        if($other['kind']!=='import'||!$aliases)continue;
        $undo=one($db,'SELECT data FROM ah_settings WHERE id=?',['import_undo_'.$other['id']]);
        $otherPlan=$undo?decode($undo['data']):($payload['plan']??[]);
        if(isset($otherPlan['namespace']))foreach(incPlanAliases($otherPlan) as $source=>$target)
            if(isset($aliases[incAlias($otherPlan['namespace'],(string)$source)]))fail(409,'Ein anderer Import verwendet eine Quellzuordnung aus diesem Import.');
    }
    return ['id'=>$id,'changes'=>$changes,'aliases'=>$aliases,'summary'=>['remove'=>$counts['remove']??(object)[],'restore'=>$counts['restore']??(object)[],
        'aliases'=>count($aliases),'retained_legacy_aliases'=>$retained]];
}
function importLifecycle(PDO $db,string $root,array $u,string $id,string $action): array {
    if(in_array($action,['undo-preview','undo'],true))admin($u);
    $quarantine=null;$original=null;
    try{
        $result=transaction($db,function()use($db,$root,$u,$id,$action,&$quarantine,&$original){
            $d=importDraft($db,$id,$u);$status=importStatus($d);$key='import_'.$id;
            if($action==='undo-preview'||$action==='undo'){
                $undo=importUndoPlan($db,$d);
                $token=hash('sha256',jencode($undo));
                if($action==='undo-preview')return $undo['summary']+['token'=>$token];
                if(!hash_equals($token,(string)(body()['token']??'')))fail(409,'Bitte Rückabwicklung erneut prüfen.');
                foreach($undo['changes'] as $target=>$x){
                    if($x['before']===null)query($db,'DELETE FROM ah_records WHERE id=?',[$target]);
                    else query($db,'UPDATE ah_records SET data=?,version=? WHERE id=?',[jencode($x['before']),$x['version']+1,$target]);
                }
                foreach(array_keys($undo['aliases']) as $alias)query($db,'DELETE FROM ah_settings WHERE id=?',[$alias]);
                query($db,"UPDATE ah_proposals SET status='rolled_back' WHERE id=?",[$undo['id']]);
                $d['rolled_back_at']=stamp();
                audit($db,$key,$u['id'],'import_rollback',$undo['summary']);
            }elseif($action==='discard'){
                if(!in_array($status,['draft','pending'],true))fail(409,'Nur offene Entwürfe können verworfen werden.');
                query($db,"UPDATE ah_proposals SET status='rejected',reviewer=?,reason=? WHERE target=? AND kind='import' AND status='pending'",[$u['id'],'Import verworfen.',$key]);
                $d['discarded_at']=stamp();
                audit($db,$key,$u['id'],'import_discard',[]);
            }else{
                if(in_array($status,['pending','approved'],true))fail(409,'Import zuerst verwerfen oder rückabwickeln.');
                $media=getRecord($db,$d['media_id']);$filename=$media['data']['datei']??null;
                if($media){
                    if($media['kind']!=='staged_media'||$media['id']!=='draft_'.$id||($media['data']['owner']??null)!==$d['owner']||
                        !preg_match('/^draft_'.preg_quote($id,'/').'\.(json|ged|pdf|png|jpg)$/D',(string)$filename))fail(409,'Die Originalquelle ist nicht eindeutig diesem Import zugeordnet.');
                    foreach(query($db,"SELECT id,data FROM ah_records WHERE kind IN ('media','staged_media') AND id<>?",[$media['id']]) as $r)
                        if((decode($r['data'])['datei']??null)===$filename)fail(409,'Die Originalquelle wird noch an anderer Stelle verwendet.');
                    $original=$root.'/private/media/'.$filename;
                    if(file_exists($original)){
                        $dest=$root.'/private/media/.removed-'.$id;
                        if(file_exists($dest)||!@rename($original,$dest))fail(503,'Originaldatei konnte nicht zum Löschen vorbereitet werden.');
                        $quarantine=$dest;
                    }
                    query($db,'DELETE FROM ah_records WHERE id=?',[$media['id']]);
                }
                foreach(query($db,"SELECT id FROM ah_proposals WHERE target=? AND kind='import'",[$key]) as $p){
                    foreach(importAuditRows($db,$p['id']) as $a)query($db,'DELETE FROM ah_audit WHERE id=?',[$a['id']]);
                    query($db,'DELETE FROM ah_settings WHERE id=?',['import_undo_'.$p['id']]);
                }
                query($db,"DELETE FROM ah_proposals WHERE target=? AND kind='import'",[$key]);
                query($db,'DELETE FROM ah_settings WHERE id=?',[$key]);
                audit($db,$key,$u['id'],'import_delete',[]);
                return ['deleted'=>true];
            }
            unset($d['proposal']);
            query($db,'UPDATE ah_settings SET data=? WHERE id=?',[jencode($d),$key]);
            return ['status'=>importStatus($d)];
        });
    }catch(Throwable $e){if($quarantine)rename($quarantine,$original);throw $e;}
    if($quarantine&&!@unlink($quarantine))$result['warning']='Importdaten gelöscht. Die ausgeblendete Originaldatei .removed-'.$id.' muss im privaten Medienordner manuell gelöscht werden.';
    return $result;
}
