<?php
if(PHP_SAPI!=='cli'){http_response_code(404);exit;}
require __DIR__.'/private/core.php';
try{
    $cfg=require __DIR__.'/config.php';$db=db($cfg);$cmd=$argv[1]??'';
    if($cmd==='check'){
        echo 'PHP '.PHP_VERSION."\n";
        foreach(['pdo_mysql','mbstring','fileinfo'] as $extension)echo $extension.': '.(extension_loaded($extension)?'OK':'FEHLT')."\n";
        echo 'Datenbank: '.$db->getAttribute(PDO::ATTR_DRIVER_NAME)."\n";
        echo 'Medien beschreibbar: '.(is_writable(__DIR__.'/private/media')?'ja':'nein')."\n";
        echo 'PHP-Limit: '.ini_get('memory_limit')."\n";
    }elseif($cmd==='install'){
        $input=json_decode(stream_get_contents(STDIN),true,64,JSON_THROW_ON_ERROR);echo jencode(install($db,$cfg,$input,__DIR__))."\n";
    }elseif($cmd==='export'){
        $meta=getRecord($db,'original_import');$out=$meta?(array)json_decode($meta['_raw_data'],false,512,JSON_THROW_ON_ERROR):[];$map=['person'=>'personen','family'=>'familien','relationship'=>'beziehungen','media'=>'medien','source'=>'quellen','place'=>'orte','issue'=>'pruefhinweise','source_page'=>'quellenseiten'];foreach($map as $key)$out[$key]=[];
        foreach(records($db) as $r)if(isset($map[$r['kind']]))$out[$map[$r['kind']]][]=json_decode($r['_raw_data'],false,512,JSON_THROW_ON_ERROR);echo jencode($out)."\n";
    }else{fwrite(STDERR,"Befehle: check | install (JSON über stdin) | export (JSON über stdout)\n");exit(1);}
}catch(Throwable $e){fwrite(STDERR,$e->getMessage()."\n");exit(1);}
