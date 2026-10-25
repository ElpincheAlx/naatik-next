# Revalidación Fedora — 2026-10-24

Se leyeron AGENTS.md y los árboles Fedora y Windows antes de modificar.
Next ya tenía cambios locales de tutorial, interfaz bilingüe, OCR, Anki y
apariencia. Se conservaron. Windows es una referencia de solo lectura: el
tutorial corregido está en `Naatik-next-windows-tutorial`; no se encontraron
catálogos bilingües en esa referencia ni en `Naatik-next-windows`.
Ambas referencias son carpetas sin metadatos Git, no checkouts comprobables con
`git status`. No se modificaron, ni tampoco JapaneseMining o Naatik Go.

Se corrigieron dos fallos adicionales: el texto de cancelación se resolvía al
importar `processes.py`, y la detección de cancelación de captura solo reconocía
la terminación española. Ahora el texto se obtiene al cancelar, y cancelar en
inglés sigue siendo silencioso. Hay regresiones de ambos comportamientos.
Las pruebas de adaptadores, Anki y procesos ya no presuponen español para esas
aserciones. También se ajustaron los enlaces del documento raíz del paquete.

## Entorno y reproducción

Trabajo en `/tmp/HISTORICAL-REVIEW/source`, una copia sin venv,
modelos, diccionarios ni scripts personales. Instalación real offline de base
desde la wheelhouse de Next, con hashes del lock, en una venv nueva. No se usó
el entorno de la copia habitual ni otro proyecto. HOME, XDG_CONFIG_HOME,
XDG_DATA_HOME, XDG_STATE_HOME, XDG_CACHE_HOME y XDG_RUNTIME_DIR son temporales;
PYTHONNOUSERSITE=1, sin PYTHONPATH/PYTHONHOME para instalar y ejecutar la suite.
El harness externo de escritorio usa PYTHONPATH solo para localizar esta copia
temporal de código; no permite paquetes del usuario.

Los scripts adjuntos registran los comandos ejecutados. Para reproducirlos en
otra ubicación hay que adaptar las rutas temporales y preparar una wheelhouse
con los hashes fijados. `native-desktop.py` necesita KDE/X11, Qt xcb, Spectacle y
xdotool; sus coordenadas corresponden a este escritorio 1920×1080. No es un
instalador ni una dependencia de la aplicación.

## Resultados

- `unittest-final.log`: 254 pruebas, 251 correctas, 3 omitidas, sin fallos.
  Incluye perfil nuevo/anterior/vacío, omitir/reiniciar/retomar/completar,
  entrada `--capture`, supresión de tutorial en segundo plano y popups,
  diccionarios ausentes sin diálogos repetidos, activación y reintento real de
  worker/SQLite en ambos idiomas, persistencia y cambios de idioma.
- Dos omisiones corresponden al runtime opcional de análisis de frases ausente
  en la copia aislada; la tercera es el test de fallo por prohibición de bind,
  inaplicable porque los sockets están permitidos en la ejecución autorizada.
  El transporte Anki HTTP de loopback sí se ejecutó; no contactó Anki habitual.
- `install-en.log`: instalación base nueva offline en inglés. La suite verifica
  cancelación real por TTY antes de crear perfil, bytecode o venv, y selección
  obligatoria no interactiva para perfiles nuevos.
- `repair-*.log`, `repair-results.json`: reparación real sin idioma explícito
  conserva inglés; cambio explícito a español modifica solo ui_language.
  Se conservaron todas las preferencias de prueba, Anki, apariencia, rutas
  explícitas, progreso paso 3 y SHA256 de SQLite con un diccionario sintético
  desactivado y prioridad 41. No se acreditan modelos reales con estas rutas.
- `desktop-results.json`: escritorio real X11, arranque ES/EN con tutorial,
  segundo arranque reenviado al propietario, cierre SIGTERM 143 y retirada de
  lock/endpoint. `--capture` en inglés no abrió tutorial; selección cancelada
  mediante Escape. Se instrumentó Window para registrar estado/capturas sin
  suprimir sus workers ni sustituir el broker.
- `native-results.json`, `native-region.png`: adaptador real Spectacle 6.7.5,
  selección sintética de 551×211 píxeles, cancelación Escape en inglés y atajo
  temporal Ctrl+Alt+Shift+F12 mediante libX11/Qt xcb. No se guardó el atajo.
  Esta prueba del adaptador no acredita la cadena completa captura→OCR→Anki.
- `offscreen/`: renderizados de ocho pestañas, seis pasos, OCR, selector de
  idioma y dos popups por idioma. Se revisaron visualmente pantallas
  representativas ES/EN, incluidos los seis elementos de la primera prueba,
  selector, editor, diccionarios, OCR y popups. Workers suprimidos en estos
  renderizados; no acreditan inferencia ni captura global. `desktop-*` contiene
  además ventanas obtenidas en escritorio real.
- `preservation.json`: locks y ambos scripts personales sin cambios respecto
  al comienzo de esta sesión. No se instalaron recursos opcionales ni se tocó
  un perfil habitual. Sin commit ni push.

## Pendiente, sin PASS

Instalación online completa, máquina/VM limpia, Wayland, bootstrap gráfico Tk
interactivo, inferencia de modelos opcionales reales y análisis de frases real.
No se probó AnkiConnect habitual, portapapeles del escritorio con OCR completo,
ni botones físicos Stream Deck/StreamController. La suite cubre esos flujos
con fixtures/offscreen cuando corresponde; no equivale a validarlos físicamente.
No se reemplazan los mecanismos Fedora ni se modifican scripts personales.
