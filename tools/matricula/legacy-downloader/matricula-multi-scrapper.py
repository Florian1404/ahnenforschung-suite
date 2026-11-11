import os, re, sys, queue, shutil, subprocess, threading, time
from pathlib import Path
from io import BytesIO
from tkinter import filedialog, messagebox
import tkinter as tk
import customtkinter as ctk
import img2pdf
from pypdf import PdfReader, PdfWriter

# Versuchen, openpyxl für Excel-Support zu laden
try:
    import openpyxl
    HAS_EXCEL = True
except ImportError:
    HAS_EXCEL = False

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")
EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".jp2", ".j2k"}

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Matricula Downloader (Queue Mode)")
        self.geometry("900x650")
        self.minsize(820, 580)
        self.q = queue.Queue()
        self.proc = None
        self.busy = False
        self.cancelled = False
        self.in_cooldown = False
        
        self.url = tk.StringVar()
        self.folder = tk.StringVar(value=str(Path.home() / "Downloads" / "Matricula"))
        self.mode = tk.StringVar(value="📥 Matricula laden")
        self.autopdf = tk.BooleanVar(value=False)
        self.pdf_source = tk.StringVar()
        self.pdf_file = tk.StringVar()
        
        self.build()
        self.after(80, self.events)

    def build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        m = ctk.CTkFrame(self, corner_radius=16)
        m.grid(row=0, column=0, padx=16, pady=16, sticky="nsew")
        m.grid_columnconfigure(0, weight=1)
        m.grid_rowconfigure(5, weight=1)

        h = ctk.CTkFrame(m, fg_color="transparent")
        h.grid(row=0, column=0, padx=22, pady=(15, 6), sticky="ew")
        h.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(h, text="Matricula Downloader", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(h, text="Kirchenbücher einzeln, als Liste (TXT/XLSX) oder kopiert laden", text_color="gray65").grid(row=1, column=0, sticky="w")
        ctk.CTkButton(h, text="?", width=38, height=32, command=self.help).grid(row=0, column=1, rowspan=2, padx=(8, 0))

        self.tabs = ctk.CTkSegmentedButton(m, values=["📥 Matricula laden", "📄 PDF erstellen"], variable=self.mode, command=self.switch)
        self.tabs.grid(row=1, column=0, padx=22, pady=(6, 10), sticky="ew")

        self.df = ctk.CTkFrame(m, fg_color="transparent")
        self.df.grid(row=2, column=0, padx=22, sticky="ew")
        self.df.grid_columnconfigure(0, weight=1)
        self.pf = ctk.CTkFrame(m, fg_color="transparent")
        self.pf.grid(row=2, column=0, padx=22, sticky="ew")
        self.pf.grid_columnconfigure(0, weight=1)
        self.pf.grid_remove()
        
        self.build_download()
        self.build_pdf()

        self.log = ctk.CTkTextbox(m, height=120, corner_radius=10, font=ctk.CTkFont(family="Consolas", size=11))
        self.log.grid(row=5, column=0, padx=22, pady=(8, 5), sticky="nsew")
        self.log.configure(state="disabled")
        self.write("Bereit.")

        p = ctk.CTkFrame(m, fg_color="transparent")
        p.grid(row=6, column=0, padx=22, sticky="ew")
        p.grid_columnconfigure(0, weight=1)
        self.bar = ctk.CTkProgressBar(p, height=12)
        self.bar.grid(row=0, column=0, sticky="ew")
        self.bar.set(0)
        self.plabel = ctk.CTkLabel(p, text="Bereit", width=130)
        self.plabel.grid(row=0, column=1, padx=(10, 0))

        b = ctk.CTkFrame(m, fg_color="transparent")
        b.grid(row=7, column=0, padx=22, pady=(8, 15), sticky="ew")
        b.grid_columnconfigure(0, weight=1)
        self.start = ctk.CTkButton(b, text="⬇ Download / Queue starten", height=42, font=ctk.CTkFont(weight="bold"), command=self.start_download)
        self.start.grid(row=0, column=0, sticky="ew")
        self.pdfbutton = ctk.CTkButton(b, text="PDF erstellen", height=42, font=ctk.CTkFont(weight="bold"), command=self.folder_to_pdf)
        self.pdfbutton.grid(row=0, column=0, sticky="ew")
        self.pdfbutton.grid_remove()
        self.reset = ctk.CTkButton(b, text="Reset", width=95, height=42, command=self.reset_fields)
        self.reset.grid(row=0, column=1, padx=(8, 0))
        self.stop = ctk.CTkButton(b, text="■ Abbruch", width=120, height=42, fg_color="#B3261E", hover_color="#8C1D18", command=self.cancel, state="disabled")
        self.stop.grid(row=0, column=2, padx=(8, 0))
    def build_download(self):
        ctk.CTkLabel(self.df, text="Matricula-URLs (getrennt durch Komma/Leerzeichen ODER XLS/TXT-Dateipfad)", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, pady=(0, 4), sticky="w")
        f = ctk.CTkFrame(self.df, fg_color="transparent")
        f.grid(row=1, column=0, sticky="ew")
        f.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(f, textvariable=self.url, height=38, placeholder_text="URL1, URL2 ODER Pfad zu einer .txt/.xlsx Datei").grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(f, text="📄 Liste / Excel", width=100, height=38, command=self.select_list_file).grid(row=0, column=1, padx=(7, 0))
        
        ctk.CTkLabel(self.df, text="Basis-Speicherordner", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, pady=(9, 4), sticky="w")
        f2 = ctk.CTkFrame(self.df, fg_color="transparent")
        f2.grid(row=3, column=0, sticky="ew")
        f2.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(f2, textvariable=self.folder, height=38).grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(f2, text="📁", width=55, height=38, command=self.select_folder).grid(row=0, column=1, padx=(7, 0))
        ctk.CTkCheckBox(self.df, text="Nach Download automatisch PDF erstellen", variable=self.autopdf).grid(row=4, column=0, pady=(9, 0), sticky="w")

    def build_pdf(self):
        ctk.CTkLabel(self.pf, text="Bilder-Ordner", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, pady=(0, 4), sticky="w")
        f = ctk.CTkFrame(self.pf, fg_color="transparent")
        f.grid(row=1, column=0, sticky="ew")
        f.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(f, textvariable=self.pdf_source, height=38, placeholder_text="Ordner mit Kirchenbuchbildern").grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(f, text="📁", width=55, height=38, command=self.choose_source).grid(row=0, column=1, padx=(7, 0))
        ctk.CTkLabel(self.pf, text="PDF-Dateiname", font=ctk.CTkFont(weight="bold")).grid(row=2, column=0, pady=(9, 4), sticky="w")
        f = ctk.CTkFrame(self.pf, fg_color="transparent")
        f.grid(row=3, column=0, sticky="ew")
        f.grid_columnconfigure(0, weight=1)
        ctk.CTkEntry(f, textvariable=self.pdf_file, height=38).grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(f, text="📁", width=55, height=38, command=self.choose_target).grid(row=0, column=1, padx=(7, 0))
        self.pdfstats = ctk.CTkLabel(self.pf, text="Noch kein Ordner ausgewählt.", text_color="gray65")
        self.pdfstats.grid(row=4, column=0, pady=(8, 0), sticky="w")

    def switch(self, v):
        if self.busy: return
        if v == "📥 Matricula laden":
            self.pf.grid_remove(); self.df.grid(); self.start.grid(); self.pdfbutton.grid_remove()
        else:
            self.df.grid_remove(); self.pf.grid(); self.start.grid_remove(); self.pdfbutton.grid()

    def write(self, s):
        self.log.configure(state="normal"); self.log.insert("end", s + "\n"); self.log.see("end"); self.log.configure(state="disabled")

    def select_folder(self):
        x = filedialog.askdirectory(title="Speicherordner auswählen")
        if x: self.folder.set(x)

    def select_list_file(self):
        x = filedialog.askopenfilename(title="Datei mit URLs auswählen", filetypes=[("Unterstützte Listen", "*.txt *.xlsx *.xls")])
        if x: self.url.set(x)

    def choose_source(self):
        x = filedialog.askdirectory(title="Bilder-Ordner auswählen")
        if x:
            self.pdf_source.set(x); imgs = self.images(x); self.set_pdf_name(x)
            self.pdfstats.configure(text=f"{len(imgs)} Bilddateien gefunden")

    def choose_target(self):
        x = filedialog.asksaveasfilename(title="PDF speichern", defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile=Path(self.pdf_file.get()).name or "Kirchenbuch.pdf")
        if x: self.pdf_file.set(x)

    def scraper(self):
        exe = shutil.which("matricula-online-scraper")
        return [exe] if exe else [sys.executable, "-m", "matricula_online_scraper"]

    def env(self):
        e = os.environ.copy(); e["PYTHONUNBUFFERED"] = "1"; e["PYTHONWARNINGS"] = "ignore::UserWarning"; return e

    def extract_urls(self, text):
        # Findet jede URL, die mit der Matricula-Domain beginnt, unabhängig von Zeichen drumherum
        return re.findall(r'(https://data\.matricula-online\.eu/\S+)', text)

    def start_download(self):
        target = self.url.get().strip()
        if self.busy: return
        
        urls = []
        
        # Fall 1: Eingabe ist eine Excel-Datei
        if os.path.isfile(target) and (target.lower().endswith('.xlsx') or target.lower().endswith('.xls')):
            if not HAS_EXCEL:
                messagebox.showerror("Fehler", "Für Excel-Dateien wird das Paket 'openpyxl' benötigt.\nBitte installiere es im Terminal via: pip install openpyxl"); return
            try:
                wb = openpyxl.load_workbook(target, data_only=True)
                for sheet in wb.worksheets:
                    for row in sheet.iter_rows(values_only=True):
                        for cell in row:
                            if cell and isinstance(cell, str):
                                found = self.extract_urls(cell)
                                if found: urls.extend(found)
                if not urls:
                    messagebox.showwarning("Leere Excel", "Keine gültigen Matricula-URLs in der Excel-Tabelle gefunden."); return
                self.write(f"📊 Excel geladen: {len(urls)} URLs extrahiert.")
            except Exception as e:
                messagebox.showerror("Fehler", f"Excel-Datei konnte nicht gelesen werden: {e}"); return
                
        # Fall 2: Eingabe ist eine Textdatei
        elif os.path.isfile(target) and target.lower().endswith('.txt'):
            try:
                with open(target, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                    urls = self.extract_urls(content)
                if not urls:
                    messagebox.showwarning("Leere Liste", "Keine gültigen Matricula-URLs in der Textdatei gefunden."); return
                self.write(f"📋 Textdatei geladen: {len(urls)} URLs extrahiert.")
            except Exception as e:
                messagebox.showerror("Fehler", f"Datei konnte nicht gelesen werden: {e}"); return
                
        # Fall 3: URLs wurden direkt (ggf. mehrfach und formatiert) ins Feld kopiert
        else:
            urls = self.extract_urls(target)
            if not urls:
                messagebox.showwarning("Eingabe-Fehler", "Keine gültige Matricula-URL erkannt.\n\nHinweis: URLs müssen mit 'https://matricula-online.eu' beginnen."); return
            self.write(f"✏️ {len(urls)} URL(s) direkt aus dem Eingabefeld übernommen.")

        # Bereinigung: Doppelte Einträge unter Beibehaltung der Reihenfolge entfernen
        seen = set()
        urls = [x for x in urls if not (x in seen or seen.add(x))]

        base_folder = Path(self.folder.get())
        base_folder.mkdir(parents=True, exist_ok=True)
        
        self.busy = True
        self.cancelled = False
        self.controls(False)
        self.bar.set(0)
        
        threading.Thread(target=self.queue_manager, args=(urls, base_folder), daemon=True).start()

    def queue_manager(self, urls, base_folder):
        total = len(urls)
        for index, url in enumerate(urls, 1):
            if self.cancelled: break
            
            self.write(f"🔄 Vorbereitung [{index}/{total}]: {url}")
            self.q.put(("status_update", f"Download {index}/{total}…"))
            
            self.download_single(url, base_folder)
            
            if index < total and not self.cancelled:
                self.in_cooldown = True
                cooldown_time = 120
                self.write(f"⏱ Download [{index}/{total}] fertig. Starte 2 Minuten Pause zum Schutz vor Server-Sperren...")
                
                while cooldown_time > 0 and not self.cancelled:
                    mins, secs = divmod(cooldown_time, 60)
                    self.q.put(("cooldown_tick", (mins, secs, cooldown_time / 120.0)))
                    time.sleep(1)
                    cooldown_time -= 1
                    
                self.in_cooldown = False
                if self.cancelled: break

        if self.cancelled:
            self.q.put(("cancelled", None))
        else:
            self.q.put(("queue_done", f"Alle {total} Downloads erfolgreich verarbeitet!"))
    def download_single(self, url, base_folder):
        try:
            self.proc = subprocess.Popen(
                self.scraper() + ["parish", "fetch", url],
                cwd=base_folder,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=self.env()
            )
            
            for line in self.proc.stdout:
                if self.cancelled: break
                m = re.search(r"(\d+)\s*/\s*(\d+)", line)
                if m: self.q.put(("progress", (int(m.group(1)), int(m.group(2)))))
            
            if self.cancelled:
                if self.proc.poll() is None: self.proc.terminate()
                return
                
            code = self.proc.wait()
            if code == 0:
                self.q.put(("single_done", (url, base_folder)))
            else:
                self.q.put(("error_logged", f"Fehler bei URL (Exit-Code {code}): {url}"))
        except Exception as e:
            self.q.put(("error_logged", f"Fehler: {str(e)} bei {url}"))
        finally:
            self.proc = None

    def post_download_pdf_generation(self, url, base_folder):
        subfolders = [f for f in base_folder.iterdir() if f.is_dir()]
        if not subfolders: return
        latest_folder = max(subfolders, key=os.path.getmtime)
        
        if self.images(latest_folder):
            self.write(f"📄 Erstelle PDF für {latest_folder.name}...")
            self.set_pdf_name(latest_folder)
            self.make_pdf_sync(latest_folder, self.pdf_file.get())

    def make_pdf_sync(self, folder, out):
        imgs = self.images(folder)
        if not imgs: return
        out = Path(out).with_suffix(".pdf")
        writer = PdfWriter()
        try:
            for i, img in enumerate(imgs, 1):
                if self.cancelled: return
                r = PdfReader(BytesIO(img2pdf.convert(str(img))))
                for page in r.pages: writer.add_page(page)
                self.q.put(("progress", (i, len(imgs))))
            with open(out, "wb") as f: writer.write(f)
            self.q.put(("status_update", "PDF fertig!"))
        except Exception as e:
            try: out.unlink(missing_ok=True)
            except: pass
            self.q.put(("error_logged", f"PDF-Fehler bei {folder.name}: {e}"))

    def images(self, folder):
        return sorted([p for p in Path(folder).rglob("*") if p.is_file() and p.suffix.lower() in EXT], key=lambda p: [int(x) if x.isdigit() else x.lower() for x in re.split(r"(\d+)", p.name)])

    def clean(self, s):
        return re.sub(r'[<>:"/\\|?*]', '_', str(s)).strip(" ._") or "Kirchenbuch"

    def derive_name(self, folder):
        imgs = self.images(folder)
        if not imgs: return "Kirchenbuch.pdf"
        n = imgs[0].stem
        
        # 1. Eindeutige vorangestellte Nummerierung extrahieren (z. B. "01-15")
        num_prefix = ""
        prefix_match = re.match(r"^(\d+-\d+|\d+)_", n)
        if prefix_match:
            num_prefix = prefix_match.group(1) + " - "

        # 2. Die Jahreszahlen aus dem Dateinamen extrahieren
        m = re.search(r"_(\d{4})_(\d{4})", n)
        if m: 
            return self.clean(f"{num_prefix}{m.group(1)}-{m.group(2)}") + ".pdf"
            
        # Fallback falls kein Jahreszahl-Format matcht: Nutze die Nummerierung + Ordnername
        return self.clean(f"{num_prefix}{Path(folder).name}") + ".pdf"

    def set_pdf_name(self, folder):
        self.pdf_file.set(str(Path(folder) / self.derive_name(folder)))

    def make_pdf(self, folder, out):
        imgs = self.images(folder)
        if not imgs: self.q.put(("error", "Keine Bilder gefunden.")); return
        out = Path(out).with_suffix(".pdf"); writer = PdfWriter(); self.q.put(("pdf_start", len(imgs)))
        try:
            for i, img in enumerate(imgs, 1):
                if self.cancelled: self.q.put(("cancelled", None)); return
                r = PdfReader(BytesIO(img2pdf.convert(str(img))))
                for page in r.pages: writer.add_page(page)
                self.q.put(("pdf_progress", (i, len(imgs))))
            with open(out, "wb") as f: writer.write(f)
            self.q.put(("pdf_done", (out, len(imgs), out.stat().st_size / 1024 / 1024)))
        except Exception as e:
            try: out.unlink(missing_ok=True)
            except: pass
            self.q.put(("error", f"PDF-Fehler: {e}"))

    def folder_to_pdf(self):
        if self.busy: return
        folder = self.pdf_source.get().strip()
        if not folder:
            folder = filedialog.askdirectory(title="Bilder-Ordner auswählen")
            if not folder: return
            self.pdf_source.set(folder)
        imgs = self.images(folder)
        if not imgs:
            messagebox.showwarning("Keine Bilder", "Keine unterstützten Bilder gefunden."); return
        self.set_pdf_name(folder); self.busy = True; self.cancelled = False; self.controls(False); self.bar.set(0); self.plabel.configure(text=f"Seite 0 / {len(imgs)}"); self.write(f"📄 PDF-Erstellung gestartet – {len(imgs)} Seiten")
        threading.Thread(target=self.make_pdf, args=(folder, self.pdf_file.get()), daemon=True).start()

    def controls(self, on):
        s = "normal" if on else "disabled"
        for x in [self.tabs, self.start, self.pdfbutton]: x.configure(state=s)
        self.stop.configure(state="disabled" if on else "normal")

    def cancel(self):
        self.cancelled = True
        if self.proc and self.proc.poll() is None:
            try: self.proc.terminate()
            except: pass

    def finish(self, ok, msg):
        self.busy = False; self.controls(True); self.bar.set(1 if ok else 0); self.plabel.configure(text="Fertig" if ok else "Fehler"); self.write(("✓ " if ok else "✗ ") + msg)
        (messagebox.showinfo if ok else messagebox.showerror)("Matricula Downloader", msg)

    def events(self):
        try:
            while True:
                t, d = self.q.get_nowait()
                if t == "progress":
                    a, b = d; self.bar.set(a / b if b else 0); self.plabel.configure(text=f"Seite {a} / {b}")
                elif t == "status_update":
                    self.plabel.configure(text=d)
                elif t == "cooldown_tick":
                    mins, secs, progress = d
                    self.bar.set(progress)
                    self.plabel.configure(text=f"Pause: {mins:02d}:{secs:02d}")
                elif t == "single_done":
                    url, b_folder = d
                    self.write(f"✓ Download fertig: {url}")
                    if self.autopdf.get():
                        self.post_download_pdf_generation(url, b_folder)
                elif t == "error_logged":
                    self.write(f"⚠️ {d}")
                elif t == "queue_done":
                    self.finish(True, d)
                elif t == "pdf_start":
                    self.plabel.configure(text=f"Seite 0 / {d}"); self.bar.set(0)
                elif t == "pdf_progress":
                    a, b = d; self.bar.set(a / b); self.plabel.configure(text=f"Seite {a} / {b}")
                elif t == "pdf_done":
                    p, n, s = d; self.finish(True, f"PDF erfolgreich erstellt.\n\n{p}\n\n{n} Seiten | {s:.1f} MB")
                elif t == "error": self.finish(False, d)
                elif t == "cancelled":
                    self.busy = False; self.controls(True); self.plabel.configure(text="Abgebrochen"); self.write("Abgebrochen.")
        except queue.Empty: pass
        self.after(80, self.events)

    def help(self):
        w = ctk.CTkToplevel(self); w.title("Hilfe"); w.geometry("620x560"); w.transient(self)
        t = ctk.CTkTextbox(w, wrap="word"); t.pack(fill="both", expand=True, padx=18, pady=18)
        t.insert("1.0", "MATRICULA DOWNLOADER (QUEUE MODE)\n\n📥 UNTERSTÜTZTE EINGABEMETHODEN\n\n1. Direktes Kopieren:\nKopiere eine oder mehrere URLs direkt in das Textfeld. Mehrere Links können durch Kommas, Leerzeichen oder Zeilenumbrüche getrennt sein. Das Skript bereinigt die Links automatisch.\n\n2. Excel-Listen (.xlsx / .xls):\nErstelle eine Excel-Tabelle und füge deine Links in beliebige Zellen ein. Klicke auf '📄 Liste / Excel', um die Datei zu laden. Das Skript durchsucht alle Tabellenblätter.\n\n3. Text-Listen (.txt):\nEine klassische Textdatei mit einer URL pro Zeile.\n\nPAUSEN-SYSTEM\nNach jedem Buch wird automatisch eine Pause von 2 Minuten eingelegt, um die Server-Fairness zu wahren.\n\nPDF-NAMEN\nDer Dateiname zieht sich die vorangestellte Nummer (z. B. '01-15') vom ersten Bild sowie die Jahreszahlen heraus. Format: '01-15 - 1820-1845.pdf'.")
        t.configure(state="disabled"); ctk.CTkButton(w, text="Schließen", command=w.destroy).pack(pady=(0, 18))

    def reset_fields(self):
        if self.busy: return
        self.url.set("")
        self.folder.set(str(Path.home() / "Downloads" / "Matricula"))
        self.pdf_source.set("")
        self.pdf_file.set("")
        self.autopdf.set(True)
        self.bar.set(0)
        self.plabel.configure(text="Bereit")
        self.pdfstats.configure(text="Noch kein Ordner ausgewählt.")
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.write("Bereit.")

if __name__ == "__main__":
    App().mainloop()
