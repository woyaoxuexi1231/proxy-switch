; Recreate an existing desktop shortcut after copy so Explorer picks up this
; build's icon. Tauri skips shortcut creation in update mode, and Windows
; caches the previous exe icon by path even after the binary is replaced.
; Only touch the shortcut when it already exists — do not force one on users
; who declined the finish-page checkbox.
!include LogicLib.nsh

!macro NSIS_HOOK_POSTINSTALL
  ${If} ${FileExists} "$DESKTOP\${PRODUCTNAME}.lnk"
    Delete "$DESKTOP\${PRODUCTNAME}.lnk"
    CreateShortcut "$DESKTOP\${PRODUCTNAME}.lnk" "$INSTDIR\${MAINBINARYNAME}.exe" "" "$INSTDIR\${MAINBINARYNAME}.exe" 0
  ${EndIf}
  System::Call 'shell32::SHChangeNotify(i 0x08000000, i 0, p 0, p 0)'
  System::Call 'shell32::SHChangeNotify(i 0x00002000, i 0x0005, t "$DESKTOP\${PRODUCTNAME}.lnk", i 0)'
!macroend
