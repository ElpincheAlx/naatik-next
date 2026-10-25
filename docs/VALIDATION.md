> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# Evidencia y límites — 2026-10-19

Las secciones iniciales registran la primera entrega. El estado actual de JMdict
y MangaOCR está al final y en [JMDICT-MANGA.md](JMDICT-MANGA.md). La confirmación
manual del usuario y la consulta nueva de su configuración normal se distinguen
en el último apartado; no sustituyen las condiciones de las pruebas históricas.

Esta es una primera implementación funcional, con revisión interactiva pendiente;
no se considera un producto terminado por el resultado de los tests.

## Entorno inspeccionado sin alterar proyectos existentes

- Fedora 44, x86_64, sesión declarada `x11`, escritorio `KDE`, `DISPLAY=:0`.
- Spectacle 6.7.5 (`spectacle-6.7.5-1.fc44.x86_64`). Versión y opciones verificadas
  con plataforma offscreen; admite region/background/output/new-instance.
- Tesseract 5.5.3, datos `eng`, `jpn`, `jpn_vert`, `spa`.
- Python 3.14, PySide6 6.11.1, Argos 1.11.0.
- Paquetes Argos locales `ja_en` (1.1) y `en_es`; rutas probadas en→es, ja→en,
  ja→en→es. No se han instalado, descargado ni modificado modelos.
- Entornos antiguos MangaOCR y PaddleOCR encontrados mediante archivos de
  configuración, sin ejecutarlos. Metadatos locales: manga-ocr 0.1.16 en Python
  3.14; paddleocr 3.7.0 y paddlepaddle 3.3.1 en Python 3.12. No acreditan una
  integración funcional en Next. Se presentan como incompatibles todavía.
- No se consultó ningún servicio ni se ejecutaron scripts de JapaneseMining.
- Documento confirmado por el usuario: `${REFERENCE_ROOT}/ARCHITECTURE.md`, copia
  en REFERENCE-JapaneseMining.md; SHA-256
  `4b346a0f2ca335083a580c9f999a355a061389e6e7177b5841e676fbbc0467e1`.

## Pruebas automatizadas

`python -m unittest discover -v`: **16 pruebas correctas**.

Incluyen importación y consulta, activación/prioridad, reapertura de SQLite,
eliminación en cascada sin tocar original, duplicados por hash/título-revisión,
rollback por entrada inválida y cancelación posterior a escrituras, rutas
peligrosas, enlaces ZIP, relación de compresión excesiva, tipos no compatibles,
preferencias XDG y JSON corrupto. Workers reales comprueban error, timeout,
cancelación durante importación y cierre silencioso. Pruebas unitarias con mocks
comprueban que la mera presencia de comando/paquete no acredita disponibilidad;
esas pruebas no se cuentan como inferencia real.

## Ejecución real local

`python -m tools.real_smoke`:

- Prueba Tesseract sobre imagen generada: `TEST 123`; estado **listo**.
- Imagen `examples/hello.png` → OCR `Hello world`.
- Ese resultado → modelo Argos en→es → `Hola mundo`.
- `こんにちは。` → modelos ja→en→es → `Hola.`.
- No se simularon resultados, servidores ni modelos en estas comprobaciones.

`python -m tools.gui_smoke`:

- Ventana Qt offscreen, cuatro pestañas y workers de ejecución reales.
- Vista previa → OCR `Hello world` → traducción `Hola mundo`.
- Importación del diccionario local de gramática → consulta `くらい` con definición.
- Temporizador Qt de 5 ms siguió ejecutándose durante las tareas (115 ticks en
  la pasada final). Todos los procesos administrados terminaron al cerrar.
- Captura de esta prueba: gui-smoke.png (referencia histórica no distribuida). No representa una captura
  del escritorio ni valida Spectacle.

Importación adicional a SQLite temporal, leyendo ZIP locales sin modificarlos:

| Recurso | Resultado |
| --- | --- |
| 新和英 | 152 202 entradas; consulta 日本 correcta |
| 日本語文法辞典(全集) | 535 entradas; consulta くらい correcta |
| JMdict con ejemplos | Rechazado por definiciones enriquecidas; rollback |
| アクセント辞典 | Rechazado: term_meta_bank todavía no compatible |
| KANJIDIC | Rechazado: kanji_bank todavía no compatible |

