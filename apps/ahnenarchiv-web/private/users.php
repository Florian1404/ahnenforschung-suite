<?php
declare(strict_types=1);
function invitationSchema(PDO $db): void {
    $tail=$db->getAttribute(PDO::ATTR_DRIVER_NAME)==='mysql'?' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin':'';
    query($db,"CREATE TABLE IF NOT EXISTS ah_invitations (id VARCHAR(100) PRIMARY KEY, email VARCHAR(254) NOT NULL, name VARCHAR(200) NOT NULL, role VARCHAR(20) NOT NULL, token_hash VARCHAR(64) NOT NULL UNIQUE, expires BIGINT NOT NULL, status VARCHAR(20) NOT NULL, delivery VARCHAR(20) NOT NULL, actor VARCHAR(100) NOT NULL, created VARCHAR(50) NOT NULL)$tail");
}
function accountInput(array $b): array {
    $email=strtolower(trim((string)($b['email']??'')));$name=trim((string)($b['name']??''));$role=$b['role']??'member';
    if(!filter_var($email,FILTER_VALIDATE_EMAIL)||strlen($email)>254||!$name||mb_strlen($name)>200||!in_array($role,['member','admin'],true))fail(422,'Name, E-Mail und Rolle prüfen.');
    return [$email,$name,$role];
}
function invitationLookup(PDO $db,array $b): array {
    $t=$b['token']??'';if(!is_string($t)||!preg_match('/^[A-Za-z0-9_-]{43}$/D',$t))fail(410,'Einladung ungültig, abgelaufen oder widerrufen.');
    $i=one($db,'SELECT * FROM ah_invitations WHERE token_hash=?',[hash('sha256',$t)]);
    if(!$i||$i['status']!=='pending'||(int)$i['expires']<=time())fail(410,'Einladung ungültig, abgelaufen oder widerrufen.');return $i;
}
function invitationPublic(PDO $db,string $path,array $b): array {
    invitationSchema($db);throttle($db,'invitation-accept');
    if($path==='/api/invitations/preview'){$i=invitationLookup($db,$b);return array_intersect_key($i,array_flip(['name','email','role','expires']));}
    if(($b['password']??null)!==($b['repeat']??null))fail(422,'Passwörter unterscheiden sich.');$hash=passwordHash($b['password']??null);
    return transaction($db,function()use($db,$b,$hash){
        $i=invitationLookup($db,$b);if(one($db,'SELECT id FROM ah_users WHERE email=?',[$i['email']]))fail(409,'Für diese E-Mail besteht bereits ein Konto. Bitte anmelden.');
        $id=uid();query($db,'INSERT INTO ah_users VALUES (?,?,?,?,?,1)',[$id,$i['email'],$i['name'],$hash,$i['role']]);
        query($db,"UPDATE ah_invitations SET status='accepted' WHERE id=?",[$i['id']]);
        query($db,"UPDATE ah_invitations SET status='revoked' WHERE email=? AND status='pending'",[$i['email']]);
        audit($db,$id,$i['actor'],'invitation_accepted',['invitation_id'=>$i['id'],'role'=>$i['role']]);return ['message'=>'Konto eingerichtet. Du kannst dich jetzt anmelden.'];
    });
}
function createAdminUser(PDO $db,array $u,array $b): array {
    admin($u);[$email,$name,$role]=accountInput($b);$hash=passwordHash($b['password']??null);invitationSchema($db);
    return transaction($db,function()use($db,$u,$email,$name,$role,$hash){
        if(one($db,'SELECT id FROM ah_users WHERE email=?',[$email]))fail(409,'Für diese E-Mail besteht bereits ein Konto.');
        $id=uid();query($db,'INSERT INTO ah_users VALUES (?,?,?,?,?,1)',[$id,$email,$name,$hash,$role]);
        query($db,"UPDATE ah_invitations SET status='revoked' WHERE email=? AND status='pending'",[$email]);
        audit($db,$id,$u['id'],'user_created',['email'=>$email,'role'=>$role]);return userJson(one($db,'SELECT * FROM ah_users WHERE id=?',[$id]));
    });
}
function invitationAdmin(PDO $db,array $cfg,array $u,string $method,string $path): array {
    admin($u);invitationSchema($db);
    if($method==='GET')return query($db,"SELECT id,email,name,role,expires,status,delivery,created FROM ah_invitations ORDER BY created DESC")->fetchAll();
    if(preg_match('#^/api/invitations/([A-Za-z0-9_-]+)/revoke$#D',$path,$m))return transaction($db,function()use($db,$u,$m){
        $i=one($db,'SELECT * FROM ah_invitations WHERE id=?',[$m[1]]);if(!$i)fail(404,'Einladung nicht gefunden.');
        if($i['status']==='pending')query($db,"UPDATE ah_invitations SET status='revoked' WHERE id=?",[$i['id']]);
        audit($db,$i['id'],$u['id'],'invitation_revoked',[]);return ['ok'=>true];
    });
    throttle($db,'invite-send');[$email,$name,$role]=accountInput(body());$t=token();$id=uid();$expires=time()+7*86400;
    transaction($db,function()use($db,$u,$email,$name,$role,$t,$id,$expires){
        if(one($db,'SELECT id FROM ah_users WHERE email=?',[$email]))fail(409,'Für diese E-Mail besteht bereits ein Konto.');
        query($db,"UPDATE ah_invitations SET status='revoked' WHERE email=? AND status='pending'",[$email]);
        query($db,'INSERT INTO ah_invitations VALUES (?,?,?,?,?,?,?,?,?,?)',[$id,$email,$name,$role,hash('sha256',$t),$expires,'pending','failed',$u['id'],stamp()]);
        audit($db,$id,$u['id'],'invitation_created',['email'=>$email,'role'=>$role,'expires'=>$expires]);
    });
    $url=$cfg['base_url'].'/#invite='.$t;$from=$cfg['mail_from']??('noreply@'.parse_url($cfg['base_url'],PHP_URL_HOST));$sent=false;
    if(($cfg['invite_mail_enabled']??true)&&filter_var($from,FILTER_VALIDATE_EMAIL)&&!preg_match('/[\r\n]/',$from)&&function_exists('mail')){
        $message=invitationMessage($name,$role,$url,$from);
        try {$sent=@mail($email,'Einladung zum Ahnenarchiv',$message['body'],$message['headers']);}catch(Throwable $e){$sent=false;}
    }
    if($sent)query($db,"UPDATE ah_invitations SET delivery='accepted' WHERE id=?",[$id]);
    return ['id'=>$id,'url'=>$url,'expires'=>$expires,'mail_accepted'=>$sent,'message'=>$sent?'Einladungs-E-Mail an den Mailserver übergeben. Bitte gegebenenfalls auch den Spamordner prüfen.':'E-Mail konnte nicht versendet werden. Du kannst den Einladungslink kopieren und selbst weitergeben.'];
}

