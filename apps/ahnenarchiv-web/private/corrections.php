<?php
declare(strict_types=1);
require_once __DIR__.'/core.php';
// Exact source-file correction: the three embedded portraits were rotated in the seed.
const PORTRAIT_FIX=[
 ['person'=>'person_a01aa536-f542-5a49-af7d-a7c1186b5b2e','old'=>'medium_1d6d8e95-6ca5-5015-adca-539239ca938f','new'=>'medium_bdca00ad-58f4-5075-8470-821b55958844','page'=>147],
 ['person'=>'person_f669c158-c16c-5f89-b5b8-38f19043ff6c','old'=>'medium_b223b3f5-a303-52c6-8f32-359709b6117f','new'=>'medium_1d6d8e95-6ca5-5015-adca-539239ca938f','page'=>148],
 ['person'=>'person_11413b07-aa2c-518b-bf0b-f5dea17c0985','old'=>'medium_bdca00ad-58f4-5075-8470-821b55958844','new'=>'medium_b223b3f5-a303-52c6-8f32-359709b6117f','page'=>149],
];
function portraitCorrection(PDO $db): ?array {
    $people=[];$media=[];$allCorrect=true;$allOriginal=true;
    foreach(PORTRAIT_FIX as $fix){$p=getRecord($db,$fix['person']);$m=getRecord($db,$fix['new']);
        if(!$p||$p['kind']!=='person'||!$m||$m['kind']!=='media')fail(409,'Die erwarteten Personen oder Bilder fehlen. Bildzuordnung bitte manuell prüfen.');
        $people[$p['id']]=$p;$media[$m['id']]=$m;
        $allCorrect=$allCorrect&&($p['data']['portraet_medien_id']??null)===$fix['new'];
        $allOriginal=$allOriginal&&($p['data']['portraet_medien_id']??null)===$fix['old'];
    }
    if($allCorrect)return null;
    if(!$allOriginal)fail(409,'Porträtzuordnungen wurden bereits teilweise geändert. Die Korrektur überschreibt keine abweichenden Zuordnungen.');
    $knownMedia=array_column(PORTRAIT_FIX,'new');$knownPeople=array_column(PORTRAIT_FIX,'person');$changes=[];$summary=[];
    foreach(PORTRAIT_FIX as $fix){$p=$people[$fix['person']];$data=$p['data'];$data['portraet_medien_id']=$fix['new'];
        $data['anhaenge']=array_values(array_filter($data['anhaenge']??[],fn($a)=>!in_array($a['medium_id']??null,$knownMedia,true)));
        $data['anhaenge'][]=['medium_id'=>$fix['new'],'rolle'=>'portraet','seite'=>$fix['page'],'beschreibung'=>'Bildzuordnung anhand der beschrifteten Originalseite korrigiert.','zuordnung'=>'korrigiert_nach_originalseite','quellen_verweise'=>[['quelle_id'=>'quelle_pdf','seite'=>$fix['page']]]];
        $changes[]=['id'=>$p['id'],'kind'=>'person','base_version'=>$p['version'],'after'=>$data];
        $summary[]=['name'=>$data['anzeigename'],'old'=>$fix['old'],'new'=>$fix['new'],'page'=>$fix['page']];
        $m=$media[$fix['new']];$data=$m['data'];
        $data['zuordnungen']=array_values(array_filter($data['zuordnungen']??[],fn($a)=>!in_array($a['person_id']??null,$knownPeople,true)));
        $data['zuordnungen'][]=['person_id'=>$fix['person'],'rolle'=>'portraet','status'=>'korrigiert_nach_originalseite','quellen_verweise'=>[['quelle_id'=>'quelle_pdf','seite'=>$fix['page']]]];
        if(isset($data['person_ids']))$data['person_ids']=array_merge(array_values(array_diff($data['person_ids'],$knownPeople)),[$fix['person']]);
        $changes[]=['id'=>$m['id'],'kind'=>'media','base_version'=>$m['version'],'after'=>$data];
    }
    return ['changes'=>$changes,'summary'=>$summary];
}
function portraitFixSubmit(PDO $db,array $u): array {
    admin($u);return transaction($db,function()use($db,$u){
        $prior=one($db,"SELECT * FROM ah_proposals WHERE kind='portrait_fix' AND target='portrait_fix_20261009' AND status='pending'");if($prior)return proposalJson($prior);
        $payload=portraitCorrection($db);if(!$payload)return ['already_correct'=>true];$id=uid();
        query($db,'INSERT INTO ah_proposals VALUES (?,?,?,?,?,?,?,?,?,?,?)',[$id,$u['id'],'portrait_fix','portrait_fix_20261009',0,jencode($payload),'Porträtkorrektur anhand Originalstammbaum, Seiten 147–149','pending',stamp(),null,'']);return proposalJson(one($db,'SELECT * FROM ah_proposals WHERE id=?',[$id]));
    });
}
function portraitFixApprove(PDO $db,array $u,array $p): void {
    $payload=decode($p['payload']);
    foreach($payload['changes'] as $change){$r=getRecord($db,$change['id']);
        if(!$r||$r['kind']!==$change['kind']||$r['version']!==$change['base_version'])fail(409,'Datensatz inzwischen geändert. Vorschlag ablehnen und Korrektur erneut zur Prüfung anlegen.');
        $version=$r['version']+1;$after=$change['after'];
        query($db,'UPDATE ah_records SET data=?,version=? WHERE id=?',[jencode(preserveShape($after,json_decode($r['_raw_data']))),$version,$r['id']]);
        audit($db,$r['id'],$u['id'],'approve',['proposal'=>$p['id'],'source'=>$p['source'],'before'=>json_decode($r['_raw_data'],false),'after'=>$after,'version'=>$version]);
    }
}

