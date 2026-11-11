import os
import json
import re
import time
import threading
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
import pandas as pd
import customtkinter as ctk

# Hinweis: Für den Excel-Export von Pandas wird das Paket 'openpyxl' benötigt.
# Installation über: pip install requests beautifulsoup4 pandas openpyxl customtkinter

# =====================================================================
# 1. SEPARATER PARSER FÜR DIE ECHTE MATRICULA-WEBSITE
# =====================================================================
class MatriculaParser:
    """Bestandsindex; lädt keine Kirchenbuchbilder."""
    BASE = "https://data.matricula-online.eu"
    SLUGS = {"Österreich": "oesterreich", "Deutschland": "deutschland",
             "Polen": "polen", "Serbien": "serbien", "Luxemburg": "luxemburg",
             "Bosnien": "bosnien", "Slowenien": "slowenien", "Italien": "italien",
             "Privatarchiv": "privatarchive", "Schweiz": "schweiz"}

    def __init__(self, pause=3.0):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "MatriculaBestandsbrowser/3.0 (private genealogical index)",
                                     "Accept-Language": "de,en;q=0.7"})
        self.pause = pause
        self.last_request = 0.0
        self.errors = []
        self.visited = set()
        self.stop_event = threading.Event()

    @staticmethod
    def path_segments(url):
        return [p for p in urlparse(url).path.split("/") if p]

    @staticmethod
    def clean_url(url):
        p = urlparse(url)
        return p._replace(query="", fragment="").geturl().rstrip("/") + "/"

    def get_soup(self, url):
        if self.stop_event.is_set():
            raise InterruptedError("Scan wurde angehalten")
        wait = max(0, self.pause - (time.monotonic() - self.last_request))
        if wait:
            time.sleep(wait)
        self.last_request = time.monotonic()
        for attempt in range(3):
            try:
                resp = self.session.get(url, timeout=25)
                if resp.status_code in (403, 429):
                    raise PermissionError(f"HTTP {resp.status_code} bei {url}. Scan beendet; keine Umgehung von Zugriffssperren.")
                if resp.status_code in (500, 502, 503, 504):
                    time.sleep(min(30, 5 * (attempt + 1)))
                    continue
                resp.raise_for_status()
                return BeautifulSoup(resp.text, "html.parser")
            except (requests.Timeout, requests.ConnectionError) as exc:
                if attempt == 2:
                    raise RuntimeError(f"Netzwerkfehler bei {url}: {exc}") from exc
                time.sleep(5 * (attempt + 1))
        raise RuntimeError(f"Serverfehler bei {url}")

    def child_links(self, parent_url, soup):
        """Nur echte Pfadkinder derselben Domain, keine Navigation oder Buchseiten."""
        parent = self.path_segments(parent_url)
        found = {}
        for a in soup.select("a[href]"):
            name = a.get_text(" ", strip=True)
            href = a.get("href", "")
            target = self.clean_url(urljoin(parent_url, href))
            seg = self.path_segments(target)
            if (urlparse(target).netloc != urlparse(self.BASE).netloc or
                len(seg) != len(parent) + 1 or seg[:len(parent)] != parent or
                not name or len(name) < 2):
                continue
            name = re.sub(r"^\s*\d+\s+", "", name).strip()
            found[target] = name
        return found

    def pages(self, url, max_pages=200):
        """Ermittelt ?page= / ?p= Seiten, ohne ?pg= Bildseiten zu verfolgen."""
        queue = [url]
        seen = set()
        while queue:
            page = queue.pop(0)
            if page in seen:
                continue
            if len(seen) >= max_pages:
                raise RuntimeError(f"Mehr als {max_pages} Ergebnisseiten: {url}")
            seen.add(page)
            soup = self.get_soup(page)
            yield soup
            for a in soup.select("a[href]"):
                nxt = urljoin(page, a['href'])
                parsed = urlparse(nxt)
                if (parsed.netloc == urlparse(url).netloc and
                    parsed.path.rstrip('/') == urlparse(url).path.rstrip('/') and
                    re.search(r"(?:^|&)(?:page|p)=\d+", parsed.query) and
                    nxt not in seen and nxt not in queue):
                    queue.append(nxt)

    @staticmethod
    def expected_count(soup):
        # Seiten mit Überschrift z.B. "Matriken ... 1 gesamt"
        txt = soup.get_text(" ", strip=True)
        m = re.search(r"\b(\d+)\s+gesamt\b", txt, re.I)
        return int(m.group(1)) if m else None

    def parse_books(self, ort_url, soup):
        """Foto-Link direkt aus Zeile, ansonsten eindeutige Signatur aus Tabellenzeile.
        Keine Bild- oder ?pg=Folgeseiten nötig.
        """
        books = {}
        for tr in soup.select("tr"):
            cells = tr.find_all("td", recursive=False)
            if len(cells) < 2:
                continue
            texts = [c.get_text(" ", strip=True) for c in cells]
            row_text = " ".join(texts)
            # Matricula verwendet oft eine leere Kameraspalte vor Signatur und Typ.
            candidates = []
            for c in cells:
                for a in c.select("a[href]"):
                    href = urljoin(ort_url, a['href'])
                    if len(self.path_segments(href)) == len(self.path_segments(ort_url)) + 1:
                        candidates.append(href)
                for element in c.select("[data-href], [onclick]"):
                    href = element.get('data-href', '')
                    if not href:
                        match = re.search(r"['\"]([^'\"]+/[^'\"]+)['\"]", element.get('onclick',''))
                        href = match.group(1) if match else ''
                    if href:
                        full = urljoin(ort_url, href)
                        if len(self.path_segments(full)) == len(self.path_segments(ort_url)) + 1:
                            candidates.append(full)
            # Vorhandener Buchlink gewinnt; sonst Signatur aus Tabellen-Spalten.
            signature = ''
            url = ''
            if candidates:
                url = self.clean_url(candidates[0])
                signature = self.path_segments(url)[-1]
            else:
                # Tabellensignatur ist meist erste nichtleere Zelle. Nur bei
                # weiteren Typ-/Datumsangaben eine URL aus der Signatur ableiten.
                values = [x for x in texts if x]
                if len(values) < 2:
                    continue
                signature = values[0]
                if not re.fullmatch(r"[\w.\-]+", signature, re.UNICODE):
                    continue
                if not (re.search(r"\b(1[5-9]\d\d|20\d\d)\b", row_text) or
                        re.search(r"tauf|trau|heirat|sterbe|tod|matrik|firm|geburt", row_text, re.I)):
                    continue
                url = urljoin(self.clean_url(ort_url), requests.utils.requote_uri(signature) + "/")
            if not signature or not url:
                continue
            # Metadaten über den tatsächlich sichtbaren Tabelleninhalt hinaus
            # nicht erraten. Original-Tabellenzeile bleibt für spätere Analyse.
            values = [x for x in texts if x]
            typ = next((v for v in values if v != signature and
                        re.search(r"tauf|trau|heirat|sterbe|tod|matrik|firm|geburt", v, re.I)), "")
            zeitraum = next((v for v in values if re.search(r"\b\d{4}\s*[-–]\s*\d{4}\b", v)), "")
            url = self.clean_url(url) + "?pg=1"
            books[url] = {"titel": typ or signature, "typ": typ,
                          "zeitraum": zeitraum, "signatur": signature,
                          "url": url, "tabellenzeile": row_text}
        return list(books.values())

    def scrape_land_live(self, land, callback, checkpoint=None):
        self.errors = []
        self.visited = set()
        self.stop_event.clear()
        slug = self.SLUGS.get(land)
        if not slug:
            raise ValueError(f"Unbekannter Länder-Slug: {land}. URL bitte prüfen.")
        country_url = f"{self.BASE}/de/{slug}/"
        callback(f"Lade Länderübersicht: {country_url}")
        archives = {}
        for soup in self.pages(country_url):
            archives.update(self.child_links(country_url, soup))
        if not archives:
            raise RuntimeError("Keine Archive gefunden: möglicherweise wurde die Seitenstruktur geändert.")
        result = (checkpoint or {}).copy()
        for i, (archive_url, archive_name) in enumerate(sorted(archives.items()), 1):
            callback(f"Archiv {i}/{len(archives)}: {archive_name}")
            locations = {}
            try:
                for soup in self.pages(archive_url):
                    locations.update(self.child_links(archive_url, soup))
                    # Alphabetregister ggf. über ?page= eingebunden
            except PermissionError:
                raise
            except Exception as exc:
                self.errors.append(f"{archive_url}: {exc}")
                continue
            if not locations:
                self.errors.append(f"Keine Orte in {archive_url}")
            archive_data = result.setdefault(archive_name, {})
            for j, (ort_url, ort_name) in enumerate(sorted(locations.items()), 1):
                if self.stop_event.is_set():
                    raise InterruptedError("Abbruch")
                if ort_name in archive_data and archive_data[ort_name]:
                    continue
                callback(f"{archive_name} · Ort {j}/{len(locations)}: {ort_name}")
                try:
                    books = {}
                    expected = None
                    for soup in self.pages(ort_url):
                        if expected is None:
                            expected = self.expected_count(soup)
                        for b in self.parse_books(ort_url, soup):
                            books[b['url']] = b
                    if expected is not None and len(books) != expected:
                        self.errors.append(f"Buchanzahl {ort_url}: erwartet {expected}, gefunden {len(books)}")
                    if not books:
                        self.errors.append(f"Keine Bücher erkannt: {ort_url}")
                    else:
                        archive_data[ort_name] = list(books.values())
                except PermissionError:
                    raise
                except Exception as exc:
                    self.errors.append(f"{ort_url}: {exc}")
                if checkpoint is not None:
                    checkpoint.clear()
                    checkpoint.update(result)
        return result