// ASCII-safe MIME transport: both alternatives decode independently to UTF-8.
function invitationMessage(string $name,string $role,string $url,string $from): array {
    $roleName=$role==='admin'?'Administrator':'Mitforschender';
    $text="Hallo ".$name.",\r\n\r\nDu bist zum Ahnenarchiv eingeladen. Öffne diesen Link und lege dein eigenes Passwort fest:\r\n\r\n".$url."\r\n\r\nDer Link gilt sieben Tage und kann einmal verwendet werden. Deine Rolle: ".$roleName.".\r\n\r\nViele Grüße\r\nDas Ahnenarchiv\r\n";
    $escape=fn(string $v)=>htmlspecialchars($v,ENT_QUOTES|ENT_SUBSTITUTE,'UTF-8');
    $html='<!doctype html><html lang="de"><head><meta charset="utf-8"><title>Einladung zum Ahnenarchiv</title></head><body style="font-family:Arial,sans-serif;color:#243c35;background:#ffffff;padding:24px"><h1>Willkommen im Ahnenarchiv</h1><p>Hallo '.$escape($name).',</p><p>Du bist eingeladen, gemeinsam unsere Familiengeschichte zu bewahren. Lege dein eigenes Passwort fest:</p><p><a href="'.$escape($url).'" style="display:inline-block;background:#243c35;color:#ffffff;padding:14px 20px;text-decoration:none;border-radius:6px">Einladung annehmen</a></p><p>Falls der Button nicht funktioniert, kopiere diesen Link in deinen Browser:</p><p><a href="'.$escape($url).'">'.$escape($url).'</a></p><p>Der Link gilt sieben Tage und kann einmal verwendet werden. Deine Rolle: '.$escape($roleName).'.</p><p>Viele Grüße<br>Das Ahnenarchiv</p></body></html>';
    $boundary='ahnen_'.bin2hex(random_bytes(18));$body='';
    foreach(['text/plain'=>$text,'text/html'=>$html] as $type=>$content){
        $body.='--'.$boundary."\r\nContent-Type: ".$type."; charset=UTF-8\r\nContent-Transfer-Encoding: base64\r\n\r\n".chunk_split(base64_encode($content),76,"\r\n");
    }
    $body.='--'.$boundary."--\r\n";
    $headers=implode("\r\n",['From: '.$from,'Reply-To: '.$from,'MIME-Version: 1.0','Content-Type: multipart/alternative; boundary="'.$boundary.'"','Content-Transfer-Encoding: 7bit']);
    return ['body'=>$body,'headers'=>$headers];
}
