# -*- coding: utf-8 -*-
"""Matricula Bestandsbrowser v5.1 – nur Bestandsmetadaten, keine Buchbilder.
Installation: py -m pip install requests beautifulsoup4 customtkinter
Start: py matricula-bestand5_1.py
"""
import json
import re
import threading
import time
import os
import unicodedata
import shutil
import tkinter as tk
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup
try:
    import customtkinter as ctk
except ImportError as exc:
    raise SystemExit('Fehlendes Paket: py -m pip install requests beautifulsoup4 customtkinter') from exc
from tkinter import filedialog, messagebox, ttk

ROOT = 'https://data.matricula-online.eu'
SLUGS = {'Österreich':'oesterreich','Deutschland':'deutschland','Polen':'polen',
         'Serbien':'serbien','Luxemburg':'luxemburg','Bosnien':'bosnien',
         'Slowenien':'slowenien','Italien':'italien','Privatarchiv':'privatarchive',
         'Schweiz':'schweiz'}
ROOTDIR = Path(__file__).resolve().parent

def parts(url):
    return [x for x in urlsplit(url).path.split('/') if x]

def normalize(url):
    p = urlsplit(url)
    return urlunsplit((p.scheme,p.netloc,p.path.rstrip('/')+'/', '', ''))

def child(parent, target):
    a,b = parts(parent),parts(target)
    return urlsplit(target).netloc == urlsplit(ROOT).netloc and len(b)==len(a)+1 and b[:len(a)]==a

def page_content(soup):
    return soup.select_one('#page-main-content') or soup.select_one('main') or soup

def choose_name(tag):
    # Abzeichen/Zählungen sind häufig eigene Elemente; deren Zahl nicht in den Namen aufnehmen.
    clone = BeautifulSoup(str(tag), 'html.parser')
    a = clone.find('a') or clone
    for x in a.select('.badge, .count, .badge-pill, small, .fa, i, svg'):
        x.decompose()
    name = a.get_text(' ',strip=True)
    return re.sub(r'\s+\d+\s*$', '', name).strip()

def discover_children(base, soup):
    result={}
    content=page_content(soup)
    for a in content.select('a[href]'):
        url=normalize(urljoin(base,a['href']))
        if not child(base,url):
            continue
        name=choose_name(a)
        if not name or name.isdigit() or (len(name)==1 and name.isalpha()):
            continue
        result[url]=name
    return result

def parse_books(ort_url, soup):
    books={}
    content=page_content(soup)
    for tr in content.select('tr'):
        cells=tr.find_all('td',recursive=False)
        if len(cells)<2:
            continue
        row=[c.get_text(' ',strip=True) for c in cells]
        candidates=[]
        for a in tr.select('a[href]'):
            url=normalize(urljoin(ort_url,a['href']))
            if not child(ort_url,url):
                continue
            camera=bool(a.select_one('.fa-camera, .fa-camera-retro, [class*=camera], [title*=Buch], [aria-label*=Buch]'))
            camera = camera or 'camera' in ' '.join(a.get('class',[])).lower() or 'buch' in str(a.get('title','')).lower()
            candidates.append((not camera,url))
        if not candidates:
            continue  # Kein konstruierter Link: nur tatsächlich vorhandene Ziel-URL.
        candidates.sort()
        base=candidates[0][1]
        signature=parts(base)[-1]
        # Typischer Matricula-Aufbau: Kamera | Signatur | Typ | Zeitraum.
        nonblank=[x for x in row if x]
        sig_index=next((i for i,x in enumerate(nonblank) if x.strip()==signature),None)
        if sig_index is not None:
            trailing=nonblank[sig_index+1:]
        else:
            trailing=nonblank
        zeit=next((x for x in trailing if re.search(r'(?<!\d)\d{4}\s*[-–/]\s*\d{4}(?!\d)',x)), '')
        typ=next((x for x in trailing if x != zeit and x != signature), '')
        if not typ:
            typ=next((x for x in nonblank if x != signature and x != zeit),'')
        books[base]={
            'signatur':signature,'titel':typ or signature,'typ':typ,
            'zeitraum':zeit,'url_base':base,'url':base+'?pg=1',
            'quelle':'direkter HTML-Link','tabellenzeile':' | '.join(row)
        }
    return books

def atomic_json(path,obj):
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
    tmp.replace(path)

def output_paths(land):
    slug=SLUGS[land]
    stem=ROOTDIR / ('matricula-bestand-'+slug+'-v4')
    return stem.with_suffix('.json'),stem.with_suffix('.txt'),ROOTDIR/(stem.name+'-status.json')

