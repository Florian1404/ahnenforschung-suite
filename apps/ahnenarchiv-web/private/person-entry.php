<?php
declare(strict_types=1);

const ENTRY_LINES=['huschka','kreutzwiesner','böck','schiessl'];

function entryText(mixed $value,int $max,string $label): ?string {
    if($value===null)return null;
    if(!is_string($value)||mb_strlen($value)>$max)fail(422,$label.' fehlt oder ist zu lang.');
    return trim($value)===''?null:trim($value);
}
function entryLine(mixed $line): ?string {
    if($line===null)return null;
    if(!in_array($line,ENTRY_LINES,true))fail(422,'Unbekannte Hauptlinie.');
    return $line;
}
function entryDate(mixed $date): ?string {
    $date=entryText($date,10,'Datum');dateValue($date);return $date;
}
function entryDuplicate(PDO $db,array $person,?array $other=null): void {
    if(!incKnown($person))return;
    $date=gp($person,'geburt.datum.iso');$names=incNames($person);
    $people=array_column(records($db,'person'),'data');if($other)$people[]=$other;
    foreach($people as $p){
        if(!incKnown($p)||!array_intersect($names,incNames($p)))continue;
        $birth=gp($p,'geburt.datum.iso');
        $precision=min(strlen($date??''),strlen($birth??''));
        if(!$precision||substr($date,0,$precision)===substr($birth,0,$precision))
            fail(409,'Mögliche Dublette: '.$p['anzeigename'].($birth?' (* '.$birth.')':'').'. Bitte die vorhandene Person auswählen oder das Geburtsdatum genauer angeben.');
    }
}
function entryBefore(string $a,string $b): bool {
    $length=min(strlen($a),strlen($b));return substr($a,0,$length)<substr($b,0,$length);
}
function entryMarriageDate(array $person,?string $date): void {
    if(!$date)return;
    $birth=gp($person,'geburt.datum.iso');$death=gp($person,'tod.datum.iso');
    if(($birth&&entryBefore($date,$birth))||($death&&entryBefore($death,$date)))fail(422,'Hochzeit liegt außerhalb der Lebensdaten von '.$person['anzeigename'].'.');
}
function entryEvent(array $data,string $event,?string $date,?string $place): array {
    $old=$data[$event]??[];
    if($date!==gp($data,$event.'.datum.iso')){
        if(!empty($old['datum']))$data[$event]['alternativen'][]=['wert'=>$old,'grund'=>'Stand vor Freigabe','bevorzugt'=>false];
        sp($data,$event.'.datum.iso',$date);
    }
    if($place!==gp($data,$event.'.ort_original'))sp($data,$event.'.ort_original',$place);
    return $data;
}
function entryNewPerson(string $id,array $changes,?string $line): array {
    $p=['id'=>$id,'datensatz_typ'=>'person','lebensstatus'=>'unbekannt','forschung'=>['status'=>'freigegebener_vorschlag']];
    foreach(['geburt','hochzeit','tod','taufe','bestattung'] as $event)$p[$event]=['datum'=>['iso'=>null],'ort_original'=>null];
    foreach($changes as $key=>$value)sp($p,$key,$value);
    if($line!==null)$p['hauptlinie']=$line;
    if(gp($p,'tod.datum.iso'))$p['lebensstatus']='verstorben';
    validate('person',$p);return $p;
}

