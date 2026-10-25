# Evidencia Fedora bilingüe — 2026-10-23

La revalidación del 24 de octubre se encuentra en
[2026-10-24/README.md](2026-10-24/README.md). Incluye correcciones adicionales,
254 pruebas y gates de escritorio real ejecutados con autorización. Las
limitaciones del sandbox descritas abajo corresponden a la ejecución histórica.

`unittest.log`: 252 pruebas, 248 correctas, 4 omitidas, sin fallos.
`install-en.log`: instalación base real offline en una copia de /tmp con venv
nueva, HOME/XDG propios, sin paquetes del usuario; ruedas existentes verificadas
contra requirements.lock. No hubo instalación sobre la copia habitual.
Los logs `repair-*` y `update-check.txt` registran reparación conservando idioma,
cambio explícito a español, preferencias y SHA256 de SQLite sintética.
`preservation.json`: locks y scripts personales comparados con la instantánea
previa al trabajo. No se añadieron dependencias ni versiones.

`screens/`: renderizados Qt offscreen de 8 pestañas, 6 pasos de tutorial,
asistente OCR, selector de idioma y ambos popups, en ES/EN. Se revisaron
visualmente. Workers suprimidos; contenido sintético. No prueban captura, atajos,
modelo real ni botones físicos. La ventana Tk del bootstrap necesita display
real y no se revisó visualmente; su gate de idioma está implementado.

El sandbox no abre DISPLAY=:0 (xdotool: Failed creating new xdo instance),
niega bind del socket IPC nombrado y listener HTTP loopback. No se solicitó
elevación ni se modificaron servicios, scripts personales ni perfiles habituales.
Los logs contienen rutas temporales a efectos de reproducción.