const FAMILY_CONFIRMATION=[
 ['id'=>'beziehung_62a68aba-e153-5940-8d04-c17eecdf8509','from'=>'person_81c723b8-903f-5724-b9b5-aa46bb81d867','to'=>'person_79cf385d-bbc3-535c-836f-79498daffdf6'],
 ['id'=>'beziehung_8603f734-2486-50ea-949a-7dd8ae353bed','from'=>'person_6d5206e0-b52c-5d8d-8b37-5fe9048f2d84','to'=>'person_79cf385d-bbc3-535c-836f-79498daffdf6'],
 ['id'=>'beziehung_5963a2d2-7210-5fef-9e57-c2dd52cecac2','from'=>'person_79cf385d-bbc3-535c-836f-79498daffdf6','to'=>'person_f669c158-c16c-5f89-b5b8-38f19043ff6c'],
 ['id'=>'beziehung_0cb5ebf4-cd06-5bfc-870e-f5b0b036bc2e','from'=>'person_35eae18e-5bf6-5be9-8cd0-90e0a4cebe27','to'=>'person_f669c158-c16c-5f89-b5b8-38f19043ff6c'],
];
function familyConfirmationSubmit(PDO $db,array $u): array {
    admin($u);return transaction($db,function()use($db,$u){
        $prior=one($db,"SELECT * FROM ah_proposals WHERE kind='relationship_confirmation' AND target='family_confirmation_20261009' AND status='pending'");if($prior)return proposalJson($prior);
        $changes=[];$summary=[];
        foreach(FAMILY_CONFIRMATION as $edge){$r=getRecord($db,$edge['id']);
            if(!$r||$r['kind']!=='relationship'||($r['data']['typ']??'')!=='eltern_kind'||($r['data']['von_person_id']??'')!==$edge['from']||($r['data']['zu_person_id']??'')!==$edge['to'])fail(409,'Erwartete Eltern-Kind-Verbindung fehlt oder wurde geändert. Bitte einzeln prüfen.');
            if(($r['data']['belegt']??false)===true)continue;
            $data=$r['data'];$data['belegt']=true;$data['status']='bestaetigt';
            $data['bestaetigung']=['quelle'=>'Ausdrückliche Bestätigung von Flo Huschka am 09.10.2026: Eltern-Kind-Verbindungen sind belegt.','pruefer'=>$u['id'],'datum'=>stamp()];
            $changes[]=['id'=>$r['id'],'kind'=>'relationship','base_version'=>$r['version'],'after'=>$data];
            $parent=getRecord($db,$edge['from']);$child=getRecord($db,$edge['to']);$summary[]=['parent'=>$parent['data']['anzeigename']??$edge['from'],'child'=>$child['data']['anzeigename']??$edge['to']];
        }
        if(!$changes)return ['already_correct'=>true];$id=uid();
        query($db,'INSERT INTO ah_proposals VALUES (?,?,?,?,?,?,?,?,?,?,?)',[$id,$u['id'],'relationship_confirmation','family_confirmation_20261009',0,jencode(['changes'=>$changes,'summary'=>$summary]),'Bestätigung von Flo Huschka am 09.10.2026: Otto/Maria → Florian; Florian/Daniela → Luca.','pending',stamp(),null,'']);return proposalJson(one($db,'SELECT * FROM ah_proposals WHERE id=?',[$id]));
    });
}