Se comparó SHA-256 de cada original antes/después. No se preimportó nada en los
 datos persistentes del usuario. Las lenguas no declaradas en index.json se
muestran como `?`, sin inferirlas por el nombre del ZIP.

## Reproducibilidad y apertura

Se creó otro venv limpio en `/tmp/HISTORICAL-REVIEW`, instalado exclusivamente
con `.wheelhouse`, `--no-index --no-deps --require-hashes -r requirements.lock`.
Allí volvió a pasar la inferencia real OCR/traducción. Este directorio es solo
una prueba; el lanzador estable usa `${PROJECT_ROOT}/.venv`.

`desktop-file-validate naatik-next.desktop`, sintaxis bash y compilación Python:
correctos. La entrada distintiva del menú quedó instalada.

## Pendiente de revisión manual

El lanzamiento con display real y Spectacle abortan en este entorno. Error
observado al lanzar la app: `qt.qpa.xcb: could not connect to display :0`.
La prueba offscreen funciona. No se alteraron permisos de X ni la sesión gráfica.

Desde una terminal del escritorio del usuario, un único comando estable:

```bash
/historical-home/Naatik-next/launch
```

Seguir el recorrido del README: captura de región, Escape, vista previa, OCR,
corrección/copia, traducción, gestión de diccionarios, cancelación y reapertura.
La integración Spectacle está implementada para KDE/X11 y necesita confirmar
su interacción real. Wayland, inferencia MangaOCR/PaddleOCR, Yomitan enriquecido,
kanji/acento, traducción larga y administración de modelos desde la GUI quedan
fuera de esta primera entrega.

## Corrección de vista previa — revisión de captura del usuario

Se revisó `Imagen de ChatGPT 19 oct 2026, 08_48_37 a.m.png`, localizada en
`~/Descargas`. La GUI mostraba una región de 43×45 ampliada y recortada por abajo.
El QLabel recibía un pixmap escalado a 960×200 sin considerar su altura real.

La vista previa ahora pinta la imagen completa dentro del área disponible,
conserva proporciones, se adapta a cada redimensionado y no amplía imágenes
pequeñas. Esto solo cambia la presentación; el PNG original utilizado por OCR
conserva sus dimensiones.

Validación: 18 tests correctos, incluidos dos de renderizado Qt offscreen que
comprueban los extremos superior e inferior de una imagen pequeña y una imagen
vertical en tres tamaños de widget. Estas comprobaciones no validan la captura
interactiva con Spectacle en la sesión gráfica real, que sigue pendiente.

## Investigación de 日本 → Japanese

Reproducción sin OCR y comparación real con la API oficial de Argos: mismas
seis salidas, mismos hashes de modelos y bibliotecas. La inferencia ya devuelve
`▁Japanese`, por lo que no se añadió ninguna sustitución a la decodificación.
El OCR original histórico no es recuperable desde la captura ni los datos
persistentes; la regresión de procedencia usa OCR simulado y no lo valida.
Ahora pasan 19 pruebas. Diagnóstico, etapas y comando reproducible en
[TRANSLATION-DIAGNOSIS.md](TRANSLATION-DIAGNOSIS.md).


## Ampliación JMdict y MangaOCR

JMdict local enriquecido importado: 513 033 filas comparadas íntegramente con el
ZIP. Consulta 日本 con significados, dos lecturas, tablas y ejemplos. Importación,
consulta, borrado asíncrono y cancelación real con rollback comprobados desde GUI
offscreen, siempre con datos temporales y hash del original sin cambios.

MangaOCR integrado como motor seleccionable: carga e inferencia reales con modelo
local, proceso propio persistente, selección guardada, idioma japonés fijo,
cancelación, recarga y cierre comprobados. La GUI siguió procesando eventos.
PaddleOCR sigue pendiente. La captura interactiva sigue sin validación en sesión
real. Pasan 28 pruebas. Evidencias, alcance y recursos exactos:
[JMDICT-MANGA.md](JMDICT-MANGA.md).


## Consulta de 日本 en la configuración normal y confirmación manual nueva

Comprobación dirigida del agente, 2026-10-19; no se repitió la batería completa.

- Inspección inicial con SQLite `mode=ro`: **JMdict [2025-11-01]**, revisión
  **JMdict.2025-11-01**, ya importado y **activo**, prioridad **0**, **513 033 filas**.
