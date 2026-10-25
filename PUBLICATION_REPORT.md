# Informe de preparación / Publication report — 2026-10-24

> Nota actual: el informe de preparación inicial que sigue es histórico.
> Posteriormente el titular autorizó MIT y la publicación; véase la decisión
> actual al final. El tamaño indicado pertenece a la copia inicial.

La carpeta `~/naatik` contiene una copia publicable para revisión, creada desde
las fuentes actuales de `Naatik-next`, incluidos tutorial y catálogos ES/EN.
No se utilizaron las fuentes de ninguna copia temporal de pruebas anterior.
No se inicializó Git en esta carpeta, ni se hizo commit, push o repositorio remoto.
No se modificaron el proyecto de origen, otros proyectos, entornos anteriores,
scripts personales, servicios ni el perfil habitual.

## Contenido

- `naatik_next/`: aplicación completa, tutorial, i18n, ambos catálogos y
  `model-catalog.json` necesario para verificar recursos opcionales.
- `launch`, plantilla `.desktop`, instalador/desinstalador, empaquetado y
  herramientas de diagnóstico mantenidas, con permisos originales.
- Suite completa de pruebas, todos los locks originales y los dos PNG sintéticos
  `hello.png` y `nihon.png`, inspeccionados visualmente. No contienen fuentes
  tipográficas embebidas ni son capturas de datos del usuario.
- README bilingüe, AGENTS.md intacto, inventario/avisos y evidencia de terceros,
  resumen de validación y estado de licencia.
- `.gitignore` y `SOURCE_MANIFEST.json` con hashes originales, transformaciones
  documentales/herramientas y exclusiones. Los módulos de ejecución, pruebas,
  locks y recursos necesarios coinciden byte a byte con el origen actual.

Tamaño del árbol: **206 archivos, 2050448 bytes aparentes (1.96 MiB)**.
El espacio asignado por el sistema de archivos puede ser mayor.

## Exclusiones y privacidad

No se copiaron .git, .venv*, .wheelhouse*, cachés, __pycache__, paquetes binarios,
modelos, ZIP de diccionarios, bases personales, perfiles, configuración personal,
credenciales/tokens, logs, volcados, temporales, archivos dist previos ni scripts
personales de captura. No se borraron sus originales.

Los documentos técnicos conservados tienen rutas identificables anonimizadas.
Los enlaces a material local no incluido se señalan como referencias históricas.
No se publican capturas históricas, muestras del usuario ni sus salidas OCR.
Se preservan versiones/orígenes, licencias/fuentes, avisos, hashes y alcance de
terceros; los resultados históricos no acreditan esta copia ni una VM limpia.
La revisión estática no encontró enlaces simbólicos, rutas de usuario obligatorias,
claves privadas ni coincidencias de patrones de tokens reales. No sustituye una
revisión humana de publicación. Todos los JSON y Python incluidos se analizaron.

Se omitieron tres diagnósticos locales que descubrían datos del entorno normal:
`tools/gui_smoke.py`, `tools/multidictionary_smoke.py` y
`tools/selection_lookup_smoke.py`. No son requisitos de ejecución ni importados
por la suite. Permanecen en el origen. Los diagnósticos JMdict conservados exigen
`--dictionary /ruta/al/ZIP` y no buscan otros proyectos.

## Ajustes de esta copia

README e indicaciones de empaquetado adaptados a una descarga limpia, sin rutas
personales. El empaquetador conserva `.gitignore`, informe, manifiesto y estado
de licencia; las instrucciones raíz proceden del README bilingüe.
El diagnóstico `independent_smoke` se ajustó al tutorial actual y al estado
válido de un motor opcional no preparado; no descarga modelos automáticamente.
El validador público selecciona español explícitamente antes de instalar, de
acuerdo con sus aserciones. No se cambió la lógica de negocio ni dependencias.

## Pruebas ejecutadas en el paquete extraído

Se generó y extrajo un paquete nuevo desde esta copia. Bubblewrap ocultó **todo
/home y los temporales anteriores**, deshabilitó la red y proporcionó /dev y
/tmp privados. Solo se expusieron esta revisión y sus entradas de prueba.
HOME/XDG nuevos, venv nueva y PYTHONNOUSERSITE=1; importaciones de aplicación y
PySide6 comprobadas dentro del árbol extraído y su propia venv. Los valores por
defecto de modelos/apuntadores pertenecen a la copia y a su XDG, no a otro proyecto.

La entrada offline fue una copia separada de ruedas disponibles, verificada por
los locks antes de instalar. No se reutilizó una venv. Tras ocultar el origen,
instalación, arranque y pruebas no podían leer Naatik-next, JapaneseMining ni
ningún otro directorio del usuario original. Esta prueba no verifica descargar
las ruedas desde Internet. El sistema Fedora, Python y bibliotecas nativas sí
siguen siendo prerrequisitos, como indica el README.

- Instalación base offline real: correcta, incluyendo menú en XDG temporal.
- Suite: **254 pruebas, 251 correctas, 3 omitidas, sin fallos** (36.880 s).
  Dos omisiones por análisis de frases opcional ausente; una porque el gate
  de error de bind no aplica cuando los sockets están permitidos.