# =====================================================================
# 2. INTERFACE (GUI AUF BASIS VON CUSTOMTKINTER DARK MODE)
# =====================================================================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class MatriculaBrowser(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Matricula Bestandsbrowser")
        self.geometry("950x840")
        self.resizable(False, False)

        self.db_data = {}
        self.parser = MatriculaParser()

        self.laender_liste = [
            "Deutschland", "Österreich", "Polen", "Serbien",
            "Luxemburg", "Bosnien", "Slowenien", "Italien",
            "Privatarchiv", "Schweiz"
        ]

        self.setup_gui()
        self.load_json_data(silent=True)

    def setup_gui(self):
        self.main_frame = ctk.CTkFrame(self, corner_radius=15)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        self.header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=10, pady=(10, 20))

        self.title_label = ctk.CTkLabel(
            self.header_frame, text="🏛️ Matricula Bestandsbrowser",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.pack(side="left")

        self.help_button = ctk.CTkButton(
            self.header_frame, text="❓ Konzept & Hilfe", width=140,
            command=self.open_help_window
        )
        self.help_button.pack(side="right")

        self.step_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.step_frame.pack(fill="x", padx=10, pady=5)

        self.lbl_step1 = ctk.CTkLabel(self.step_frame, text="1. Land wählen:",
                                      font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_step1.pack(anchor="w", pady=(5, 2))
        self.combo_land = ctk.CTkOptionMenu(self.step_frame, values=self.laender_liste,
                                            command=self.on_land_selected)
        self.combo_land.pack(fill="x", pady=(0, 15))
        self.combo_land.set("Bitte wählen...")

        self.lbl_step2 = ctk.CTkLabel(self.step_frame, text="2. Diözese / Archiv wählen:",
                                      font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_step2.pack(anchor="w", pady=(5, 2))
        self.combo_dioezese = ctk.CTkOptionMenu(self.step_frame, values=["Warte auf Land..."],
                                                command=self.on_dioezese_selected)
        self.combo_dioezese.pack(fill="x", pady=(0, 15))

        self.lbl_step3 = ctk.CTkLabel(self.step_frame, text="3. Ort / Pfarrei wählen:",
                                      font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_step3.pack(anchor="w", pady=(5, 2))
        self.combo_ort = ctk.CTkOptionMenu(self.step_frame, values=["Warte auf Diözese..."],
                                           command=self.on_ort_selected)
        self.combo_ort.pack(fill="x", pady=(0, 15))

        self.lbl_step4 = ctk.CTkLabel(self.step_frame, text="4. Kirchenbuch wählen:",
                                      font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_step4.pack(anchor="w", pady=(5, 2))
        self.combo_buch = ctk.CTkOptionMenu(self.step_frame, values=["Warte auf Ort/Pfarrei..."],
                                            command=self.on_buch_selected)
        self.combo_buch.pack(fill="x", pady=(0, 20))

        self.lbl_details = ctk.CTkLabel(self.main_frame,
                                        text="Details zum ausgewählten Kirchenbuch:",
                                        font=ctk.CTkFont(size=12, weight="bold"))
        self.lbl_details.pack(anchor="w", padx=10)

        self.txt_details = ctk.CTkTextbox(self.main_frame, height=140, font=("Consolas", 13))
        self.txt_details.pack(fill="x", padx=10, pady=(0, 20))
        self.txt_details.configure(state="disabled")

        self.button_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.button_frame.pack(fill="x", padx=10, pady=10)

        self.btn_load_json = ctk.CTkButton(self.button_frame, text="📂 JSON laden", width=120,
                                           fg_color="#565b5e", hover_color="#6e7478",
                                           command=self.import_json_via_gui)
        self.btn_load_json.pack(side="left", padx=(0, 10))

        self.btn_refresh_land = ctk.CTkButton(self.button_frame, text="🌐 Land aktualisieren",
                                              command=self.force_land_refresh)
        self.btn_refresh_land.pack(side="left", padx=(0, 10))

        self.btn_delete_json = ctk.CTkButton(self.button_frame, text="🗑️ JSON löschen", width=120,
                                             fg_color="#dc3545", hover_color="#bd2130",
                                             command=self.delete_json_file)
        self.btn_delete_json.pack(side="left")
        self.btn_stop = ctk.CTkButton(self.button_frame, text="⏹ Stop", width=70,
                                      command=lambda: self.parser.stop_event.set())
        self.btn_stop.pack(side="left", padx=(8, 0))

        # Rechtsbündige Knöpfe
        self.btn_excel = ctk.CTkButton(self.button_frame, text="📊 Excel-Linkliste erstellen",
                                       fg_color="#1f538d", hover_color="#2a6cb8",
                                       command=self.export_to_excel)
        self.btn_excel.pack(side="right", padx=(10, 0))

        self.btn_copy_url = ctk.CTkButton(self.button_frame, text="📋 URL kopieren",
                                          fg_color="#28a745", hover_color="#218838",
                                          command=self.copy_url_to_clipboard)
        self.btn_copy_url.pack(side="right")

        self.status_label = ctk.CTkLabel(self.main_frame, text="Bereit.",
                                         text_color="gray60", font=ctk.CTkFont(size=11))
        self.status_label.pack(anchor="w", padx=10, pady=(10, 0))

        self.progress_bar = ctk.CTkProgressBar(self.main_frame, height=6)
        self.progress_bar.pack(fill="x", padx=10, pady=(2, 10))
        self.progress_bar.set(0)

    # -----------------------------------------------------------------
    # Länderspezifische Dateinamengenerierung
    # -----------------------------------------------------------------
    def get_filename_for_land(self, land_name):
        """Erzeugt einen sauberen Dateinamen wie matricula-bestand-oesterreich.json"""
        clean = re.sub(r"\s*\(.*?\)", "", land_name).strip().lower()
        clean = (clean
                 .replace("ö", "oesterreich" if clean == "österreich" else "oe")
                 .replace("ä", "ae")
                 .replace("ü", "ue")
                 .replace("ß", "ss")
                 .replace(" ", "_"))
        return f"matricula-bestand-{clean}.json"

    # -----------------------------------------------------------------
    # Dropdown-Logik
    # -----------------------------------------------------------------
    def on_land_selected(self, land):
        self.reset_dropdowns(from_step=2)
        if land not in self.db_data or not self.db_data[land]:
            answer = messagebox.askyesno(
                "Live-Update erforderlich",
                f"Für {land} liegen keine lokalen Daten vor.\nOnline-Live-Update jetzt starten?"
            )
            if answer:
                self.start_live_scraping(land)
            else:
                self.combo_land.set("Bitte wählen...")
        else:
            self.populate_dioezesen(land)

    def populate_dioezesen(self, land):
        if land in self.db_data and isinstance(self.db_data[land], dict) and self.db_data[land]:
            dioezesen = sorted(self.db_data[land].keys())
            self.combo_dioezese.configure(values=dioezesen)
            if dioezesen:
                first_val = dioezesen[0]
                self.combo_dioezese.set(first_val)
                self.on_dioezese_selected(first_val)
        else:
            self.combo_dioezese.configure(values=["Keine Archive vorhanden"])
            self.combo_dioezese.set("Keine Archive vorhanden")

    def on_dioezese_selected(self, dioezese):
        self.reset_dropdowns(from_step=3)
        land = self.combo_land.get()
        if (land in self.db_data and dioezese in self.db_data[land]
                and isinstance(self.db_data[land][dioezese], dict)):
            orte = sorted(self.db_data[land][dioezese].keys())
            if orte:
                self.combo_ort.configure(values=orte)
                first_ort = orte[0]
                self.combo_ort.set(first_ort)
                self.on_ort_selected(first_ort)
                return
        self.combo_ort.configure(values=["Keine Orte"])
        self.combo_ort.set("Keine Orte")

    def on_ort_selected(self, ort):
        self.reset_dropdowns(from_step=4)
        land = self.combo_land.get()
        dioezese = self.combo_dioezese.get()
        if (land in self.db_data and dioezese in self.db_data[land]
                and ort in self.db_data[land][dioezese]):
            buecher = self.db_data[land][dioezese][ort]
            if isinstance(buecher, list) and buecher:
                buch_titel = [b["titel"] for b in buecher if "titel" in b]
                if buch_titel:
                    self.combo_buch.configure(values=buch_titel)
                    first_buch = buch_titel[0]
                    self.combo_buch.set(first_buch)
                    self.on_buch_selected(first_buch)
                    return
        self.combo_buch.configure(values=["Keine Bücher"])
        self.combo_buch.set("Keine Bücher")

    def on_buch_selected(self, buch_titel):
        land = self.combo_land.get()
        dioezese = self.combo_dioezese.get()
        ort = self.combo_ort.get()
        if (land in self.db_data and dioezese in self.db_data[land]
                and ort in self.db_data[land][dioezese]):
            buecher = self.db_data[land][dioezese][ort]
            selected = next((b for b in buecher
                             if isinstance(b, dict) and b.get("titel") == buch_titel), None)
            if selected:
                details = (
                    f"Pfarrei/Ort: {ort}\n"
                    f"Buch-Titel:  {selected.get('titel', 'N/A')}\n"
                    f"Typ/Inhalt:  {selected.get('typ', 'N/A')}\n"
                    f"Zeitraum:    {selected.get('zeitraum', 'N/A')}\n"
                    f"Signatur:    {selected.get('signatur', 'N/A')}\n"
                    f"Direkt-URL:  {selected.get('url', 'N/A')}"
                )
                self.update_textbox(details)
                return
        self.update_textbox("")

    def reset_dropdowns(self, from_step):
        if from_step <= 2:
            self.combo_dioezese.configure(values=["Warte auf Land..."])
            self.combo_dioezese.set("Warte auf Land...")
        if from_step <= 3:
            self.combo_ort.configure(values=["Warte auf Diözese..."])
            self.combo_ort.set("Warte auf Diözese...")
        if from_step <= 4:
            self.combo_buch.configure(values=["Warte auf Ort/Pfarrei..."])
            self.combo_buch.set("Warte auf Ort/Pfarrei...")
        self.update_textbox("")

    def update_textbox(self, text):
        self.txt_details.configure(state="normal")
        self.txt_details.delete("1.0", tk.END)
        self.txt_details.insert("1.0", text)
        self.txt_details.configure(state="disabled")

    # -----------------------------------------------------------------
    # JSON-Verwaltung (Länderspezifische Logik & Multi-Lader)
    # -----------------------------------------------------------------
    def load_json_data(self, filepath=None, silent=False):
        """Sucht länderspezifische JSONs und lädt/mergt diese im Speicher."""
        if not filepath:
            self.db_data = {}
            found_any = False
            pattern = re.compile(r"^matricula-bestand-.*\.json$")
            
            for file in os.listdir("."):
                if pattern.match(file):
                    try:
                        with open(file, "r", encoding="utf-8") as f:
                            raw_data = json.load(f)
                        if isinstance(raw_data, dict):
                            if "dioezesen" in raw_data:
                                self.db_data["Österreich"] = raw_data["dioezesen"]
                            else:
                                self.db_data.update(raw_data)
                            found_any = True
                    except Exception:
                        continue
            
            if not found_any:
                if not silent:
                    messagebox.showinfo("Info", "Keine länderspezifischen Bestandsdaten gefunden.")
                return False
        else:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)
                
                if isinstance(raw_data, dict):
                    if "dioezesen" in raw_data:
                        self.db_data["Österreich"] = raw_data["dioezesen"]
                    else:
                        self.db_data.update(raw_data)
                else:
                    raise Exception("Ungültiges JSON-Format.")
            except Exception as e:
                if not silent:
                    messagebox.showerror("Ladefehler", f"Die JSON-Datei konnte nicht verarbeitet werden:\n{e}")
                return False

        laender = sorted(list(self.db_data.keys()))
        if hasattr(self, "combo_land") and laender:
            komplette_liste = sorted(list(set(self.laender_liste + laender)))
            self.combo_land.configure(values=komplette_liste)
            
            standard_land = laender[0]
            for l in laender:
                if "österreich" in l.lower() or "oesterreich" in l.lower():
                    standard_land = l
                    break
            
            self.combo_land.set(standard_land)
            self.populate_dioezesen(standard_land)

        if hasattr(self, "status_label"):
            cnt = len(self.db_data.keys())
            self.status_label.configure(text=f"📂 {cnt} Länderbereiche geladen.", text_color="#00cc66")
        return True

    def import_json_via_gui(self):
        filepath = filedialog.askopenfilename(
            title="Matricula JSON-Datenbank auswählen",
            filetypes=[("JSON-Datenbank", "*.json"), ("Alle Dateien", "*.*")]
        )
        if filepath:
            self.load_json_data(filepath=filepath, silent=False)

    def save_json_data(self, land, data=None, errors=None, incomplete=False):
        """JSON + vollständige TXT-Liste, atomar gespeichert; Scanreport separat."""
        data = data if data is not None else self.db_data.get(land, {})
        errors = errors if errors is not None else []
        filename = Path(self.get_filename_for_land(land))
        tmp = filename.with_suffix('.json.tmp')
        with tmp.open('w', encoding='utf-8') as f:
            json.dump({land: data}, f, ensure_ascii=False, indent=2)
        os.replace(tmp, filename)
        txt = filename.with_suffix('.txt')
        lines = []
        tree = {"land": land, "archive": []}
        for archiv, orte in sorted(data.items()):
            archiv_node = {"name": archiv, "url": "", "orte": []}
            tree["archive"].append(archiv_node)
            for ort, buecher in sorted(orte.items()):
                ort_node = {"name": ort, "url": "", "kirchenbuecher": buecher}
                archiv_node["orte"].append(ort_node)
                for buch in buecher:
                    seg = urlparse(buch.get('url','')).path.rstrip('/').rsplit('/', 1)[0]
                    ort_url = self.parser.BASE + seg + '/'
                    dioe_url = self.parser.BASE + seg.rsplit('/', 1)[0] + '/'
                    ort_node['url'] = ort_url
                    archiv_node['url'] = dioe_url
                    lines.append('\t'.join([land, archiv, dioe_url, ort,
                        ort_url, buch.get('signatur',''), buch.get('typ',''),
                        buch.get('zeitraum',''), buch.get('url','')]))
        tree_path = filename.with_name(filename.stem + '-hierarchie.json')
        tree_path.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding='utf-8')
        txt_tmp = txt.with_suffix('.txt.tmp')
        txt_tmp.write_text('\n'.join(lines) + ('\n' if lines else ''), encoding='utf-8')
        os.replace(txt_tmp, txt)
        report = filename.with_suffix('.status.json')
        report.write_text(json.dumps({'land':land, 'vollstaendig':not incomplete and not errors,
                           'anzahl_buecher':len(lines), 'fehler':errors}, ensure_ascii=False, indent=2), encoding='utf-8')

    def delete_json_file(self):
        land = self.combo_land.get()
        if not land or land == "Bitte wählen...":
            messagebox.showwarning("Hinweis", "Bitte wähle zuerst das Land aus, dessen lokale Daten gelöscht werden sollen.")
            return

        filename = self.get_filename_for_land(land)
        if os.path.exists(filename):
            confirm = messagebox.askyesno(
                "Datenbank löschen",
                f"Möchtest du die lokale Datei für '{land}' ({filename}) wirklich unwiderruflich löschen?"
            )
            if confirm:
                try:
                    os.remove(filename)
                    if land in self.db_data:
                        del self.db_data[land]
                    
                    self.combo_land.set("Bitte wählen...")
                    self.reset_dropdowns(from_step=2)
                    
                    laender = sorted(list(self.db_data.keys()))
                    komplette_liste = sorted(list(set(self.laender_liste + laender)))
                    self.combo_land.configure(values=komplette_liste)
                    
                    self.status_label.configure(text=f"🗑️ Daten für {land} gelöscht.")
                    messagebox.showinfo("Erfolg", f"Lokale Daten für {land} erfolgreich gelöscht.")
                except Exception as e:
                    messagebox.showerror("Fehler", f"Datei konnte nicht gelöscht werden:\n{e}")
        else:
            messagebox.showwarning("Hinweis", f"Keine lokale Datei für '{land}' gefunden ({filename}).")

    # -----------------------------------------------------------------
    # Scraping (Thread-sicher)
    # -----------------------------------------------------------------
    def force_land_refresh(self):
        land = self.combo_land.get()
        if land in self.laender_liste or land in self.db_data:
            parser_land = "Österreich" if "österreich" in land.lower() or "oesterreich" in land.lower() else land
            self.start_live_scraping(parser_land)
        else:
            messagebox.showwarning("Fehler", "Bitte wählen Sie zuerst ein gültiges Land aus.")

    def start_live_scraping(self, land):
        self.btn_refresh_land.configure(state="disabled")
        self.btn_delete_json.configure(state="disabled")
        threading.Thread(target=self.scraping_worker, args=(land,), daemon=True).start()

    def scraping_worker(self, land):
        try:
            land_clean = re.sub(r"\s*\(.*?\)", "", land).strip()
            # Erst vorhandenen Katalog als Checkpoint verwenden. Bereits gefundene
            # Bücher bleiben bei Netzwerkfehlern erhalten.
            existing = dict(self.db_data.get(land_clean, {}))
            extracted_data = self.parser.scrape_land_live(
                land_clean,
                lambda text: self.after(0, lambda t=text: self.set_status(t, busy=True)),
                checkpoint=existing
            )
            self.db_data[land_clean] = extracted_data
            self.save_json_data(land_clean, extracted_data, self.parser.errors)
            self.after(0, lambda: self.scraping_finished_success(land_clean))
        except Exception as e:
            error_msg = str(e)
            land_clean = re.sub(r"\s*\(.*?\)", "", land).strip()
            if 'existing' in locals() and existing:
                self.db_data[land_clean] = existing
                try:
                    self.save_json_data(land_clean, existing, self.parser.errors + [error_msg], incomplete=True)
                except Exception as save_error:
                    error_msg += f"; Speichern fehlgeschlagen: {save_error}"
            self.after(0, lambda msg=error_msg: self.scraping_finished_error(msg))

    def scraping_finished_success(self, land):
        self.set_status("Bereit.")
        self.btn_refresh_land.configure(state="normal")
        self.btn_delete_json.configure(state="normal")
        msg = (f"Die Bestandsdaten für '{land}' wurden gespeichert.\n"
               f"JSON + TXT + status.json im Programmordner.\n"
               f"Fehler/Warnungen: {len(self.parser.errors)}")
        if self.parser.errors:
            messagebox.showwarning("Scan nur teilweise bestätigt", msg)
        else:
            messagebox.showinfo("Scraping beendet", msg)
        self.load_json_data(silent=True)

    def scraping_finished_error(self, error_msg):
        self.set_status("Fehler beim Scannen.")
        self.btn_refresh_land.configure(state="normal")
        self.btn_delete_json.configure(state="normal")
        messagebox.showerror("Scraping abgebrochen", f"Ein Fehler ist aufgetreten:\n{error_msg}")

    # -----------------------------------------------------------------
    # Export & Zwischenablage
    # -----------------------------------------------------------------
    def copy_url_to_clipboard(self):
        land = self.combo_land.get()
        dioezese = self.combo_dioezese.get()
        ort = self.combo_ort.get()
        buch = self.combo_buch.get()
        if (land in self.db_data and dioezese in self.db_data[land]
                and ort in self.db_data[land][dioezese]):
            buecher = self.db_data[land][dioezese][ort]
            selected = next((b for b in buecher if b.get("titel") == buch), None)
            if selected and selected.get("url"):
                self.clipboard_clear()
                self.clipboard_append(selected["url"])
                self.update_idletasks()
                self.set_status("📋 URL erfolgreich in die Zwischenablage kopiert.")
                return
        messagebox.showwarning("Fehler", "Bitte wählen Sie zuerst ein Kirchenbuch aus.")

    def export_to_excel(self):
        land = self.combo_land.get()
        dioezese = self.combo_dioezese.get()
        ort = self.combo_ort.get()
        if (land in self.db_data and dioezese in self.db_data[land]
                and ort in self.db_data[land][dioezese]):
            buecher = self.db_data[land][dioezese][ort]
            if not buecher:
                messagebox.showwarning("Export fehlgeschlagen",
                                       "Keine Bücher für diesen Ort vorhanden.")
                return

            safe_name = re.sub(r'[\\/:*?"<>|]', "_", f"Matricula_{land}_{dioezese}_{ort}.xlsx")
            filepath = filedialog.asksaveasfilename(
                defaultextension=".xlsx", filetypes=[("Excel-Dateien", "*.xlsx")],
                initialfile=safe_name.replace(" ", "_"),
                title="Excel-Linkliste exportieren"
            )
            if filepath:
                try:
                    data_list = [{
                        "Land": land, "Diözese_Archiv": dioezese, "Ort_Pfarrei": ort,
                        "Buch_Titel": b.get("titel", ""), "Typ": b.get("typ", ""),
                        "Zeitraum": b.get("zeitraum", ""), "Signatur": b.get("signatur", ""),
                        "Direkt_URL": b.get("url", "")
                    } for b in buecher]
                    pd.DataFrame(data_list).to_excel(filepath, index=False)
                    self.set_status("📊 Excel-Export erfolgreich erstellt.")
                    messagebox.showinfo("Export erfolgreich",
                                        f"Die Linkliste für '{ort}' wurde exportiert.")
                except Exception as e:
                    messagebox.showerror("Export-Fehler", str(e))
        else:
            messagebox.showwarning("Fehler", "Bitte wählen Sie einen gültigen Ort aus.")

    def open_help_window(self):
        help_win = ctk.CTkToplevel(self)
        help_win.title("Konzept & Hilfe")
        help_win.geometry("500x350")
        help_win.transient(self)
        help_win.after(100, help_win.grab_set)
        help_text = (
            "🏛️ Matricula Bestandsbrowser - Konzept\n\n"
            "1. Streng datensparend:\n"
            "Es werden niemals Bilder geladen. Rein textbasierte URLs.\n\n"
            "2. Schonendes Indexieren: mindestens drei Sekunden Abstand.\n"
            "Bei HTTP 403/429 wird sofort gestoppt.\n\n"
            "3. JSON/TXT pro Land mit separatem Prüfstatus.\n"
            "Fehlende Bücher werden im Statusbericht vermerkt."
        )
        txt = ctk.CTkTextbox(help_win, font=("Arial", 12))
        txt.pack(fill="both", expand=True, padx=15, pady=15)
        txt.insert("0.0", help_text)
        txt.configure(state="disabled")

    def set_status(self, text, busy=False):
        self.status_label.configure(text=text)
        if busy:
            self.progress_bar.configure(mode="indeterminate")
            self.progress_bar.start()
        else:
            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")
            self.progress_bar.set(0)


if __name__ == "__main__":
    app = MatriculaBrowser()
    app.mainloop()