function relationshipStatusSubmit(PDO $db,array $u,string $target,array $b): array {
    $status=$b['belegstatus']??'';$source=$b['source']??'';
    if(!in_array($status,['bestaetigt','ungeklaert'],true)||!is_string($source)||!trim($source)||mb_strlen($source)>20000)fail(422,'Belegstatus und Quelle / Begründung erforderlich.');
    return transaction($db,function()use($db,$u,$target,$b,$status,$source){
        $r=getRecord($db,$target);if(!$r||!in_array($r['kind'],['relationship','family'],true))fail(404,'Verbindung nicht gefunden.');
        if(one($db,"SELECT id FROM ah_proposals WHERE kind='relationship_status' AND target=? AND status='pending'",[$target]))fail(409,'Diese Verbindung wartet bereits auf Freigabe.');
        if(!isset($b['base_version'])||$b['base_version']!==$r['version'])fail(409,'Verbindung inzwischen geändert. Seite neu laden.');
        $data=$r['data'];$before=$data['belegstatus']??(($data['belegt']??false)?'bestaetigt':'nicht_eingeordnet');
        $data['belegt']=$status==='bestaetigt';$data['belegstatus']=$status;
        $data['bestaetigung']=['quelle'=>$source,'einreicher'=>$u['id'],'datum'=>stamp()];
        $label=$r['kind']==='family'?implode(' ↔ ',array_map(fn($id)=>getRecord($db,$id)['data']['anzeigename']??$id,$data['partner_person_ids']??[])):(getRecord($db,$data['von_person_id'])['data']['anzeigename']??'').' → '.(getRecord($db,$data['zu_person_id'])['data']['anzeigename']??'');
        $id=uid();$payload=['changes'=>[['id'=>$r['id'],'kind'=>$r['kind'],'base_version'=>$r['version'],'after'=>$data]],'summary'=>[['label'=>$label,'before'=>$before,'after'=>$status]]];
        query($db,'INSERT INTO ah_proposals VALUES (?,?,?,?,?,?,?,?,?,?,?)',[$id,$u['id'],'relationship_status',$target,$r['version'],jencode($payload),$source,'pending',stamp(),null,'']);return proposalJson(one($db,'SELECT * FROM ah_proposals WHERE id=?',[$id]));
    });
}
function templateConfirmationSubmit(PDO $db,array $u): array {
    admin($u);return transaction($db,function()use($db,$u){
        $prior=one($db,"SELECT * FROM ah_proposals WHERE kind='template_confirmation' AND status='pending'");if($prior)return proposalJson($prior);
        $seed=decode(file_get_contents(dirname(__DIR__).'/seed/stammbaum-huschka.json'));$changes=[];$summary=[];
        foreach($seed['beziehungen'] as $original){
            if(($original['elternschaft_typ']??'')!=='elternteil_aus_diagramm')continue;
            $r=getRecord($db,$original['id']);if(!$r||$r['kind']!=='relationship')continue;$d=$r['data'];
            if(($d['status']??'')!=='aus_vorlage'||isset($d['belegstatus'])||($d['belegt']??false)||($d['von_person_id']??'')!==$original['von_person_id']||($d['zu_person_id']??'')!==$original['zu_person_id']||($d['elternschaft_typ']??'')!=='elternteil_aus_diagramm')continue;
            $d['belegt']=true;$d['belegstatus']='bestaetigt';$d['bestaetigung']=['quelle'=>'Eindeutige Verbindungslinie in der ursprünglichen Stammbaumvorlage; Übernahme nach Admin-Prüfung.','einreicher'=>$u['id'],'datum'=>stamp()];
            $changes[]=['id'=>$r['id'],'kind'=>'relationship','base_version'=>$r['version'],'after'=>$d];
            $summary[]=['label'=>(getRecord($db,$d['von_person_id'])['data']['anzeigename']??'').' → '.(getRecord($db,$d['zu_person_id'])['data']['anzeigename']??''),'before'=>'aus_vorlage','after'=>'bestaetigt'];
        }
        if(!$changes)return ['already_correct'=>true];$id=uid();
        query($db,'INSERT INTO ah_proposals VALUES (?,?,?,?,?,?,?,?,?,?,?)',[$id,$u['id'],'template_confirmation','template_confirmation_20261009',0,jencode(['changes'=>$changes,'summary'=>$summary]),'Eindeutig eingezeichnete Elternschaft aus der Stammbaumvorlage übernehmen. Explizit fragliche oder individuell bewertete Beziehungen ausgeschlossen. Keine Aussage über biologische Elternschaft oder unbekannte Namen.','pending',stamp(),null,'']);return proposalJson(one($db,'SELECT * FROM ah_proposals WHERE id=?',[$id]));
    });
}

