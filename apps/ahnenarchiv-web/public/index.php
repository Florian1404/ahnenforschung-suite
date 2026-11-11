<?php
declare(strict_types=1);
$root=dirname(__DIR__);
require_once $root.'/private/api.php';
header('X-Content-Type-Options: nosniff');header('Referrer-Policy: no-referrer');header('Cache-Control: no-store');
header("Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' blob: data:; connect-src 'self'; frame-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'");
try {
    if(!is_file($root.'/config.php'))fail(503,'Bitte config.example.php nach config.php kopieren und einrichten.');
    $cfg=require $root.'/config.php';
    $url=parse_url($cfg['base_url']??'');$scheme=$url['scheme']??'';$host=$url['host']??'';
    if(!$host||!in_array($scheme,['http','https'],true)||!empty($url['path'])||!empty($url['query'])||!empty($url['fragment']))fail(503,'base_url muss die Domain ohne abschließenden Schrägstrich enthalten.');
    $expected=$host.(isset($url['port'])?':'.$url['port']:'');
    if(strtolower($_SERVER['HTTP_HOST']??'')!==strtolower($expected))fail(403,'Host nicht erlaubt.');
    if(($cfg['require_https']??true)&&empty($_SERVER['HTTPS'])||(($cfg['require_https']??true)&&($_SERVER['HTTPS']??'')==='off'))fail(403,'Bitte die HTTPS-Adresse verwenden.');
    $method=$_SERVER['REQUEST_METHOD']??'GET';$path=parse_url($_SERVER['REQUEST_URI']??'/',PHP_URL_PATH);
    if(!in_array($method,['GET','POST'],true))fail(405,'Methode nicht erlaubt.');
    if($method==='GET'&&in_array($path,['/','/setup'],true)&&!empty($_SERVER['QUERY_STRING'])){header('Location: '.$path,true,303);exit;}
    if($method==='POST'){
        $origin=$_SERVER['HTTP_ORIGIN']??null;
        if($origin!==null&&$origin!==$cfg['base_url'])fail(403,'Ungültiger Ursprung.');
        if(($_SERVER['HTTP_SEC_FETCH_SITE']??'')==='cross-site')fail(403,'Ungültiger Ursprung.');
        $limit=(in_array($path,['/api/upload','/api/imports'],true)||preg_match('#^/api/imports/[a-f0-9]{32}/(preview|submit)$#D',$path))?(int)$cfg['max_upload_bytes']:1048576;
        if((int)($_SERVER['CONTENT_LENGTH']??0)>$limit)fail(413,'Anfrage oder Datei zu groß.');
        if(!in_array($path,['/api/upload','/api/imports'],true)&&!str_starts_with(strtolower($_SERVER['CONTENT_TYPE']??''),'application/json'))fail(415,'JSON-Anfrage erforderlich.');
    }
    if($method==='GET'&&$path==='/'){header('Content-Type: text/html; charset=utf-8');readfile(__DIR__.'/index.html');exit;}
    if($method==='GET'&&$path==='/setup'){header('Content-Type: text/html; charset=utf-8');readfile(__DIR__.'/setup.html');exit;}
    $db=db($cfg);
    if($path==='/api/setup'&&$method==='POST')$result=install($db,$cfg,body(),$root);
    else $result=api($db,$cfg,$root,$method,$path);
    header('Content-Type: application/json; charset=utf-8');echo jencode($result);
} catch(ApiError $e){http_response_code($e->status);header('Content-Type: application/json; charset=utf-8');echo jencode(['detail'=>$e->getMessage()]);}
catch(Throwable $e){http_response_code(503);header('Content-Type: application/json; charset=utf-8');error_log('Ahnenarchiv: '.$e->getMessage());echo '{"detail":"Serverfehler. Bitte Einrichtung und Serverprotokoll prüfen."}';}