- Base normal: `~/.local/share/naatik-next/dictionaries.sqlite3`. Se comprobó que
  columnas e índices requeridos ya existían; la inicialización del worker no
  necesitó migraciones. No hubo importación, activación ni cambio de prioridad.
- Se ejecutó **Window.lookup → Task/QProcess → worker(action=lookup) → Store.lookup
  → Window.looked_up → render_results/DictionaryView**, consultando esa base normal.
  La ventana Qt, las preferencias y el estado de logs del ensayo fueron aislados;
  se deshabilitó únicamente la detección automática de arranque de esa ventana
  de prueba para no recargar motores ajenos al objetivo.
- **Cuatro resultados**: Japan; lecturas **にほん / にっぽん**; ejemplos japonés/inglés
  y **dos tablas** presentes en el QTextDocument. Visor identificado como
  **Diccionario: JMdict [2025-11-01]**. Se inspeccionó además la imagen renderizada.
- El panel de traducción retuvo el valor centinela `Japanese`, tomado del caso
  Argos ya diagnosticado: no se ejecutó otra traducción. El texto/editor del ensayo
  también eran centinelas, no OCR nuevo. Esto prueba separación de paneles y
  procedencia de la consulta, sin atribuir exactitud a una nueva inferencia OCR.
- Se verificaron hashes SHA-256 de la base normal y settings.json antes/después:
  **idénticos**. No se modificaron preferencias o diccionarios del usuario. Como
  JMdict estaba importado y activo, no hizo falta probar otra importación aislada.
- Renderizado **Qt offscreen**. No se realizó interacción en el escritorio real.
  No se encontró un defecto que requiriera cambiar el código de la aplicación.

Evidencia de la ejecución, estado y hashes:
normal-jmdict-lookup-evidence.json (referencia histórica no distribuida).

**Nueva evidencia manual aportada por el usuario:** confirmó que
**Capturar región → MangaOCR → 日本** funcionó en su sesión gráfica real,
**sin editar el texto OCR**. Se registra como confirmación del usuario de ese caso,
no como una prueba interactiva realizada por el agente. No acredita cancelación,
limpieza, timeout ni todos los casos de captura. Tampoco reconstruye el OCR original
de las capturas anteriores que contenían texto corregido. El diagnóstico de
traducción de a249fea permanece sin cambios; Japan aquí es resultado de JMdict,
no una sustitución de la salida Japanese de Argos.

## Consulta de selección en Captura y resultado — 2026-10-19

Se añadió acción compartida por botón y menú contextual del editor, panel propio
con `DictionaryView`/`render_results`, y consulta mediante `Task`/worker existente.
No hay tokenización. Esta operación conserva exactamente espacios y saltos de la
selección; la consulta manual de administración conserva su comportamiento previo.
No se añaden dependencias. Argos y el diagnóstico de a249fea permanecen separados.

Validación dirigida:

- `QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest tests.test_selection_lookup tests.test_processes -v`:
  9 pruebas aprobadas. Incluyen worker real en SQLite aislada, prioridad descendente,
  activación, ausencia de diccionarios/coincidencias, espacios exactos, acción
  deshabilitada, procedencia y conservación del texto original, edición y Argos.
  Respuestas fuera de orden y errores antiguos se inyectan como regresiones de UI;
  no se presentan como inferencia real. La cola conserva solo la petición más
  reciente, con identificación por generación y selección; los cambios de texto
  también invalidan respuestas.
- `.venv/bin/python -m tools.selection_lookup_smoke`: worker real y panel Qt
  **offscreen**, con snapshot SQLite de la configuración normal abierto en origen
  en modo lectura. JMdict [2025-11-01] ya estaba activo: 日本 devuelve 4 filas,
  Japan y las lecturas にほん / にっぽん. Se procesaron dos respuestas reales al
  reemplazar una consulta en espera; el bucle Qt siguió atendiendo un temporizador.
  Se inspeccionó la imagen del panel `/tmp/HISTORICAL-REVIEW`.
- Hash SHA-256 de la base normal antes/después:
  `cac8a153f230ce9b5ca70dd8aecd59756d9b2bf4e88330d83ac6dd711d069aea`.
  Preferencias antes/después:
  `5913f27d5ef7cba0df41fd58fa9aca2a0f03dc9b8244abdafcd40c36cbe529fa`.
  No se modificaron los diccionarios ni preferencias normales ni el ZIP original.