// Prepare the same grouped change at submission and at approval under the write lock.
function entryPlan(PDO $db,string $id,int $base,array $payload,string $proposalId): array {
    $row=getRecord($db,$id);
    if(($base===0&&$row)||($base>0&&(!$row||$row['kind']!=='person'||$row['version']!==$base)))fail(409,'Person inzwischen geändert. Bitte den aktuellen Stand öffnen und erneut einreichen.');
    $changes=$payload['changes']??[];
    if(!is_array($changes))fail(422,'Personenangaben ungültig.');
    if($changes)validate('patch',['changes'=>$changes]);
    $line=array_key_exists('line',$payload)?entryLine($payload['line']):null;
    $p=$row?$row['data']:entryNewPerson($id,$changes,$line);
    if($row){
        foreach($changes as $key=>$value){
            if(str_ends_with($key,'.datum.iso')&&gp($p,$key)!==$value){
                $event=explode('.',$key)[0];$old=$p[$event]??[];if($old)$p[$event]['alternativen'][]=['wert'=>$old,'grund'=>'Stand vor Freigabe','bevorzugt'=>false];
            }
            sp($p,$key,$value);
        }
        if(array_key_exists('line',$payload)){if($line===null)unset($p['hauptlinie']);else $p['hauptlinie']=$line;}
        if(gp($p,'tod.datum.iso'))$p['lebensstatus']='verstorben';
        chronology($p);
    }else entryDuplicate($db,$p);
    $normalized=['changes'=>$changes,'person_name'=>$p['anzeigename']];
    if(array_key_exists('line',$payload))$normalized['line']=$line;
    if($row){$normalized['before']=[];foreach($changes as $key=>$value)$normalized['before'][$key]=gp($row['data'],$key);$normalized['before_line']=$row['data']['hauptlinie']??null;}
    $writes=[];$m=$payload['marriage']??null;
    if($m!==null){
        if(!is_array($m))fail(422,'Hochzeitsangaben ungültig.');
        $date=entryDate($m['date']??null);$place=entryText($m['place']??null,300,'Hochzeitsort');
        entryMarriageDate($p,$date);
        $mode=$m['mode']??null;$partnerName=null;$family=null;
        $normalizedMarriage=['mode'=>$mode,'date'=>$date,'place'=>$place];
        if($mode==='unknown'){
            if(!empty($m['family_id']))fail(422,'Eine vorhandene Ehe kann nicht vom Ehepartner getrennt werden.');
            if(!$date&&!$place)fail(422,'Bitte Hochzeitsdatum oder Hochzeitsort eintragen.');
            $p=entryEvent($p,'hochzeit',$date,$place);
        }elseif($mode==='existing'||$mode==='new'){
            if($mode==='existing'){
                $partnerId=identifier($m['partner_id']??null);
                if($partnerId===$id)fail(422,'Eine Person kann nicht mit sich selbst verheiratet sein.');
                $partnerRow=getRecord($db,$partnerId);
                if(!$partnerRow||$partnerRow['kind']!=='person')fail(409,'Ehepartner wurde nicht gefunden.');
                $partner=$partnerRow['data'];$normalizedMarriage['partner_id']=$partnerId;
            }else{
                if(!is_array($m['partner']??null)||!empty($m['family_id']))fail(422,'Neue Partnerdaten ungültig.');
                $input=$m['partner'];$partnerId='person_spouse_'.hash('sha256',$id.'|'.$proposalId);
                if(strlen($partnerId)>100||getRecord($db,$partnerId))fail(409,'Kennung für Ehepartner bereits belegt.');
                $pc=['anzeigename'=>entryText($input['name']??null,200,'Name des Ehepartners'),
                     'namen.geburtsname'=>entryText($input['birth_name']??null,200,'Geburtsname'),
                     'geburt.datum.iso'=>entryDate($input['birth']??null),'geburt.ort_original'=>entryText($input['birth_place']??null,300,'Geburtsort'),
                     'tod.datum.iso'=>entryDate($input['death']??null),'tod.ort_original'=>entryText($input['death_place']??null,300,'Sterbeort')];
                $partner=entryNewPerson($partnerId,$pc,entryLine($input['line']??null));
                entryDuplicate($db,$partner,$p);
                $normalizedMarriage['partner']=['name'=>$pc['anzeigename'],'birth_name'=>$pc['namen.geburtsname'],'birth'=>$pc['geburt.datum.iso'],'birth_place'=>$pc['geburt.ort_original'],'death'=>$pc['tod.datum.iso'],'death_place'=>$pc['tod.ort_original'],'line'=>$partner['hauptlinie']??null];
                $writes[]=['person',$partner,null];
            }
            $partnerName=$partner['anzeigename'];entryMarriageDate($partner,$date);
            $pair=[$id,$partnerId];sort($pair,SORT_STRING);
            if(!empty($m['family_id'])){
                $family=getRecord($db,identifier($m['family_id']));
                $pairBefore=$family['data']['partner_person_ids']??[];sort($pairBefore,SORT_STRING);
                if(!$family||$family['kind']!=='family'||$pairBefore!==$pair)fail(409,'Diese Ehe gehört zu anderen Personen oder ist nicht mehr vorhanden.');
                if(($m['family_version']??null)!==$family['version'])fail(409,'Ehe wurde inzwischen geändert. Bitte erneut öffnen.');
            }else{
                $matches=array_values(array_filter(records($db,'family'),function($f)use($pair){
                    $ids=$f['data']['partner_person_ids']??[];sort($ids,SORT_STRING);return $ids===$pair;
                }));
                if(count($matches)>1)fail(409,'Mehrere Ehen zu diesem Paar gefunden. Bitte die passende vorhandene Ehe auswählen.');
                $family=$matches[0]??null;
                if($family){
                    $oldDate=gp($family['data'],'hochzeit.datum.iso');$oldPlace=gp($family['data'],'hochzeit.ort_original');
                    if(($oldDate&&$date&&$date!==$oldDate)||($oldPlace&&$place&&$place!==$oldPlace))fail(409,'Zu diesem Paar gibt es bereits eine Ehe mit anderen Angaben. Bitte vorhandene Ehe ausdrücklich auswählen.');
                    $date=$date??$oldDate;$place=$place??$oldPlace;
                }
            }
            if($family){
                $normalizedMarriage['family_id']=$family['id'];$normalizedMarriage['family_version']=$family['version'];
                $normalizedMarriage['before_date']=gp($family['data'],'hochzeit.datum.iso');$normalizedMarriage['before_place']=gp($family['data'],'hochzeit.ort_original');
            }
            $f=$family?$family['data']:['id'=>'family_'.hash('sha256',implode('|',$pair)),'partner_person_ids'=>$pair,'kinder_person_ids'=>[],'status'=>'freigegebener_vorschlag'];
            $f=entryEvent($f,'hochzeit',$date,$place);$f['hochzeit']=$f['hochzeit']??['datum'=>['iso'=>null],'ort_original'=>null];
            if(!$family||$f!==$family['data'])$writes[]=['family',$f,$family];
            $normalizedMarriage['date']=$date;$normalizedMarriage['place']=$place;
        }else fail(422,'Bitte Ehepartner auswählen oder als unbekannt kennzeichnen.');
        $normalizedMarriage['partner_name']=$partnerName;$normalized['marriage']=$normalizedMarriage;
    }
    if(!$row||$p!==$row['data'])array_unshift($writes,['person',$p,$row]);
    if(!$writes)fail(422,'Keine Änderung eingetragen.');
    return [$normalized,$writes];
}

