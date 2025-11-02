; PACTS HITL Continue Hotkey (AutoHotkey v2)
; Press Ctrl+Alt+C to instantly signal HITL continue
;
; Installation:
; 1. Download AutoHotkey v2 from https://www.autohotkey.com/
; 2. Right-click this file → Run Script
; 3. Press Ctrl+Alt+C when PACTS is waiting for HITL

#Requires AutoHotkey v2.0

; Ctrl+Alt+C hotkey
^!c::
{
    ; Get the script's directory (where this .ahk file is located)
    scriptDir := A_ScriptDir

    ; Create hitl/continue.ok in the same directory
    continueFile := scriptDir . "\continue.ok"

    ; Create the file (empty file)
    try {
        FileAppend("", continueFile)
        TrayTip("PACTS HITL", "Continue signal sent!", 1)
    } catch as err {
        MsgBox("Failed to create continue file: " . err.Message)
    }
}

; Show instructions on startup
TrayTip("PACTS HITL Hotkey Active", "Press Ctrl+Alt+C to continue automation", 3)
