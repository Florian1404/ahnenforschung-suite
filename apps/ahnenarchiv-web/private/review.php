<?php
declare(strict_types=1);

// Shared single/batch review logic. Caller owns the transaction.
function ahReviewProposal(PDO $db,array $u,string $id,array $b): array {
    admin($u);identifier($id);
    if(!in_array($b['decision']??null,['approve','reject'],true))fail(422,'Entscheidung fehlt.');
    $p=one($db,'SELECT * FROM ah_proposals WHERE id=?',[$id]);if(!$p)fail(404,'Vorschlag nicht gefunden.');if($p['status']!=='pending')fail(409,'Vorschlag bereits bearbeitet.');
    $status='rejected';$reason=mb_substr((string)($b['reason']??''),0,20000);
    if(in_array($p['kind'],['person_entry','import','portrait_fix','relationship_confirmation','relationship_status','template_confirmation'],true)){
        if($b['decision']==='approve'){if($p['kind']==='person_entry')entryApprove($db,$u,$p);elseif($p['kind']==='import')importApprove($db,$u,$p);else portraitFixApprove($db,$u,$p);$status='approved';$reason='';}
        query($db,'UPDATE ah_proposals SET status=?,reviewer=?,reason=? WHERE id=?',[$status,$u['id'],$reason,$p['id']]);return proposalJson(one($db,'SELECT * FROM ah_proposals WHERE id=?',[$p['id']]));
    }
    if($b['decision']==='approve'){
        $payload=decode($p['payload']);validate($p['kind'],$payload);$r=getRecord($db,$p['target']);$before=$r?json_decode($r['_raw_data'],false,512,JSON_THROW_ON_ERROR):null;$version=1;
        if($p['kind']==='patch'){
            if(!$r||$r['version']!==(int)$p['base_version'])fail(409,'Datensatz inzwischen geändert. Vorschlag auf Basis des aktuellen Stands neu einreichen.');$data=$r['data'];
            foreach($payload['changes'] as $key=>$value){if(str_ends_with($key,'.datum.iso')){$ev=explode('.',$key)[0];$old=$data[$ev]??[];$data[$ev]['alternativen'][]=['wert'=>$old,'grund'=>'Stand vor Freigabe','bevorzugt'=>false];}sp($data,$key,$value);}
            if(gp($data,'tod.datum.iso'))$data['lebensstatus']='verstorben';chronology($data);
            $data['forschung']['freigegebene_ergaenzungen'][]=['vorschlag_id'=>$p['id'],'quelle'=>$p['source'],'pruefer'=>$u['id'],'datum'=>stamp()];$version=$r['version']+1;
            query($db,'UPDATE ah_records SET data=?,version=? WHERE id=?',[jencode(preserveShape($data,json_decode($r['_raw_data']))),$version,$r['id']]);
        }else{
            if($r)fail(409,'Zieldatensatz existiert bereits.');$data=$payload;$data['id']=$p['target'];
            if($p['kind']==='person'){$data['datensatz_typ']='person';$data['lebensstatus']=$data['lebensstatus']??'unbekannt';$data['forschung']['status']='freigegebener_vorschlag';foreach(['geburt','hochzeit','tod','taufe','bestattung'] as $ev)$data[$ev]=$data[$ev]??['datum'=>['iso'=>null],'ort_original'=>null];}
            if($p['kind']==='relationship'){relationship($db,$data);$data['elternschaft_typ']=$data['elternschaft_typ']??'ungeklaert';$data['biologisch_bestaetigt']=$data['elternschaft_typ']==='biologisch';$data['status']='freigegeben';}
            if($p['kind']==='media'){
                foreach($data['person_ids'] as $pid){$per=getRecord($db,$pid);if(!$per||$per['kind']!=='person')fail(409,'Bildperson muss zuerst freigegeben werden.');}
                $upload=getRecord($db,$data['upload_id']);if(!$upload||$upload['kind']!=='staged_media'||$upload['data']['owner']!==$p['actor'])fail(409,'Upload fehlt oder gehört nicht zum Einreicher.');
                foreach(['datei','mime_type','sha256'] as $k)$data[$k]=$upload['data'][$k];$data['zuordnungen']=array_map(fn($pid)=>['person_id'=>$pid],$data['person_ids']);
            }
            saveRecord($db,$p['target'],$p['kind'],$data);
        }
        audit($db,$p['target'],$u['id'],'approve',['proposal'=>$p['id'],'source'=>$p['source'],'before'=>$before,'after'=>$data,'version'=>$version]);$status='approved';$reason='';
    }
    query($db,'UPDATE ah_proposals SET status=?,reviewer=?,reason=? WHERE id=?',[$status,$u['id'],$reason,$p['id']]);return proposalJson(one($db,'SELECT * FROM ah_proposals WHERE id=?',[$p['id']]));
}

function ahReviewBatch(PDO $db,array $u,array $b): array {
    admin($u);$ids=$b['ids']??null;
    if(!is_array($ids)||!array_is_list($ids)||!$ids||count($ids)>500)fail(422,'Bitte 1 bis 500 Vorschläge auswählen.');
    foreach($ids as $id)identifier($id);
    if(count(array_unique($ids))!==count($ids))fail(422,'Vorschläge dürfen nicht doppelt ausgewählt sein.');
    return transaction($db,function()use($db,$u,$ids){
        $rows=[];
        foreach($ids as $id){$row=one($db,'SELECT * FROM ah_proposals WHERE id=?',[$id]);
            if(!$row||$row['status']!=='pending')fail(409,'Auswahl inzwischen geändert. Prüfliste aktualisieren; es wurde nichts freigegeben.');
            $rows[]=$row;
        }
        // Referenced people must exist before relationship and media approvals.
        $rank=['person'=>0,'person_entry'=>0,'import'=>1,'patch'=>2,'relationship'=>3,'media'=>4];
        usort($rows,fn($a,$b)=>($rank[$a['kind']]??5)<=>($rank[$b['kind']]??5));
        foreach($rows as $row){
            try { ahReviewProposal($db,$u,$row['id'],['decision'=>'approve']); }
            catch(ApiError $e){$payload=decode($row['payload']);$label=$payload['anzeigename']??$payload['person_name']??$payload['title']??$row['target'];
                fail($e->status,$label.': '.$e->getMessage().' Die gesamte Auswahl bleibt offen.');}
        }
        audit($db,'batch_'.uid(),$u['id'],'approve_batch',['proposal_ids'=>$ids,'count'=>count($ids)]);
        return ['ok'=>true,'approved'=>count($ids),'ids'=>$ids];
    });
}
