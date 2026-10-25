# Evidencia de arranque (2026-10-20)

| Comprobación | Resultado y alcance |
|---|---|
| Cuatro entradas reales con Next detenido | Ejecutadas antes/después. Bind AF_UNIX bloqueado por EPERM: arranque exitoso NO acreditado. Ahora error visible, exit 1, sin bloqueo/localizador retenido. |
| Scripts y .desktop | Cuatro acciones ejecutadas desde `/`, fuente/rutas con espacios, Unicode, comilla y `$()`. Perfil correcto pese al XDG del llamador. Mismo bloqueo. Gio retorna 0 al lanzar aunque Next falle: no se cuenta como éxito. |
| Worker con propietario SIGKILL | QProcess/señales reales, trabajo sintético. Antes huérfano vivo; después terminado. |
| QLock y localizador tras muerte | Procesos/archivos reales; listen sustituido. Recuperación probada, socket nombrado no acreditado. |
| Rutas largas, runtime diferente, socket vivo | Pruebas unitarias; transporte/probe inyectados donde indicado. No equivalen a IPC nombrado real. |
| Popups/portapapeles/cierre | Qt offscreen y portapapeles local, bandeja inyectada; no selección global ni pegado externo. |
| Perfil normal y script existente | 3495 archivos contrastados: 0 cambios, 0 añadidos. Script permanece no versionado. |
| Anki/Apariencia/KDE/StreamController | Sin implementación ni cambios. |

`baseline.json` conserva la reproducción previa. `real-launches.json` contiene
el resultado real de `tools/startup_review.py`, incluidos fallos del proceso
lanzado por Gio. `orphan-before.json`/`orphan-after.json` usan un worker sintético,
no modelos descargados. La suite completa: **204 pruebas, OK, 1 omitida** (socket nombrado no permitido).
Su resultado consta en `tests.log`; `preservation.json` repite la comprobación
del perfil normal y script después de la suite final.
No se versiona el inventario privado de rutas del perfil normal, solo su resultado
agregado. SHA256 del script conservado:
`26887b6cd26519c1f03d95e93425bd931ca7a8319cc76f1de4990872b3e93ad4`.

Pendiente en sesión gráfica: propietario/cliente con socket nombrado, concurrencia
real de las acciones, las cuatro aperturas exitosas, bandeja, selección, OCR y
pegado en otra aplicación; SIGINT/SIGTERM/rearranque y recuperación con esa pila.
Sigue [la prueba manual](../../STARTUP.md). No se afirma resuelto el fallo completo
por pasar IPC simulado. No se instalaron recursos ni se modificó el perfil normal.