- Primer inicio/tutorial y apertura explícita del asistente OCR; Tesseract real
  con `examples/hello.png` devolvió **Hello world**. Guardar motor/idioma y
  segundo inicio conservaron la configuración. Sin modelos ni diccionarios previos.
- `launch` real desde un cwd ajeno en **ES y EN**, persistencia del tutorial,
  segunda invocación reenviada a la instancia propietaria, SIGTERM 143 y limpieza
  de lock/endpoint. Qt **offscreen**; broker/worker reales, sin acreditar display.
- Reparación offline conserva idioma/preferencias; cambio explícito modifica
  solo ui_language. Diccionario sintético desactivado con prioridad 41 conservó
  su SHA256. Desinstalación retiró solo su menú y conservó configuración,
  diccionario y entorno.
- `.gitignore`: 15 casos de exclusión y 11 rutas necesarias verificadas en un
  repositorio de prueba separado, nunca dentro de este árbol.
- Hashes internos del paquete, exclusiones, permisos y procedencia de módulos
  comprobados. La carpeta entregada no contiene la venv ni el perfil de pruebas.

Resumen legible por máquina: [docs/publication-validation.json](docs/publication-validation.json).
Los logs brutos quedan fuera del árbol publicable; no se publican logs privados.
Para reproducir: empaqueta con el comando del README, extrae en otra ruta, usa
HOME/XDG nuevos y una venv creada allí, y ejecuta la suite offscreen. Para repetir
el aislamiento fuerte se necesita Bubblewrap (herramienta diagnóstica opcional)
con /home oculto, /tmp privado, red aislada y solo la revisión expuesta.

## Pendientes y licencia

Sin PASS nuevo para instalación online, VM limpia, Wayland, bootstrap Tk
interactivo, modelos opcionales reales, captura/atajos/portapapeles del escritorio,
AnkiConnect con colección real ni botones físicos Stream Deck/StreamController.
Las pruebas offscreen y de IPC no equivalen a esos gates de escritorio.
La validación anterior de captura Spectacle y atajo X11 pertenece a las fuentes
originales y está descrita como histórica; no se repitió para esta copia.

**No se encontró licencia propia del proyecto. No se eligió ni concedió una.**
Consulta [LICENSE-STATUS.md](LICENSE-STATUS.md). Las licencias de dependencias no
sustituyen la decisión del titular sobre el código propio.

## English summary

Prepared directly from the current working sources. Runtime code, tests, locks,
examples, launch and AGENTS are unchanged. Includes bilingual README, tutorial,
ES/EN catalogs, installation/uninstallation/packaging tools and third-party
provenance. Private diagnostics, environments, caches, user resources, profiles,
credentials, logs and symlinks are absent. Selected historical docs are redacted;
legacy diagnostics that automatically read unrelated local data are omitted.

A newly generated archive was extracted and installed with all original /home
projects and prior /tmp files hidden, networking disabled, and fresh HOME/XDG/venv.
Offline wheels were separately supplied and hash-checked; no old environment was
reused. 254 tests: 251 passed, 3 skipped. Real Tesseract returned Hello world.
Actual launch/IPC/shutdown passed in ES/EN with Qt offscreen. Repair and uninstall
preserved synthetic preferences and dictionary bytes. Online/clean-VM install,
real desktop capture/hotkeys, optional models, real Anki and physical buttons
remain unqualified here. No own project license was found or selected.
No Git repository, commit, push or remote was created in the prepared folder.

## Decisión posterior del titular: MIT y publicación — 2026-10-24

Tras la preparación inicial, el titular autorizó expresamente añadir el texto
estándar completo de MIT, Copyright (c) 2026 ElpincheAlx, realizar el commit
inicial y publicar un repositorio público. LICENSE cubre el código propio;
los avisos y licencias independientes de terceros se mantienen intactos en su
alcance. README y LICENSE-STATUS reflejan esta decisión. Los hashes originales
de SOURCE_MANIFEST se conservan; los hashes de la publicación actual se registran
por separado, sin pretender que existía una licencia durante las pruebas anteriores.

Se detectó que GitHub considera `ElpincheAlx/naatik` y `ElpincheAlx/Naatik` el
mismo nombre: ya pertenece al proyecto Go privado. Tras consultarlo, el titular
eligió **ElpincheAlx/naatik-next**, sujeto a disponibilidad, para esta publicación
Fedora. El repositorio Go existente no se sobrescribe ni cambia de visibilidad.
Destino autorizado: https://github.com/ElpincheAlx/naatik-next .
La identidad ya configurada en las fuentes es Alx Hndz <alx@naatik.local>;
se reutiliza solo para este commit, sin cambiar la configuración global.

Los cambios de esta fase son de licencia, documentación y manifiestos. No se
modifican runtime, pruebas, locks o recursos, ni se reetiquetan como nuevas las
254 pruebas anteriores. La revisión previa al commit comprueba contenido,
exclusiones, integridad de manifiestos y empaquetado con LICENSE incluido.
No se crean tags ni releases.

After the initial preparation, the owner explicitly selected MIT for project-owned
code and authorized the initial commit and public publication. Third-party terms
remain independent. Original hashes and the historical lack of a license are
preserved; current publication hashes are recorded separately. GitHub's
case-insensitive name collision with the existing private Go project was resolved
by the owner's choice of ElpincheAlx/naatik-next. No runtime/dependency changes
or new claims about the previous test results are made in this phase.
