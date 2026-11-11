# -*- coding: utf-8 -*-
"""Matricula Bestandsbrowser v5 – nur Bestandsmetadaten, keine Buchbilder.
Installation: py -m pip install requests beautifulsoup4 customtkinter
Start: py matricula-bestand4.py
"""
import json
import re
import threading
import time
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


# Gruppierungen sind nur praktische Archivfilter: Diözesangrenzen != Ländergrenzen.
REGION_GROUPS = {
 'Österreich': {
    'Kärnten': ['Kärnten:'], 'Wien / Niederösterreich': ['Wien','Niederösterreich:','Niederösterreich ('],
    'Oberösterreich': ['Oberösterreich:'], 'Steiermark': ['Steiermark:'],
    'Salzburg': ['Salzburg:'], 'Tirol': ['Tirol:'], 'Vorarlberg': ['Vorarlberg:'],
    'Burgenland': ['Burgenland:'], 'Überregionale Archive': ['Altösterreich','Metropolis']
 },
 'Deutschland': {
    'Bayern (Archivgruppe)': ['Augsburg','Bamberg','Eichstätt','München und Freising','Passau','Regensburg','Würzburg'],
    'Baden-Württemberg (Archivgruppe)': ['Landesarchiv Baden-Württemberg','Rottenburg-Stuttgart'],
    'Nordrhein-Westfalen (Archivgruppe)': ['Aachen','Essen,','Münster,','Paderborn'],
    'Hessen (Archivgruppe)': ['Fulda','Limburg','Mainz'],
    'Niedersachsen (Archivgruppe)': ['Hildesheim','Osnabrück','Vechta'],
    'Sachsen (Archivgruppe)': ['Dresden-Meißen'],
    'Sachsen-Anhalt (Archivgruppe)': ['Magdeburg'],
    'Berlin / überregional (Archivgruppe)': ['Berlin','Geheimes Staatsarchiv'],
    'Rheinland-Pfalz (Archivgruppe)': ['Rheinland,']
 }
}
# Nur Großstädte >= ca. 500k (Stand 2026, Auswahlhilfe, keine geographisch vollständige Suche).
CITIES = {
 'Deutschland': ['Berlin','Hamburg','München','Köln','Frankfurt am Main','Stuttgart','Düsseldorf','Leipzig',
                 'Dortmund','Essen','Bremen','Dresden','Hannover','Nürnberg','Duisburg'],
 'Österreich': ['Wien'],
 'Polen': ['Warschau','Krakau','Łódź','Wrocław','Poznań'],
 'Italien': ['Rom','Mailand','Neapel','Turin','Palermo','Genua'],
 'Serbien': ['Belgrad'],
}
CITY_ALIASES = {
 'München': ['münchen','muenchen'], 'Köln':['köln','koeln'], 'Nürnberg':['nürnberg','nuernberg'],
 'Wien':['wien','vienna'], 'Berlin':['berlin'], 'Hamburg':['hamburg'],
 'Frankfurt am Main':['frankfurt'], 'Düsseldorf':['düsseldorf','duesseldorf'],
 'Warschau':['warszawa','warschau'], 'Krakau':['kraków','krakau'],
 'Łódź':['łódź','lodz'], 'Wrocław':['wrocław','breslau'], 'Poznań':['poznań','posen'],
 'Gdańsk':['gdańsk','danzig'], 'Rom':['roma','rom'], 'Mailand':['milano','mailand'],
 'Neapel':['napoli','neapel'], 'Turin':['torino','turin'], 'Genua':['genova','genua'],
 'Belgrad':['beograd','belgrad'], 'Novi Sad':['novi sad']
}
BATCH_SIZE=25

def groups_for(land):
    return ['Alle Regionen / Archivgruppen'] + list(REGION_GROUPS.get(land, {}))

def archive_in_region(land, name, region):
    if region=='Alle Regionen / Archivgruppen':return True
    return any(name.casefold().startswith(s.casefold()) for s in REGION_GROUPS.get(land,{}).get(region,[]))

def choose_archive_items(items, land, region, archive):
    out=[]
    for url,name in items:
        if not archive_in_region(land,name,region):continue
        if archive != 'Alle Archive' and archive.casefold() not in (name.casefold(),parts(url)[-1].casefold()):continue
        out.append((url,name))
    return out