function entrySubmit(PDO $db,array $user,array $b): array {
    $base=$b['base_version']??0;$payload=$b['payload']??null;
    if(!is_int($base)||$base<0||!is_array($payload))fail(422,'Ungültige Erfassung.');
    $id=identifier($b['id']??uid());
    $target=$base>0?identifier($b['target']??null):'person_'.$id;
    identifier($target);
    $source=entryText($b['source']??null,20000,'Quelle')??'';
    if(!$base&&!$source)fail(422,'Bitte die Quelle der neuen Person eintragen.');
    return transaction($db,function()use($db,$user,$base,$payload,$id,$target,$source){
        $previous=one($db,'SELECT * FROM ah_proposals WHERE id=?',[$id]);
        if($previous){if($previous['actor']!==$user['id']||$previous['kind']!=='person_entry'||$previous['target']!==$target)fail(409,'Vorschlagskennung bereits verwendet.');return proposalJson($previous);}
        [$p]=entryPlan($db,$target,$base,$payload,$id);
        query($db,'INSERT INTO ah_proposals VALUES (?,?,?,?,?,?,?,?,?,?,?)',[$id,$user['id'],'person_entry',$target,$base,jencode($p),$source,'pending',stamp(),null,'']);
        return proposalJson(one($db,'SELECT * FROM ah_proposals WHERE id=?',[$id]));
    });
}
function entryApprove(PDO $db,array $user,array $proposal): void {
    [, $writes]=entryPlan($db,$proposal['target'],(int)$proposal['base_version'],decode($proposal['payload']),$proposal['id']);
    foreach($writes as [$kind,$data,$row]){
        $id=$row['id']??$data['id'];$data['id']=$id;$before=$row?json_decode($row['_raw_data'],false,512,JSON_THROW_ON_ERROR):null;
        $version=($row['version']??0)+1;
        if($kind==='person')$data['forschung']['freigegebene_ergaenzungen'][]=['vorschlag_id'=>$proposal['id'],'quelle'=>$proposal['source'],'pruefer'=>$user['id'],'datum'=>stamp()];
        if($kind==='family')$data['hochzeit']['freigabe']=['vorschlag_id'=>$proposal['id'],'quelle'=>$proposal['source']];
        if($row)query($db,'UPDATE ah_records SET data=?,version=? WHERE id=?',[jencode(preserveShape($data,$before)),$version,$id]);
        else saveRecord($db,$id,$kind,$data);
        audit($db,$id,$user['id'],'approve',['proposal'=>$proposal['id'],'source'=>$proposal['source'],'before'=>$before,'after'=>$data,'version'=>$version]);
    }
}
