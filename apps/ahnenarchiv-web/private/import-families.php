<?php
declare(strict_types=1);

function incMarriageDate(array $event): ?string {
    $date=gp($event,'datum.iso');
    return is_string($date)&&preg_match('/^\d{4}(?:-\d{2}){0,2}$/D',$date)&&!gp($event,'datum.konflikt')?$date:null;
}
function incMarriageDatesAgree(string $a,string $b): bool {
    return $a===$b||str_starts_with($a,$b.'-')||str_starts_with($b,$a.'-');
}
function incMarriageScore(array $incoming,array $existing): ?int {
    $a=incMarriageDate($incoming);$b=incMarriageDate($existing);
    if($a&&$b&&!incMarriageDatesAgree($a,$b))return null;
    $placeA=incKey((string)($incoming['ort_original']??''));$placeB=incKey((string)($existing['ort_original']??''));
    $exact=$a&&$a===$b&&strlen($a)===10;
    if(!$exact&&$placeA!==''&&$placeB!==''&&$placeA!==$placeB)return null;
    return ($a&&$b?($exact?8:4):0)+($placeA!==''&&$placeA===$placeB?2:($placeA!==''&&$placeB!==''?-1:0));
}
function incMarriageLabel(array $event): string {
    return (incMarriageDate($event)??'Datum offen').(!empty($event['ort_original'])?' · '.$event['ort_original']:'');
}
function incFamilyPlans(array $incoming,array $stored,array $map,array $names,array &$out): void {
    $existing=[];$groups=[];
    foreach($stored as $row){
        $partners=$row['data']['partner_person_ids']??[];sort($partners,SORT_STRING);
        $existing[jencode($partners)][]=$row;
    }
    foreach($incoming as $f){
        $partners=array_values(array_filter(array_map(fn($id)=>$map[$id]??null,$f['partner_person_ids'])));
        if(!$partners||count($partners)!==count($f['partner_person_ids']))continue;
        sort($partners,SORT_STRING);
        $children=array_values(array_filter(array_map(fn($id)=>$map[$id]??null,$f['kinder_person_ids'])));
        $groups[jencode($partners)][]=['partners'=>$partners,'children'=>$children,'event'=>$f['hochzeit']];
    }
    $planned=[];
    foreach($groups as $key=>$entries){
        $matches=$existing[$key]??[];
        $conflictingInput=false;
        for($i=0;$i<count($entries);$i++)for($j=0;$j<$i;$j++)
            if(incMarriageScore($entries[$i]['event'],$entries[$j]['event'])===null){$conflictingInput=true;break 2;}
        $pair=implode(' und ',array_map(fn($id)=>$names[$id]??$id,$entries[0]['partners']));
        foreach($entries as $entry){
            $event=$entry['event'];$target=null;
            if($matches){
                $ranked=[];
                foreach($matches as $row){
                    $score=incMarriageScore($event,$row['data']['hochzeit']??[]);
                    if($score!==null)$ranked[$score][]=$row;
                }
                if($ranked){
                    $best=max(array_keys($ranked));
                    // For repeated groups a place alone does not identify a wedding.
                    if(count($ranked[$best])===1&&((count($matches)===1&&!$conflictingInput)||$best>=4))$target=$ranked[$best][0];
                }
            }
            $id=$target['id']??'fam_'.hash('sha256',$key);
            if(($matches&&!$target)||(!$matches&&$conflictingInput)||
                (isset($planned[$id])&&incMarriageScore($event,$planned[$id]['after']['hochzeit']??[])===null)){
                $reason=$matches?'Bestand: '.implode('; ',array_map(fn($r)=>incMarriageLabel($r['data']['hochzeit']??[]),$matches)):'Die Importdatei enthält abweichende Hochzeitsangaben.';
                $out['family_conflicts'][]=$pair.' — Import: '.incMarriageLabel($event).'. '.$reason;
                continue;
            }
            $after=$planned[$id]['after']??$target['data']??['id'=>$id,'partner_person_ids'=>$entry['partners'],'kinder_person_ids'=>[],'status'=>'freigegebener_import'];
            $after['kinder_person_ids']=array_values(array_unique(array_merge($after['kinder_person_ids']??[],$entry['children'])));
            $oldEvent=$after['hochzeit']??[];
            $oldDate=incMarriageDate($oldEvent);$newDate=incMarriageDate($event);
            if($oldDate&&$newDate&&$oldDate!==$newDate)unset($event['datum']); // Keep precision and date metadata together.
            $after['hochzeit']=incMerge($after['hochzeit']??null,$event,$out['warnings'],'Hochzeit: '.$pair);
            $planned[$id]=['id'=>$id,'after'=>$after,'target'=>$target];
        }
    }
    foreach($planned as $f){
        if($f['target']){
            if($f['after']!==$f['target']['data'])$out['family_patches'][]=['id'=>$f['id'],'base_version'=>$f['target']['version'],'after'=>$f['after']];
        }else $out['families'][]=$f['after'];
    }
    $out['family_conflicts']=array_values(array_unique($out['family_conflicts']));
}

function incFamilyReviewToken(array $plan): string {
    return hash('sha256',jencode([$plan['source_map'],$plan['families'],$plan['family_patches'],$plan['family_conflicts']]));
}
