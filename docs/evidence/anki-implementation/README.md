# Evidencia de implementación Anki — 2026-10-21

Base: `18fa3a6`, diseño `cb5d115`. No commit ni integración realizados por esta
tarea. El script previo sin seguimiento `naatik-next-capturar.sh` se conserva.

- Regresión: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -q`
  → **216 pruebas, OK, 2 omitidas**, 31.382 s. Omisiones: listener HTTP loopback
  y gate IPC real, restringidos por el sandbox. No se confunden con éxito real.
- Contratos Anki tras endurecer el tipo booleano del preflight:
  `QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest tests.test_anki -q`
  → **11 pruebas, OK, 1 omitida**, 0.104 s (listener HTTP).
- Anki y popups: **37 pruebas, OK, 1 omitida** antes del último endurecimiento
  booleano/preflight y comprobación de mazo mediante tarjetas durante recuperación.
  Ambos cambios están incluidos en la regresión/contratos posteriores respectivos.
- `git diff --check` → PASS.
- `QT_QPA_PLATFORM=offscreen .venv/bin/python -m tools.anki_ui_review` → capturas
  sintéticas, cero HTTP, HOME/XDG temporales, cero acceso a colecciones.
  Primer uso (referencia histórica no distribuida), compositor (referencia histórica no distribuida).
  Revisión visual offscreen; no prueba interacción con el escritorio real.

Las pruebas verifican metadatos sin mutación, ausencia de selección implícita,
instantánea independiente en ambos popups, conservar edición al cerrar/cancelar,
revisión y envío explícitos, bloqueo entre borradores equivalentes, `allowDuplicate:
false`, ID positivo, respuesta perdida y recuperación por etiqueta sin reenvío,
cero/múltiples coincidencias o contenido modificado, rechazo local y registro
corrupto. Transporte con conexiones inyectadas cubre redirección rechazada,
JSON/esquema roto, límite, desconexión, errores redactados y ausencia de reintentos.
Los datos de FakeClient no acreditan comportamiento de un paquete real.

Pendientes externos: `command -v anki` no encontró ejecutable. El sandbox rechaza
listeners locales; no se hicieron peticiones HTTP al Anki personal, ni se abrieron,
copiaron, enumeraron o exportaron colecciones. No se instalaron dependencias.
La prueba con base separada y puerto propio está en [ANKI.md](../../ANKI.md).

Fuentes oficiales revisadas en esta tarea:

- [Manual de archivos y `-b`](https://docs.ankiweb.net/manual/files): opción de
  base alternativa confirmada; no implica que se haya iniciado Anki.
- [Ficha AnkiConnect](https://ankiweb.net/shared/info/2055492159): exige JavaScript;
  no permitió comprobar el paquete actual.
- [README oficial archivado](https://raw.githubusercontent.com/FooSoft/anki-connect/master/README.md):
  confirma traslado a SourceHut.
- [Origen actual del mantenedor](https://git.sr.ht/~foosoft/anki-connect): bloqueado
  por robots en la herramienta web; `curl` del shell falló por resolución DNS.
- [Implementación oficial histórica](https://raw.githubusercontent.com/FooSoft/anki-connect/master/plugin/__init__.py):
  referencia del protocolo, no evidencia de compatibilidad de la versión actual.

No se atribuye versión/hash/licencia del artefacto actual por inferencia. No se
acredita instalación desde cero ni creación real de una nota. Apariencia continúa
pendiente después de Anki.