// Explicitly requested upgrade: source certainty is independent of name/biological certainty.
function adoptTemplateEvidence(PDO $db,array $u,string $root): array {
    admin($u);return transaction($db,function()use($db,$u,$root){
        $marker='template_evidence_142';if(one($db,'SELECT id FROM ah_settings WHERE id=?',[$marker]))return ['already_applied'=>true];
        $seed=decode(file_get_contents($root.'/seed/stammbaum-huschka.json'));$pending=array_column(query($db,"SELECT target FROM ah_proposals WHERE kind='relationship_status' AND status='pending'")->fetchAll(),'target');$count=0;
        foreach(['beziehungen'=>'relationship','familien'=>'family'] as $key=>$kind)foreach($seed[$key] as $original){
            if($kind==='relationship'&&($original['elternschaft_typ']??'')!=='elternteil_aus_diagramm')continue;
            if($kind==='family'&&!in_array($original['typ']??'',['ehe','partnerschaft'],true))continue;
            $r=getRecord($db,$original['id']);if(!$r||$r['kind']!==$kind||in_array($r['id'],$pending,true))continue;$d=$r['data'];
            if(isset($d['belegstatus'])||($d['belegt']??false))continue;
            if($kind==='relationship'&&(($d['status']??'')!=='aus_vorlage'||($d['elternschaft_typ']??'')!==$original['elternschaft_typ']||($d['von_person_id']??'')!==$original['von_person_id']||($d['zu_person_id']??'')!==$original['zu_person_id']))continue;
            if($kind==='family'&&(($d['typ']??'')!==$original['typ']||($d['partner_person_ids']??[])!==$original['partner_person_ids']||($d['forschung']['status']??'')!=='aus_vorlage'))continue;
            $d['belegt']=true;$d['belegstatus']='bestaetigt';$d['bestaetigung']=['quelle'=>'Eindeutig aus ursprünglicher PDF-Vorlage übernommen, auf Anweisung von Flo; Update 1.4.2.','pruefer'=>$u['id'],'datum'=>stamp()];$version=$r['version']+1;
            query($db,'UPDATE ah_records SET data=?,version=? WHERE id=?',[jencode(preserveShape($d,json_decode($r['_raw_data']))),$version,$r['id']]);
            audit($db,$r['id'],$u['id'],'template_evidence',['source'=>$d['bestaetigung']['quelle'],'before'=>json_decode($r['_raw_data']),'after'=>$d,'version'=>$version]);$count++;
        }
        query($db,"UPDATE ah_proposals SET status='rejected',reviewer=?,reason=? WHERE kind='template_confirmation' AND status='pending'",[$u['id'],'Durch automatische Übernahme eindeutiger Vorlagenverbindungen in Update 1.4.2 ersetzt.']);
        query($db,'INSERT INTO ah_settings (id,data) VALUES (?,?)',[$marker,jencode(['count'=>$count,'actor'=>$u['id'],'date'=>stamp()])]);return ['adopted'=>$count];
    });
}