Esta prueba no ejecutó OCR ni traducción: el original y Argos fueron centinelas
explícitos. Sigue vigente la evidencia manual del usuario de captura regional →
MangaOCR → 日本 sin editar, con el alcance limitado registrado anteriormente.
El nuevo botón, menú contextual y panel requieren revisión interactiva en el
escritorio; no se declara realizada a partir de Qt offscreen.

Comprobaciones adicionales del cambio compartido: `tests.test_storage` (8 pruebas)
y `tests.test_dictionary_content` (5 pruebas) aprobadas. El primer comando de
validación adicional incluyó por error un nombre inexistente
`tests.test_rich_dictionary`; se corrigió a `tests.test_dictionary_content`. No fue
un fallo del renderizador. No se repitieron inferencias OCR/traducción ni la
importación completa del ZIP por no haber cambios en esas rutas.

## Atajo global para captura seguida de OCR — 2026-10-19

Se añadió configuración persistente, registro nativo X11 por conexión propia,
liberación al cambiar/desactivar/cerrar, control de conflictos y cadena de
captura→OCR sin traducción. La espera previa al proceso es cancelable y bloquea
capturas repetidas desde el primer disparo. Cancelar preserva la imagen y textos
anteriores; la ventana restaura su maximización. No se alteraron preferencias
normales, recursos de JapaneseMining ni servicios del usuario.

Validación dirigida de `tests.test_hotkey`, `tests.test_processes` y
`tests.test_selection_lookup`: preferencias aisladas, reapertura, Restaurar,
cambio/desactivación/cierre, errores de escritura/registro, conflicto/rollback,
repetición y respuestas anteriores de diccionario, cancelación, motor no listo,
selección MangaOCR y cambio de idioma durante captura. Qt y protocolo X11
simulados/offscreen: no acreditan activación global en un escritorio real.

`tools.hotkey_flow_smoke` sí ejecutó **Tesseract 5.5.3 real**, con su prueba real
de disponibilidad y jpn sobre `examples/nihon.png`: **日本** en original y editor;
Argos no se inició. La activación y captura se inyectaron en el límite del worker.
La vista de preferencias se inspeccionó offscreen. No se repitió la carga de
MangaOCR, la importación JMdict ni la inferencia Argos al no cambiar esos motores.

El display :0 declarado KDE/X11 no es accesible desde el agente. Un intento de
servidor Xorg dummy aislado tampoco pudo crear sockets. Pendiente explícito:
registro real/conflicto real y captura→OCR desde otra aplicación. No hay soporte
Wayland implementado ni probado. El usuario sí confirmó anteriormente por GUI
la consulta 日本 con Japan, にほん / にっぽん y JMdict; esa evidencia no acredita
el atajo. APIs oficiales y recorrido manual: [GLOBAL-HOTKEY.md](GLOBAL-HOTKEY.md).
Inventario incremental: [hotkey-dependency-evidence.json](hotkey-dependency-evidence.json).

Resultado: **13 pruebas nuevas de atajo** y **9 regresiones dirigidas** aprobadas.
El fallo de escritura al desactivar no reactiva el registro: se mantiene liberado
en la sesión y la GUI avisa de la preferencia anterior que queda en disco.

## Integraciones → Stream Deck e instancia única — 2026-10-19

**37 pruebas dirigidas aprobadas** (`test_integrations`, `test_instance`,
`test_hotkey`, `test_processes`, `test_selection_lookup`). Generación ejecutable
con quoting y perfil XDG estable, sobrescritura confirmada, copiar/abrir carpeta,
cola/coalescencia de arranque, OCR no listo, cancelación/nueva captura, repetición,
protocolo cerrado y conservación de la acción del atajo y el botón existentes.

Transporte local real: QLocalSocket sobre socketpair Unix heredado, incluso entre
procesos, con ACK, fragmentación y deduplicación. Exclusión real: cinco procesos
QLockFile simultáneos, un ganador. Controlador de `main` abierto/cerrado y listen
simulados donde el entorno impide sockets con nombre; no se declara un recorrido
completo de arranque/captura verificado. Se corrigió el fixture para drenar los
DeferredDelete de Qt entre casos y aislar umask/logging del `main` simulado.