def export(data):
    j,t,s=output_paths(data['land'])
    atomic_json(j,data)
    rows=['Land\tArchiv\tArchiv_URL\tOrt\tOrt_URL\tSignatur\tTyp\tZeitraum\tBuch_URL\tViewer_URL']
    counts={'archive':len(data['archive']),'orte':0,'buecher':0,'offen':0,'fehler':0}
    for a in data['archive'].values():
        for o in a['orte'].values():
            counts['orte']+=1
            if o['status']!='fertig':counts['offen']+=1
            if o['status']=='fehler':counts['fehler']+=1
            for b in o['buecher'].values():
                counts['buecher']+=1
                fields=[data['land'],a['name'],a['url'],o['name'],o['url'],b['signatur'],b['typ'],b['zeitraum'],b['url_base'],b['url']]
                rows.append('\t'.join(str(x).replace('\t',' ').replace('\n',' ') for x in fields))
    tmp=t.with_suffix('.txt.tmp')
    tmp.write_text('\n'.join(rows)+'\n',encoding='utf-8')
    tmp.replace(t)
    status={'land':data['land'],'scanbereich':data.get('scanbereich'),'letztes_paket':data.get('letztes_paket'),
            'stand':datetime.now(timezone.utc).isoformat(),
            'abgeschlossen':bool(data.get('scan_abgeschlossen')), 'paket_status':data.get('paket_status',{}),
            'vollstaendigkeit_bestaetigt':bool(data.get('scan_abgeschlossen')) and not data['fehler'] and counts['offen']==0,
            'zahlen':counts,'fehler':data['fehler'],
            'hinweis':'Buchlinks aus Listen-HTML; Zielseiten nicht einzeln geprüft. Anzahl gegen Matricula im Browser prüfen.'}
    atomic_json(s,status)
    return j,t,s,counts



# Archivgruppen sind Auswahlhilfen, keine exakten politischen Grenzgeometrien.
# Mehrfachzuordnung wird explizit unterstützt (z.B. Erzdiözese Wien in Wien UND NÖ).
# Die Bezeichnungen sind von den realen Matricula-Landesverzeichnissen abgeleitet.
REGION_GROUPS = {
    'Österreich': {
        'Burgenland': ['Burgenland:'],
        'Kärnten': ['Kärnten:'],
        'Niederösterreich': ['Niederösterreich:', 'Niederösterreich (', 'Wien/Niederösterreich'],
        'Oberösterreich': ['Oberösterreich:'],
        'Salzburg': ['Salzburg:'],
        'Steiermark': ['Steiermark:'],
        'Tirol': ['Tirol:'],
        'Vorarlberg': ['Vorarlberg:'],
        'Wien': ['Wien,', 'Wien:', 'Wien/Niederösterreich'],
    },
    'Deutschland': {
        'Baden-Württemberg': ['Landesarchiv Baden-Württemberg', 'Rottenburg-Stuttgart'],
        'Bayern': ['Augsburg,', 'Bamberg,', 'Eichstätt,', 'München und Freising,',
                   'Passau,', 'Regensburg,', 'Würzburg,'],
        'Berlin': ['Berlin,'],
        'Hessen': ['Fulda,', 'Limburg,', 'Mainz,'],
        'Niedersachsen': ['Hildesheim,', 'Osnabrück,', 'Vechta,'],
        'Nordrhein-Westfalen': ['Aachen,', 'Essen,', 'Münster,', 'Paderborn,'],
        'Rheinland-Pfalz': ['Rheinland,', 'Limburg,', 'Mainz,'],
        'Sachsen': ['Dresden-Meißen,'],
        'Sachsen-Anhalt': ['Magdeburg,'],
    },
}
REGION_PROMPT = 'Bundesland / Region wählen…'
ARCHIVE_PROMPT = 'Diözese / Archiv wählen…'
ALL_REGIONS = 'Alle Bundesländer / Regionen'
ALL_ARCHIVES = 'Alle Archive der Auswahl'
OTHER_REGION = 'Überregional / nicht zugeordnet'
BATCH_SIZE = 25
AREA_OPTIONS = ['Alle Orte', 'A–F', 'G–L', 'M–R', 'S–Z', '0–9 / Sonstige']
PACKAGE_DEFAULT = 'Nächstes offenes Paket'
PACKAGE_ALL = 'Alle Pakete (bis Stop)'
MODE_NEW = 'Neue / offene Orte'
MODE_ERRORS = 'Problemorte nachprüfen'


def groups_for(land):
    if land not in REGION_GROUPS:
        return [REGION_PROMPT, ALL_REGIONS]
    return [REGION_PROMPT] + list(REGION_GROUPS[land]) + [OTHER_REGION, ALL_REGIONS]


def archive_regions(land, name):
    matches = [region for region, prefixes in REGION_GROUPS.get(land, {}).items()
               if any(name.casefold().startswith(prefix.casefold()) for prefix in prefixes)]
    return matches or [OTHER_REGION]


def archive_in_region(land, name, region):
    return region == ALL_REGIONS or region in archive_regions(land, name)


def choose_archive_items(items, land, region, archive):
    if region == REGION_PROMPT or archive == ARCHIVE_PROMPT:
        return []
    selected = [(url, name) for url, name in items if archive_in_region(land, name, region)]
    if archive != ALL_ARCHIVES:
        selected = [(url, name) for url, name in selected
                    if name == archive or parts(url)[-1].casefold() == archive.casefold()]
    return sorted(selected, key=lambda x: (x[1].casefold(), x[0]))


def first_character(name):
    text = unicodedata.normalize('NFKD', name.strip().casefold())
    letters = [c for c in text if not unicodedata.combining(c)]
    return letters[0].upper() if letters else ''


def matches_area(name, area):
    if area == AREA_OPTIONS[0]:
        return True
    c = first_character(name)
    if area == 'A–F': return 'A' <= c <= 'F'
    if area == 'G–L': return 'G' <= c <= 'L'
    if area == 'M–R': return 'M' <= c <= 'R'
    if area == 'S–Z': return 'S' <= c <= 'Z'
    return not ('A' <= c <= 'Z')


