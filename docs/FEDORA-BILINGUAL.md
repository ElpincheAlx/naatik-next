> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# Fedora: tutorial e interfaz Español / English

Para una descarga nueva, empieza por [README](../README.md); este documento conserva también resultados históricos anonimizados.

Revalidación del 24 de octubre de 2026: se conservaron los cambios locales
existentes y se corrigieron dos problemas al cambiar de idioma: el mensaje
predeterminado de cancelación retenía el idioma de importación del módulo, y
Escape en una captura en inglés podía mostrar una advertencia de error.
La suite actual ejecutó 254 pruebas (251 correctas, 3 omitidas). Hay evidencia
adicional de escritorio real X11, captura Spectacle y atajo temporal en
[evidence/fedora-bilingual/2026-10-24/README.md](evidence/fedora-bilingual/2026-10-24/README.md).
Consulta `VALIDACION.txt` del paquete para distinguir esas comprobaciones de
los límites pendientes. Los registros anteriores se conservan como históricos.

Esta entrega adapta el tutorial corregido de Windows a Next para Fedora. La
referencia Windows inspeccionada no tenía interfaz bilingüe: esa parte se
implementó aquí. Se conservaron los cambios locales preexistentes de OCR, Anki,
apariencia y sus diagnósticos. No se modificaron Windows, JapaneseMining ni Naatik Go.

## Instalación independiente

Plataforma del lock: Fedora 44, Linux x86_64, CPython 3.14 estándar, CPU.
Necesitas Python 3.14 y venv/pip del sistema; para el asistente gráfico de primer
arranque, `python3-tkinter`. Tesseract, sus datos y Spectacle son componentes
nativos opcionales para OCR/captura. Consulta README.md y
THIRD_PARTY_DEPENDENCIES.md para versiones, licencias y límites existentes.

Extrae el paquete en una carpeta nueva y abre una terminal allí:

```sh
bash tools/install.sh
```

Primero aparece `Idioma / Language`: 1 Español, 2 English, c cancelar. Enter
conserva la elección existente; en un perfil nuevo propone español. Cancelar
no crea el entorno, no guarda preferencias y no descarga nada. Para ejecución
sin terminal interactiva debes indicar idioma en el primer uso:

```sh
bash tools/install.sh --language es
# or
bash tools/install.sh --language en
./launch
```

También puedes ejecutar `./launch` sin entorno Qt: el asistente Tk presenta
primero Español/English y Cancelar; después pide confirmación explícita para
preparar el entorno. Si no hay Tk, usa el procedimiento de terminal anterior.
No se instala Tesseract, Spectacle, diccionarios ni modelos por avanzar el tutorial.
El instalador no usa entornos de otros proyectos. Pip puede mostrar sus propios
mensajes en inglés; no son textos de Next.

El paquete es código fuente con instalador Fedora; no incluye Python, ruedas,
modelos, diccionarios ni un RPM. La instalación normal de dependencias requiere
red. Para una wheelhouse previamente obtenida y verificada contra los locks:

```sh
NAATIK_NEXT_OFFLINE=1 NAATIK_NEXT_WHEELHOUSE=/ruta/ruedas bash tools/install.sh --language es
```

No copies una venv de otra ruta. Cada copia crea su propio entorno. Los recursos
opcionales CPU se preparan desde los asistentes, con confirmaciones, versiones y
hashes existentes; el tutorial no los da por instalados.

## Actualización y reparación sin perder preferencias

Cierra Next. Haz una copia de seguridad de tu carpeta de código y de tus datos
XDG. Extrae/actualiza el código en tu ruta elegida, conservando datos, modelos,
diccionarios y rutas explícitas. No ejecutes `uninstall.sh` para actualizar.
Ejecuta `bash tools/install.sh`; Enter conserva el idioma existente. Sin TTY,
si ya hay `ui_language` se conserva automáticamente. `--language es|en` es un
cambio explícito. Una reparación no reemplaza el resto de settings.json.