GUI inspeccionada **offscreen**, selector inyectado, script creado en XDG/datos
de prueba y ejecutado con un lanzador de prueba desde `/` usando caracteres
especiales. No hay nueva inferencia OCR ni captura real en esta validación.
`launch --help` acredita la entrada `--capture` sin arrancar GUI ni workers.
QLocalServer.listen está bloqueado (`Unknown error 1`) y el display :0 no es
accesible. Pendiente concreto: socket con nombre y activación completa con Next
abierto/cerrado desde terminal/StreamController y botón físico en escritorio real.

No se cambió StreamController, OSPlugin ni servicios/repositorios anteriores.
Guía, API oficial, detalle del protocolo y revisión manual: [STREAM-DECK.md](STREAM-DECK.md).
Inventario/evidencia incremental: [stream-deck-dependency-evidence.json](stream-deck-dependency-evidence.json).

## Cinco ZIP locales: términos, gramática, kanji y acento — 2026-10-19

**68 pruebas unitarias aprobadas** con
`QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -q`. Las nuevas regresiones verifican tipos combinados,
asociación de pitch por expresión y lectura, representación segura de kanji/pitch,
metadatos no admitidos con avisos, validación transaccional, cancelación,
migración aditiva/idempotente, prioridad/activación y borrado aislado. Incluyen
inspección/importación secuencial con **workers reales**, confirmación de diálogo
inyectada y cancelación de un worker de kanji sin iniciar el resto del lote.

Prueba real dirigida: `tools.multidictionary_smoke` importó los cinco ZIP en
SQLite/XDG aislados, comparó **1 003 190 filas originales JSON** una a una y
comprobó consultas extraídas de cada fuente. Resultado:

| Título literal | Revisión | Filas | Consulta real |
| --- | --- | ---: | --- |
| JMdict [2025-11-01] | JMdict.2025-11-01 | 513 033 | 日本, 4 filas |
| 新和英 | Shinwaei1 | 152 202 | 日本, 2 filas |
| 日本語文法辞典(全集) | DOJG_v1.01;2022-04-30;better formatting | 535 | くらい, 2 filas |
| KANJIDIC [2025-345] | kanjidic2.2025-345 | 10 383 | 亜, 1 fila; también 日 por GUI |
| アクセント辞典 | pitch1 | 327 037 | 日本, にほん [2] / にっぽん [3] |

Cada archivo pasó duplicado SHA-256, cancelación con rollback completo y
activación/prioridad persistida. La eliminación se comprueba por diccionario y
recuenta las filas restantes para asegurar que las demás fuentes conservan sus
entradas. Se reforzó expresamente esta comprobación y se repitió el ensayo real;
no se repitieron OCR, MangaOCR ni Argos.

La migración a esquema 2 sobre backup de la base normal conservó íntegramente
las huellas lógicas de su fila dictionaries y sus 513 033 terms, sin reconstruir
ni perder los valores de activación/prioridad/metadata. No se importó en el perfil
normal; sus archivos se leyeron para backup/huellas y conservaron SHA-256. Los
cinco originales también conservaron sus hashes. Huellas concretas, títulos,
revisiones, bancos y licencias: [local-dictionaries-evidence.json](local-dictionaries-evidence.json).

Consultas por la ruta de selección de la GUI, worker real, Qt **offscreen**:
日本, 日 y くらい, con secciones de bilingües/gramática/kanji/acento, origen y
asociación exacta de variantes. Hubo actividad del temporizador durante la
consulta. Se inspeccionó `/tmp/HISTORICAL-REVIEW`. Texto OCR y Argos
fueron centinelas, conservados; no se infiere exactitud OCR ni traducción de ellos.
La nueva selección múltiple/confirmación y el recorrido de escritorio siguen
pendientes de comprobación interactiva; offscreen y aceptación inyectada no la
acreditan. Guía y tabla por archivo: [LOCAL-DICTIONARIES.md](LOCAL-DICTIONARIES.md).

Se mantiene el diagnóstico de traducción a249fea, el atajo/Stream Deck y las
pruebas manuales anteriores con su alcance original. No se modifica ningún
servicio/entorno/repositorio previo ni se añaden ZIP, modelos o SQLite a Git.

Regresión adicional de cancelación en la frontera commit/ACK: si el proceso ya
confirmó el ZIP antes de recibir la cancelación, la GUI comprueba su presencia,
refresca la tabla y comunica que ya está completo, sin prometer rollback después
de un commit terminado. La unidad reproduce esa frontera de forma controlada;
la cancelación real del worker durante la escritura se verifica por separado.
