<?php
declare(strict_types=1);

// A number identifies a slot within a particular diagram, not a person globally.
function incNumberRef(mixed $ref): ?array {
    if(!is_array($ref)||!is_string($ref['kreis']??null)||!is_string($ref['nummer']??null))return null;
    $kreis=strtolower(trim($ref['kreis']));$number=strtoupper(trim($ref['nummer']));
    if(!preg_match('/^[a-z0-9][a-z0-9_-]{1,63}$/D',$kreis)||!preg_match('/^\d+(?:[.-]\d+)*(?:-[A-Z])?$/D',$number)||strlen($number)>50)return null;
    return ['kreis'=>$kreis,'nummer'=>$number];
}
function incNumberKey(array $ref): string {
    return 'da_'.hash('sha256',$ref['kreis']."\0".$ref['nummer']);
}
function incNormalizeNumbers(mixed $refs): array {
    if(!is_array($refs)||!array_is_list($refs)||count($refs)>100)fail(422,'d’Aboville-IDs müssen eine Liste aus Nummernkreis und Nummer sein.');
    $out=[];
    foreach($refs as $ref){$n=incNumberRef($ref);if(!$n)fail(422,'Ungültige d’Aboville-ID: Nummer und eindeutigen Nummernkreis angeben.');$out[incNumberKey($n)]=$n;}
    return array_values($out);
}
function incNumbers(array $p,bool $knownDocumentsOnly=false): array {
    $out=[];
    foreach($p['daboville_ids']??[] as $x)if($ref=incNumberRef($x)){
        if(!$knownDocumentsOnly||preg_match('/^(b|s)_pdf_2021-s5-(schiessl|maerz)$/D',$ref['kreis']))$out[incNumberKey($ref)]=$ref;
    }
    // These reviewed exports recorded the document and diagram page, even in older imports.
    foreach($p['externe_ids']??[] as $x){
        if(!is_array($x)||!in_array($x['system']??null,['b_pdf_2021','s_pdf_2021'],true)||!is_int($x['seite']??null)||$x['seite']<1)continue;
        $ref=incNumberRef(['kreis'=>$x['system'].'-s'.$x['seite'],'nummer'=>$x['wert']??null]);
        if(!$ref||($x['seite']===5&&in_array($ref['nummer'],['1-M','1-W'],true)))continue;
        $out[incNumberKey($ref)]=$ref;
    }
    return $out;
}
function incNumberIndex(array $persons, bool $knownDocumentsOnly=false): array {
    $out=[];
    foreach($persons as $p)foreach(incNumbers($p,$knownDocumentsOnly) as $key=>$ref)$out[$key][$p['id']]=true;
    return $out;
}
function incNumbersSeparate(array $a,array $b): bool {
    if(!$a||!$b||array_intersect_key($a,$b))return false;
    return (bool)array_intersect(array_column($a,'kreis'),array_column($b,'kreis'));
}
function incPlanAliases(array $plan): array {return $plan['identity_map']??$plan['source_map']??[];}