def batch_list(urls, size=BATCH_SIZE):
    return [(i//size+1, i, urls[i:i+size]) for i in range(0,len(urls),size)]

def names_match_city(name,city):
    if city=='Alle Orte':return True
    search=name.casefold()
    return any(re.search(r'(?<!\w)'+re.escape(alias.casefold())+r'(?!\w)',search) for alias in CITY_ALIASES.get(city,[city.casefold()]))

class Scraper:
    def __init__(self,delay=3.5):
        self.delay=max(3.5,float(delay)); self.stop=threading.Event()
        self.session=requests.Session()
        self.ua='MatriculaBestandsbrowser/5.0 (private genealogical metadata index)'
        self.session.headers.update({'User-Agent':self.ua,'Accept-Language':'de,en;q=0.8'})
        self.last=0
        self.robot=RobotFileParser();self.robot.set_url(ROOT+'/robots.txt');self.robots_checked=False

    def robots_check(self):
        if not self.robots_checked:
            try:
                r=self.session.get(ROOT+'/robots.txt',timeout=20)
                if r.status_code in (403,429):raise PermissionError(f'robots.txt: HTTP {r.status_code}')
                if r.status_code!=200:raise RuntimeError(f'robots.txt: HTTP {r.status_code}')
                self.robot.parse(r.text.splitlines())
            except requests.RequestException as exc:raise RuntimeError(f'robots.txt nicht erreichbar: {exc}') from exc
            self.robots_checked=True

    def get(self,url):
        if self.stop.is_set():raise InterruptedError('Scan gestoppt')
        self.robots_check()
        if not self.robot.can_fetch(self.ua,url):raise PermissionError(f'robots.txt untersagt Zugriff: {url}')
        for attempt in range(3):
            wait=self.delay-(time.monotonic()-self.last)
            if wait>0 and self.stop.wait(wait):raise InterruptedError('Scan gestoppt')
            self.last=time.monotonic()
            try:r=self.session.get(url,timeout=(10,30))
            except requests.RequestException as exc:
                if attempt==2:raise RuntimeError(f'Netzwerkfehler {url}: {exc}') from exc
                if self.stop.wait(8*(attempt+1)):raise InterruptedError('Scan gestoppt')
                continue
            if r.status_code in (403,429):raise PermissionError(f'HTTP {r.status_code} bei {url}; Scan angehalten')
            if r.status_code in (500,502,503,504):
                if attempt==2:raise RuntimeError(f'HTTP {r.status_code} bei {url}')
                if self.stop.wait(8*(attempt+1)):raise InterruptedError('Scan gestoppt')
                continue
            r.raise_for_status();return BeautifulSoup(r.text,'html.parser')
        raise RuntimeError('Unbekannter HTTP-Fehler')

    def pages(self,base):
        queue=deque([base]);seen=set()
        while queue:
            current=queue.popleft()
            if current in seen:continue
            if len(seen)>=200:raise RuntimeError('Zu viele Seiten / Schleifenverdacht: '+base)
            seen.add(current)
            soup=self.get(current); yield soup
            for a in page_content(soup).select('a[href]'):
                target=urljoin(current,a['href']);p=urlsplit(target)
                if p.netloc!=urlsplit(base).netloc or p.path.rstrip('/')!=urlsplit(base).path.rstrip('/'):continue
                q=parse_qs(p.query)
                if not any(k in q for k in ('page','p')):continue
                if target not in seen and target not in queue:queue.append(target)

    def load_data(self,land):
        j,_,_=output_paths(land)
        if j.exists():
            d=json.loads(j.read_text(encoding='utf-8'))
            if d.get('version') not in (4,5) or d.get('land')!=land or 'archive' not in d:
                raise RuntimeError('Bestehende JSON-Datei hat ein unerwartetes Format: '+str(j))
            # Wichtig: das Format der bestehenden v4-Daten nicht zerstören.
            return d
        return {'version':4,'land':land,'url':ROOT+'/de/'+SLUGS[land]+'/',
                'archive':{},'fehler':[],'scanbereich':None,'scan_abgeschlossen':False}

    def archives(self,land,data,status):
        # Nur beim ersten Mal Online-Verzeichnis lesen; danach den lokalen Index verwenden.
        cache=data.setdefault('archiv_index',{})
        if cache and data.get('archiv_index_vollstaendig'):
            return list(cache.items())
        for a in data.get('archive',{}).values():cache[a['url']]=a['name']
        # Bei vorhandenem Teil-Index ALLE Archive trotzdem einmal komplett laden, bevor
        # Region/Alle Archive als vollständig gelten können.
        if data.get('archiv_index_vollstaendig'):
            return list(cache.items())
        status('Lese einmalig Landes-Archivverzeichnis ...')
        discovered={}
        for soup in self.pages(ROOT+'/de/'+SLUGS[land]+'/'):
            discovered.update(discover_children(ROOT+'/de/'+SLUGS[land]+'/',soup))
        if not discovered:raise RuntimeError('Keine Archive gefunden')
        cache.update(discovered);data['archiv_index_vollstaendig']=True
        export(data)
        return list(cache.items())

    def locations(self,archive,data,status):
        # Vollständige Ortsliste pro Archiv wird lokal gespeichert: kein Durchrattern beim Wiedereinstieg.
        cached=archive.setdefault('orts_index',{})
        if archive.get('orts_index_vollstaendig'):
            return list(cached.items())
        status('Lese Ortsverzeichnis einmalig: '+archive['name'])
        found={}
        for soup in self.pages(archive['url']):found.update(discover_children(archive['url'],soup))
        if not found:raise RuntimeError('Keine Orte entdeckt: '+archive['url'])
        cached.update(found);archive['orts_index_vollstaendig']=True
        export(data)
        return list(cached.items())

    def run(self,land,region,archive_filter,city,package,status):
        self.stop.clear();data=self.load_data(land)
        data['scanbereich']={'region':region,'archiv':archive_filter,'stadt':city,'paket':package}
        data['scan_abgeschlossen']=False
        export(data)
        try:
            available=self.archives(land,data,status)
            selected=choose_archive_items(available,land,region,archive_filter)
            if not selected:raise RuntimeError('Keine passenden Archive gefunden; Archivgruppe prüfen')
            for idx,(aurl,aname) in enumerate(selected,1):
                if self.stop.is_set():raise InterruptedError('Benutzerstopp')
                archive=data['archive'].setdefault(aurl,{'name':aname,'url':aurl,'orte':{},'status':'offen'})
                all_places=self.locations(archive,data,status)
                all_places=sorted(((u,n) for u,n in all_places if names_match_city(n,city)),key=lambda x:x[0])
                # GEZIELTE Stadtfilter sind nur wörtliche Ortstitel; keine vollständige Stadt-Geographie!
                if city!='Alle Orte' and not all_places:
                    status(f'{aname}: keine Ortsnamen passend zu {city}')
                    continue
                place_batches=batch_list(all_places)
                if package=='Alle Pakete (bis Stop)':
                    selected_batches=place_batches
                elif package=='Nächstes offenes Paket':
                    # Neu/offen zuerst. Fehlerhafte/leere Orte separat durch explizite Paketwahl nachprüfen.
                    selected_batches=[b for b in place_batches if any(
                        archive['orte'].get(u,{}).get('status') in ('offen',None) for u,n in b[2])][:1]
                    if not selected_batches:
                        status(f'{aname}: keine neuen offenen Pakete (Fehlerorte separat prüfen)')
                        continue
                else:
                    selected_batches=[b for b in place_batches if str(b[0])==package]
                if package not in ('Alle Pakete (bis Stop)','Nächstes offenes Paket') and not selected_batches:
                    status(f'{aname}: Paket {package} nicht vorhanden ({len(place_batches)} insgesamt)')
                    continue
                for batch_number,start_index,items in selected_batches:
                    key=f'{aurl}|{city}|{batch_number}'
                    # Aus Sicherheitsgründen bis zu 2 Orte zurückgehen, OHNE die fertigen erneut abzurufen.
                    # Somit geht bei einem Abbruch während einer Speicherung kein neuer Erfolg verloren.
                    pending=[(start_index+i,url,name) for i,(url,name) in enumerate(items)
                             if archive['orte'].get(url,{}).get('status')!='fertig']
                    if not pending:
                        data.setdefault('paket_status',{})[key]='fertig'
                        continue
                    data.setdefault('paket_status',{})[key]='laeuft';export(data)
                    for index,url,name in pending:
                        if self.stop.is_set():raise InterruptedError('Benutzerstopp')
                        ort=archive['orte'].setdefault(url,{'name':name,'url':url,'status':'offen','buecher':{}})
                        status(f'{aname} | Paket {batch_number}/{len(place_batches)} | Ort {index+1}/{len(all_places)}: {name}')
                        try:
                            found={}
                            for soup in self.pages(url):found.update(parse_books(url,soup))
                            # Keine alten Bücher vernichten, falls durch HTML-Änderung weniger erkannt werden.
                            if found:ort['buecher'].update(found)
                            ort['status']='fertig' if found else 'leer_pruefen'
                            if not found:data['fehler'].append({'url':url,'meldung':'Keine Kirchenbücher gefunden; prüfen'})
                        except (PermissionError,InterruptedError):raise
                        except Exception as exc:
                            ort['status']='fehler';data['fehler'].append({'url':url,'meldung':str(exc)})
                        data['checkpoint']={'archiv_url':aurl,'archiv':aname,'stadt':city,
                            'paket':batch_number,'orts_index':index,'ort_url':url,
                            'zeit':datetime.now(timezone.utc).isoformat()}
                        export(data)
                    if all(archive['orte'].get(url,{}).get('status')=='fertig' for _,url,_ in pending):
                        data['paket_status'][key]='fertig'
                    else:data['paket_status'][key]='pruefen'
                    data['letztes_paket']={'archiv':aname,'nummer':batch_number,'orte':len(items)}
                    export(data)
                if package=='Alle Pakete (bis Stop)' and city=='Alle Orte':
                    archive['status']='fertig' if all(archive['orte'].get(u,{}).get('status')=='fertig' for u,_ in all_places) else 'teilweise'
            # Kein "Land fertig" bei Teilbereich!
            data['scan_abgeschlossen']=(region=='Alle Regionen / Archivgruppen' and archive_filter=='Alle Archive'
                and city=='Alle Orte' and package=='Alle Pakete (bis Stop)' and
                all(a.get('status')=='fertig' for a in data['archive'].values()))
        finally:export(data)
        return data

ctk.set_appearance_mode('Dark');ctk.set_default_color_theme('blue')
class Browser(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title('Matricula Bestandsbrowser v5 – Teilbestände')
        self.geometry('1190x850');self.minsize(920,650)
        self.parser=Scraper();self.data=None
        self.main=ctk.CTkFrame(self);self.main.pack(fill='both',expand=True,padx=12,pady=12)
        ctk.CTkLabel(self.main,text='🏛️ Matricula Bestandsbrowser 5 · Gezielte Teilbestände',
            font=ctk.CTkFont(size=22,weight='bold')).pack(anchor='w',padx=12,pady=10)
        opt=ctk.CTkFrame(self.main);opt.pack(fill='x',padx=10,pady=6)
        for col in range(5):opt.grid_columnconfigure(col,weight=1)
        for col,title in enumerate(['1 · Land','2 · Bundesland / Archivgruppe','3 · Archiv / Diözese','4 · Großstadt (optional)','5 · Orts-Paket (25)']):
            ctk.CTkLabel(opt,text=title).grid(row=0,column=col,padx=5,pady=(8,2),sticky='w')
        self.land=ctk.CTkOptionMenu(opt,values=list(SLUGS),command=self.land_changed,width=165)
        self.land.grid(row=1,column=0,padx=5,pady=5,sticky='ew');self.land.set('Österreich')
        self.region=ctk.CTkOptionMenu(opt,values=groups_for('Österreich'),command=self.region_changed,width=205)
        self.region.grid(row=1,column=1,padx=5,pady=5,sticky='ew')
        self.archive=ctk.CTkComboBox(opt,values=['Alle Archive'],width=230)
        self.archive.grid(row=1,column=2,padx=5,pady=5,sticky='ew');self.archive.set('Alle Archive')
        self.city=ctk.CTkOptionMenu(opt,values=['Alle Orte']+CITIES.get('Österreich',[]),width=150)
        self.city.grid(row=1,column=3,padx=5,pady=5,sticky='ew');self.city.set('Alle Orte')
        self.package=ctk.CTkComboBox(opt,values=['Nächstes offenes Paket','Alle Pakete (bis Stop)']+[str(i) for i in range(1,501)],width=165)
        self.package.grid(row=1,column=4,padx=5,pady=5,sticky='ew');self.package.set('Nächstes offenes Paket')
        self.btn_index=ctk.CTkButton(opt,text='🔎 Archivliste laden',command=self.fetch_index)
        self.btn_index.grid(row=2,column=0,padx=5,pady=8,sticky='ew')
        self.btn_start=ctk.CTkButton(opt,text='▶ Gewählten Teilbestand scannen',command=self.scan)
        self.btn_start.grid(row=2,column=1,columnspan=2,padx=5,pady=8,sticky='ew')
        self.btn_stop=ctk.CTkButton(opt,text='⏹ Stop',command=self.stop_scan,state='disabled')
        self.btn_stop.grid(row=2,column=3,padx=5,pady=8,sticky='ew')
        ctk.CTkButton(opt,text='📂 JSON öffnen',command=self.open_json).grid(row=2,column=4,padx=5,pady=8,sticky='ew')
        ctk.CTkLabel(self.main,text='Hinweis: Bundesland-Gruppen folgen Archiven, nicht exakt heutigen Grenzen. Stadtfilter findet nur passende Ortsnamen.',
            text_color='#e5b85c').pack(anchor='w',padx=15)
        self.tree=ttk.Treeview(self.main,columns=('status','url'),show='tree headings')
        self.tree.heading('#0',text='Land / Archiv / Ort / Kirchenbuch')
        self.tree.heading('status',text='Status / Zeitraum');self.tree.heading('url',text='URL')
        self.tree.column('#0',width=350);self.tree.column('status',width=140);self.tree.column('url',width=520)
        self.tree.pack(fill='both',expand=True,padx=12,pady=8)
        self.tree.bind('<<TreeviewSelect>>',self.show_detail)
        self.details=ctk.CTkTextbox(self.main,height=75);self.details.pack(fill='x',padx=12,pady=5)
        bar=ctk.CTkFrame(self.main,fg_color='transparent');bar.pack(fill='x',padx=12,pady=5)
        ctk.CTkButton(bar,text='📋 URL kopieren',command=self.copy_url).pack(side='left',padx=4)
        ctk.CTkButton(bar,text='📄 Export',command=self.export_now).pack(side='left',padx=4)
        ctk.CTkButton(bar,text='❓ Hilfe',command=self.help).pack(side='right',padx=4)
        self.stat=ctk.CTkLabel(self.main,text='Paket 1 = Orte 1–25. Vorhandene fertige Orte werden nicht erneut abgefragt.',anchor='w')
        self.stat.pack(fill='x',padx=15,pady=8)
        self.land_changed('Österreich')

    def say(self,msg):self.after(0,lambda m=msg:self.stat.configure(text=m[:200]))
    def land_changed(self,land):
        self.region.configure(values=groups_for(land));self.region.set('Alle Regionen / Archivgruppen')
        self.city.configure(values=['Alle Orte']+CITIES.get(land,[]));self.city.set('Alle Orte')
        self.load_local();self.region_changed(self.region.get())
    def region_changed(self,_):
        options=['Alle Archive']
        if self.data:
            options += [n for u,n in self.data.get('archiv_index',{}).items()
                        if archive_in_region(self.land.get(),n,self.region.get())]
            options += [a['name'] for a in self.data.get('archive',{}).values()
                        if archive_in_region(self.land.get(),a['name'],self.region.get())]
        self.archive.configure(values=list(dict.fromkeys(options)));self.archive.set('Alle Archive')
    def load_local(self):
        try:self.data=self.parser.load_data(self.land.get())
        except Exception as exc:
            self.data=None;self.say('JSON-Ladefehler: '+str(exc));return
        self.refresh_tree()
    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        if not self.data:return
        root=self.tree.insert('','end',text=self.data['land'],values=('',self.data['url']),open=True)
        for a in self.data['archive'].values():
            aid=self.tree.insert(root,'end',text=a['name'],values=(a.get('status',''),a['url']))
            for o in a.get('orte',{}).values():
                oid=self.tree.insert(aid,'end',text=o['name'],values=(o.get('status',''),o['url']))
                for b in o.get('buecher',{}).values():
                    self.tree.insert(oid,'end',text=f"{b['signatur']} · {b['titel']}",values=(b['zeitraum'],b['url']))
    def show_detail(self,_=None):
        sel=self.tree.selection()
        if sel:
            item=self.tree.item(sel[0]);self.details.delete('1.0','end')
            self.details.insert('1.0',f"{item['text']}\n{item['values'][0]}\n{item['values'][1]}")
    def copy_url(self):
        sel=self.tree.selection()
        if sel:
            values=self.tree.item(sel[0],'values')
            if len(values)>1:self.clipboard_clear();self.clipboard_append(values[1]);self.say('URL kopiert')
    def export_now(self):
        if not self.data:return
        j,t,s,n=export(self.data)
        messagebox.showinfo('Export',f'{j.name}\n{t.name}\n{s.name}\n\n{n["buecher"]} Bücher')
    def open_json(self):
        p=filedialog.askopenfilename(filetypes=[('JSON','*.json')])
        if p:
            try:
                d=json.loads(Path(p).read_text(encoding='utf-8'))
                if d.get('version') not in (4,5) or 'archive' not in d:raise ValueError('Nur v4/v5 Bestandsdateien')
                self.land.set(d['land']);self.data=d;self.refresh_tree();self.region_changed(self.region.get())
            except Exception as exc:messagebox.showerror('Importfehler',str(exc))
    def stop_scan(self):self.parser.stop.set();self.say('Stop – letzter Ort bleibt auf Datenträger gespeichert')
    def set_busy(self,busy):
        self.btn_start.configure(state='disabled' if busy else 'normal')
        self.btn_stop.configure(state='normal' if busy else 'disabled')
        self.btn_index.configure(state='disabled' if busy else 'normal')
    def fetch_index(self):
        self.parser.stop.clear()
        self.set_busy(True)
        def task():
            error=None
            try:
                d=self.parser.load_data(self.land.get());self.parser.archives(self.land.get(),d,self.say)
            except Exception as exc:error=str(exc)
            self.after(0,lambda e=error:self.finished(e,only_index=True))
        threading.Thread(target=task,daemon=True).start()
    def scan(self):
        self.set_busy(True)
        args=(self.land.get(),self.region.get(),self.archive.get(),self.city.get(),self.package.get().strip())
        def task():
            error=None
            try:self.parser.run(*args,self.say)
            except Exception as exc:error=str(exc)
            self.after(0,lambda e=error:self.finished(e))
        threading.Thread(target=task,daemon=True).start()
    def finished(self,error,only_index=False):
        self.set_busy(False);self.load_local();self.region_changed(self.region.get()) if only_index else None
        if error:self.say('Unterbrochen: '+error);messagebox.showwarning('Scan',error)
        else:self.say('Archivindex geladen' if only_index else 'Paket beendet. JSON/TXT aktualisiert.')
    def help(self):
        messagebox.showinfo('Teilbestände',
            '1. Land und ggf. Archivgruppe wählen. Archivliste einmal laden.\n'
            '2. Einzelnes Archiv wählen (empfohlen).\n'
            '3. Nächstes offenes Paket: automatisch die nächsten 25 noch nicht begonnenen Orte.\n'
            'Paket 1 = Orte 1–25; Paket 2 = 26–50 usw.\n'
            '4. Paket "Alle Pakete" ermöglicht langfristige Scans mit Wiederaufnahme.\n'
            '5. Die Ortsliste wird je Archiv einmal gespeichert. Fertige Orte werden nie neu geladen.\n'
            '6. Bereits bestehende v4-JSONs bleiben erhalten und werden ergänzt.\n'
            'Achtung: Diözesen überschreiten Landesgrenzen, reine Stadtname-Suche ist nicht vollständig.\n'
            '403/429: sofortiger Stopp, keine Umgehung.')

if __name__=='__main__':Browser().mainloop()
