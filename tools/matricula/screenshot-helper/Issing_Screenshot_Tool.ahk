#Requires AutoHotkey v2.0
#SingleInstance Force
Persistent

; ================================================================
; Screenshot-Tool fuer historische Kirchenbuecher (Matricula etc.)
; AutoHotkey v2 / Windows 10 und 11
;
; F5    Mausposition des Buttons "Naechste Seite" merken (einmalig)
; F6    Erste Ecke des gewuenschten Ausschnitts merken
; F7    Gegenueberliegende zweite Ecke merken
; F8    Screenshot als PNG speichern und auf naechste Seite klicken
; F9    Pause / Fortsetzen
; Esc   Beenden
;
; Die beiden Ecken duerfen in BELIEBIGER Reihenfolge gesetzt werden.
; ================================================================

; --- Einstellungen -----------------------------------------------
outputFolder := A_ScriptDir "\Issing_Trauungen"
startNumber := 1          ; erste Bildnummer, z. B. 1 -> 0001.png
numberWidth := 4         ; 4 -> 0001.png, 0002.png, ...
endNumber := 0           ; 0 = unbegrenzt, sonst letzte Bildnummer
waitAfterClick := 1500   ; Millisekunden nach dem Weiter-Klick
; ----------------------------------------------------------------

CoordMode("Mouse", "Screen")
DirCreate(outputFolder)

nextNumber := startNumber
nextPagePos := unset
cornerA := unset
cornerB := unset
isPaused := false
helperPath := A_Temp "\ahk_kirchenbuch_capture_" A_TickCount ".ps1"

; Hilfsskript fuer native PNG-Screenshots (keine weiteren Bibliotheken).
psScript := "param([int]$X, [int]$Y, [int]$Width, [int]$Height, [string]$OutputPath)`r`n"
psScript .= "Add-Type -AssemblyName System.Drawing`r`n"
psScript .= "$bmp = New-Object System.Drawing.Bitmap($Width, $Height)`r`n"
psScript .= "$gfx = [System.Drawing.Graphics]::FromImage($bmp)`r`n"
psScript .= "try {`r`n"
psScript .= "    $gfx.CopyFromScreen($X, $Y, 0, 0, $bmp.Size)`r`n"
psScript .= "    $bmp.Save($OutputPath, [System.Drawing.Imaging.ImageFormat]::Png)`r`n"
psScript .= "} finally {`r`n"
psScript .= "    $gfx.Dispose()`r`n"
psScript .= "    $bmp.Dispose()`r`n"
psScript .= "}`r`n"
FileAppend(psScript, helperPath, "UTF-8")
OnExit(RemoveHelper)

Notify("Bereit | F5 Weiter-Button | F6/F7 Ecken | F8 Aufnahme + Weiter | F9 Pause | Esc Ende", 4500)

F5::SaveNextPagePosition()
F6::SaveCorner("A")
F7::SaveCorner("B")
F8::CaptureAndAdvance()
F9::TogglePause()
Esc::ExitApp()

SaveNextPagePosition() {
    global nextPagePos
    MouseGetPos(&x, &y)
    nextPagePos := {x: x, y: y}
    Notify("F5: Weiter-Button gespeichert bei " x ", " y)
}

SaveCorner(which) {
    global cornerA, cornerB
    MouseGetPos(&x, &y)
    if (which = "A") {
        cornerA := {x: x, y: y}
    } else {
        cornerB := {x: x, y: y}
    }
    Notify("F" (which = "A" ? "6" : "7") ": Ecke " which " gespeichert bei " x ", " y)
}

CaptureAndAdvance() {
    global outputFolder, numberWidth, nextNumber, endNumber, waitAfterClick
    global nextPagePos, cornerA, cornerB, isPaused, helperPath

    if isPaused {
        Notify("PAUSE aktiv. Mit F9 fortsetzen.")
        return
    }
    if !IsSet(cornerA) || !IsSet(cornerB) {
        MsgBox("Zuerst mit F6 und F7 die beiden gegenueberliegenden Ecken markieren.", "Screenshot-Tool")
        return
    }

    left := Min(cornerA.x, cornerB.x)
    top := Min(cornerA.y, cornerB.y)
    width := Abs(cornerB.x - cornerA.x)
    height := Abs(cornerB.y - cornerA.y)
    if (width < 15 || height < 15) {
        MsgBox("Der Aufnahmebereich ist zu klein. F6/F7 erneut setzen.", "Screenshot-Tool")
        return
    }

    ; Vorhandene PNGs niemals ohne Nachfrage ueberschreiben.
    loop {
        if (endNumber > 0 && nextNumber > endNumber) {
            MsgBox("Endnummer " endNumber " erreicht.", "Screenshot-Tool")
            return
        }
        filename := Format("{:0" numberWidth "d}", nextNumber) ".png"
        outPath := outputFolder "\" filename
        if !FileExist(outPath)
            break
        nextNumber += 1
    }

    ; Tooltips duerfen nicht auf dem Bild landen.
    ToolTip()
    Sleep(200)

    cmd := 'powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File "' helperPath '"'
    cmd .= " -X " left " -Y " top " -Width " width " -Height " height
    cmd .= ' -OutputPath "' outPath '"'
    try {
        exitCode := RunWait(cmd, , "Hide")
    } catch as err {
        MsgBox("Aufnahme konnte nicht gestartet werden:`n" err.Message, "Screenshot-Tool")
        return
    }
    if (exitCode != 0 || !FileExist(outPath)) {
        MsgBox("PowerShell-Screenshot fehlgeschlagen (Exitcode " exitCode ").", "Screenshot-Tool")
        return
    }

    nextNumber += 1
    if IsSet(nextPagePos) {
        MouseClick("Left", nextPagePos.x, nextPagePos.y, 1, 0)
        Sleep(waitAfterClick)
        Notify("Gespeichert: " filename " | Naechste Seite geoeffnet")
    } else {
        Notify("Gespeichert: " filename " | F5 nicht gesetzt, kein Weiter-Klick")
    }
}

TogglePause() {
    global isPaused
    isPaused := !isPaused
    Notify(isPaused ? "PAUSE | F9 zum Fortsetzen" : "FORTGESETZT | F8 fuer naechstes Bild")
}

Notify(message, milliseconds := 1800) {
    ToolTip(message, 10, 10)
    SetTimer(ClearTooltip, -milliseconds)
}

ClearTooltip() {
    ToolTip()
}

RemoveHelper(*) {
    global helperPath
    try {
        if FileExist(helperPath)
            FileDelete(helperPath)
    }
}