def filtered_locations(archive, area, search):
    raw = archive.get('orts_index', {})
    needle = search.strip().casefold()
    return sorted(((u, n) for u, n in raw.items()
                   if matches_area(n, area) and (not needle or needle in n.casefold())),
                  key=lambda x: (x[1].casefold(), x[0]))


def batch_list(items, size=BATCH_SIZE):
    return [(i//size+1, i, items[i:i+size]) for i in range(0, len(items), size)]


def journal_path(land):
    return ROOTDIR / f'matricula-bestand-{SLUGS[land]}-v4-journal.jsonl'


def append_journal(land, archive, place, checkpoint):
    """Durable kleiner Fortschrittseintrag je Ort. Die riesige JSON muss nicht je Ort geschrieben werden."""
    record = {'archiv_url': archive['url'], 'archiv_name': archive['name'],
              'ort': place, 'checkpoint': checkpoint}
    with journal_path(land).open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(record, ensure_ascii=False, separators=(',', ':')) + '\n')
        fh.flush()
        os.fsync(fh.fileno())


def replay_journal(data):
    path = journal_path(data['land'])
    if not path.exists(): return 0
    recovered = 0
    with path.open('r', encoding='utf-8') as fh:
        for line in fh:
            try: record = json.loads(line)
            except json.JSONDecodeError:
                # Crash während der allerletzten Journalzeile: letzte Teilzeile ignorieren.
                break
            a_url = record['archiv_url']
            archive = data['archive'].setdefault(a_url, {
                'url': a_url, 'name': record['archiv_name'], 'status': 'teilweise', 'orte': {}})
            place = record['ort']
            existing = archive['orte'].get(place['url'])
            if existing:
                merged = dict(existing)
                merged.update(place)
                merged['buecher'] = {**existing.get('buecher', {}), **place.get('buecher', {})}
                place = merged
            archive['orte'][place['url']] = place
            data['checkpoint'] = record.get('checkpoint', data.get('checkpoint'))
            recovered += 1
    return recovered


def persist_full(data):
    """Atomaren Snapshot erstellen; Original einmalig sichern und Journal danach löschen."""
    original = output_paths(data['land'])[0]
    backup = original.with_name(original.name + '.vor-v5_1.bak')
    if original.exists() and not backup.exists():
        temp_backup = backup.with_name(backup.name + '.tmp')
        shutil.copy2(original, temp_backup)
        temp_backup.replace(backup)
    result = export(data)
    path = journal_path(data['land'])
    if path.exists(): path.unlink()
    return result


class Scraper:
    def __init__(self, delay=3.5):
        self.delay = max(3.5, float(delay))
        self.stop = threading.Event()
        self.session = requests.Session()
        self.ua = 'MatriculaBestandsbrowser/5.1 (private genealogical metadata index)'
        self.session.headers.update({'User-Agent': self.ua, 'Accept-Language': 'de,en;q=0.8'})
        self.last = 0
        self.robot = RobotFileParser()
        self.robot.set_url(ROOT + '/robots.txt')
        self.robots_checked = False

    def robots_check(self):
        if self.robots_checked: return
        try:
            resp = self.session.get(ROOT + '/robots.txt', timeout=20)
            if resp.status_code in (403, 429):
                raise PermissionError(f'robots.txt: HTTP {resp.status_code}')
            if resp.status_code != 200:
                raise RuntimeError(f'robots.txt: HTTP {resp.status_code}')
            self.robot.parse(resp.text.splitlines())
        except requests.RequestException as exc:
            raise RuntimeError(f'robots.txt nicht erreichbar: {exc}') from exc
        self.robots_checked = True

    def get(self, url):
        if self.stop.is_set(): raise InterruptedError('Scan gestoppt')
        self.robots_check()
        if not self.robot.can_fetch(self.ua, url):
            raise PermissionError('robots.txt untersagt: ' + url)
        for attempt in range(3):
            wait = self.delay - (time.monotonic() - self.last)
            if wait > 0 and self.stop.wait(wait): raise InterruptedError('Scan gestoppt')
            self.last = time.monotonic()
            try: resp = self.session.get(url, timeout=(10, 30))
            except requests.RequestException as exc:
                if attempt == 2: raise RuntimeError(f'Netzwerkfehler {url}: {exc}') from exc
                if self.stop.wait(8 * (attempt+1)): raise InterruptedError('Scan gestoppt')
                continue
            if resp.status_code in (403, 429):
                raise PermissionError(f'HTTP {resp.status_code} bei {url}; Scan angehalten')
            if resp.status_code in (500, 502, 503, 504):
                if attempt == 2: raise RuntimeError(f'HTTP {resp.status_code} bei {url}')
                if self.stop.wait(8 * (attempt+1)): raise InterruptedError('Scan gestoppt')
                continue
            resp.raise_for_status()
            return BeautifulSoup(resp.text, 'html.parser')
        raise RuntimeError('Unbekannter HTTP-Fehler')

    def pages(self, base):
        queue, seen = deque([base]), set()
        while queue:
            current = queue.popleft()
            if current in seen: continue
            if len(seen) >= 200: raise RuntimeError('Zu viele Seiten / Schleifenverdacht: ' + base)
            seen.add(current)
            soup = self.get(current)
            yield soup
            for a in page_content(soup).select('a[href]'):
                target = urljoin(current, a['href'])
                p = urlsplit(target)
                if (p.netloc != urlsplit(base).netloc or
                    p.path.rstrip('/') != urlsplit(base).path.rstrip('/')):
                    continue
                q = parse_qs(p.query)
                if not any(k in q for k in ('page', 'p')): continue
                if target not in seen and target not in queue: queue.append(target)

    def load_data(self, land):
        j, _, _ = output_paths(land)
        if j.exists():
            data = json.loads(j.read_text(encoding='utf-8'))
            if data.get('version') not in (4, 5) or data.get('land') != land or 'archive' not in data:
                raise RuntimeError('Bestehende JSON-Datei hat unerwartetes Format: ' + str(j))
        else:
            data = {'version': 4, 'land': land, 'url': ROOT + '/de/' + SLUGS[land] + '/',
                    'archive': {}, 'fehler': [], 'scanbereich': None, 'scan_abgeschlossen': False}
        data['journal_eintraege'] = replay_journal(data)
        return data

    def archives(self, land, data, status):
        cache = data.setdefault('archiv_index', {})
        if data.get('archiv_index_vollstaendig'):
            return list(cache.items())
        for a in data.get('archive', {}).values(): cache[a['url']] = a['name']
        status('Lese einmalig Archivverzeichnis: ' + land)
        found = {}
        base = ROOT + '/de/' + SLUGS[land] + '/'
        for soup in self.pages(base): found.update(discover_children(base, soup))
        if not found: raise RuntimeError('Keine Archive gefunden: ' + base)
        cache.update(found)
        data['archiv_index_vollstaendig'] = True
        persist_full(data)
        return list(cache.items())

    def locations(self, archive, data, status):
        cache = archive.setdefault('orts_index', {})
        if archive.get('orts_index_vollstaendig'):
            return list(cache.items())
        status('Lese Ortsverzeichnis einmalig: ' + archive['name'])
        found = {}
        for soup in self.pages(archive['url']):
            found.update(discover_children(archive['url'], soup))
        if not found: raise RuntimeError('Keine Orte gefunden: ' + archive['url'])
        cache.update(found)
        archive['orts_index_vollstaendig'] = True
        persist_full(data)
        return list(cache.items())

    def run(self, land, region, archive_filter, area, search, package, mode, status):
        if region == REGION_PROMPT or archive_filter == ARCHIVE_PROMPT:
            raise ValueError('Bitte Bundesland und Diözese bewusst auswählen.')
        self.stop.clear()
        data = self.load_data(land)
        data['scanbereich'] = {'region': region, 'archiv': archive_filter,
                              'ortbereich': area, 'ortfilter': search, 'paket': package, 'modus': mode}
        data['scan_abgeschlossen'] = False
        try:
            available = self.archives(land, data, status)
            selected = choose_archive_items(available, land, region, archive_filter)
            if not selected: raise ValueError('Keine Archive in dieser Auswahl gefunden.')
            total_processed = 0
            for aurl, aname in selected:
                if self.stop.is_set(): raise InterruptedError('Benutzerstopp')
                archive = data['archive'].setdefault(aurl, {'name': aname, 'url': aurl,
                                                            'orte': {}, 'status': 'offen'})
                self.locations(archive, data, status)
                locations = filtered_locations(archive, area, search)
                if not locations:
                    status(f'{aname}: keine passenden Ortsnamen, nichts gescannt')
                    continue
                batches = batch_list(locations)
                selected_batches = batches if package == PACKAGE_ALL else []
                if package == PACKAGE_DEFAULT:
                    eligible = lambda b: any(
                        (archive['orte'].get(u, {}).get('status') in ('fehler','leer_pruefen') if mode == MODE_ERRORS
                         else archive['orte'].get(u, {}).get('status', 'offen') == 'offen')
                        for u, _ in b[2])
                    selected_batches = [b for b in batches if eligible(b)][:1]
                elif package != PACKAGE_ALL:
                    selected_batches = [b for b in batches if str(b[0]) == package]
                if not selected_batches:
                    status(f'{aname}: kein passendes/offenes Paket')
                    continue
                for number, start_index, items in selected_batches:
                    key = f'{aurl}|{area}|{search.casefold()}|{number}|{mode}'
                    data.setdefault('paket_status', {})[key] = 'laeuft'
                    for index, (url, name) in enumerate(items, start_index):
                        if self.stop.is_set(): raise InterruptedError('Benutzerstopp')
                        old_status = archive['orte'].get(url, {}).get('status','offen')
                        if old_status == 'fertig': continue
                        if mode == MODE_ERRORS and old_status not in ('fehler','leer_pruefen'): continue
                        if mode == MODE_NEW and old_status != 'offen': continue
                        place = archive['orte'].setdefault(url, {
                            'name': name, 'url': url, 'status': 'offen', 'buecher': {}})
                        status(f'{aname} | Paket {number}/{len(batches)} | '
                               f'Ort {index+1}/{len(locations)}: {name} | heute {total_processed} bearbeitet')
                        try:
                            found = {}
                            for soup in self.pages(url):
                                found.update(parse_books(url, soup))
                            if found: place['buecher'].update(found)
                            place['status'] = 'fertig' if found or place['buecher'] else 'leer_pruefen'
                            if not found and not place['buecher']:
                                data['fehler'].append({'url': url, 'meldung': 'Keine Kirchenbuchlinks gefunden'})
                        except (PermissionError, InterruptedError): raise
                        except Exception as exc:
                            place['status'] = 'fehler'
                            data['fehler'].append({'url': url, 'meldung': str(exc)})
                        checkpoint = {'archiv_url': aurl, 'archiv': aname,
                                      'paket': number, 'orts_index': index,
                                      'ort_url': url, 'ort': name,
                                      'zeit': datetime.now(timezone.utc).isoformat()}
                        data['checkpoint'] = checkpoint
                        append_journal(land, archive, place, checkpoint)
                        total_processed += 1
                    data['paket_status'][key] = 'bearbeitet'
                    data['letztes_paket'] = {'archiv': aname, 'nummer': number,
                                            'orte': len(items), 'modus': mode}
                    # Bei 219k Büchern nur einmal je Paket die riesige JSON+TXT exportieren.
                    persist_full(data)
                    status(f'{aname}: Paket {number}/{len(batches)} gespeichert, '
                           f'{total_processed} Orte in diesem Lauf bearbeitet')
                    if package == PACKAGE_DEFAULT:
                        # NUR EIN Paket pro Klick, selbst wenn "Alle Archive" gewählt wurde.
                        return data
                if package == PACKAGE_ALL and area == AREA_OPTIONS[0] and not search and mode == MODE_NEW:
                    archive['status'] = ('fertig' if all(
                        archive['orte'].get(u,{}).get('status') == 'fertig'
                        for u in archive['orts_index']) else 'teilweise')
                    persist_full(data)
            return data
        finally:
            # Nach einem normalen Paket wurde bereits exportiert; nicht erneut 219k Bücher schreiben.
            # Bei Stop/Fehler bleibt das Journal bis zum sicheren Export erhalten.
            if journal_path(land).exists():
                persist_full(data)

ctk.set_appearance_mode('Dark')
ctk.set_default_color_theme('blue')


class Browser(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title('Matricula Bestandsbrowser 5.1 · Bundesland / Diözese')
        self.geometry('1260x870')
        self.minsize(1020, 670)
        self.parser = Scraper()
        self.data = None
        self.tree_meta = {}
        self.main = ctk.CTkFrame(self)
        self.main.pack(fill='both', expand=True, padx=12, pady=12)
        ctk.CTkLabel(self.main,
            text='🏛️ Matricula 5.1 · Bundesländer → Diözesen → Orte → Bücher',
            font=ctk.CTkFont(size=22, weight='bold')).pack(anchor='w', padx=12, pady=(10, 2))
        ctk.CTkLabel(self.main,
            text='Ein Klick = maximal 25 Orte. Bestehende Bücher bleiben erhalten. '
                 'Bundesländer sind Archivgruppen, keine geografische Pfarrei-Zuordnung.',
            text_color='#e5b85c').pack(anchor='w', padx=14, pady=(0, 8))

        opts = ctk.CTkFrame(self.main)
        opts.pack(fill='x', padx=10, pady=5)
        for i in range(5): opts.grid_columnconfigure(i, weight=1, uniform='filters')
        labels = ['1 · Land', '2 · Bundesland / Region', '3 · Diözese / Archiv',
                  '4 · Anfangsbuchstaben', '5 · Scanpaket (25 Orte)']
        for i, name in enumerate(labels):
            ctk.CTkLabel(opts, text=name, anchor='w').grid(
                row=0, column=i, padx=6, pady=(10, 3), sticky='ew')

        self.land = ctk.CTkOptionMenu(opts, values=list(SLUGS), command=self.on_land, width=175)
        self.land.grid(row=1, column=0, padx=6, pady=4, sticky='ew')
        self.land.set('Österreich')
        self.region = ctk.CTkOptionMenu(opts, values=groups_for('Österreich'),
                                       command=self.on_region, width=205)
        self.region.grid(row=1, column=1, padx=6, pady=4, sticky='ew')
        self.region.set(REGION_PROMPT)
        self.archive = ctk.CTkOptionMenu(opts, values=[ARCHIVE_PROMPT],
                                        command=self.on_archive, width=215)
        self.archive.grid(row=1, column=2, padx=6, pady=4, sticky='ew')
        self.archive.set(ARCHIVE_PROMPT)
        self.area = ctk.CTkOptionMenu(opts, values=AREA_OPTIONS,
                                     command=lambda _: self.update_preview(), width=125)
        self.area.grid(row=1, column=3, padx=6, pady=4, sticky='ew')
        self.area.set(AREA_OPTIONS[0])
        self.package = ctk.CTkOptionMenu(opts,
                       values=[PACKAGE_DEFAULT, PACKAGE_ALL] + [str(i) for i in range(1, 501)],
                       command=lambda _: self.update_preview(), width=175)
        self.package.grid(row=1, column=4, padx=6, pady=4, sticky='ew')
        self.package.set(PACKAGE_DEFAULT)

        ctk.CTkLabel(opts, text='Ortsnamenfilter (optional, nur Textsuche):',
                     anchor='w').grid(row=2, column=0, columnspan=2, padx=6, pady=(8, 3), sticky='ew')
        self.place_search = ctk.CTkEntry(opts,
            placeholder_text='z. B. München, Sankt Martin, Peißenberg…')
        self.place_search.grid(row=3, column=0, columnspan=2, padx=6, pady=(0, 8), sticky='ew')
        self.place_search.bind('<KeyRelease>', lambda _: self.update_preview())
        ctk.CTkLabel(opts, text='Scanmodus:', anchor='w').grid(
            row=2, column=2, padx=6, pady=(8, 3), sticky='ew')
        self.mode = ctk.CTkOptionMenu(opts, values=[MODE_NEW, MODE_ERRORS],
                    command=lambda _: self.update_preview())
        self.mode.grid(row=3, column=2, padx=6, pady=(0, 8), sticky='ew')
        self.mode.set(MODE_NEW)
        self.preview = ctk.CTkLabel(opts, text='Wähle zuerst Bundesland und Archiv.',
                                    anchor='w', text_color='#9cc9e7', wraplength=380)
        self.preview.grid(row=2, column=3, columnspan=2, rowspan=2,
                          padx=6, pady=(3, 8), sticky='ew')

        actions = ctk.CTkFrame(self.main, fg_color='transparent')
        actions.pack(fill='x', padx=10, pady=(2, 6))
        self.btn_index = ctk.CTkButton(actions, text='🔎 Archivliste laden',
                                       command=self.fetch_index, width=155)
        self.btn_index.pack(side='left', padx=4)
        self.btn_locations = ctk.CTkButton(actions, text='🗂️ Ortsindex laden',
                                           command=self.fetch_locations, width=155)
        self.btn_locations.pack(side='left', padx=4)
        self.btn_scan = ctk.CTkButton(actions, text='▶ Ausgewähltes Paket scannen',
                                     command=self.scan, width=225)
        self.btn_scan.pack(side='left', padx=4)
        self.btn_stop = ctk.CTkButton(actions, text='⏹ Stopp', command=self.stop_scan,
                                     width=95, state='disabled')
        self.btn_stop.pack(side='left', padx=4)
        self.btn_export = ctk.CTkButton(actions, text='📄 JSON / TXT exportieren',
                                       command=self.export_now, width=180)
        self.btn_export.pack(side='right', padx=4)

        tree_frame = tk.Frame(self.main)
        tree_frame.pack(fill='both', expand=True, padx=12, pady=(4, 6))
        self.tree = ttk.Treeview(tree_frame, columns=('status', 'url'), show='tree headings')
        self.tree.heading('#0', text='Bundesland / Diözese / Ort / Kirchenbuch')
        self.tree.heading('status', text='Status / Zeitraum')
        self.tree.heading('url', text='URL')
        self.tree.column('#0', width=430)
        self.tree.column('status', width=145)
        self.tree.column('url', width=490)
        scroll = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.tree.pack(fill='both', expand=True)
        self.tree.bind('<<TreeviewOpen>>', self.expand_tree)
        self.tree.bind('<<TreeviewSelect>>', self.show_detail)
        self.tree.bind('<Double-1>', self.pick_scope_from_tree)
        self.details = ctk.CTkTextbox(self.main, height=65)
        self.details.pack(fill='x', padx=12, pady=4)
        bottom = ctk.CTkFrame(self.main, fg_color='transparent')
        bottom.pack(fill='x', padx=12, pady=4)
        ctk.CTkButton(bottom, text='📋 Ausgewählte URL kopieren',
                      command=self.copy_url, width=230).pack(side='left', padx=3)
        ctk.CTkButton(bottom, text='❓ Bedienung / Hinweise',
                      command=self.help, width=200).pack(side='right', padx=3)
        self.stat = ctk.CTkLabel(self.main, text='', anchor='w')
        self.stat.pack(fill='x', padx=15, pady=(2, 7))
        self.load_local()
        self.on_region(REGION_PROMPT)

    def say(self, message):
        self.after(0, lambda s=str(message): self.stat.configure(text=s[:230]))

    def on_land(self, land):
        self.region.configure(values=groups_for(land))
        self.region.set(REGION_PROMPT)
        self.archive.configure(values=[ARCHIVE_PROMPT])
        self.archive.set(ARCHIVE_PROMPT)
        self.area.set(AREA_OPTIONS[0])
        self.package.set(PACKAGE_DEFAULT)
        self.load_local()
        self.update_preview()

    def on_region(self, region):
        current = self.archive.get()
        options = [ARCHIVE_PROMPT]
        if region != REGION_PROMPT and self.data:
            known = dict(self.data.get('archiv_index', {}))
            for url, a in self.data.get('archive', {}).items():
                known[url] = a['name']
            selected = sorted({name for name in known.values()
                               if archive_in_region(self.land.get(), name, region)},
                              key=str.casefold)
            options += [ALL_ARCHIVES] + selected
        self.archive_values = options
        self.archive.configure(values=options)
        self.archive.set(current if current in options else ARCHIVE_PROMPT)
        self.update_preview()

    def on_archive(self, _):
        self.update_preview()

    def update_preview(self):
        if not self.data: return
        region, archive_name = self.region.get(), self.archive.get()
        if region == REGION_PROMPT:
            self.preview.configure(text='Bitte Bundesland oder Archivgruppe auswählen.')
            return
        if archive_name == ARCHIVE_PROMPT:
            known = {**self.data.get('archiv_index', {})}
            known.update({u: a['name'] for u, a in self.data['archive'].items()})
            n = sum(archive_in_region(self.land.get(), a, region) for a in known.values())
            self.preview.configure(text=f'{n} Archive in dieser Gruppe. Jetzt Diözese auswählen.')
            return
        known = dict(self.data.get('archiv_index', {}))
        known.update({u: a['name'] for u, a in self.data['archive'].items()})
        chosen = choose_archive_items(known.items(), self.land.get(), region, archive_name)
        count_archives = len(chosen)
        count_places = count_done = count_problem = count_books = 0
        indexed = 0
        for url, _ in chosen:
            a = self.data['archive'].get(url)
            if not a or not a.get('orts_index_vollstaendig'): continue
            indexed += 1
            for u, n in filtered_locations(a, self.area.get(), self.place_search.get()):
                count_places += 1
                place = a['orte'].get(u, {})
                st = place.get('status', 'offen')
                count_done += st == 'fertig'
                count_problem += st in ('fehler', 'leer_pruefen')
                count_books += len(place.get('buecher', {}))
        self.preview.configure(text=(
            f'{count_archives} Archiv(e), {indexed} Ortsindex(e) geladen | '
            f'{count_places} Orte, {count_done} fertig, {count_problem} Problemorte | '
            f'{count_books:,} Bücher'.replace(',', '.')))

    def load_local(self):
        try:
            self.data = self.parser.load_data(self.land.get())
        except Exception as exc:
            self.data = None
            self.say('Fehler beim Laden: ' + str(exc))
            self.refresh_tree()
            return
        self.refresh_tree()
        self.on_region(self.region.get())
        if self.data.get('journal_eintraege'):
            self.say(f"{self.data['journal_eintraege']} Orte aus Fortschrittsjournal wiederhergestellt")

    def refresh_tree(self):
        existing_rows = self.tree.get_children()
        if existing_rows:
            self.tree.delete(*existing_rows)
        self.tree_meta.clear()
        if not self.data: return
        data = self.data
        total_books = sum(len(p.get('buecher', {}))
                          for a in data['archive'].values()
                          for p in a.get('orte', {}).values())
        root = self.tree.insert('', 'end', text=f"{data['land']} · {total_books:,} Bücher".replace(',', '.'),
                                values=('', data['url']), open=True)
        self.tree_meta[root] = ('land', None, None)
        known = dict(data.get('archiv_index', {}))
        known.update({u: a['name'] for u, a in data['archive'].items()})
        for region in groups_for(data['land']):
            if region in (REGION_PROMPT, ALL_REGIONS): continue
            pairs = [(u, n) for u, n in known.items()
                     if region in archive_regions(data['land'], n)]
            if not pairs: continue
            rid = self.tree.insert(root, 'end', text=f'{region} ({len(pairs)} Archive)',
                                   values=('', ''), open=False)
            self.tree_meta[rid] = ('region', region, None)
            for url, name in sorted(pairs, key=lambda x: x[1].casefold()):
                a = data['archive'].get(url, {})
                places = a.get('orte', {})
                completed = sum(p.get('status') == 'fertig' for p in places.values())
                registered = len(a.get('orts_index', {}))
                status = f'{completed}/{registered}' if registered else 'nicht geladen'
                aid = self.tree.insert(rid, 'end', text=name, values=(status, url))
                self.tree_meta[aid] = ('archive', region, url)
                if places: self.tree.insert(aid, 'end', text='…')

    def expand_tree(self, _=None):
        row = self.tree.focus()
        info = self.tree_meta.get(row)
        if not info or info[0] not in ('archive', 'place'): return
        children = self.tree.get_children(row)
        if not children or self.tree.item(children[0], 'text') != '…': return
        self.tree.delete(children[0])
        kind, region, url = info
        if kind == 'archive':
            a = self.data['archive'].get(url, {})
            for place_url, p in sorted(a.get('orte', {}).items(),
                                       key=lambda x: x[1]['name'].casefold()):
                pid = self.tree.insert(row, 'end', text=p['name'],
                                       values=(p.get('status', ''), p['url']))
                self.tree_meta[pid] = ('place', region, (url, place_url))
                if p.get('buecher'): self.tree.insert(pid, 'end', text='…')
        else:
            archive_url, place_url = url
            place = self.data['archive'][archive_url]['orte'][place_url]
            for b in sorted(place.get('buecher', {}).values(),
                            key=lambda b: b.get('signatur', '')):
                bid = self.tree.insert(row, 'end',
                       text=f"{b.get('signatur','')} · {b.get('titel','')}",
                       values=(b.get('zeitraum',''), b.get('url', '')))
                self.tree_meta[bid] = ('book', region, b.get('url', ''))

    def pick_scope_from_tree(self, _=None):
        row = self.tree.focus()
        info = self.tree_meta.get(row)
        if not info: return
        kind, region, key = info
        if kind not in ('region', 'archive'): return
        self.region.set(region)
        self.on_region(region)
        if kind == 'archive':
            name = (self.data['archive'][key]['name'] if key in self.data['archive']
                    else self.data.get('archiv_index', {}).get(key))
            if name:
                self.archive.set(name)
                self.update_preview()
        self.say('Auswahl aus dem Baum übernommen: ' + str(region))

    def show_detail(self, _=None):
        row = self.tree.focus()
        if not row: return
        item = self.tree.item(row)
        self.details.delete('1.0', 'end')
        self.details.insert('1.0', f"{item['text']}\n" + ' | '.join(map(str,item.get('values',[]))))

    def copy_url(self):
        row = self.tree.focus()
        if not row: return
        values = self.tree.item(row, 'values')
        if len(values) >= 2 and str(values[1]).startswith('http'):
            self.clipboard_clear()
            self.clipboard_append(values[1])
            self.say('URL in Zwischenablage kopiert.')

    def set_busy(self, busy):
        self.btn_scan.configure(state='disabled' if busy else 'normal')
        self.btn_stop.configure(state='normal' if busy else 'disabled')
        self.btn_index.configure(state='disabled' if busy else 'normal')
        self.btn_locations.configure(state='disabled' if busy else 'normal')
        self.btn_export.configure(state='disabled' if busy else 'normal')

    def _start_worker(self, work, only_index=False):
        self.parser.stop.clear()
        self.set_busy(True)
        def task():
            err = None
            try: work()
            except Exception as exc: err = str(exc)
            self.after(0, lambda e=err: self.finished(e, only_index))
        threading.Thread(target=task, daemon=True).start()

    def fetch_index(self):
        land = self.land.get()
        def job():
            data = self.parser.load_data(land)
            self.parser.archives(land, data, self.say)
        self._start_worker(job, only_index=True)

    def fetch_locations(self):
        land, region, archive_name = self.land.get(), self.region.get(), self.archive.get()
        if region == REGION_PROMPT or archive_name in (ARCHIVE_PROMPT, ALL_ARCHIVES):
            messagebox.showwarning('Ortssuche', 'Bitte zuerst EINE Diözese / EIN Archiv auswählen.')
            return
        def job():
            data = self.parser.load_data(land)
            for url, name in choose_archive_items(self.parser.archives(land, data, self.say),
                                                   land, region, archive_name):
                a = data['archive'].setdefault(url, {'name': name, 'url': url,
                                                      'orte': {}, 'status': 'offen'})
                self.parser.locations(a, data, self.say)
        self._start_worker(job, only_index=True)

    def scan(self):
        land, region, archive_name = self.land.get(), self.region.get(), self.archive.get()
        if region == REGION_PROMPT or archive_name == ARCHIVE_PROMPT:
            messagebox.showwarning('Scanbereich', 'Bitte Bundesland und Diözese bewusst auswählen.')
            return
        package = self.package.get()
        if archive_name == ALL_ARCHIVES and not messagebox.askyesno(
                'Mehrere Archive', 'Du hast alle Archive dieser Region ausgewählt.\n'
                'Ein Standardlauf scannt trotzdem nur EIN Paket (max. 25 Orte).\nFortfahren?'):
            return
        if package == PACKAGE_ALL and not messagebox.askyesno(
                'Langer Scan', '„Alle Pakete“ kann viele Stunden dauern.\n'
                'Fertige Orte werden übersprungen. Diesen langen Scan wirklich starten?'):
            return
        args = (land, region, archive_name, self.area.get(), self.place_search.get().strip(),
                package, self.mode.get(), self.say)
        self._start_worker(lambda: self.parser.run(*args))

    def stop_scan(self):
        self.parser.stop.set()
        self.say('Stopp angefordert · Letzter Ort ist im Fortschrittsjournal gesichert.')

    def export_now(self):
        if not self.data: return
        try:
            j, t, s, counts = persist_full(self.data)
            messagebox.showinfo('Export erfolgreich',
                f'{j.name}\n{t.name}\n{s.name}\n\n{counts["buecher"]:,} Kirchenbücher'.replace(',', '.'))
        except Exception as exc:
            messagebox.showerror('Exportfehler', str(exc))

    def finished(self, error, only_index=False):
        selection_region, selection_archive = self.region.get(), self.archive.get()
        self.set_busy(False)
        self.load_local()
        if selection_region in groups_for(self.land.get()):
            self.region.set(selection_region)
            self.on_region(selection_region)
            if selection_archive in self.archive_values: self.archive.set(selection_archive)
        self.update_preview()
        if error:
            self.say('Unterbrochen: ' + error)
            messagebox.showwarning('Scan unterbrochen', error)
        else:
            self.say('Index geladen.' if only_index else 'Paket erledigt und JSON/TXT gespeichert.')

    def help(self):
        messagebox.showinfo('Matricula 5.1 · Auswahl und Wiederaufnahme',
            '1. Land wählen, danach Bundesland / Region.\n'
            '2. Archivliste laden (nur beim ersten Mal notwendig).\n'
            '3. Bewusst eine Diözese / ein Archiv auswählen.\n'
            '4. Optional nach Ortsnamen oder A–F, G–L usw. eingrenzen.\n'
            '5. Standard: „Nächstes offenes Paket“ = maximal 25 Orte pro Klick.\n'
            '6. „Problemorte nachprüfen“ bearbeitet nur Fehler- und Leerstellen.\n'
            '7. Großes JSON/TXT wird paketweise exportiert; je Ort sichert ein '
            'kleines Journal den letzten Fortschritt.\n'
            '8. Doppelklick auf ein Archiv im Baum übernimmt es in die Auswahl.\n\n'
            'Wichtig: Bundesländer sind Archivgruppen, keine exakte Gemeinde- oder '
            'Regierungsbezirkszuordnung. Mehrfachzuordnungen sind möglich.\n'
            'Gefundene fertige Orte werden nicht erneut gescannt.\n'
            'Bei HTTP 403/429 wird gestoppt; keine Umgehung von Sperren.')


if __name__ == '__main__':
    Browser().mainloop()
