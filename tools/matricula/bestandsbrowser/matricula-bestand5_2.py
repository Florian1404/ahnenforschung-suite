# -*- coding: utf-8 -*-
"""Matricula Bestandsbrowser v5.2 · Bestandsindex, SQLite-Downloadkatalog, Einzelbuch-Download.
Installation (Python >= 3.12):
    py -m pip install requests beautifulsoup4 customtkinter matricula-online-scraper
Optional für PDFs:
    py -m pip install img2pdf
Start:
    py matricula-bestand5_2.py

Bestehende v4/v5.1 JSONs bleiben unverändert; Downloadstatus in SQLite.
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

# =====================================================================
# 6. Lokaler Downloadkatalog (SQLite) und Einzelbuch-Downloader
# =====================================================================
import hashlib
from contextlib import contextmanager
import importlib.util
import queue
import sqlite3
import subprocess
import sys

DATABASE_PATH = ROOTDIR / 'matricula-katalog.sqlite3'
DEFAULT_DOWNLOAD_ROOT = ROOTDIR / 'Matricula_Buecher'
IMAGE_EXT = {'.jpg', '.jpeg', '.png', '.webp', '.tif', '.tiff', '.jp2', '.j2k'}
DOWNLOAD_IDLE_TIMEOUT = 20 * 60  # Ein einzelnes Buch kann viele Seiten besitzen.


def book_identity(url):
    """Book URL normalisieren: '?pg=1' und Grund-URL haben dieselbe ID."""
    p = urlsplit(str(url or ''))
    if p.hostname != 'data.matricula-online.eu' or p.scheme not in ('http', 'https'):
        raise ValueError('Unzulässige Kirchenbuch-URL: ' + str(url))
    path = re.sub(r'/+', '/', p.path).rstrip('/') + '/'
    if len([s for s in path.split('/') if s]) < 5:
        raise ValueError('URL enthält keine vollständige Kirchenbuch-Signatur: ' + str(url))
    canonical = 'https://data.matricula-online.eu' + path
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest(), canonical


def safe_component(s, maximum=42):
    value = unicodedata.normalize('NFKD', str(s))
    value = ''.join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r'[^a-zA-Z0-9._-]+', '_', value).strip(' ._')
    return (value or 'Unbekannt')[:maximum].rstrip(' ._') or 'Unbekannt'


def item_record(land, archive, place, book):
    k, base = book_identity(book.get('url_base') or book.get('url'))
    return (k, base, land, archive['url'], archive['name'],
            place['url'], place['name'], str(book.get('signatur', '')),
            str(book.get('titel', '')), str(book.get('typ', '')),
            str(book.get('zeitraum', '')), str(book.get('url') or base + '?pg=1'))


class CatalogStore:
    """Metadaten und Downloadstatus getrennt, damit das 5.1-JSON unverändert bleibt."""
    def __init__(self, path=DATABASE_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript('''
              CREATE TABLE IF NOT EXISTS books (
                book_key TEXT PRIMARY KEY, canonical_url TEXT NOT NULL UNIQUE,
                land TEXT NOT NULL, archive_url TEXT NOT NULL, archive_name TEXT NOT NULL,
                place_url TEXT NOT NULL, place_name TEXT NOT NULL,
                signature TEXT, title TEXT, kind TEXT, date_range TEXT,
                viewer_url TEXT NOT NULL
              );
              CREATE INDEX IF NOT EXISTS ix_books_place ON books(place_url);
              CREATE INDEX IF NOT EXISTS ix_books_archive ON books(archive_url);
              CREATE TABLE IF NOT EXISTS downloads (
                book_key TEXT PRIMARY KEY REFERENCES books(book_key),
                status TEXT NOT NULL DEFAULT 'offen',
                folder TEXT, pages INTEGER NOT NULL DEFAULT 0,
                bytes INTEGER NOT NULL DEFAULT 0, error TEXT,
                changed_at TEXT NOT NULL, finished_at TEXT
              );
              CREATE TABLE IF NOT EXISTS image_files (
                book_key TEXT NOT NULL REFERENCES books(book_key),
                filename TEXT NOT NULL, size_bytes INTEGER NOT NULL,
                PRIMARY KEY(book_key,filename)
              );
              CREATE TABLE IF NOT EXISTS sources (
                land TEXT PRIMARY KEY, fingerprint TEXT NOT NULL,
                updated_at TEXT NOT NULL
              );
            ''')
            # Ein vorzeitig abgebrochener Prozess gilt nicht als vollständig.
            conn.execute("UPDATE downloads SET status='unterbrochen' WHERE status='laeuft'")

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(str(self.path), timeout=30)
        try:
            conn.execute('PRAGMA busy_timeout = 30000')
            conn.execute('PRAGMA journal_mode = WAL')
            conn.execute('PRAGMA foreign_keys = ON')
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    @staticmethod
    def fingerprint(land):
        src = list(output_paths(land)[:1]) + [journal_path(land)]
        bits = []
        for file in src:
            if file.exists():
                st = file.stat()
                bits.append(f'{file.name}:{st.st_size}:{st.st_mtime_ns}')
        return '|'.join(bits)

    def sync_catalog(self, data, force=False, callback=None):
        """Alle Metadaten upserten; Downloads und lokale Dateien NIE zurücksetzen."""
        land = data['land']
        fingerprint = self.fingerprint(land)
        with self.connect() as conn:
            old = conn.execute('SELECT fingerprint FROM sources WHERE land=?', (land,)).fetchone()
            if not force and old and old[0] == fingerprint:
                n = conn.execute('SELECT COUNT(*) FROM books WHERE land=?', (land,)).fetchone()[0]
                return n, False
            upsert = '''INSERT INTO books
             (book_key,canonical_url,land,archive_url,archive_name,place_url,place_name,
              signature,title,kind,date_range,viewer_url)
             VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
             ON CONFLICT(book_key) DO UPDATE SET
               canonical_url=excluded.canonical_url,land=excluded.land,
               archive_url=excluded.archive_url,archive_name=excluded.archive_name,
               place_url=excluded.place_url,place_name=excluded.place_name,
               signature=excluded.signature,title=excluded.title,kind=excluded.kind,
               date_range=excluded.date_range,viewer_url=excluded.viewer_url'''
            pending = []
            processed = skipped = 0
            for archive in data.get('archive', {}).values():
                for place in archive.get('orte', {}).values():
                    for book in place.get('buecher', {}).values():
                        try:
                            pending.append(item_record(land, archive, place, book))
                        except (ValueError, KeyError):
                            skipped += 1
                            continue
                        processed += 1
                        if len(pending) >= 1000:
                            conn.executemany(upsert, pending)
                            pending.clear()
                            if callback and processed % 15000 < 1000:
                                callback(f'SQLite-Katalog: {processed:,} Bücher verarbeitet…'.replace(',', '.'))
            if pending:
                conn.executemany(upsert, pending)
            conn.execute('INSERT INTO sources(land,fingerprint,updated_at) VALUES(?,?,?) '
                         'ON CONFLICT(land) DO UPDATE SET fingerprint=excluded.fingerprint, '
                         'updated_at=excluded.updated_at', (land, fingerprint, utcnow()))
            n = conn.execute('SELECT COUNT(*) FROM books WHERE land=?', (land,)).fetchone()[0]
        if callback and skipped:
            callback(f'{skipped} ungültige Buch-URLs beim SQLite-Import übersprungen.')
        return n, True

    def ensure_book(self, record):
        with self.connect() as conn:
            conn.execute('''INSERT INTO books
               (book_key,canonical_url,land,archive_url,archive_name,place_url,place_name,
               signature,title,kind,date_range,viewer_url)
               VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
               ON CONFLICT(book_key) DO UPDATE SET
                 archive_name=excluded.archive_name,place_name=excluded.place_name,
                 title=excluded.title,kind=excluded.kind,date_range=excluded.date_range,
                 viewer_url=excluded.viewer_url''', record)

    def get_download(self, key):
        with self.connect() as conn:
            conn.row_factory = sqlite3.Row
            r = conn.execute('SELECT * FROM downloads WHERE book_key=?', (key,)).fetchone()
            return dict(r) if r else None

    def get_statuses(self, keys):
        if not keys: return {}
        results = {}
        with self.connect() as conn:
            for i in range(0, len(keys), 250):
                batch = keys[i:i+250]
                placeholders = ','.join('?' for _ in batch)
                for key, status, pages in conn.execute(
                    f'SELECT book_key,status,pages FROM downloads WHERE book_key IN ({placeholders})', batch
                ):
                    results[key] = (status, pages)
        return results

    def set_download(self, key, status, folder=None, pages=0, size=0, error=None, done=False):
        with self.connect() as conn:
            conn.execute('''INSERT INTO downloads
                 (book_key,status,folder,pages,bytes,error,changed_at,finished_at)
                 VALUES(?,?,?,?,?,?,?,?)
                 ON CONFLICT(book_key) DO UPDATE SET status=excluded.status,
                   folder=excluded.folder,pages=excluded.pages,bytes=excluded.bytes,
                   error=excluded.error,changed_at=excluded.changed_at,
                   finished_at=excluded.finished_at''',
                 (key, status, str(folder) if folder else None, pages, size, error,
                  utcnow(), utcnow() if done else None))

    def register_files(self, key, folder, images):
        with self.connect() as conn:
            conn.execute('DELETE FROM image_files WHERE book_key=?', (key,))
            conn.executemany('INSERT INTO image_files(book_key,filename,size_bytes) VALUES(?,?,?)',
                             ((key, str(p.relative_to(folder)), p.stat().st_size) for p in images))

    def stats(self):
        with self.connect() as conn:
            books = conn.execute('SELECT COUNT(*) FROM books').fetchone()[0]
            done = conn.execute("SELECT COUNT(*) FROM downloads WHERE status='heruntergeladen'").fetchone()[0]
            pending = conn.execute("SELECT COUNT(*) FROM downloads WHERE status IN ('fehler','unterbrochen')").fetchone()[0]
        return books, done, pending

    def search_books(self, term, land=None, limit=200):
        """Suche nach Ort, Buchsignatur, Typ und Titel ohne den ganzen Baum aufzubauen.

        Gibt (item_record, downloadstatus, seitenzahl) zurück.
        """
        term = str(term or '').strip()
        if len(term) < 2:
            return []
        # Prozent/Unterstrich sind hier Suchtext, keine LIKE-Musterzeichen.
        escaped = term.replace('!', '!!').replace('%', '!%').replace('_', '!_')
        pattern = '%' + escaped + '%'
        sql = """SELECT b.book_key,b.canonical_url,b.land,b.archive_url,b.archive_name,
                    b.place_url,b.place_name,b.signature,b.title,b.kind,b.date_range,
                    b.viewer_url,COALESCE(d.status,'offen'),COALESCE(d.pages,0)
                 FROM books b LEFT JOIN downloads d ON d.book_key=b.book_key
                 WHERE (b.place_name LIKE ? ESCAPE '!' OR b.signature LIKE ? ESCAPE '!'
                    OR b.title LIKE ? ESCAPE '!' OR b.kind LIKE ? ESCAPE '!')"""
        args = [pattern]*4
        if land:
            sql += ' AND b.land=?'
            args.append(land)
        sql += ' ORDER BY b.place_name,b.signature LIMIT ?'
        args.append(max(1,min(500,int(limit))))
        with self.connect() as conn:
            return [(tuple(row[:12]),row[12],row[13]) for row in conn.execute(sql,args)]

    def export_downloads(self, dest):
        with self.connect() as conn, Path(dest).open('w', encoding='utf-8') as fh:
            fh.write('Land\tArchiv\tOrt\tSignatur\tTitel\tZeitraum\tURL\tStatus\tBilder\tBytes\tOrdner\tFehler\n')
            for row in conn.execute('''SELECT b.land,b.archive_name,b.place_name,b.signature,b.title,
                b.date_range,b.viewer_url,COALESCE(d.status,'offen'),COALESCE(d.pages,0),
                COALESCE(d.bytes,0),COALESCE(d.folder,''),COALESCE(d.error,'')
                FROM books b LEFT JOIN downloads d ON d.book_key=b.book_key
                ORDER BY b.land,b.archive_name,b.place_name,b.signature'''):
                fh.write('\t'.join(str(v).replace('\t',' ').replace('\r',' ').replace('\n',' ') for v in row)+'\n')


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def download_directory(root, record):
    key, _, land, _, archive, _, place, signature, *_ = record
    return (Path(root) / safe_component(land, 25) /
            safe_component(archive, 43) / safe_component(place, 43) /
            f'{safe_component(signature, 24)}_{key[:12]}')


def valid_image(path):
    try:
        if path.stat().st_size < 16: return False
        with path.open('rb') as fh: head = fh.read(20)
        return (head.startswith(b'\xff\xd8\xff') or head.startswith(b'\x89PNG\r\n\x1a\n') or
                head.startswith((b'II*\x00', b'MM\x00*')) or
                (head.startswith(b'RIFF') and head[8:12] == b'WEBP') or
                head.startswith(b'\x00\x00\x00\x0cjP  \r\n\x87\n') or
                head.startswith(b'\xff\x4f\xff\x51'))
    except OSError:
        return False


def list_images(folder):
    p = Path(folder)
    if not p.is_dir(): return []
    return sorted((f for f in p.rglob('*') if f.is_file() and f.suffix.casefold() in IMAGE_EXT
                   and valid_image(f)), key=lambda x: str(x).casefold())


def cli_command():
    exe = shutil.which('matricula-online-scraper')
    if exe: return [exe]
    if importlib.util.find_spec('matricula_online_scraper'):
        return [sys.executable, '-m', 'matricula_online_scraper']
    raise RuntimeError('Downloader nicht installiert. Bitte in PowerShell ausführen:\n'
                       'py -m pip install -U matricula-online-scraper')


def terminate_process(proc):
    if proc and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=6)
        except subprocess.TimeoutExpired:
            proc.kill()
        except OSError:
            pass


def download_one(record, root, catalog, stop_event, post, set_process):
    """Lädt ein einzelnes, bewusst gewähltes Buch in isolierten Arbeitsordner."""
    key, base = record[:2]
    folder = download_directory(root, record)
    final = folder / 'bilder'
    partial = folder / '.teilweise'
    manifest = folder / 'manifest.json'
    folder.mkdir(parents=True, exist_ok=True)
    if manifest.exists() and list_images(final):
        images = list_images(final)
        catalog.register_files(key, final, images)
        catalog.set_download(key, 'heruntergeladen', final, len(images),
                             sum(p.stat().st_size for p in images), done=True)
        return f'Bereits vorhanden: {len(images)} Bilddateien'
    if final.exists():
        raise RuntimeError('Zielordner „bilder“ existiert ohne gültiges Manifest. '
                           'Bitte Dateien prüfen, nichts wird überschrieben: ' + str(final))
    partial.mkdir(parents=True, exist_ok=True)
    catalog.set_download(key, 'laeuft', partial)
    post('log', f'Start: {record[6]} / {record[7]} → {folder}')
    cmd = cli_command() + ['parish', 'fetch', record[-1], '-o', str(partial)]
    proc = None
    output = queue.Queue()
    try:
        if stop_event.is_set(): raise InterruptedError('Download vom Benutzer angehalten')
        proc = subprocess.Popen(cmd, cwd=str(folder), stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                text=True, encoding='utf-8', errors='replace', bufsize=1)
        set_process(proc)
        def forward_output():
            try:
                for line in proc.stdout:
                    output.put(line.rstrip())
            finally:
                output.put(None)
        threading.Thread(target=forward_output, daemon=True).start()
        last_activity = time.monotonic()
        eof = False
        while True:
            if stop_event.is_set(): raise InterruptedError('Download vom Benutzer angehalten')
            if time.monotonic() - last_activity > DOWNLOAD_IDLE_TIMEOUT:
                raise TimeoutError('Downloader hat seit 20 Minuten keine Ausgabe geliefert.')
            try:
                line = output.get(timeout=0.5)
                if line is None:
                    eof = True
                elif line:
                    last_activity = time.monotonic()
                    if re.search(r'(HTTP\s*(403|429)|\b403\s+Forbidden\b|\b429\s+Too Many Requests\b)', line, re.I):
                        raise PermissionError('Server blockiert den Download (403/429). Keine Wiederholung.')
                    match = re.search(r'(\d+)\s*/\s*(\d+)', line)
                    if match: post('progress', (int(match.group(1)), int(match.group(2))))
                    post('log', line[:250])
            except queue.Empty:
                pass
            if eof and proc.poll() is not None and output.empty(): break
        code = proc.wait(timeout=15)
        if code != 0:
            raise RuntimeError(f'Downloader meldet Exit-Code {code}. Teildaten bleiben erhalten.')
        imgs = list_images(partial)
        if not imgs:
            raise RuntimeError('Downloader beendete sich ohne Fehler, aber keine gültigen Bilder gefunden.')
        if stop_event.is_set(): raise InterruptedError('Download vom Benutzer angehalten')
        partial.rename(final)
        imgs = list_images(final)
        total_bytes = sum(p.stat().st_size for p in imgs)
        manifest_data = {'buch_url': base, 'viewer_url': record[-1], 'buch_key': key,
                         'land': record[2], 'archiv': record[4], 'ort': record[6],
                         'signatur': record[7], 'status': 'heruntergeladen',
                         'bilder': len(imgs), 'bytes': total_bytes, 'zeit': utcnow(),
                         'quelle': 'matricula-online-scraper parish fetch'}
        atomic_json(manifest, manifest_data)
        catalog.register_files(key, final, imgs)
        catalog.set_download(key, 'heruntergeladen', final, len(imgs), total_bytes, done=True)
        return f'{len(imgs)} Bilder ({total_bytes/1024/1024:.1f} MiB) gespeichert'
    except Exception as exc:
        status = 'unterbrochen' if isinstance(exc, InterruptedError) else 'fehler'
        catalog.set_download(key, status, partial, error=str(exc))
        raise
    finally:
        terminate_process(proc)
        set_process(None)


ctk.set_appearance_mode('Dark')
ctk.set_default_color_theme('blue')


class Browser(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title('Matricula Bestandsbrowser 5.2 · Bestände & Downloads')
        self.geometry('1360x970')
        self.minsize(1080, 760)
        self.parser = Scraper()
        self.data = None
        self.catalog = CatalogStore()
        self.catalog_busy = False
        self.download_busy = False
        self.pdf_busy = False
        self.download_terms_ack = False
        self.download_events = queue.Queue()
        self.download_stop = threading.Event()
        self.active_process = None
        self.proc_lock = threading.Lock()
        self.download_root = tk.StringVar(value=str(self._local_config().get(
            'download_root', DEFAULT_DOWNLOAD_ROOT)))
        self.tree_meta = {}
        self.main = ctk.CTkFrame(self)
        self.main.pack(fill='both', expand=True, padx=12, pady=12)
        ctk.CTkLabel(self.main,
            text='🏛️ Matricula 5.2 · Bestandsbrowser + Buch-Downloads',
            font=ctk.CTkFont(size=22, weight='bold')).pack(anchor='w', padx=12, pady=(10, 2))
        ctk.CTkLabel(self.main,
            text='Bestandsscan maximal 25 Orte pro Paket · Manuelle Einzelbuch-Downloads · SQLite speichert Downloadstatus.',
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
        self.btn_db_sync = ctk.CTkButton(actions, text='🗃 SQLite abgleichen',
                                          command=lambda: self.request_catalog_sync(force=True), width=145)
        self.btn_db_sync.pack(side='right', padx=4)

        search_frame = ctk.CTkFrame(self.main, fg_color='transparent')
        search_frame.pack(fill='x', padx=12, pady=(2, 3))
        self.quick_search = ctk.CTkEntry(search_frame,
            placeholder_text='Buchsuche in SQLite: Ort, Signatur oder Titel (z. B. Peißenberg, 01-01D)')
        self.quick_search.pack(side='left', fill='x', expand=True, padx=(0, 6))
        self.quick_search.bind('<Return>', lambda _event: self.find_book())
        ctk.CTkButton(search_frame, text='🔎 Bücher suchen', width=145,
                      command=self.find_book).pack(side='left', padx=(0, 6))
        ctk.CTkButton(search_frame, text='↩ Verzeichnis', width=130,
                      command=self.refresh_tree).pack(side='left')

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
        self.details = ctk.CTkTextbox(self.main, height=62)
        self.details.pack(fill='x', padx=12, pady=4)

        dl = ctk.CTkFrame(self.main)
        dl.pack(fill='x', padx=12, pady=(2, 4))
        dl.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(dl, text='Speicherort für Kirchenbücher:', anchor='w').grid(
            row=0, column=0, columnspan=3, sticky='w', padx=8, pady=(7, 0))
        ctk.CTkEntry(dl, textvariable=self.download_root).grid(
            row=1, column=0, columnspan=3, sticky='ew', padx=8, pady=(2, 6))
        ctk.CTkButton(dl, text='📁 Ziel wählen', width=115,
                      command=self.choose_download_dir).grid(row=1, column=3, padx=8, pady=(2, 6))
        self.btn_download = ctk.CTkButton(dl, text='⬇ Ausgewähltes Buch herunterladen',
            command=self.download_selected, fg_color='#227d4c', hover_color='#1e633d', width=245)
        self.btn_download.grid(row=2, column=0, padx=8, pady=(2, 6), sticky='w')
        ctk.CTkButton(dl, text='📂 Ordner öffnen', command=self.open_download_folder,
                      width=140).grid(row=2, column=1, padx=5, pady=(2, 6))
        ctk.CTkButton(dl, text='🔎 Dateien prüfen', command=self.verify_selected_download,
                      width=130).grid(row=2, column=2, padx=5, pady=(2, 6))
        ctk.CTkButton(dl, text='📄 Buch als PDF', command=self.make_selected_pdf,
                      width=130).grid(row=2, column=3, padx=8, pady=(2, 6))
        self.download_stats = ctk.CTkLabel(dl, text='SQLite-Katalog wird vorbereitet…', anchor='w')
        self.download_stats.grid(row=3, column=0, columnspan=4, sticky='ew', padx=8, pady=(1, 5))
        pb = ctk.CTkFrame(self.main, fg_color='transparent')
        pb.pack(fill='x', padx=12, pady=0)
        self.download_progress = ctk.CTkProgressBar(pb)
        self.download_progress.pack(side='left', fill='x', expand=True)
        self.download_progress.set(0)
        self.download_progress_label = ctk.CTkLabel(pb, text='Download bereit.', width=225)
        self.download_progress_label.pack(side='right', padx=6)
        self.download_log = ctk.CTkTextbox(self.main, height=72, font=('Consolas', 11))
        self.download_log.pack(fill='x', padx=12, pady=(2, 3))
        self.download_log.configure(state='disabled')
        bottom = ctk.CTkFrame(self.main, fg_color='transparent')
        bottom.pack(fill='x', padx=12, pady=4)
        ctk.CTkButton(bottom, text='📋 Ausgewählte URL kopieren',
                      command=self.copy_url, width=230).pack(side='left', padx=3)
        ctk.CTkButton(bottom, text='📑 Downloadstatus exportieren',
                      command=self.export_catalog_with_status, width=235).pack(side='left', padx=4)
        ctk.CTkButton(bottom, text='❓ Bedienung / Hinweise',
                      command=self.help, width=200).pack(side='right', padx=3)
        self.stat = ctk.CTkLabel(self.main, text='', anchor='w')
        self.stat.pack(fill='x', padx=15, pady=(2, 7))
        self.load_local()
        self.on_region(REGION_PROMPT)
        self.refresh_catalog_stats()
        self.after(180, self.process_download_events)
        self.after(550, self.request_catalog_sync)
        self.protocol('WM_DELETE_WINDOW', self.on_close)

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
        self.after(100, self.request_catalog_sync)
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

    def find_book(self):
        if self.catalog_busy:
            messagebox.showinfo('SQLite-Katalog', 'Der Katalog wird gerade aufgebaut. Suche danach erneut.')
            return
        term = self.quick_search.get().strip()
        if len(term) < 2:
            messagebox.showinfo('Buchsuche', 'Bitte mindestens zwei Zeichen eingeben.')
            return
        try:
            matches = self.catalog.search_books(term, land=self.land.get(), limit=200)
        except Exception as exc:
            messagebox.showerror('SQLite-Buchsuche', str(exc))
            return
        roots = self.tree.get_children()
        if roots:
            self.tree.delete(*roots)
        self.tree_meta.clear()
        parent = self.tree.insert('', 'end', text=f'Suchergebnisse: {term} · {len(matches)} Buch/Bücher',
                                  values=('maximal 200 Treffer', ''), open=True)
        for record, state, pages in matches:
            label = f'{record[6]} · {record[7]} · {record[8]}'
            child = self.tree.insert(parent,'end',text=label,
                values=(self.book_status_label({'status':state,'pages':pages}),record[-1]))
            self.tree_meta[child] = ('db_book',None,record)
        self.say(f'Buchsuche „{term}“: {len(matches)} Treffer (maximal 200).')

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
            books = sorted(place.get('buecher', {}).items(),
                           key=lambda item: item[1].get('signatur', ''))
            keys = []
            for b_url, b in books:
                try: keys.append(book_identity(b.get('url_base') or b.get('url'))[0])
                except ValueError: pass
            statuses = self.catalog.get_statuses(keys)
            for b_url, b in books:
                try:
                    key = book_identity(b.get('url_base') or b.get('url'))[0]
                    state = statuses.get(key)
                    status = self.book_status_label(
                        {'status': state[0], 'pages': state[1]} if state else None)
                except ValueError:
                    status = '⚠ URL ungültig'
                bid = self.tree.insert(row, 'end',
                       text=f"{b.get('signatur','')} · {b.get('titel','')}",
                       values=(status, b.get('url', '')))
                self.tree_meta[bid] = ('book', region, (archive_url, place_url, b_url))

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
        description = f"{item['text']}\n" + ' | '.join(map(str, item.get('values', [])))
        book = self._selected_book()
        if book:
            d = self.catalog.get_download(book[0])
            description += f'\nSignatur: {book[7]} | Zeitraum: {book[10]} | URL: {book[-1]}'
            if d:
                description += (f"\nDownload: {d['status']} | Bilder: {d['pages']}"
                                f" | Ordner: {d['folder']}"
                                f" | Fehler: {d['error'] or '-'}")
            else:
                description += '\nDownload: noch nicht heruntergeladen'
        self.details.insert('1.0', description)

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
        if hasattr(self, 'btn_download'):
            self.btn_download.configure(state='disabled' if busy or self.catalog_busy else 'normal')
        if hasattr(self, 'btn_db_sync'):
            self.btn_db_sync.configure(state='disabled' if busy or self.catalog_busy else 'normal')
        for widget in (self.land, self.region, self.archive):
            widget.configure(state='disabled' if busy else 'normal')

    def _start_worker(self, work, only_index=False):
        if self.catalog_busy or self.download_busy or self.pdf_busy:
            messagebox.showwarning('Andere Aufgabe', 'Bitte die laufende SQLite- oder Downloadaufgabe beenden.')
            return
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
        if self.download_busy:
            self.stop_download()
            return
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
        self.after(150, self.request_catalog_sync)
        if error:
            self.say('Unterbrochen: ' + error)
            messagebox.showwarning('Scan unterbrochen', error)
        else:
            self.say('Index geladen.' if only_index else 'Paket erledigt und JSON/TXT gespeichert.')

    def help(self):
        messagebox.showinfo('Matricula 5.2 · Scan und Download',
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
            'Bei HTTP 403/429 wird gestoppt; keine Umgehung von Sperren.\n\n'
            '9. Zum Download ein Kirchenbuch im Baum anklicken und den grünen Button nutzen.\n'
            '10. SQLite merkt sich Downloadstatus und die Bilddateien pro Buch.\n'
            '11. PDF optional aus den bereits geladenen Bildern erstellen.\n'
            '12. PNG/JPG/TIFF Dateien liegen in Matricula_Buecher, nicht in SQLite.\n'
            '13. Die Schnellsuche findet Kirchenbücher auch ohne Aufklappen der Archivstruktur.\n'
            '14. Downloadstatus werden im SQLite-Katalog gespeichert, nicht im Bestands-JSON.')


    # -----------------------------------------------------------------
    # SQLite + Downloads (bewusste Einzelauswahl, kein Massendownload)
    # -----------------------------------------------------------------
    def _selected_book(self):
        info = self.tree_meta.get(self.tree.focus())
        if not info or not self.data:
            return None
        if info[0] == 'db_book':
            return info[2]
        if info[0] != 'book':
            return None
        archive_url, place_url, book_url = info[2]
        try:
            archive = self.data['archive'][archive_url]
            place = archive['orte'][place_url]
            book = place['buecher'][book_url]
            return item_record(self.data['land'], archive, place, book)
        except (KeyError, ValueError):
            return None

    def _local_config(self):
        config_path = ROOTDIR / 'matricula-local-config.json'
        try:
            raw = json.loads(config_path.read_text(encoding='utf-8'))
            return raw if isinstance(raw, dict) else {}
        except (OSError, ValueError):
            return {}

    def choose_download_dir(self):
        folder = filedialog.askdirectory(title='Ordner für heruntergeladene Kirchenbücher',
                                        initialdir=self.download_root.get())
        if folder:
            self.download_root.set(folder)
            atomic_json(ROOTDIR / 'matricula-local-config.json',
                        {'download_root': folder})

    def log_download(self, msg):
        self.download_log.configure(state='normal')
        self.download_log.insert('end', str(msg).strip() + '\n')
        # Log klein halten, damit die GUI bei sehr langen Buchdownloads flüssig bleibt.
        if int(self.download_log.index('end-1c').split('.')[0]) > 400:
            self.download_log.delete('1.0', '160.0')
        self.download_log.see('end')
        self.download_log.configure(state='disabled')

    def post_download(self, kind, payload):
        self.download_events.put((kind, payload))

    def process_download_events(self):
        try:
            for _ in range(75):
                kind, payload = self.download_events.get_nowait()
                if kind == 'log':
                    self.log_download(payload)
                elif kind == 'progress':
                    a, b = payload
                    if b > 0:
                        self.download_progress.set(min(1, max(0, a/b)))
                        self.download_progress_label.configure(text=f'{a}/{b} Seiten (CLI-Angabe)')
                elif kind == 'status':
                    self.download_progress_label.configure(text=str(payload))
                elif kind == 'download_finished':
                    ok, detail, key, row = payload
                    self.download_busy = False
                    self.active_process = None
                    self.set_busy(False)
                    self.download_progress_label.configure(
                        text=('Heruntergeladen ✓' if ok else 'Unterbrochen / Fehler'))
                    if ok:
                        self.download_progress.set(1)
                    status = self.catalog.get_download(key)
                    # Während des Downloads darf die Suche/Ansicht gewechselt werden.
                    # Keine neue Baumzeile mit einer eventuell wiederverwendeten Tree-ID markieren.
                    selected_row_record = self._selected_book() if self.tree.focus() == row else None
                    if selected_row_record and selected_row_record[0] == key and self.tree.exists(row):
                        self.tree.set(row, 'status', self.book_status_label(status))
                        self.show_detail()
                    self.log_download(('✓ ' if ok else '⚠ ') + detail)
                    self.refresh_catalog_stats()
                    if not ok:
                        messagebox.showwarning('Kirchenbuchdownload', detail)
                elif kind == 'sync_finished':
                    self.catalog_busy = False
                    self.btn_db_sync.configure(state='normal')
                    self.btn_download.configure(state='normal' if not self.download_busy else 'disabled')
                    self.refresh_catalog_stats()
                    self.log_download(payload)
                    self.say(payload)
                elif kind == 'pdf_finished':
                    ok, detail = payload
                    self.pdf_busy = False
                    self.set_busy(False)
                    self.log_download(('✓ ' if ok else '⚠ ') + detail)
                    self.download_progress_label.configure(text=('PDF fertig' if ok else 'PDF-Fehler'))
        except queue.Empty:
            pass
        self.after(120, self.process_download_events)

    @staticmethod
    def book_status_label(download):
        if not download: return '⬇ offen'
        state = download['status']
        if state == 'heruntergeladen':
            return f"✓ heruntergeladen ({download.get('pages', 0)} Bilder)"
        if state == 'laeuft': return '⏳ lädt…'
        if state == 'unterbrochen': return '⏸ unterbrochen'
        if state == 'fehler': return '✕ Fehler'
        if state == 'dateien_fehlen': return '! Dateien fehlen'
        return state

    def refresh_catalog_stats(self):
        try:
            total, done, errors = self.catalog.stats()
            self.download_stats.configure(text=(
                f'SQLite: {total:,} Bücher | {done:,} heruntergeladen | '
                f'{errors:,} Fehler/Abbrüche'.replace(',', '.')))
        except Exception as exc:
            self.download_stats.configure(text='SQLite-Fehler: ' + str(exc))

    def request_catalog_sync(self, force=False):
        if self.catalog_busy or self.download_busy or self.pdf_busy or not self.data:
            return
        self.catalog_busy = True
        self.btn_db_sync.configure(state='disabled')
        self.btn_download.configure(state='disabled')
        data = self.data
        def worker():
            try:
                total, changed = self.catalog.sync_catalog(
                    data, force, lambda s: self.post_download('status', s))
                message = (f'{total:,} Bücher in SQLite, '
                           f'{"Katalog aktualisiert" if changed else "bereits aktuell"}').replace(',', '.')
            except Exception as exc:
                message = 'SQLite-Synchronisierung fehlgeschlagen: ' + str(exc)
            self.download_events.put(('sync_finished', message))
        threading.Thread(target=worker, daemon=True).start()

    def download_selected(self):
        if self.download_busy or self.catalog_busy or self.pdf_busy or self.btn_scan.cget('state') == 'disabled':
            messagebox.showwarning('Download', 'Aktuell läuft eine andere Aufgabe.')
            return
        record = self._selected_book()
        if not record:
            messagebox.showinfo('Buch auswählen',
                'Bitte im Verzeichnisbaum einen Ort aufklappen und EIN Kirchenbuch anklicken.')
            return
        key = record[0]
        self.catalog.ensure_book(record)
        previous = self.catalog.get_download(key)
        if previous and previous['status'] == 'heruntergeladen':
            folder = Path(previous['folder'] or '')
            if list_images(folder):
                messagebox.showinfo('Bereits heruntergeladen',
                    f'Dieses Buch ist bereits katalogisiert ({previous["pages"]} Bilder).\n\n{folder}')
                return
            self.catalog.set_download(key, 'dateien_fehlen', folder,
                                      error='Registrierter Zielordner enthält keine lesbaren Bilder.')
        if not self.download_terms_ack:
            consent = messagebox.askyesno('Matricula Nutzungsbedingungen',
                'Kirchenbuchbilder dürfen nur im Rahmen der aktuellen Matricula-'
                'Nutzungsbedingungen und geltenden Gesetze verwendet werden.\n\n'
                'Dieses Programm startet ausschließlich den von dir gewählten '
                'Einzelbuch-Download. Es umgeht keine Zugangssperren.\n\n'
                'Hast du die Bedingungen geprüft und möchtest du fortfahren?')
            if not consent: return
            self.download_terms_ack = True
        if not messagebox.askyesno('Einzelnes Kirchenbuch herunterladen',
                                   f'{record[4]}\n{record[6]}\n{record[7]} · {record[8]}\n'
                                   f'{record[10]}\n\nDownload wirklich starten?'):
            return
        self.download_stop.clear()
        self.download_busy = True
        self.set_busy(True)
        self.download_progress.set(0)
        self.download_progress_label.configure(text='Download läuft…')
        self.download_row = self.tree.focus()
        row = self.download_row
        self.log_download('––––––––––––––––––––––––––––')
        def worker():
            try:
                # Matricula-Sperren respektieren, bevor der externe Downloader startet.
                self.parser.robots_check()
                if not self.parser.robot.can_fetch(self.parser.ua, record[-1]):
                    raise PermissionError('robots.txt untersagt diesen Abruf.')
                result = download_one(record, self.download_root.get(), self.catalog,
                                      self.download_stop, self.post_download,
                                      self._remember_process)
                self.post_download('download_finished', (True, result, key, row))
            except Exception as exc:
                # Auch einen abgewiesenen Vorab-Check im Downloadkatalog dokumentieren.
                try:
                    previous_state = self.catalog.get_download(key)
                    if not previous_state or previous_state['status'] not in ('fehler','unterbrochen'):
                        self.catalog.set_download(key, 'fehler', error=str(exc))
                except Exception:
                    pass
                self.post_download('download_finished', (False, str(exc), key, row))
        threading.Thread(target=worker, daemon=True).start()

    def _remember_process(self, proc):
        with self.proc_lock:
            self.active_process = proc

    def stop_download(self):
        self.download_stop.set()
        with self.proc_lock:
            proc = self.active_process
        if proc:
            # Nicht im UI-Thread auf einen möglicherweise blockierenden Prozess warten.
            threading.Thread(target=terminate_process, args=(proc,), daemon=True).start()
        self.log_download('⏹ Abbruch angefordert. Bereits vorhandene Teildateien bleiben erhalten.')

    def open_download_folder(self):
        record = self._selected_book()
        if not record:
            messagebox.showinfo('Buch auswählen', 'Bitte ein Kirchenbuch auswählen.')
            return
        info = self.catalog.get_download(record[0])
        path = Path(info['folder']) if info and info.get('folder') else download_directory(
            self.download_root.get(), record)
        if not path.exists():
            messagebox.showinfo('Noch nicht heruntergeladen', str(path))
            return
        if sys.platform.startswith('win'):
            os.startfile(str(path))
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', str(path)])
        else:
            subprocess.Popen(['xdg-open', str(path)])

    def verify_selected_download(self):
        record = self._selected_book()
        if not record: return
        data = self.catalog.get_download(record[0])
        if not data:
            messagebox.showinfo('Dateiprüfung', 'Dieses Buch wurde noch nicht heruntergeladen.')
            return
        folder = Path(data['folder']) if data.get('folder') else None
        images = list_images(folder) if folder else []
        if not images:
            self.catalog.set_download(record[0], 'dateien_fehlen', folder,
                                      error='Keine Bilddateien im registrierten Zielordner.')
            messagebox.showwarning('Dateiprüfung', 'Keine gültigen Bilddateien gefunden.')
        else:
            messagebox.showinfo('Dateiprüfung',
                f'{len(images)} gültige Bilddateien gefunden.\n'
                'Hinweis: Eine vollständige Seitennummernfolge kann damit nicht garantiert werden.')
        row = self.tree.focus()
        if row:
            self.tree.set(row, 'status', self.book_status_label(self.catalog.get_download(record[0])))
        self.show_detail()
        self.refresh_catalog_stats()

    def export_catalog_with_status(self):
        target = filedialog.asksaveasfilename(title='Katalog mit Downloadstatus exportieren',
                  initialfile='matricula-downloadstatus.tsv', defaultextension='.tsv',
                  filetypes=[('Tabellen als TXT/TSV', '*.tsv'), ('Textdatei', '*.txt')])
        if target:
            try:
                self.catalog.export_downloads(target)
                self.say('Downloadstatus exportiert: ' + target)
            except Exception as exc:
                messagebox.showerror('Exportfehler', str(exc))

    def make_selected_pdf(self):
        if self.download_busy or self.pdf_busy or self.catalog_busy or self.btn_scan.cget('state') == 'disabled':
            return
        record = self._selected_book()
        if not record: return
        previous = self.catalog.get_download(record[0])
        if not previous or previous['status'] != 'heruntergeladen':
            messagebox.showinfo('PDF', 'Bitte dieses Buch zuerst vollständig herunterladen.')
            return
        files = list_images(previous['folder'])
        if not files:
            messagebox.showwarning('PDF', 'Keine gültigen Bilddateien gefunden.')
            return
        try:
            import img2pdf
        except ImportError:
            messagebox.showwarning('PDF-Modul fehlt',
                'Für PDF-Dateien: py -m pip install img2pdf')
            return
        target = filedialog.asksaveasfilename(
            title='PDF für dieses Kirchenbuch speichern',
            initialfile=safe_component(record[7] + '_' + record[8], 65) + '.pdf',
            initialdir=str(Path(previous['folder']).parent),
            defaultextension='.pdf', filetypes=[('PDF-Datei', '*.pdf')])
        if not target: return
        self.pdf_busy = True
        self.set_busy(True)
        def worker():
            tmp = Path(target + '.tmp')
            try:
                with tmp.open('wb') as out:
                    img2pdf.convert(*(str(p) for p in files), outputstream=out)
                tmp.replace(target)
                self.post_download('pdf_finished', (True, f'PDF erstellt: {target}'))
            except Exception as exc:
                tmp.unlink(missing_ok=True)
                self.post_download('pdf_finished', (False, 'PDF fehlgeschlagen: ' + str(exc)))
        threading.Thread(target=worker, daemon=True).start()

    def on_close(self):
        if self.download_busy or self.pdf_busy or self.btn_scan.cget('state') == 'disabled':
            if not messagebox.askyesno('Programm schließen',
                                       'Es läuft noch eine Aufgabe. Wirklich abbrechen und schließen?'):
                return
            self.parser.stop.set()
            self.stop_download()
        self.destroy()


if __name__ == '__main__':
    Browser().mainloop()
