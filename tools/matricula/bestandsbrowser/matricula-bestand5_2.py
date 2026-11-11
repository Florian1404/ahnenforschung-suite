# -*- coding: utf-8 -*-
"""Matricula Bestandsbrowser v4 – nur Bestandsmetadaten, keine Buchbilder.
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
    status={'land':data['land'],'scanbereich':data.get('scanbereich'),
            'stand':datetime.now(timezone.utc).isoformat(),
            'abgeschlossen':bool(data.get('scan_abgeschlossen')),
            'vollstaendigkeit_bestaetigt':bool(data.get('scan_abgeschlossen')) and not data['fehler'] and counts['offen']==0,
            'zahlen':counts,'fehler':data['fehler'],
            'hinweis':'Buchlinks aus Listen-HTML; Zielseiten nicht einzeln geprüft. Anzahl gegen Matricula im Browser prüfen.'}
    atomic_json(s,status)
    return j,t,s,counts

class Scraper:
    def __init__(self,delay=3.5):
        self.delay=max(3.,float(delay));self.stop=threading.Event()
        self.session=requests.Session()
        self.ua='MatriculaBestandsbrowser/4.0 (private research index; metadata only)'
        self.session.headers.update({'User-Agent':self.ua,'Accept-Language':'de,en;q=0.8'})
        self.last=0
        self.robot=RobotFileParser()
        self.robot.set_url(ROOT+'/robots.txt')
        self.robots_checked=False

    def robots_check(self):
        if not self.robots_checked:
            try:
                r=self.session.get(ROOT+'/robots.txt',timeout=20)
                if r.status_code in (403,429):raise PermissionError(f'robots.txt: HTTP {r.status_code}')
                if r.status_code==200:self.robot.parse(r.text.splitlines())
                else:raise RuntimeError(f'robots.txt nicht prüfbar: HTTP {r.status_code}')
            except requests.RequestException as exc:
                raise RuntimeError(f'robots.txt konnte nicht geprüft werden: {exc}') from exc
            self.robots_checked=True
        return True

    def get(self,url):
        if self.stop.is_set():raise InterruptedError('Scan gestoppt')
        self.robots_check()
        if not self.robot.can_fetch(self.ua,url):raise PermissionError(f'robots.txt erlaubt diesen Pfad nicht: {url}')
        for attempt in range(3):
            remaining=self.delay-(time.monotonic()-self.last)
            if remaining>0 and self.stop.wait(remaining):raise InterruptedError('Scan gestoppt')
            self.last=time.monotonic()
            try:
                r=self.session.get(url,timeout=25)
            except requests.RequestException as exc:
                if attempt==2:raise RuntimeError(f'Netzwerkfehler {url}: {exc}') from exc
                if self.stop.wait(5*(attempt+1)):raise InterruptedError('Scan gestoppt')
                continue
            if r.status_code in (403,429):raise PermissionError(f'HTTP {r.status_code} bei {url}; Abbruch ohne Sperrumgehung')
            if r.status_code in (500,502,503,504):
                if attempt==2:raise RuntimeError(f'HTTP {r.status_code} bei {url}')
                if self.stop.wait(5*(attempt+1)):raise InterruptedError('Scan gestoppt')
                continue
            r.raise_for_status()
            return BeautifulSoup(r.text,'html.parser')
        raise RuntimeError('Fehler bei '+url)

    def pages(self,base):
        queue=deque([base]);seen=set()
        while queue:
            current=queue.popleft()
            if current in seen:continue
            if len(seen)>=200:raise RuntimeError('Mehr als 200 Verzeichnisseiten bei '+base)
            seen.add(current)
            soup=self.get(current)
            yield soup
            for a in page_content(soup).select('a[href]'):
                target=urljoin(current,a['href'])
                parsed=urlsplit(target)
                if parsed.netloc!=urlsplit(base).netloc or parsed.path.rstrip('/')!=urlsplit(base).path.rstrip('/'):continue
                q=parse_qs(parsed.query)
                if not any(k in q for k in ('page','p')):continue
                if target not in seen and target not in queue:queue.append(target)

    def run(self,land,archive_filter,status):
        self.stop.clear()
        land_url=ROOT+'/de/'+SLUGS[land]+'/'
        j,_,_=output_paths(land)
        if j.exists():
            try:
                data=json.loads(j.read_text(encoding='utf-8'))
                if data.get('version')!=4 or data.get('land')!=land:raise ValueError('Falsches JSON-Format')
            except (ValueError,KeyError) as exc:
                raise RuntimeError(f'Vorhandene Datei nicht lesbar: {j}: {exc}') from exc
        else:
            data={'version':4,'land':land,'url':land_url,'archive':{},'fehler':[],
                  'scanbereich':archive_filter,'scan_abgeschlossen':False}
        data['scanbereich']=archive_filter;data['scan_abgeschlossen']=False
        export(data)
        try:
            status('Lese Archivverzeichnis ...')
            archives={}
            for soup in self.pages(land_url):archives.update(discover_children(land_url,soup))
            if not archives:raise RuntimeError('Keine Archive erkannt: HTML-Struktur überprüfen')
            selected=[(url,name) for url,name in archives.items() if archive_filter=='Alle Archive' or archive_filter.lower() in (name.lower(),parts(url)[-1].lower())]
            if not selected:raise RuntimeError(f'Archiv {archive_filter!r} nicht im Verzeichnis gefunden')
            for idx,(aurl,aname) in enumerate(selected,1):
                if self.stop.is_set():raise InterruptedError('Scan gestoppt')
                status(f'Archiv {idx}/{len(selected)}: {aname}')
                archive=data['archive'].setdefault(aurl,{'name':aname,'url':aurl,'orte':{},'status':'offen'})
                try:
                    locations={}
                    for soup in self.pages(aurl):locations.update(discover_children(aurl,soup))
                    if not locations:raise RuntimeError('Keine Orte erkannt')
                    archive['status']='fertig'
                except PermissionError:raise
                except InterruptedError:raise
                except Exception as exc:
                    archive['status']='fehler'
                    data['fehler'].append({'url':aurl,'meldung':str(exc)})
                    export(data)
                    continue
                for k,(ourl,oname) in enumerate(locations.items(),1):
                    if self.stop.is_set():raise InterruptedError('Scan gestoppt')
                    ort=archive['orte'].setdefault(ourl,{'name':oname,'url':ourl,'status':'offen','buecher':{}})
                    if ort['status']=='fertig':continue
                    status(f'{aname} · Ort {k}/{len(locations)}: {oname}')
                    try:
                        found={}
                        for soup in self.pages(ourl):found.update(parse_books(ourl,soup))
                        ort['buecher']=found
                        # Leere Orte erhalten; wenn kein Buch gefunden ist, zur Kontrolle markieren.
                        ort['status']='fertig' if found else 'leer_pruefen'
                        if not found:data['fehler'].append({'url':ourl,'meldung':'Keine Buchlinks erkannt; manuell prüfen'})
                    except PermissionError:raise
                    except InterruptedError:raise
                    except Exception as exc:
                        ort['status']='fehler'
                        data['fehler'].append({'url':ourl,'meldung':str(exc)})
                    export(data)
                export(data)
            data['scan_abgeschlossen']=True
        finally:
            export(data)
        return data

ctk.set_appearance_mode('Dark')
ctk.set_default_color_theme('blue')

class Browser(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title('Matricula Bestandsbrowser v4')
        self.geometry('1050x800')
        self.minsize(850,620)
        self.parser=Scraper();self.data=None
        self.main=ctk.CTkFrame(self)
        self.main.pack(fill='both',expand=True,padx=14,pady=14)
        ctk.CTkLabel(self.main,text='🏛️ Matricula Bestandsbrowser 4',font=ctk.CTkFont(size=23,weight='bold')).pack(anchor='w',padx=15,pady=12)
        settings=ctk.CTkFrame(self.main)
        settings.pack(fill='x',padx=12,pady=5)
        ctk.CTkLabel(settings,text='Land').grid(row=0,column=0,padx=8,pady=8)
        self.land=ctk.CTkOptionMenu(settings,values=list(SLUGS),command=lambda _:self.load_local())
        self.land.grid(row=0,column=1,padx=8,pady=8);self.land.set('Österreich')
        ctk.CTkLabel(settings,text='Scanumfang').grid(row=0,column=2,padx=8)
        self.scope=ctk.CTkComboBox(settings,values=['Altösterreich (evangelisch)','Alle Archive'],width=240)
        self.scope.grid(row=0,column=3,padx=8);self.scope.set('Altösterreich (evangelisch)')
        self.start=ctk.CTkButton(settings,text='🌐 Scan starten / fortsetzen',command=self.scan)
        self.start.grid(row=1,column=0,columnspan=2,padx=8,pady=8,sticky='ew')
        self.stop=ctk.CTkButton(settings,text='⏹ Stop',width=100,command=self.stop_scan,state='disabled')
        self.stop.grid(row=1,column=2,padx=8)
        ctk.CTkButton(settings,text='📂 JSON öffnen',command=self.open_json).grid(row=1,column=3,padx=8)
        self.tree=ttk.Treeview(self.main,columns=('status','url'),show='tree headings')
        self.tree.heading('#0',text='Land / Archiv / Ort / Kirchenbuch')
        self.tree.heading('status',text='Status / Zeitraum')
        self.tree.heading('url',text='URL')
        self.tree.column('#0',width=330,stretch=True)
        self.tree.column('status',width=130,stretch=False)
        self.tree.column('url',width=430,stretch=True)
        self.tree.pack(fill='both',expand=True,padx=12,pady=8)
        self.tree.bind('<<TreeviewSelect>>',self.show_detail)
        self.details=ctk.CTkTextbox(self.main,height=85)
        self.details.pack(fill='x',padx=12,pady=6)
        buttons=ctk.CTkFrame(self.main,fg_color='transparent')
        buttons.pack(fill='x',padx=12,pady=6)
        ctk.CTkButton(buttons,text='📋 URL kopieren',command=self.copy_url).pack(side='left',padx=4)
        ctk.CTkButton(buttons,text='📄 Dateien exportieren',command=self.export_now).pack(side='left',padx=4)
        ctk.CTkButton(buttons,text='❓ Hilfe',command=self.help).pack(side='right',padx=4)
        self.progress=ctk.CTkProgressBar(self.main);self.progress.pack(fill='x',padx=15,pady=4);self.progress.set(0)
        self.stat=ctk.CTkLabel(self.main,text='Bereit. Zuerst Archiv einzeln testen.',anchor='w')
        self.stat.pack(fill='x',padx=15,pady=(3,10))
        self.load_local()

    def say(self,msg):self.after(0,lambda:self.stat.configure(text=msg[:190]))
    def load_local(self):
        j,_,_=output_paths(self.land.get())
        self.data=json.loads(j.read_text(encoding='utf-8')) if j.exists() else None
        self.refresh_tree()
    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        if not self.data:return
        root=self.tree.insert('', 'end',text=self.data['land'],values=('',self.data['url']),open=True)
        for a in self.data['archive'].values():
            aid=self.tree.insert(root,'end',text=a['name'],values=(a['status'],a['url']))
            for o in a['orte'].values():
                oid=self.tree.insert(aid,'end',text=o['name'],values=(o['status'],o['url']))
                for b in o['buecher'].values():
                    self.tree.insert(oid,'end',text=f"{b['signatur']} · {b['titel']}",values=(b['zeitraum'],b['url']))
    def show_detail(self,_=None):
        ids=self.tree.selection()
        if not ids:return
        item=self.tree.item(ids[0]); self.details.delete('1.0','end')
        self.details.insert('1.0',f"{item['text']}\n{item['values'][0]}\n{item['values'][1]}")
    def copy_url(self):
        ids=self.tree.selection()
        if not ids:return
        vals=self.tree.item(ids[0],'values')
        if len(vals)>1:
            self.clipboard_clear();self.clipboard_append(vals[1]);self.say('URL in Zwischenablage')
    def export_now(self):
        if not self.data:return messagebox.showinfo('Hinweis','Noch keine Daten')
        j,t,s,n=export(self.data)
        messagebox.showinfo('Export',f'{j.name}\n{t.name}\n{s.name}\n\n{n["orte"]} Orte, {n["buecher"]} Bücher')
    def open_json(self):
        p=filedialog.askopenfilename(filetypes=[('JSON','*.json')])
        if not p:return
        try:
            d=json.loads(Path(p).read_text(encoding='utf-8'))
            if d.get('version')!=4 or 'archive' not in d:raise ValueError('Benötigt Version-4-JSON')
            self.data=d;self.land.set(d['land']);self.refresh_tree()
        except Exception as exc:messagebox.showerror('Importfehler',str(exc))
    def stop_scan(self):self.parser.stop.set();self.say('Stop angefordert – sichere bisherigen Fortschritt ...')
    def scan(self):
        land=self.land.get();scope=self.scope.get().strip() or 'Alle Archive'
        self.parser.stop.clear();self.start.configure(state='disabled');self.stop.configure(state='normal')
        self.progress.configure(mode='indeterminate');self.progress.start()
        threading.Thread(target=self.worker,args=(land,scope),daemon=True).start()
    def worker(self,land,scope):
        error=None
        try:self.parser.run(land,scope,self.say)
        except Exception as exc:error=str(exc)
        self.after(0,lambda:self.finished(error))
    def finished(self,error):
        self.progress.stop();self.progress.configure(mode='determinate');self.progress.set(0)
        self.start.configure(state='normal');self.stop.configure(state='disabled')
        self.load_local()
        if error:
            self.say('Scan unterbrochen: '+error)
            messagebox.showwarning('Scan unterbrochen','Bereits erfasste Daten wurden gespeichert.\n'+error)
        else:
            self.say('Scan beendet. Statusbericht kontrollieren!')
            messagebox.showinfo('Scan beendet','JSON, TXT und Statusbericht erzeugt.\nVollständigkeit anhand des Statusberichts prüfen.')
    def help(self):
        messagebox.showinfo('Matricula v4',
            '1. Land und Archiv wählen; erster Test: Altösterreich (evangelisch).\n'
            '2. Scan starten. Nach jedem Ort erfolgt ein Checkpoint.\n'
            '3. Stop jederzeit möglich; erneuter Scan setzt fertige Orte fort.\n'
            '4. JSON: Hierarchie inkl. URLs; TXT: tabellarische Buchlinks.\n'
            '5. Status-JSON: Fehler, offene Orte und Hinweise.\n'
            '6. Keine Bilder, keine Sperrumgehung; HTTP 403/429 beendet den Scan.\n'
            'Hinweis: Linktreffer sind kein Beweis vollständiger Erfassung.')

if __name__=='__main__':Browser().mainloop()