El idioma de interfaz se guarda por perfil en
`$XDG_CONFIG_HOME/naatik-next/settings.json` (por defecto
`~/.config/naatik-next/settings.json`), clave `ui_language`. El tutorial usa la
clave `tutorial`, con estado y paso; no certifica recursos. No se cambian el
idioma OCR, la ruta de traducción, Anki ni la prioridad de diccionarios.
Si cambias la ruta del programa, el instalador registra el acceso de escritorio
de esa copia. Los scripts personales con rutas explícitas siguen apuntando a su
ruta original: no se editan automáticamente. No se incluyen en el paquete los
scripts personales `naatik-next-capturar.sh` y `naatik-next-capture-copy.sh`.

## Uso y configuración inicial

- Configuración → Idioma / Settings → Language cambia la interfaz del perfil.
  Se conservan el editor y los procesos. Los nuevos mensajes usan la elección;
  algunos informes de diagnóstico ya generados se actualizan al repetir la acción.
- Ayuda → Tutorial y configuración inicial / Help → Tutorial and initial setup
  abre o retoma bienvenida, OCR, traducción, diccionarios, Anki opcional y prueba.
  Incluye Volver, Continuar, Omitir por ahora y Reiniciar tutorial.
- Omitir conserva el paso para retomarlo desde Ayuda. Completar permite volver
  al comienzo desde Ayuda. Cerrar deja el tutorial en curso.
- El primer inicio normal de un perfil nuevo abre el tutorial. Los perfiles
  anteriores (incluso settings.json vacío) no lo abren automáticamente.
  `--capture`, `--capture-copy`, `--translator` y `--phrase` tampoco lo abren.
- OCR: reutiliza el asistente existente y comprueba los recursos elegidos.
  Traducción: revisa el plan y confirma cualquier descarga. Diccionarios:
  importa tus ZIP Yomitan, confirma la revisión y activa los que quieras usar.
- Si una consulta del editor OCR no tiene diccionarios activos, muestra una
  explicación y `Importar o activar diccionarios…`. Activa/importa uno, vuelve al
  editor y pulsa Consultar selección; también puedes ejecutar OCR de nuevo.
  Las consultas automáticas no abren diálogos repetidos.
- Captura, portapapeles, atajos, bandeja, instancia única y comandos de Stream
  Deck/StreamController conservan los mecanismos Fedora existentes. Los atajos
  externos se asignan con los comandos de Integraciones, como antes.

## English quick start

Extract into a new folder. Run `bash tools/install.sh`, choose English before
any environment creation or dependency download, or use
`bash tools/install.sh --language en`. Cancel at the language prompt with `c`.
Then run `./launch`. The GUI bootstrap also offers a cancellable language choice
before preparation if system Tk is installed.

Settings → Language stores the UI choice per XDG profile. OCR language and
translation languages remain independent. Help → Tutorial and initial setup
resumes onboarding. Skipping/completing never certifies installed resources.
Downloads still require confirmation in the existing setup assistants.

For update/repair, preserve your code backup, XDG data and explicit resource
paths; rerun the installer and keep the current language with Enter. Existing
noninteractive profiles keep their saved language unless `--language` explicitly
changes it. Personal capture scripts are not changed or shipped. See
VALIDACION.txt for tested paths and remaining desktop/network gates.

## Arquitectura y validación

Los catálogos `naatik_next/locales/es.json` y `en.json` comparten claves.
`i18n.t` localiza presentación y mensajes; los identificadores de motores,
estados de protocolo, códigos de idiomas y lógica de negocio se conservan.
Cada petición comunica el idioma al worker, incluso si es persistente.
No se traduce texto del usuario, resultados OCR ni contenido de diccionarios.

La suite usa unittest con HOME/XDG y venv aislados. Reproducción:

```sh
QT_QPA_PLATFORM=offscreen PYTHONNOUSERSITE=1 .venv/bin/python -m unittest discover -v
QT_QPA_PLATFORM=offscreen .venv/bin/python -m tools.bilingual_review --output /tmp/HISTORICAL-REVIEW
```

Usa HOME/XDG temporales también al reproducir estas pruebas. La revisión visual
suprime workers: verifica presentación, no inferencia ni captura global. La suite
real de workers verifica consultas/SQLite, supervisión y cierre con fixtures.
La instalación completa online, VM limpia, modelos opcionales, captura global,
atajos y botones físicos necesitan gates propios descritos en VALIDACION.txt.
