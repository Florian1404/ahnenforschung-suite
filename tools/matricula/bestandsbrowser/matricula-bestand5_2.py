import os
import json
import re
import time
import random
import threading
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
    def __init__(self):
        self.base_url = "https://data.matricula-online.eu"
        self.main_url = f"{self.base_url}/de/"
        self.session = requests.Session()
        
        # PERFEKTE TARNUNG: Vollständige Header eines echten Google Chrome Browsers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        })
        
    def _get_soup(self, url):
        try:
            # Zufällige Wartezeit zwischen 0.5 und 1.5 Sekunden gegen Muster-Erkennung (WAF)
            time.sleep(random.uniform(0.5, 1.5)) 
            res = self.session.get(url, timeout=15)
            
            if res.status_code == 403:
                raise PermissionError("Zugriff verweigert (HTTP 403 Forbidden).\nDeine IP wurde eventuell temporär blockiert. Nutze einen VPN oder starte deinen Router neu.")
            if res.status_code != 200:
                return None
                
            return BeautifulSoup(res.text, 'html.parser')
        except requests.RequestException:
            return None

    def _iter_paginated(self, start_url, max_pages=200):
        visited = set()
        queue = [start_url]
        while queue and len(visited) < max_pages:
            url = queue.pop(0)
            if url in visited:
                continue
            visited.add(url)
            soup = self._get_soup(url)
            if soup is None:
                continue
            yield soup
            base_path = urlparse(start_url).path
            for a in soup.select("a[href]"):
                href = a.get("href", "").strip()
                if "?page=" in href or "&page=" in href:
                    full = urljoin(url, href)
                    if urlparse(full).path == base_path and full not in visited:
                        queue.append(full)

    def _is_valid_link(self, href, text):
        if not href or not text or "#" in href:
            return False
        text_lower = text.strip().lower()
        if "{" in text or "}" in text:
            return False
        
        # Exakter Abgleich für Systemlinks
        exact_blacklist = {
            "anmelden", "impressum", "datenschutz", "matricula", "bestände",
            "landkarte", "ortssuche", "deutsch", "english", "slovenščina",
            "česky", "italiano", "kontakt", "unterstützen",
            "allgemeine infos", "nutzungsbedingungen", "hilfe", "zum inhalt springen",
            "weiter", "zurück", "nächste", "vorherige", "«", "»"
        }
        if text_lower in exact_blacklist:
            return False
            
        # Teilstring-Sperren für Navigations-Reste
        substring_blacklist = ["zum inhalt springen", "nutzungsbedingungen"]
        if any(x in text_lower for x in substring_blacklist):
            return False
            
        return True

    def _get_alphabetical_links(self, base_url, soup):
        """Erkennt, ob eine Diözese ein A-Z Register besitzt und extrahiert die Links."""
        alpha_links = {}
        base_path = urlparse(base_url).path.rstrip("/") + "/"
        for a in soup.select("a[href]"):
            href = a.get("href", "").strip()
            text = a.get_text(strip=True)
            if len(text) == 1 and text.isupper() and text.isalpha():
                full_url = urljoin(base_url, href)
                full_path = urlparse(full_url).path.rstrip("/") + "/"
                if full_path.startswith(base_path) and len(full_path.replace(base_path, "").strip("/")) == 1:
                    alpha_links[text] = full_url
        return alpha_links

    def _collect_sublinks(self, parent_url, soups):
        links = {}
        parent_path = urlparse(parent_url).path.rstrip("/") + "/"
        for soup in soups:
            for a in soup.select("a[href]"):
                href = a.get("href", "").strip()
                text = a.get_text(" ", strip=True).strip()
                if not self._is_valid_link(href, text):
                    continue
                full_url = urljoin(parent_url, href)
                full_path = urlparse(full_url).path
                if not full_path.startswith(parent_path):
                    continue
                if full_path.rstrip("/") + "/" == parent_path:
                    continue
                if "?page=" in full_url:
                    continue
                if any(x in full_url.lower() for x in ["facebook", "twitter", "browser"]):
                    continue
                clean_name = re.sub(r"^\d+\s*", "", text).strip()
                
                # Buchstaben-Index-Links herausfiltern (z.B. "A", "B" etc.)
                if len(clean_name) == 1 and clean_name.isupper():
                    continue
                    
                if clean_name and full_url not in links.values():
                    links[clean_name] = full_url
        return links

    def scrape_land_live(self, land_klartext, status_callback):
        """EXTRAKTOR-LOGIK: Holt die Bestandsstruktur eines Landes."""
        status_callback("🌐 Ermittle Länder-URL...")
        land_clean = re.sub(r"\s*\(.*?\)", "", land_klartext).strip()
        such_begriff = land_clean.lower()
        
        if such_begriff in self.slug_map:
            slug = self.slug_map[such_begriff]
            land_url = f"{self.base_url}/de/{slug}/"
        else:
            slug = (such_begriff
                    .replace("ö", "oesterreich" if such_begriff == "österreich" else "oe")
                    .replace("ä", "ae")
                    .replace("ü", "ue")
                    .replace("ß", "ss"))
            land_url = f"{self.base_url}/de/{slug}/"

        status_callback(f"🌐 Öffne Länderseite: {land_url}")

        land_soups = list(self._iter_paginated(land_url))
        if not land_soups:
            raise Exception(f"Länderseite nicht erreichbar oder keine Daten unter:\n{land_url}")

        dioezesen_links = self._collect_sublinks(land_url, land_soups)
        total_dioe = len(dioezesen_links)
        if total_dioe == 0:
            raise Exception(f"Keine gültigen Diözesen gefunden.\nURL: {land_url}")

        land_dict = {}

        for idx_d, (d_name, d_url) in enumerate(sorted(dioezesen_links.items()), 1):
            status_callback(f"🌐 [{idx_d}/{total_dioe}] Scanne Archiv: {d_name}...")
            land_dict[d_name] = {}

            dioe_soups = list(self._iter_paginated(d_url))
            if not dioe_soups:
                continue

            # PRÜFUNG AUF A-Z REGISTER (für Österreich / Deutschland essenziell)
            alpha_links = self._get_alphabetical_links(d_url, dioe_soups[0])
            orte_links = {}

            if alpha_links:
                total_alphas = len(alpha_links)
                for idx_a, (letter, alpha_url) in enumerate(sorted(alpha_links.items()), 1):
                    status_callback(f"🌐 [{idx_d}/{total_dioe}] {d_name} → Register '{letter}' ({idx_a}/{total_alphas})...")
                    alpha_soups = list(self._iter_paginated(alpha_url))
                    sub_orte = self._collect_sublinks(alpha_url, alpha_soups)
                    orte_links.update(sub_orte)
            else:
                orte_links = self._collect_sublinks(d_url, dioe_soups)

            total_orte = len(orte_links)
            
            for idx_o, (o_name, o_url) in enumerate(sorted(orte_links.items()), 1):
                status_callback(
                    f"🌐 [{idx_d}/{total_dioe}] {d_name} → "
                    f"[{idx_o}/{total_orte}] {o_name}"
                )
                land_dict[d_name][o_name] = []

                for soup_ort in self._iter_paginated(o_url):
                    for row in soup_ort.select("table tr"):
                        if row.find("th"):  # Tabellenkopf überspringen
                            continue
                        cols = row.find_all("td")
                        if len(cols) < 3:
                            continue
                        try:
                            first_td = cols[0]
                            titel_a = first_td.find("a")

                            titel_text = (titel_a.get_text(strip=True)
                                          if titel_a else first_td.get_text(strip=True))
                            url_text = (urljoin(o_url, titel_a.get('href'))
                                        if titel_a and titel_a.get('href') else o_url)

                            typ_text = cols[1].get_text(strip=True) if len(cols) > 1 else "N/A"
                            zeitraum_text = cols[2].get_text(strip=True) if len(cols) > 2 else "N/A"
                            signatur_text = cols[3].get_text(strip=True) if len(cols) > 3 else "N/A"

                            if not titel_text:
                                continue

                            land_dict[d_name][o_name].append({
                                "titel": titel_text,
                                "typ": typ_text,
                                "zeitraum": zeitraum_text,
                                "signatur": signatur_text,
                                "url": url_text
                            })
                        except Exception:
                            continue

                if not land_dict[d_name][o_name]:
                    del land_dict[d_name][o_name]

            if not land_dict[d_name]:
                del land_dict[d_name]

        if not land_dict:
            raise Exception("Scan abgeschlossen, aber keine Kirchenbücher gefunden.")
        return land_dict


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

    def save_json_data(self, land):
        """Speichert die Länderstruktur sauber ab."""
        try:
            filename = self.get_filename_for_land(land)
            land_data = {land: self.db_data.get(land, {})}
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(land_data, f, ensure_ascii=False, indent=4)
        except Exception as e:
            messagebox.showerror("Fehler", f"Fehler beim Speichern der JSON für {land}:\n{e}")

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
            extracted_data = self.parser.scrape_land_live(
                land,
                lambda text: self.after(0, lambda t=text: self.set_status(t, busy=True))
            )
            
            land_clean = re.sub(r"\s*\(.*?\)", "", land).strip()
            self.db_data[land_clean] = extracted_data
            self.save_json_data(land_clean)
            
            self.after(0, lambda: self.scraping_finished_success(land_clean))
        except Exception as e:
            error_msg = str(e)
            self.after(0, lambda msg=error_msg: self.scraping_finished_error(msg))

    def scraping_finished_success(self, land):
        self.set_status("Bereit.")
        self.btn_refresh_land.configure(state="normal")
        self.btn_delete_json.configure(state="normal")
        messagebox.showinfo("Scraping beendet",
                            f"Die Bestandsdaten für '{land}' wurden erfolgreich extrahiert.")
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
            "2. IP-Schutz durch Live-Scraping pro Land:\n"
            "Keine Massen-Downloads. Live-Update findet nur gezielt pro Land statt.\n\n"
            "3. Schnittstelle für Downloader:\n"
            "Generiert einen gezielten Excel-Export (.xlsx) für separate Download-Skripte."
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