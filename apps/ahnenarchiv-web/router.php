<?php
$path=parse_url($_SERVER['REQUEST_URI'],PHP_URL_PATH);
if(preg_match('#^/static/[a-zA-Z0-9_./-]+\.(?:mjs|js|css)$#D',$path) && !str_contains($path,'..') && is_file(__DIR__.'/public'.$path))return false;
if(in_array($path,['/static/app.js','/static/style.css','/static/setup.js'],true))return false;
require __DIR__.'/public/index.php';
