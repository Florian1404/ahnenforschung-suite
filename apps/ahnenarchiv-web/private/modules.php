<?php
declare(strict_types=1);

// Ahnenarchiv's own module API. Manifests are data; no PHP from module folders is executed.
const AH_MODULE_API = 1;
const AH_MODULE_CORE = '2.1.0';

function ahModuleCatalog(PDO $db, string $root): array {
    $setting = one($db, "SELECT data FROM ah_settings WHERE id='modules_v1'");
    $states = $setting ? decode($setting['data']) : [];
    $out = [];
    foreach (glob($root.'/private/modules/*/module.json') ?: [] as $file) {
        try { $m = json_decode(file_get_contents($file), true, 16, JSON_THROW_ON_ERROR); }
        catch (Throwable) { continue; }
        if (!is_array($m)) continue;
        $id = $m['id'] ?? '';
        if (!is_string($id) || !preg_match('/^[a-z][a-z0-9-]{0,59}$/D', $id) || basename(dirname($file)) !== $id) continue;
        if (($m['api'] ?? null) !== AH_MODULE_API || !is_string($m['version'] ?? null) || !preg_match('/^\d+\.\d+\.\d+$/D', $m['version'])) continue;
        if (!is_string($m['title'] ?? null) || !is_string($m['description'] ?? null)) continue;
        $min = $m['min_core'] ?? '1.5.0';
        if (!is_string($min) || !preg_match('/^\d+\.\d+\.\d+$/D', $min)) continue;
        $compatible = version_compare(AH_MODULE_CORE, $min, '>=');
        $asset = '/static/modules/'.$id.'/index.mjs';
        if (!is_file($root.'/public'.$asset)) continue;
        $out[] = ['id'=>$id, 'title'=>mb_substr($m['title'],0,120), 'description'=>mb_substr($m['description'],0,1000),
            'version'=>$m['version'], 'api'=>AH_MODULE_API, 'compatible'=>$compatible, 'min_core'=>$min,
            'enabled'=>$compatible && ($states[$id] ?? true) === true, 'asset'=>$asset];
    }
    usort($out, fn($a,$b)=>strcmp($a['id'],$b['id']));
    return $out;
}

function ahModuleApi(PDO $db, string $root, array $u, string $method, string $path): array {
    if ($method === 'GET' && $path === '/api/modules')
        return ['core_version'=>AH_MODULE_CORE, 'api'=>AH_MODULE_API, 'modules'=>ahModuleCatalog($db,$root)];
    if ($method === 'GET' && $path === '/api/modules/research/data') {
        $enabled = false;
        foreach (ahModuleCatalog($db,$root) as $entry) if ($entry['id'] === 'research') $enabled = $entry['enabled'];
        if (!$enabled) fail(404,'Recherchemodul nicht aktiv.');
        return ['quellen'=>array_map('recordJson',records($db,'source')), 'orte'=>array_map('recordJson',records($db,'place'))];
    }
    if ($method === 'POST' && preg_match('#^/api/modules/([a-z][a-z0-9-]{0,59})$#D',$path,$m)) {
        admin($u);
        $b = body();
        if (!is_bool($b['enabled'] ?? null)) fail(422,'enabled muss wahr oder falsch sein.');
        $module = null;
        foreach (ahModuleCatalog($db,$root) as $entry) if ($entry['id'] === $m[1]) $module = $entry;
        if (!$module) fail(404,'Modul nicht installiert.');
        if (!$module['compatible'] && $b['enabled']) fail(409,'Modul benötigt einen neueren Kern.');
        return transaction($db,function()use($db,$u,$module,$b) {
            $old = one($db,"SELECT data FROM ah_settings WHERE id='modules_v1'");
            $states = $old ? decode($old['data']) : [];
            $before = $states[$module['id']] ?? true;
            $states[$module['id']] = $b['enabled'];
            if ($old) query($db,"UPDATE ah_settings SET data=? WHERE id='modules_v1'",[jencode($states)]);
            else query($db,'INSERT INTO ah_settings (id,data) VALUES (?,?)',['modules_v1',jencode($states)]);
            audit($db,'module_'.$module['id'],$u['id'],'module_toggle',['before'=>$before,'enabled'=>$b['enabled']]);
            return ['ok'=>true,'enabled'=>$b['enabled']];
        });
    }
    fail(404,'Modul-Endpunkt nicht gefunden.');
}
