#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stammbaum-Bilder: PDFs im Ordner finden, Fotos als PNG exportieren.

Installation:  py -m pip install --upgrade pymupdf
Aufruf:        py stammbaum_bilder.py
Anderer Ordner:py stammbaum_bilder.py "D:\\Stammbaeume"
Einzelne PDF:  py stammbaum_bilder.py "stammbaum-boeck.pdf"
Optionen:      py stammbaum_bilder.py --help

Das Programm verwendet vorhandene PDF-Texte, kein OCR. Zuordnungen sind
heuristisch; unsichere Treffer werden zur manuellen Prüfung abgelegt.
"""
import argparse
import csv
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

try:
    import pymupdf as fitz
except ImportError:
    sys.exit("PyMuPDF fehlt. Installiere es mit: py -m pip install --upgrade pymupdf")

BIRTH = re.compile(
    r"(?i)(?:\bgeb(?:oren)?\.?\s*(?:am\s*)?|\*\s*)"
    r"(?:\d{1,2}[.\-/ ]\d{1,2}[.\-/ ]|\d{1,2}\s+[a-zäöü]+\s+)?"
    r"((?:1[5-9]|20)\d{2})\b"
)
DATE = re.compile(r"\b\d{1,2}[.\-/]\d{1,2}[.\-/]((?:1[5-9]|20)\d{2})\b")
STOP = set("geboren gestorben verstorben heirat heiratete ehe vater mutter eltern sohn tochter "
           "seite familie familienbuch bild foto unbekannt wohnort beruf quelle getauft taufe "
           "partner kinder geb gest name vorname nachname stammbaum nummer geboren am".split())


def safe_filename(value):
    replacements = {"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss"}
    value = "".join(replacements.get(c, c) for c in unicodedata.normalize("NFKC", value))
    value = re.sub(r"[^\w-]+", "_", value, flags=re.UNICODE)
    return value.strip("_-.")[:90] or "Unbekannt"


def folder_for(pdf):
    stem = re.sub(r"(?i)^stammbaum[\s._-]*", "", pdf.stem).strip(" _.-")
    # Orts- und Familienbezeichnungen in Ordnernamen ansprechend schreiben.
    # Die Sonderregel schützt den bekannten Familiennamen Böck.
    parts = re.split(r"[\s._-]+", stem) if stem else ["Unbekannt"]
    parts = ["Böck" if p.casefold() in ("boeck", "böck") else p[:1].upper() + p[1:] for p in parts]
    return pdf.parent / ("Stammbaum " + " ".join(parts) + " Bilder")


def distance(a, b):
    dx = max(a.x0 - b.x1, b.x0 - a.x1, 0)
    dy = max(a.y0 - b.y1, b.y0 - a.y1, 0)
    return (dx * dx + dy * dy) ** 0.5


def extract_page(page, min_pixels, min_display):
    # Ein Durchgang: Bildpositionen und echte Textzeilen, kein OCR.
    lines, images = [], []
    for block in page.get_text("dict")["blocks"]:
        if block.get("type") == 0:
            for line in block.get("lines", []):
                s = " ".join(sp.get("text", "").strip() for sp in line.get("spans", []))
                s = re.sub(r"\s+", " ", s).strip()
                if s:
                    lines.append((fitz.Rect(line["bbox"]), s))
        elif block.get("type") == 1:
            r = fitz.Rect(block["bbox"])
            if (block.get("width", 0) < min_pixels or block.get("height", 0) < min_pixels
                    or r.width < min_display or r.height < min_display):
                continue
            if not 0.35 <= r.width / max(1, r.height) <= 2.3:
                continue
            images.append(r)
    return lines, images


def person_name(raw):
    # Namen vor Lebensdaten erkennen, maximal fünf Wörter.
    s = re.split(r"(?i)\b(?:geb(?:oren)?|gest(?:orben)?|verstorben|heirat(?:ete)?)\b|[(*†]", raw, maxsplit=1)[0]
    s = re.sub(r"\b\d{4}\b", " ", s)
    s = re.sub(r"(?i)^\s*(?:name|person)\s*:\s*", "", s)
    s = re.sub(r"\s+", " ", s).strip(" ,:;–-.")
    words = s.split()
    if not 2 <= len(words) <= 5 or len(s) > 70:
        return None
    if any(not re.fullmatch(r"[A-ZÄÖÜ][\wÄÖÜäöüßÀ-ÿ'’-]*", w) for w in words):
        return None
    if any(w.casefold().strip(".") in STOP for w in words):
        return None
    return (words[0], " ".join(words[1:]))


def closest_person(image, lines, radius):
    neighbors = sorted(((distance(image, rect), rect, s) for rect, s in lines
                        if distance(image, rect) <= radius), key=lambda item: item[0])
    names, years = [], []
    for d, rect, s in neighbors:
        who = person_name(s)
        if who:
            names.append((d, rect, s, who))
        m = BIRTH.search(s)
        if m:
            years.append((d, rect, s, m.group(1), True))
        elif (m := DATE.search(s)) and not re.search(r"(?i)\b(?:gest|gestorben|tod|verstorben)\b|†", s):
            years.append((d, rect, s, m.group(1), False))

    if not names:
        return None, None, "Kein Personenname erkannt", neighbors
    names.sort(key=lambda item: item[0])
    chosen = names[0]
    # Keine willkürliche Wahl zwischen zwei praktisch gleich nahen Namen.
    if len(names) > 1 and names[1][3] != chosen[3] and names[1][0] - chosen[0] < 18:
        return None, None, "Mehrere gleich nahe Namen", neighbors
    if not years:
        return chosen[3], None, "Geburtsjahr fehlt", neighbors

    def year_score(y):
        return distance(chosen[1], y[1]) + y[0] * 0.25 + (0 if y[4] else 30)

    years.sort(key=year_score)
    best = years[0]
    if len(years) > 1 and years[1][3] != best[3] and abs(year_score(years[1]) - year_score(best)) < 15:
        return chosen[3], None, "Mehrere moegliche Geburtsjahre", neighbors
    if not best[4]:
        return chosen[3], best[3], "Datum ohne eindeutige Geburtsangabe", neighbors
    # Ein offensichtlich entferntes Geburtsjahr nicht stillschweigend übernehmen.
    if distance(chosen[1], best[1]) > 85:
        return chosen[3], best[3], "Geburtsjahr zu weit vom Namen", neighbors
    return chosen[3], best[3], "OK", neighbors


def unique_path(folder, stem):
    dest = folder / (stem + ".png")
    n = 2
    while dest.exists():
        dest = folder / f"{stem}_{n:02d}.png"
        n += 1
    return dest


def process_pdf(pdf, args):
    out = folder_for(pdf)
    out.mkdir(parents=True, exist_ok=True)
    review = out / "_Pruefen"
    report = []
    counts = Counter()
    print(f"\nPDF: {pdf.name}")
    try:
        with fitz.open(str(pdf)) as doc:
            if doc.needs_pass:
                print("  Uebersprungen: PDF ist passwortgeschuetzt.")
                return
            for page_no, page in enumerate(doc, 1):
                lines, images = extract_page(page, args.min_pixels, args.min_display)
                for idx, rect in enumerate(images, 1):
                    who, year, status, neighbors = closest_person(rect, lines, args.radius)
                    if status == "OK" and who and year:
                        stem = f"{safe_filename(who[0])}_{safe_filename(who[1])}_{year}"
                        folder = out
                        counts["zugeordnet"] += 1
                    else:
                        stem = f"Unbekannt_Seite_{page_no:03d}_Bild_{idx:02d}"
                        folder = review
                        folder.mkdir(exist_ok=True)
                        counts["pruefen"] += 1
                    dest = unique_path(folder, stem)
                    try:
                        # PNG aus der exakt dargestellten Bildregion, inkl. Transparenzmasken.
                        # Das ist zuverlässiger als die rohen PDF-Bilddaten.
                        pix = page.get_pixmap(matrix=fitz.Matrix(args.dpi / 72, args.dpi / 72),
                                              clip=rect, alpha=False)
                        pix.save(str(dest))
                    except Exception as exc:
                        counts["fehler"] += 1
                        counts["zugeordnet" if folder == out else "pruefen"] -= 1
                        status = f"Fehler beim Speichern: {exc}"
                        dest = None
                    nearby = " | ".join(s for _, _, s in neighbors[:10])
                    report.append([page_no, idx, str(dest.relative_to(out)) if dest else "",
                                   " ".join(who) if who else "", year or "", status, nearby])
                if page_no % 10 == 0 or page_no == len(doc):
                    print(f"  Seiten: {page_no}/{len(doc)} | PNG: {counts['zugeordnet'] + counts['pruefen']}")
    except Exception as exc:
        print(f"  FEHLER bei {pdf.name}: {exc}")
        return

    with (out / "pruefbericht.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle, delimiter=";")
        writer.writerow(["PDF-Seite", "Bild-Nummer", "Datei", "Erkannter Name",
                         "Geburtsjahr", "Status", "Text in Bildnaehe"])
        writer.writerows(report)
    print(f"  Fertig: {counts['zugeordnet']} zugeordnet, "
          f"{counts['pruefen']} zur Pruefung, {counts['fehler']} Fehler")
    print(f"  Ordner: {out}")


def main():
    parser = argparse.ArgumentParser(description="Fotos aus Stammbaum-PDFs mit Personennamen als PNG exportieren.")
    parser.add_argument("pfad", nargs="?", type=Path, default=Path(__file__).resolve().parent,
                        help="PDF oder Verzeichnis (Standard: Ordner des Skripts)")
    parser.add_argument("--radius", type=float, default=130, help="Suchradius fuer Namen in PDF-Punkten")
    parser.add_argument("--min-pixels", type=int, default=100, help="Minimale Bildpixel pro Achse")
    parser.add_argument("--min-display", type=float, default=35, help="Minimale sichtbare Bildgroesse in Punkten")
    parser.add_argument("--dpi", type=int, default=220, help="Aufloesung des exportierten PNG")
    args = parser.parse_args()
    path = args.pfad.resolve()
    if path.is_file() and path.suffix.lower() == ".pdf":
        pdfs = [path]
    elif path.is_dir():
        pdfs = sorted((p for p in path.iterdir()
                       if p.is_file() and p.suffix.lower() == ".pdf"
                       and p.stem.lower().startswith("stammbaum")), key=lambda p: p.name.casefold())
    else:
        parser.error(f"Kein PDF und kein gueltiger Ordner: {path}")
    if not pdfs:
        print(f"Keine stammbaum*.pdf-Dateien gefunden in: {path}")
        return
    print(f"{len(pdfs)} Stammbaum-PDF(s) gefunden.")
    for pdf in pdfs:
        process_pdf(pdf, args)
    print("\nAlle PDFs abgearbeitet.")


if __name__ == "__main__":
    main()
