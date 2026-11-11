<?php
declare(strict_types=1);

final class ApiError extends RuntimeException {
    public function __construct(public int $status, string $message) { parent::__construct($message); }
}
function fail(int $status, string $message): never { throw new ApiError($status, $message); }
function uid(): string { return bin2hex(random_bytes(16)); }
function stamp(): string { return gmdate('Y-m-d\TH:i:s\Z'); }
function jencode(mixed $v): string { return json_encode($v, JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES|JSON_THROW_ON_ERROR); }
function decode(string $s): array { $v=json_decode($s,true,512,JSON_THROW_ON_ERROR); return is_array($v)?$v:[]; }
function preserveShape(mixed $value,mixed $original): mixed {
    if(is_array($value)){
        foreach($value as $key=>&$item){$old=is_object($original)?($original->$key??null):(is_array($original)?($original[$key]??null):null);$item=preserveShape($item,$old);}unset($item);
        if(is_object($original))return (object)$value;
    }return $value;
}
function token(): string { return rtrim(strtr(base64_encode(random_bytes(32)),'+/','-_'),'='); }
function db(array $cfg): PDO {
    $dsn=$cfg['dsn'];
    if (!str_starts_with($dsn,'mysql:') && !(PHP_SAPI==='cli' && str_starts_with($dsn,'sqlite:')) && !getenv('AHNEN_TEST')) fail(503,'MySQL/MariaDB-Datenbank erforderlich.');
    return new PDO($dsn,$cfg['db_user']??null,$cfg['db_password']??null,[PDO::ATTR_ERRMODE=>PDO::ERRMODE_EXCEPTION,PDO::ATTR_DEFAULT_FETCH_MODE=>PDO::FETCH_ASSOC,PDO::ATTR_EMULATE_PREPARES=>false]);
}
function query(PDO $db,string $sql,array $args=[]): PDOStatement { $s=$db->prepare($sql);$s->execute($args);return $s; }
function one(PDO $db,string $sql,array $args=[]): ?array { return query($db,$sql,$args)->fetch() ?: null; }
function transaction(PDO $db,callable $fn): mixed {
    $db->beginTransaction();
    try {
        // Alle Schreibvorgänge nehmen denselben InnoDB-Lock, auch über mehrere PHP-Worker.
        if ($db->getAttribute(PDO::ATTR_DRIVER_NAME)==='mysql') query($db,"SELECT id FROM ah_settings WHERE id='write_lock' FOR UPDATE");
        else query($db,"UPDATE ah_settings SET data=data WHERE id='write_lock'");
        $result=$fn();$db->commit();return $result;
    } catch (Throwable $e) { if($db->inTransaction())$db->rollBack();throw $e; }
}
function schema(PDO $db): void {
    $tail=$db->getAttribute(PDO::ATTR_DRIVER_NAME)==='mysql'?' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin':'';
    $tables=[
        'records'=>'id VARCHAR(100) PRIMARY KEY, kind VARCHAR(30) NOT NULL, data LONGTEXT NOT NULL, version INT NOT NULL',
        'users'=>'id VARCHAR(100) PRIMARY KEY, email VARCHAR(254) NOT NULL UNIQUE, name VARCHAR(200) NOT NULL, password TEXT NOT NULL, role VARCHAR(20) NOT NULL, active INT NOT NULL',
        'sessions'=>'id VARCHAR(64) PRIMARY KEY, user_id VARCHAR(100) NOT NULL, expires BIGINT NOT NULL',
        'proposals'=>'id VARCHAR(100) PRIMARY KEY, actor VARCHAR(100) NOT NULL, kind VARCHAR(30) NOT NULL, target VARCHAR(100) NOT NULL, base_version INT NOT NULL, payload LONGTEXT NOT NULL, source TEXT NOT NULL, status VARCHAR(30) NOT NULL, created VARCHAR(50) NOT NULL, reviewer VARCHAR(100), reason TEXT NOT NULL',
        'audit'=>'id VARCHAR(100) PRIMARY KEY, target VARCHAR(100) NOT NULL, actor VARCHAR(100) NOT NULL, action VARCHAR(100) NOT NULL, data LONGTEXT NOT NULL, created VARCHAR(50) NOT NULL',
        'shares'=>'id VARCHAR(100) PRIMARY KEY, name VARCHAR(200) NOT NULL, token_hash VARCHAR(64) NOT NULL UNIQUE, active INT NOT NULL, data LONGTEXT NOT NULL',
        'settings'=>'id VARCHAR(100) PRIMARY KEY, data LONGTEXT NOT NULL',
        'limits'=>'id VARCHAR(64) PRIMARY KEY, hits INT NOT NULL, expires BIGINT NOT NULL',
    ];
    foreach($tables as $t=>$columns)query($db,"CREATE TABLE IF NOT EXISTS ah_$t ($columns)$tail");
    if(!one($db,"SELECT id FROM ah_settings WHERE id='write_lock'")) {
        try { query($db,"INSERT INTO ah_settings (id,data) VALUES ('write_lock','{}')"); } catch(PDOException $e) { if(!one($db,"SELECT id FROM ah_settings WHERE id='write_lock'"))throw $e; }
    }
}
function installed(PDO $db): bool { return one($db,"SELECT id FROM ah_settings WHERE id='installed'")!==null; }
function getRecord(PDO $db,string $id): ?array {
    $r=one($db,'SELECT * FROM ah_records WHERE id=?',[$id]);
    if($r){$r['_raw_data']=$r['data'];$r['data']=decode($r['data']);$r['version']=(int)$r['version'];}return $r;
}
function records(PDO $db,?string $kind=null): array {
    $rows=query($db,'SELECT * FROM ah_records'.($kind?' WHERE kind=?':'').' ORDER BY id',$kind?[$kind]:[])->fetchAll();
    foreach($rows as &$r){$r['_raw_data']=$r['data'];$r['data']=decode($r['data']);$r['version']=(int)$r['version'];}return $rows;
}
function saveRecord(PDO $db,string $id,string $kind,array $data,int $version=1): void {
    query($db,'INSERT INTO ah_records (id,kind,data,version) VALUES (?,?,?,?)',[$id,$kind,jencode($data),$version]);
}
function recordJson(array $r): array { return array_merge((array)json_decode($r['_raw_data']??jencode($r['data']),false,512,JSON_THROW_ON_ERROR),['id'=>$r['id'],'version'=>$r['version']]); }
function userJson(array $u): array { return ['id'=>$u['id'],'name'=>$u['name'],'email'=>$u['email'],'role'=>$u['role'],'active'=>(bool)$u['active']]; }
function proposalJson(array $p): array { $p['payload']=decode($p['payload']);$p['base_version']=(int)$p['base_version'];return $p; }
function who(PDO $db): array {
    $auth=$_SERVER['HTTP_AUTHORIZATION']??$_SERVER['REDIRECT_HTTP_AUTHORIZATION']??'';
    $t=str_starts_with($auth,'Bearer ')?substr($auth,7):($_COOKIE['session']??'');
    $u=one($db,'SELECT u.* FROM ah_users u JOIN ah_sessions s ON s.user_id=u.id WHERE s.id=? AND s.expires>? AND u.active=1',[hash('sha256',$t),time()]);
    if(!$u)fail(401,'Bitte anmelden.');return $u;
}
function admin(array $u): void { if($u['role']!=='admin')fail(403,'Admin-Rechte erforderlich.'); }
function passwordHash(mixed $s): string {
    if(!is_string($s)||strlen($s)<12||strlen($s)>1024)fail(422,'Passwort braucht mindestens 12 Zeichen (maximal 1024 Bytes).');
    // SHA-256-Vorhash verhindert bcrypt-Abschneiden langer Passwörter bei 72 Bytes.
    return password_hash(hash('sha256',$s),PASSWORD_BCRYPT,['cost'=>12]);
}
function loginToken(PDO $db,string $uid): string {
    query($db,'DELETE FROM ah_sessions WHERE expires<?',[time()]);$t=token();query($db,'INSERT INTO ah_sessions VALUES (?,?,?)',[hash('sha256',$t),$uid,time()+30*86400]);return $t;
}
function throttle(PDO $db,string $scope='auth'): void {
    $id=hash('sha256',$scope.'|'.($_SERVER['REMOTE_ADDR']??'local'));$now=time();
    transaction($db,function()use($db,$id,$now){
        query($db,'DELETE FROM ah_limits WHERE expires<?',[$now]);
        $r=one($db,'SELECT * FROM ah_limits WHERE id=?',[$id]);
        if($r&&(int)$r['hits']>=20)fail(429,'Bitte in fünf Minuten erneut versuchen.');
        if($r)query($db,'UPDATE ah_limits SET hits=hits+1 WHERE id=?',[$id]);
        else query($db,'INSERT INTO ah_limits VALUES (?,1,?)',[$id,$now+300]);
    });
}
function body(): array {
    $raw=file_get_contents('php://input',false,null,0,1048577);if(strlen($raw)>1048576)fail(413,'Anfrage zu groß.');
    try {$v=json_decode($raw,true,64,JSON_THROW_ON_ERROR);}catch(Throwable){fail(422,'Ungültige JSON-Anfrage.');}
    if(!is_array($v)||!str_starts_with(ltrim($raw),'{'))fail(422,'JSON-Objekt erforderlich.');return $v;
}
function identifier(mixed $s): string {
    if(!is_string($s)||!preg_match('/^[A-Za-z0-9_-]{1,100}$/D',$s))fail(422,'Ungültige ID.');return $s;
}
function gp(array $p,string $path): mixed { $v=$p;foreach(explode('.',$path) as $k){if(!is_array($v))return null;$v=$v[$k]??null;}return $v; }
function dateValue(mixed $v): void {
    if($v===null||$v==='')return;
    if(!is_string($v)||!preg_match('/^(\d{4})(?:-(\d{2}))?(?:-(\d{2}))?$/D',$v,$m))fail(422,'Datum als JJJJ, JJJJ-MM oder JJJJ-MM-TT eingeben.');
    $y=(int)$m[1];$mo=isset($m[2])?(int)$m[2]:1;$d=isset($m[3])?(int)$m[3]:1;
    if($y<1||!checkdate($mo,$d,$y))fail(422,'Ungültiges Datum.');
}
function sp(array &$p,string $path,mixed $value): void {
    $keys=explode('.',$path);$last=array_pop($keys);$node=&$p;
    foreach($keys as $k){if(!isset($node[$k])||!is_array($node[$k]))$node[$k]=[];$node=&$node[$k];}
    $node[$last]=$value;
    if(str_ends_with($path,'.datum.iso')){
        $parts=$value?array_map('intval',explode('-',$value)):[];
        $node=array_merge($node,['jahr'=>$parts[0]??null,'monat'=>$parts[1]??null,'tag'=>$parts[2]??null,'qualifizierer'=>count($parts)===3?'exakt':($parts?'teilweise':'unbekannt'),'original'=>$value,'konflikt'=>false]);
    }
}
function chronology(array $p): void {
    $a=gp($p,'geburt.datum.iso');$b=gp($p,'tod.datum.iso');
    if($a&&$b&&(int)substr($b,0,4)<(int)substr($a,0,4))fail(422,'Sterbejahr liegt vor dem Geburtsjahr.');
}
function validate(mixed $kind,mixed $p): void {
    if(!is_array($p))fail(422,'Ungültige Vorschlagsdaten.');
    if($kind==='patch'){
        $fields=['namen.geburtsname','anzeigename','geschlecht','lebensstatus','biografie','geburt.datum.iso','geburt.ort_original','tod.datum.iso','tod.ort_original','taufe.datum.iso','taufe.ort_original','bestattung.datum.iso','bestattung.ort_original'];
        if(!isset($p['changes'])||!is_array($p['changes'])||!$p['changes'])fail(422,'Keine Änderungen.');
        foreach($p['changes'] as $k=>$v){
            if(!in_array($k,$fields,true))fail(422,'Feld nicht bearbeitbar.');
            if(str_ends_with($k,'.datum.iso'))dateValue($v);
            elseif($v!==null&&(!is_string($v)||strlen($v)>80000))fail(422,'Ungültiger Feldwert.');
            if($k==='anzeigename'&&(!is_string($v)||!trim($v)||mb_strlen($v)>200))fail(422,'Name fehlt oder ist zu lang.');
            if($k==='namen.geburtsname'&&$v!==null&&mb_strlen($v)>200)fail(422,'Geburtsname ist zu lang.');
            if($k==='geschlecht'&&!in_array($v,['m','w','divers','unbekannt'],true))fail(422,'Ungültiges Geschlecht.');
        }
    }elseif($kind==='person'){
        if(!is_string($p['anzeigename']??null)||!trim($p['anzeigename'])||mb_strlen($p['anzeigename'])>200)fail(422,'Neue Person braucht einen Namen oder eine vorläufige Bezeichnung.');
        foreach(['geburt','tod','taufe','bestattung'] as $ev){dateValue(gp($p,$ev.'.datum.iso'));if(isset($p[$ev])&&!is_array($p[$ev]))fail(422,'Ungültige Lebensdaten.');}
        chronology($p);
    }elseif($kind==='relationship'){
        if(isset($p['belegt'])&&!is_bool($p['belegt']))fail(422,'Belegstatus muss wahr oder falsch sein.');
        if(!in_array($p['typ']??null,['eltern_kind','partner'],true))fail(422,'Verbindung unvollständig.');
        $a=identifier($p['von_person_id']??null);$b=identifier($p['zu_person_id']??null);
        if($a===$b)fail(422,'Person kann nicht mit sich selbst verbunden sein.');
        if(!in_array($p['elternschaft_typ']??'ungeklaert',['ungeklaert','biologisch','adoptiv','pflege','stief','elternteil_aus_diagramm','annahme_rechtsform_ungeklaert','familiaere_zuordnung_ungeklaert'],true))fail(422,'Ungültige Elternschaft.');
    }elseif($kind==='media'){
        identifier($p['upload_id']??null);
        if(!is_string($p['titel']??null)||!trim($p['titel'])||mb_strlen($p['titel'])>200||!is_array($p['person_ids']??null)||!$p['person_ids']||count($p['person_ids'])>100)fail(422,'Bild braucht Titel und Personenzuordnung.');
        foreach($p['person_ids'] as $id)identifier($id);
    }else fail(422,'Unbekannter Vorschlagstyp.');
}
function relationship(PDO $db,array $p): void {
    $a=$p['von_person_id'];$b=$p['zu_person_id'];
    foreach([$a,$b] as $id){$r=getRecord($db,$id);if(!$r||$r['kind']!=='person')fail(409,'Beide Personen müssen zuerst freigegeben werden.');}
    $children=[];
    foreach(records($db,'relationship') as $r){$x=$r['data'];$from=$x['von_person_id']??'';$to=$x['zu_person_id']??'';
        if(($x['typ']??'')===$p['typ']&&(($from===$a&&$to===$b)||($p['typ']==='partner'&&$from===$b&&$to===$a)))fail(409,'Verbindung existiert bereits.');
        if(($x['typ']??'')==='eltern_kind')$children[$from][]=$to;
    }
    if($p['typ']==='partner')foreach(records($db,'family') as $f){$ids=$f['data']['partner_person_ids']??[];if(in_array($a,$ids,true)&&in_array($b,$ids,true))fail(409,'Partnerschaft existiert bereits.');}
    if($p['typ']==='eltern_kind'){
        $stack=[$b];$seen=[];while($stack){$x=array_pop($stack);if($x===$a)fail(409,'Diese Verbindung würde einen Abstammungskreis erzeugen.');if(!isset($seen[$x])){$seen[$x]=true;array_push($stack,...($children[$x]??[]));}}
    }
}
function audit(PDO $db,string $target,string $actor,string $action,array $data): void {
    query($db,'INSERT INTO ah_audit VALUES (?,?,?,?,?,?)',[uid(),$target,$actor,$action,jencode($data),stamp()]);
}
function visibleIds(PDO $db,array $share): array {
    $ids=[];foreach(records($db,'person') as $r){$p=$r['data'];$id=$r['id'];
        if(($share['person_ids']??[])&&!in_array($id,$share['person_ids'],true))continue;
        $b=gp($p,'geburt.datum.iso');$dead=gp($p,'tod.datum.iso')||str_starts_with($p['lebensstatus']??'','verstorben')||($b&&preg_match('/^\d{4}/',$b)&&(int)substr($b,0,4)<(int)gmdate('Y')-120);
        if($dead||($share['include_living']??false))$ids[]=$id;
    }return $ids;
}
function mediaIds(PDO $db,array $r): array {
    $ids=$r['data']['person_ids']??[];foreach($r['data']['zuordnungen']??[] as $a)if(!empty($a['person_id']))$ids[]=$a['person_id'];
    static $people=[];$key=spl_object_id($db);$people[$key]??=records($db,'person');
    foreach($people[$key] as $p)foreach($p['data']['anhaenge']??[] as $a)if(($a['medium_id']??null)===$r['id'])$ids[]=$p['id'];
    return array_values(array_unique($ids));
}
function publicPerson(array $r): array {
    $p=$r['data'];$out=['id'=>$r['id'],'anzeigename'=>$p['anzeigename']??null,'geschlecht'=>$p['geschlecht']??null,'generation_in_vorlage'=>$p['generation_in_vorlage']??null,'version'=>$r['version']];
    if(isset($p['hauptlinie']))$out['hauptlinie']=$p['hauptlinie'];
    $out['namen']=['familienname'=>gp($p,'namen.familienname'),'geburtsname'=>gp($p,'namen.geburtsname')];
    foreach(['geburt','tod'] as $ev)$out[$ev]=['datum'=>['iso'=>gp($p,$ev.'.datum.iso')],'ort_original'=>gp($p,$ev.'.ort_original')];return $out;
}
function install(PDO $db,array $cfg,array $b,string $root): array {
    $key=$cfg['setup_key']??'';
    if(strlen($key)<32||str_starts_with($key,'HIER-')||!is_string($b['key']??null)||!hash_equals($key,$b['key']))fail(403,'Einrichtungsschlüssel ungültig.');
    schema($db);
    return transaction($db,function()use($db,$b,$root){
        if(installed($db)||one($db,'SELECT id FROM ah_users LIMIT 1')||one($db,'SELECT id FROM ah_records LIMIT 1'))fail(409,'Einrichtung bereits erfolgt oder Datenbank nicht leer.');
        $email=strtolower(trim((string)($b['email']??'')));$name=trim((string)($b['name']??''));
        if(!filter_var($email,FILTER_VALIDATE_EMAIL)||strlen($email)>254||!$name||mb_strlen($name)>200)fail(422,'Name und E-Mail prüfen.');$hash=passwordHash($b['password']??null);
        $seed=json_decode(file_get_contents($root.'/seed/stammbaum-huschka.json'),false,512,JSON_THROW_ON_ERROR);
        $mapping=['personen'=>'person','familien'=>'family','beziehungen'=>'relationship','medien'=>'media','quellen'=>'source','orte'=>'place','pruefhinweise'=>'issue','quellenseiten'=>'source_page'];$counts=[];
        foreach($mapping as $key=>$kind){$items=$seed->$key??[];$counts[$key]=count($items);foreach($items as $obj){
            $id=$obj->id??uid();identifier($id);query($db,'INSERT INTO ah_records VALUES (?,?,?,1)',[$id,$kind,jencode($obj)]);
            if($kind==='media'){
                $src=realpath($root.'/seed/'.($obj->datei??''));$base=realpath($root.'/seed');
                if(!$src||!str_starts_with($src,$base.DIRECTORY_SEPARATOR)||!is_file($src))fail(422,'Importdatei fehlt.');
                $dest=$root.'/private/media/'.$obj->datei;if(!is_dir(dirname($dest))&&!mkdir(dirname($dest),0700,true))fail(503,'Medienverzeichnis nicht beschreibbar.');
                if(!copy($src,$dest))fail(503,'Mediendatei konnte nicht kopiert werden.');
            }
        }unset($seed->$key);}
        query($db,'INSERT INTO ah_records VALUES (?,?,?,1)',['original_import','archive_meta',jencode($seed)]);
        query($db,'INSERT INTO ah_users VALUES (?,?,?,?,?,1)',[uid(),$email,$name,$hash,'admin']);
        query($db,"INSERT INTO ah_settings VALUES ('installed',?)",[jencode(['created'=>stamp(),'schema'=>1])]);return ['ok'=>true,'importiert'=>$counts];
    });
}
