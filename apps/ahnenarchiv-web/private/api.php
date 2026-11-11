<?php
declare(strict_types=1);
require_once __DIR__.'/core.php';
require_once __DIR__.'/import.php';
require_once __DIR__.'/corrections.php';
require_once __DIR__.'/users.php';
require_once __DIR__.'/modules.php';
require_once __DIR__.'/review.php';
require_once __DIR__.'/person-entry.php';
require_once __DIR__.'/person-admin.php';
require_once __DIR__.'/event-admin.php';
require_once __DIR__.'/kreutzwiesner.php';

function api(PDO $db,array $cfg,string $root,string $method,string $path): mixed {
    $max=(int)($cfg['max_upload_bytes']??8388608);
    if($method==='GET'&&$path==='/health')return ['ok'=>true,'desktop'=>false,'backend'=>'php'];
    if($method==='GET'&&$path==='/api/capabilities')return ['desktop'=>false,'max_upload_bytes'=>$max,'imports'=>true,'import_ocr'=>!empty($cfg['import_ocr_api_key'])];
    if(!installed($db))fail(503,'Archiv noch nicht eingerichtet.');
    if($path==='/api/register'&&$method==='POST'){
        throttle($db);$b=body();$email=strtolower(trim((string)($b['email']??'')));$name=trim((string)($b['name']??''));
        if(!filter_var($email,FILTER_VALIDATE_EMAIL)||strlen($email)>254||!$name||mb_strlen($name)>200)fail(422,'Name und E-Mail prüfen.');$hash=passwordHash($b['password']??null);
        return transaction($db,function()use($db,$email,$name,$hash){
            if(one($db,'SELECT id FROM ah_users WHERE email=?',[$email]))fail(409,'Registrierung konnte nicht angelegt werden.');
            query($db,'INSERT INTO ah_users VALUES (?,?,?,?,?,0)',[uid(),$email,$name,$hash,'member']);return ['message'=>'Registrierung gespeichert. Ein Admin muss dein Konto freigeben.'];
        });
    }
    if($path==='/api/login'&&$method==='POST'){
        throttle($db);$b=body();$u=one($db,'SELECT * FROM ah_users WHERE email=?',[strtolower(trim((string)($b['email']??'')))]);
        $pw=$b['password']??'';if(!is_string($pw)||strlen($pw)>1024)fail(401,'Anmeldung fehlgeschlagen.');
        // Auch bei unbekannter E-Mail bcrypt ausführen, damit die Laufzeit kein Konto verrät.
        $hash=$u['password']??'$2y$12$N9qo8uLOickgx2ZMRZoMyeIjZAgcfl7p92ldGxad68LJZdL17lhWy';
        $valid=password_verify(hash('sha256',$pw),$hash);
        if(!$u||!$valid||!$u['active'])fail(401,'Anmeldung fehlgeschlagen oder Konto noch nicht freigegeben.');
        $t=transaction($db,fn()=>loginToken($db,$u['id']));
        setcookie('session',$t,['expires'=>time()+30*86400,'path'=>'/','secure'=>($cfg['require_https']??true),'httponly'=>true,'samesite'=>'Strict']);
        return ($b['desktop_client']??false)?['user'=>userJson($u),'token'=>$t]:['user'=>userJson($u)];
    }
    if(preg_match('#^/api/shared/([A-Za-z0-9_-]+)$#D',$path,$m)&&$method==='GET'){
        $s=one($db,'SELECT * FROM ah_shares WHERE token_hash=? AND active=1',[hash('sha256',$m[1])]);if(!$s)fail(404,'Freigabelink ungültig oder widerrufen.');
        $scope=decode($s['data']);$ids=visibleIds($db,$scope);$out=['name'=>$s['name'],'personen'=>[],'familien'=>[],'beziehungen'=>[],'medien'=>[],'pruefhinweise'=>[]];
        foreach(records($db) as $r){$p=$r['data'];
            if($r['kind']==='person'&&in_array($r['id'],$ids,true))$out['personen'][]=publicPerson($r);
            if($r['kind']==='family'&&array_intersect($ids,$p['partner_person_ids']??[]))$out['familien'][]=['id'=>$r['id'],'partner_person_ids'=>array_values(array_intersect($p['partner_person_ids']??[],$ids)),'kinder_person_ids'=>array_values(array_intersect($p['kinder_person_ids']??[],$ids)),'belegt'=>$p['belegt']??null,'belegstatus'=>$p['belegstatus']??null];
            if($r['kind']==='relationship'&&in_array($p['von_person_id']??null,$ids,true)&&in_array($p['zu_person_id']??null,$ids,true))$out['beziehungen'][]=array_merge(['id'=>$r['id']],array_intersect_key($p,array_flip(['typ','von_person_id','zu_person_id','elternschaft_typ','biologisch_bestaetigt','belegt','belegstatus','status'])));
            if($r['kind']==='media'&&($scope['allow_media']??false)){$assigned=mediaIds($db,$r);if($assigned&&!array_diff($assigned,$ids))$out['medien'][]=['id'=>$r['id'],'titel'=>$p['titel']??null,'person_ids'=>$assigned,'mime_type'=>$p['mime_type']??null];}
        }return $out;
    }
    if(preg_match('#^/api/media/([A-Za-z0-9_-]+)$#D',$path,$m)&&$method==='GET'){
        $r=getRecord($db,$m[1]);if(!$r||!in_array($r['kind'],['media','staged_media'],true))fail(404,'Medium nicht gefunden.');
        $share=$_GET['share']??'';
        if($share){$s=one($db,'SELECT * FROM ah_shares WHERE token_hash=? AND active=1',[hash('sha256',$share)]);$scope=$s?decode($s['data']):[];
            if(!$s||!($scope['allow_media']??false)||$r['kind']!=='media')fail(403,'Medium nicht freigegeben.');
            $ids=mediaIds($db,$r);if(!$ids||array_diff($ids,visibleIds($db,$scope)))fail(403,'Personen außerhalb des Freigabebereichs.');
        }else{$u=who($db);if($r['kind']==='staged_media'&&($r['data']['owner']??'')!==$u['id']&&$u['role']!=='admin')fail(403,'Kein Zugriff auf diesen Upload.');}
        $base=realpath($root.'/private/media');$file=realpath($base.'/'.($r['data']['datei']??''));
        if(!$file||!str_starts_with($file,$base.DIRECTORY_SEPARATOR)||!is_file($file))fail(404,'Datei nicht vorhanden.');
        header('Content-Type: '.($r['data']['mime_type']??'application/octet-stream'));header('Content-Disposition: inline');header('Content-Length: '.filesize($file));readfile($file);exit;
    }
    if($method==='POST'&&in_array($path,['/api/invitations/preview','/api/invitations/accept'],true))return invitationPublic($db,$path,body());
    $u=who($db);
    if(str_starts_with($path,'/api/kreutzwiesner/'))return kwApi($db,$root,$u,$method,$path);
    if($path==='/api/modules'||str_starts_with($path,'/api/modules/'))return ahModuleApi($db,$root,$u,$method,$path);
    if($path==='/api/corrections/adopt-template'&&$method==='POST')return adoptTemplateEvidence($db,$u,$root);
    if($path==='/api/corrections/template-confirmation'&&$method==='POST')return templateConfirmationSubmit($db,$u);
    if(preg_match('#^/api/connections/([A-Za-z0-9_-]+)/status$#D',$path,$m)&&$method==='POST')return relationshipStatusSubmit($db,$u,$m[1],body());
    if($path==='/api/corrections/family-confirmation'&&$method==='POST')return familyConfirmationSubmit($db,$u);
    if($path==='/api/corrections/portraits'&&$method==='POST')return portraitFixSubmit($db,$u);
    if(str_starts_with($path,'/api/person-admin/'))return paAdminApi($db,$u,$method,$path);
    if(str_starts_with($path,'/api/event-admin/'))return eaAdminApi($db,$u,$method,$path);
    if(str_starts_with($path,'/api/imports'))return importApi($db,$cfg,$root,$u,$method,$path);
    if($path==='/api/account/password'&&$method==='POST'){
        throttle($db,'password-change');$b=body();$old=$b['current_password']??'';$new=$b['new_password']??null;
        if(!is_string($old)||strlen($old)>1024||!password_verify(hash('sha256',$old),$u['password']))fail(403,'Aktuelles Passwort stimmt nicht.');
        if($new!==($b['repeat']??null))fail(422,'Neue Passwörter unterscheiden sich.');
        $hash=passwordHash($new);if($new===$old)fail(422,'Bitte ein anderes neues Passwort verwenden.');
        transaction($db,function()use($db,$u,$hash){
            $current=one($db,'SELECT password FROM ah_users WHERE id=?',[$u['id']]);if(!$current||$current['password']!==$u['password'])fail(409,'Passwort inzwischen geändert. Bitte neu anmelden.');
            query($db,'UPDATE ah_users SET password=? WHERE id=?',[$hash,$u['id']]);query($db,'DELETE FROM ah_sessions WHERE user_id=?',[$u['id']]);
            audit($db,$u['id'],$u['id'],'password_change',['sessions_revoked'=>true]);
        });
        setcookie('session','',['expires'=>1,'path'=>'/','secure'=>($cfg['require_https']??true),'httponly'=>true,'samesite'=>'Strict']);return ['ok'=>true,'sessions_revoked'=>true];
    }
    if($path==='/api/me'&&$method==='GET')return array_merge(userJson($u),['desktop'=>false]);
    if($path==='/api/logout'&&$method==='POST'){
        $auth=$_SERVER['HTTP_AUTHORIZATION']??'';$t=str_starts_with($auth,'Bearer ')?substr($auth,7):($_COOKIE['session']??'');
        query($db,'DELETE FROM ah_sessions WHERE id=?',[hash('sha256',$t)]);setcookie('session','',['expires'=>1,'path'=>'/','secure'=>($cfg['require_https']??true),'httponly'=>true,'samesite'=>'Strict']);return ['ok'=>true];
    }
    if($path==='/api/snapshot'&&$method==='GET'){
        $rows=array_values(array_filter(records($db),fn($r)=>$r['kind']!=='staged_media'||$u['role']==='admin'||($r['data']['owner']??'')===$u['id']));foreach($rows as &$r){$r['data']=json_decode($r['_raw_data'],false,512,JSON_THROW_ON_ERROR);unset($r['_raw_data']);}return ['records'=>$rows,'generated'=>stamp()];
    }
    if($path==='/api/archive'&&$method==='GET'){
        $out=['personen'=>[],'familien'=>[],'beziehungen'=>[],'medien'=>[],'pruefhinweise'=>[]];$mapping=['person'=>'personen','family'=>'familien','relationship'=>'beziehungen','media'=>'medien','issue'=>'pruefhinweise'];$q=mb_strtolower((string)($_GET['q']??''));
        $out['connection_pending_ids']=array_column(query($db,"SELECT DISTINCT target FROM ah_proposals WHERE kind='relationship_status' AND status='pending'")->fetchAll(),'target');
        foreach(records($db) as $r){if(!isset($mapping[$r['kind']]))continue;if($r['kind']==='person'&&$q&&!str_contains(mb_strtolower(jencode($r['data']['namen']??[]).($r['data']['anzeigename']??'')),$q))continue;$out[$mapping[$r['kind']]][]=recordJson($r);}return $out;
    }
    if(preg_match('#^/api/person/([A-Za-z0-9_-]+)$#D',$path,$m)&&$method==='GET'){$r=getRecord($db,$m[1]);if(!$r||$r['kind']!=='person')fail(404,'Person nicht gefunden.');return recordJson($r);}
    if($path==='/api/proposals'&&$method==='GET'){
        $rows=query($db,'SELECT * FROM ah_proposals'.($u['role']==='admin'?'':' WHERE actor=?').' ORDER BY created DESC',$u['role']==='admin'?[]:[$u['id']])->fetchAll();return array_map('proposalJson',$rows);
    }
    if($path==='/api/proposals'&&$method==='POST'){
        $b=body();$kind=$b['kind']??null;if($kind==='person_entry')return entrySubmit($db,$u,$b);$p=$b['payload']??[];validate($kind,$p);$id=identifier($b['id']??uid());$target=identifier($b['target']??($kind==='person'?'person_':'').uid());
        return transaction($db,function()use($db,$u,$b,$kind,$p,$id,$target){
            $old=one($db,'SELECT * FROM ah_proposals WHERE id=?',[$id]);if($old){if($old['actor']!==$u['id'])fail(409,'Vorschlags-ID bereits verwendet.');return proposalJson($old);}
            $base=$b['base_version']??0;if(!is_int($base)||$base<0)fail(422,'Datensatzversion fehlt oder ungültig.');
            if($kind==='patch'){$r=getRecord($db,$target);if(!$r||$r['kind']!=='person')fail(404,'Person nicht gefunden.');if(!isset($b['base_version']))fail(422,'Datensatzversion fehlt.');$p['before']=[];foreach($p['changes'] as $path=>$value)$p['before'][$path]=gp($r['data'],$path);}
            if($kind==='media'){$r=getRecord($db,$p['upload_id']);if(!$r||$r['kind']!=='staged_media'||$r['data']['owner']!==$u['id'])fail(422,'Upload fehlt oder gehört einem anderen Nutzer.');
                $actual=$r['data']['person_ids'];$wanted=$p['person_ids'];sort($actual);sort($wanted);if($actual!==$wanted)fail(422,'Personenzuordnung stimmt nicht mit Upload überein.');}
            $source=$b['source']??'';if(!is_string($source)||mb_strlen($source)>20000)fail(422,'Quelle ungültig oder zu lang.');
            query($db,'INSERT INTO ah_proposals VALUES (?,?,?,?,?,?,?,?,?,?,?)',[$id,$u['id'],$kind,$target,$base,jencode($p),$source,'pending',stamp(),null,'']);
            return proposalJson(one($db,'SELECT * FROM ah_proposals WHERE id=?',[$id]));
        });
    }
    if($path==='/api/proposals/review-batch'&&$method==='POST')return ahReviewBatch($db,$u,body());
    if(preg_match('#^/api/proposals/([A-Za-z0-9_-]+)/review$#D',$path,$m)&&$method==='POST'){
        admin($u);$b=body();return transaction($db,fn()=>ahReviewProposal($db,$u,$m[1],$b));
    }
    if($path==='/api/upload'&&$method==='POST'){
        $title=rawurldecode($_SERVER['HTTP_X_TITLE']??'');$ids=explode(',',$_SERVER['HTTP_X_PERSON_IDS']??'');$id=identifier($_SERVER['HTTP_X_UPLOAD_ID']??uid());
        if(!trim($title)||mb_strlen($title)>200||!$ids||count($ids)>100)fail(422,'Upload braucht Titel und Personenzuordnung.');foreach($ids as $pid)identifier($pid);
        $raw=file_get_contents('php://input',false,null,0,$max+1);if(strlen($raw)>$max)fail(413,'Datei überschreitet das Uploadlimit.');if(!$raw)fail(422,'Datei ist leer.');
        if(str_starts_with($raw,'%PDF-')){$ext='pdf';$mime='application/pdf';}
        else{$info=@getimagesizefromstring($raw);$types=[IMAGETYPE_JPEG=>['jpg','image/jpeg'],IMAGETYPE_PNG=>['png','image/png'],IMAGETYPE_WEBP=>['webp','image/webp']];
            if(!$info||!isset($types[$info[2]])||$info[0]*$info[1]>80000000)fail(422,'Nur gültige JPG-, PNG-, WebP-Bilder oder PDF-Dateien erlaubt.');[$ext,$mime]=$types[$info[2]];}
        $sha=hash('sha256',$raw);
        return transaction($db,function()use($db,$root,$u,$title,$ids,$id,$raw,$sha,$ext,$mime){
            foreach($ids as $pid){$r=getRecord($db,$pid);$pending=one($db,"SELECT actor FROM ah_proposals WHERE target=? AND (kind='person' OR (kind='person_entry' AND base_version=0)) AND status='pending'",[$pid]);
                if(!($r&&$r['kind']==='person')&&!($pending&&($pending['actor']===$u['id']||$u['role']==='admin')))fail(422,'Unbekannte Person: zuerst neuen Personenvorschlag anlegen.');}
            $old=getRecord($db,$id);if($old){if($old['kind']!=='staged_media'||$old['data']['owner']!==$u['id']||$old['data']['sha256']!==$sha)fail(409,'Upload-ID Konflikt.');return ['id'=>$id];}
            $filename=$id.'.'.$ext;$file=$root.'/private/media/'.$filename;$tmp=$file.'.'.uid().'.part';
            if(file_put_contents($tmp,$raw,LOCK_EX)!==strlen($raw)||!rename($tmp,$file))fail(503,'Datei konnte nicht gespeichert werden.');
            try{saveRecord($db,$id,'staged_media',['datei'=>$filename,'mime_type'=>$mime,'owner'=>$u['id'],'sha256'=>$sha,'title'=>$title,'person_ids'=>$ids]);}catch(Throwable $e){@unlink($file);throw $e;}return ['id'=>$id];
        });
    }
    if($path==='/api/users'&&$method==='POST')return createAdminUser($db,$u,body());
    if(($path==='/api/invitations'&&in_array($method,['GET','POST'],true))||($method==='POST'&&preg_match('#^/api/invitations/[A-Za-z0-9_-]+/revoke$#D',$path)))return invitationAdmin($db,$cfg,$u,$method,$path);
    if($path==='/api/users'&&$method==='GET'){admin($u);return array_map('userJson',query($db,'SELECT * FROM ah_users ORDER BY name')->fetchAll());}
    if(preg_match('#^/api/users/([A-Za-z0-9_-]+)$#D',$path,$m)&&$method==='POST'){
        admin($u);$b=body();if(!in_array($b['role']??null,['admin','member'],true)||!is_bool($b['active']??null))fail(422,'Rolle/Status ungültig.');
        return transaction($db,function()use($db,$u,$b,$m){$v=one($db,'SELECT * FROM ah_users WHERE id=?',[$m[1]]);if(!$v)fail(404,'Konto nicht gefunden.');if($u['id']===$v['id']&&($b['role']!=='admin'||!$b['active']))fail(409,'Eigenes Admin-Konto nicht deaktivieren.');
            query($db,'UPDATE ah_users SET role=?,active=? WHERE id=?',[$b['role'],(int)$b['active'],$v['id']]);if(!$b['active'])query($db,'DELETE FROM ah_sessions WHERE user_id=?',[$v['id']]);audit($db,$v['id'],$u['id'],'user_permissions',$b);return userJson(one($db,'SELECT * FROM ah_users WHERE id=?',[$v['id']]));});
    }
    if($path==='/api/shares'&&$method==='GET'){admin($u);$rows=query($db,'SELECT id,name,active,data FROM ah_shares')->fetchAll();foreach($rows as &$s){$s['active']=(bool)$s['active'];$s['data']=decode($s['data']);}return $rows;}
    if($path==='/api/shares'&&$method==='POST'){
        admin($u);$b=body();$ids=$b['person_ids']??[];if(!is_array($ids))fail(422,'Ungültiger Freigabebereich.');foreach($ids as $id){$r=getRecord($db,identifier($id));if(!$r||$r['kind']!=='person')fail(422,'Ungültiger Freigabebereich.');}
        $t=token();$id=uid();$scope=['person_ids'=>$ids,'include_living'=>($b['include_living']??false)===true,'allow_media'=>($b['allow_media']??false)===true];
        query($db,'INSERT INTO ah_shares VALUES (?,?,?,?,?)',[$id,mb_substr((string)($b['name']??'Familienstammbaum'),0,200),hash('sha256',$t),1,jencode($scope)]);return ['id'=>$id,'token'=>$t,'url'=>$cfg['base_url'].'/#share='.$t];
    }
    if(preg_match('#^/api/shares/([A-Za-z0-9_-]+)/revoke$#D',$path,$m)&&$method==='POST'){admin($u);if(!one($db,'SELECT id FROM ah_shares WHERE id=?',[$m[1]]))fail(404,'Freigabe nicht gefunden.');query($db,'UPDATE ah_shares SET active=0 WHERE id=?',[$m[1]]);return ['ok'=>true];}
    if(preg_match('#^/api/audit/([A-Za-z0-9_-]+)$#D',$path,$m)&&$method==='GET'){$rows=query($db,'SELECT id,actor,action,created,data FROM ah_audit WHERE target=? ORDER BY created DESC',[$m[1]])->fetchAll();foreach($rows as &$r)$r['data']=decode($r['data']);return $rows;}
    if(preg_match('#^/api/audit/([A-Za-z0-9_-]+)/restore$#D',$path,$m)&&$method==='POST'){
        admin($u);return transaction($db,function()use($db,$u,$m){$a=one($db,'SELECT * FROM ah_audit WHERE id=?',[$m[1]]);$d=$a?decode($a['data']):[];if(!isset($d['before']))fail(422,'Kein vorheriger Stand für diese Änderung.');$r=getRecord($db,$a['target']);
            if(!$r||$r['version']!==($d['version']??null))fail(409,'Weitere Änderungen vorhanden. Bitte einzeln korrigieren.');$version=$r['version']+1;
            query($db,'UPDATE ah_records SET data=?,version=? WHERE id=?',[jencode($d['before']),$version,$r['id']]);audit($db,$r['id'],$u['id'],'restore',['before'=>$r['data'],'after'=>$d['before'],'version'=>$version,'restored_audit'=>$a['id']]);return ['ok'=>true];});
    }
    if($path==='/api/export'&&$method==='GET'){
        admin($u);$r=getRecord($db,'original_import');$out=$r?(array)json_decode($r['_raw_data'],false,512,JSON_THROW_ON_ERROR):[];$mapping=['person'=>'personen','family'=>'familien','relationship'=>'beziehungen','media'=>'medien','source'=>'quellen','place'=>'orte','issue'=>'pruefhinweise','source_page'=>'quellenseiten'];
        foreach($mapping as $k)$out[$k]=[];foreach(records($db) as $row)if(isset($mapping[$row['kind']]))$out[$mapping[$row['kind']]][]=json_decode($row['_raw_data'],false,512,JSON_THROW_ON_ERROR);
        $out['app_ergaenzungen']=['vorschlaege'=>array_map('proposalJson',query($db,'SELECT * FROM ah_proposals')->fetchAll())];header('Content-Disposition: attachment; filename="ahnenarchiv-export.json"');return $out;
    }
    fail(404,'Nicht gefunden.');
}
