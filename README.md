# Na’atik Next — Fedora · Español / English

## Naatik Next

**Naatik Next** es una aplicación de escritorio para estudiar y comprender japonés directamente desde el contenido que aparece en pantalla.

Permite capturar texto mediante OCR, analizar palabras y frases, consultar diccionarios locales, revisar kanji y gramática, obtener traducciones y preparar contenido para herramientas de estudio como Anki.

Sus funciones pueden ejecutarse mediante **atajos de teclado configurables**, lo que permite adaptar el flujo de trabajo a las preferencias del usuario. También puede integrarse con dispositivos como **Stream Deck mediante scripts**, facilitando el acceso rápido a acciones como captura OCR, consulta, análisis o envío de contenido a herramientas de estudio.

Su flujo principal es simple: **capturar → reconocer → consultar → estudiar**.

Naatik Next está enfocado en OCR de escritorio, análisis del japonés, diccionarios, traducción y aprendizaje, sin depender de un sistema de subtítulos para anime o de un reproductor multimedia específico.

## Naatik Next

**Naatik Next** is a desktop application designed to help users study and understand Japanese directly from content displayed on their screen.

It can capture text using OCR, analyze words and sentences, search local dictionaries, provide kanji and grammar information, translate recognized text, and prepare study material for tools such as Anki.

Its features can be accessed through **configurable keyboard shortcuts**, allowing users to adapt the workflow to their own preferences. It can also be integrated with devices such as a **Stream Deck through scripts**, providing quick access to actions such as OCR capture, dictionary lookup, text analysis, or sending content to study tools.

Its main workflow is simple: **capture → recognize → look up → study**.

Naatik Next focuses on desktop OCR, Japanese language analysis, dictionaries, translation, and learning tools, without relying on anime subtitle systems or a specific media player.


Aplicación local Python/PySide6 para OCR, edición de texto, diccionarios Yomitan,
traducción Argos y preparación de tarjetas Anki. Incluye tutorial inicial e
interfaz español/inglés. Este árbol contiene fuentes para instalar desde cero;
no trae un entorno ya preparado ni datos personales.

Local Python/PySide6 application for OCR, text editing, Yomitan dictionaries,
Argos translation and Anki card preparation. Includes first-run onboarding and
Spanish/English UI. This is a source tree for a fresh installation, with no
prebuilt environment or personal data.

[Español](#español) · [English](#english) ·
[Validación de esta copia](PUBLICATION_REPORT.md) ·
[Third-party notices](docs/THIRD_PARTY_DEPENDENCIES.md) ·
[License status](LICENSE-STATUS.md)

## Español

### Requisitos Fedora

Objetivo comprobado: Fedora 44, x86_64, CPython 3.14 estándar (no free-threaded),
CPU. Los locks fijan versiones y hashes para esa plataforma. No cambies la versión
de Python ni los hashes para resolver un error sin validar el conjunto.

Requisitos base del sistema, si todavía faltan:

```sh
sudo dnf install python3 python3-pip ca-certificates
python3.14 --version
python3.14 -m venv --help
```

`python3-tkinter` solo es necesario para el bootstrap gráfico sin Qt; el instalador
de terminal funciona sin Tk. Tesseract y sus datos son opcionales para ese OCR:

```sh
sudo dnf install tesseract tesseract-langpack-eng tesseract-langpack-jpn tesseract-langpack-spa
```

Captura de pantalla: Spectacle 6 en KDE/X11 (`sudo dnf install spectacle`).
Atajos globales: libX11 y Qt xcb, con la aplicación abierta o residente. Wayland
no está acreditado; usa **Abrir imagen**. En instalaciones mínimas, consulta
las bibliotecas X11/xcb en [docs/INSTALLATION.md](docs/INSTALLATION.md).
Next no ejecuta sudo, no necesita CUDA y no usa entornos de otros proyectos.

### Instalación desde una descarga nueva

Descarga y extrae las fuentes en una carpeta elegida por ti. Abre una terminal
**dentro de esa carpeta**, junto a `launch` y `requirements.lock`:

```sh
bash tools/install.sh
./launch
```

El instalador pregunta **Idioma / Language** antes de crear la venv, instalar
paquetes Python o registrar el menú: `1` Español, `2` English, `c` cancelar.
Cancelar ahí no escribe preferencias ni descarga nada. Con perfil existente,
Enter conserva el idioma. Para una instalación no interactiva nueva, elige
explícitamente:

```sh
bash tools/install.sh --language es
# o: bash tools/install.sh --language en
```

La instalación normal necesita red para PyPI. Usa `--require-hashes` y locks
propios; no copia bibliotecas del usuario. La opción offline exige una wheelhouse
obtenida y verificada separadamente, no incluida en Git:

```sh
NAATIK_NEXT_OFFLINE=1 NAATIK_NEXT_WHEELHOUSE=/ruta/ruedas bash tools/install.sh --language es
```

`./launch` sin Qt también ofrece un bootstrap Tk cancelable con elección inicial
de idioma y confirmación de preparación. Su recorrido interactivo completo sigue
pendiente de validación. Usa el procedimiento de terminal comprobado arriba.

### Primer inicio e idioma

Un perfil nuevo abre bienvenida, OCR, traducción, diccionarios, Anki opcional y
primera prueba. Hay Volver, Continuar, Omitir por ahora y Reiniciar. Progreso y paso
se guardan por perfil. **Ayuda → Tutorial y configuración inicial** permite
retomarlo. Omitir/completar no acredita recursos ni descarga modelos.
Los perfiles anteriores, segundo plano, popups y `--capture` no abren el tutorial
automáticamente. **Configuración → Idioma** cambia la interfaz; no cambia idioma
OCR ni idiomas/ruta de traducción.

### OCR, traducción, diccionarios y Anki

- **OCR:** abre su asistente, elige Tesseract e idioma instalado, comprueba y
  guarda. Prueba `examples/hello.png` con `eng`. MangaOCR es japonés fijo y CPU,
  opcional: `bash tools/install.sh --manga-cpu`. Prepara/verifica sus pesos desde
  el asistente, con origen, licencia, hashes y confirmación de descarga. La
  presencia de un ejecutable o un archivo no acredita inferencia.
- **Traducción:** en Traducción elige idiomas/ruta, revisa el plan y confirma
  cada descarga. No incluye modelos Argos ni los busca en otros proyectos.
  El contenido OCR y las definiciones permanecen separados de la traducción.
- **Diccionarios:** importa tus ZIP Yomitan v3, revisa y confirma; activa los que
  quieras consultar y ajusta prioridad. No se suministran diccionarios. El editor
  OCR ofrece importar/activar si no hay activos; después vuelve a consultar.
  Consultas automáticas no abren diálogos repetidos. Consulta exacta, sin
  desinflexión ni análisis gramatical general.
- **Anki opcional:** prepara Anki y AnkiConnect por separado, abre el perfil
  deseado y comprueba la conexión desde Next. Elige mazo/tipo/campos y revisa el
  borrador antes de enviar. No se incluye una colección ni se configura tu Anki
  automáticamente. [Guía](docs/ANKI.md). La integración real con una colección
  separada continúa pendiente.
- **Lecturas de frases opcionales:** `bash tools/install.sh --phrase` prepara
  su entorno CPU propio con lock. No es necesario para instalar la base.

Comandos de uso desde esta misma carpeta:

```sh
./launch --show
./launch --capture
./launch --capture-copy
./launch --translator
./launch --phrase
```

La primera instancia permanece abierta/residente; ejecuta las siguientes llamadas
desde otra terminal. Popups reciben texto del portapapeles. Integraciones genera
scripts/comandos para KDE o Stream Deck/StreamController solo a petición tuya;
no modifica scripts personales ni botones existentes.

### Preferencias, actualización y desinstalación

El nombre XDG se conserva como `naatik-next` por compatibilidad. Configuración:
`$XDG_CONFIG_HOME/naatik-next/settings.json`; datos y diccionarios:
`$XDG_DATA_HOME/naatik-next`; estado/logs: `$XDG_STATE_HOME/naatik-next`.
Sin variables XDG se usan `~/.config`, `~/.local/share`, `~/.local/state`.
El idioma UI se guarda en `ui_language`; el tutorial tiene su propio estado.
No hay migración ni reutilización automática de otros proyectos.

Para actualizar, cierra Next y respalda tu código/datos XDG. Extrae las nuevas
fuentes y ejecuta `bash tools/install.sh`; conserva el idioma existente salvo que
lo cambies explícitamente. No ejecutes desinstalación para actualizar. Se
conservan preferencias, rutas explícitas, modelos, diccionarios, Anki y progreso.
Si cambias la ubicación del programa, revisa tus accesos/scripts externos; Next
no los reescribe. No copies una venv de otra ruta: reconstruye la de esta carpeta.

```sh
bash tools/uninstall.sh
```

La desinstalación retira solo la entrada de menú si todavía apunta a esta copia.
Conserva datos, preferencias, modelos, diccionarios y entornos. Cierra Next antes
de retirar manualmente la carpeta de código. Si nunca instalaste la base, no hay
venv desde la que ejecutar este script ni entrada de menú que esta copia haya creado.

## English

### Fedora requirements and fresh installation

Validated target: Fedora 44 x86_64, standard CPython 3.14 (not free-threaded), CPU.
Locks pin versions and hashes for this platform. Install missing system
prerequisites with `sudo dnf install python3 python3-pip ca-certificates`.
Check `python3.14 --version` and `python3.14 -m venv --help`. Do not use sudo pip.
System Tk (`python3-tkinter`) is optional for the GUI bootstrap.

Download and extract the sources into a folder of your choice. Open a terminal
**inside that folder**, next to `launch`:

```sh
bash tools/install.sh
./launch
```

Choose **1 Español / 2 English** before virtual environment creation, Python
package installation or desktop registration; **c** cancels without downloading
or saving preferences. Enter keeps an existing language. A fresh noninteractive
installation must explicitly choose `bash tools/install.sh --language en` (or es).
Online installation uses PyPI, pinned versions and required hashes. Offline
installation needs a separately verified wheelhouse:

```sh
NAATIK_NEXT_OFFLINE=1 NAATIK_NEXT_WHEELHOUSE=/path/to/wheels bash tools/install.sh --language en
```

No environments, wheels, models, dictionaries or user profiles are bundled.
No previous project is required or discovered. CPU works without CUDA. The
cancellable Tk bootstrap also offers language selection before preparation;
its full interactive flow remains unqualified. Use the validated terminal path.

### First launch, language and resources

New profiles show a six-step tutorial: welcome, OCR, translation, dictionaries,
optional Anki and a guided first test. Back, Continue, Skip for now and Restart
store progress per profile. **Help → Tutorial and initial setup** resumes it.
Skipping/completing never certifies resources. Legacy profiles, background use,
popups and `--capture` do not automatically open onboarding.
**Settings → Language** changes the UI independently of OCR and translation.

- **OCR:** install Tesseract and language data as needed, e.g.
  `sudo dnf install tesseract tesseract-langpack-eng tesseract-langpack-jpn`.
  Choose and check the engine/language in the OCR assistant. Test `eng` with
  `examples/hello.png`. Optional Japanese-only MangaOCR CPU uses
  `bash tools/install.sh --manga-cpu`; explicitly prepare and verify its model
  in the assistant. Downloads require confirmation and recorded provenance.
- **Translation:** choose source/target languages and route in Translation,
  inspect the plan and confirm optional model downloads. Argos models are not
  bundled or automatically reused from other projects.
- **Dictionaries:** import your own Yomitan v3 ZIPs, review, confirm, enable and
  set priorities. The OCR editor offers import/activation when none are active;
  retry the lookup after activation. Automatic lookup stays nonmodal. Exact
  lookup is separate from translation; general morphological analysis is absent.
- **Anki:** optional external Anki/AnkiConnect setup. Open your intended profile,
  check the connection, select deck/type/fields and review an editable draft
  before sending. No collection is bundled or automatically configured.
  Real Anki collection validation remains pending. See [Anki guide](docs/ANKI.md).
- **Phrase readings:** optional, prepared by `bash tools/install.sh --phrase`
  in its own pinned CPU environment; not required for the base app.

Use `./launch --show`, `--capture`, `--capture-copy`, `--translator` or `--phrase`.
The first process stays open/resident; make subsequent calls from another
terminal. Screen capture requires Spectacle 6 and KDE/X11; install `spectacle`
if needed. Global hotkeys require libX11/Qt xcb. Wayland remains unqualified;
use Open image. Stream Deck/StreamController commands are generated explicitly
from Integrations; existing personal scripts/buttons are never rewritten.

### Update and uninstall

Quit Next and back up your code/XDG data. Extract updated sources and rerun
`bash tools/install.sh`; keep the existing language unless changing it explicitly.
Do not uninstall to update or copy an old venv to a new path. Existing explicit
resource paths, preferences, dictionary priorities, Anki settings and tutorial
progress are preserved. Review external shortcuts if you move the program.

Configuration stays in `$XDG_CONFIG_HOME/naatik-next/settings.json`, data in
`$XDG_DATA_HOME/naatik-next`, state/logs in `$XDG_STATE_HOME/naatik-next`.
Defaults are `~/.config`, `~/.local/share`, `~/.local/state`. The folder name
`naatik-next` is retained for profile compatibility.

Run `bash tools/uninstall.sh` after a base installation to remove only this
copy's desktop entry. It preserves data, models, dictionaries, settings and
environments. Close Next before manually removing its source folder. A never
installed source copy has no venv or desktop entry created by this installer.

## Validation / Validación

[PUBLICATION_REPORT.md](PUBLICATION_REPORT.md) records tests of this publication
copy, including clean packaging, isolated installation/startup and remaining
limits. [VALIDACION.txt](VALIDACION.txt) is the corresponding release summary.
Historical documentation is retained for third-party provenance and design;
its old local paths/results are not instructions or proof for a fresh machine.

Earlier Fedora validation: 254 tests, 251 successful, 3 skipped; representative
ES/EN visual review, real X11 lifecycle/single instance, Spectacle region capture,
Escape and a temporary X11 shortcut. Those prior desktop results are historical,
not a new qualification of this copy. See the publication report for reruns.

Pending: full online/clean-VM installation, Wayland, interactive Tk bootstrap,
optional-model inference in this copy, physical Stream Deck buttons, and the
complete desktop capture→OCR→clipboard→real-Anki chain. Offscreen tests do not
qualify desktop capture/hotkeys. No models are certified by completing onboarding.

Run the suite only with temporary HOME/XDG and `PYTHONNOUSERSITE=1`, e.g. from
an isolated installed copy: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -v`.
The publication report describes the isolated environment used here. Manual
JMdict diagnostics require an explicit `--dictionary /path/to/fixture.zip`;
no dictionaries are automatically read from another project.

## Licencia / License

El código propio está disponible bajo [MIT](LICENSE):
**Copyright (c) 2026 ElpincheAlx**. Las licencias y los avisos independientes de
terceros se conservan y no se sustituyen por MIT. Consulta
[LICENSE-STATUS.md](LICENSE-STATUS.md) y el
[inventario de terceros](docs/THIRD_PARTY_DEPENDENCIES.md).

Project-owned code is licensed under [MIT](LICENSE):
**Copyright (c) 2026 ElpincheAlx**. Third-party components and resources retain
their independent licenses and notices; the project's MIT license does not
relicense them. See the license status and third-party inventory above.

### Source packaging / Empaquetado de fuentes

From the source root / Desde la raíz de fuentes:

```sh
python3.14 -m tools.build_fedora_package --output dist --validation VALIDACION.txt
```

The generated package includes source, bilingual instructions, validation summary,
license status and SHA256 manifests. Do not add local data or environments under
source directories; the builder excludes Python bytecode and copies only its
listed source folders/root files. Review the archive before publishing it.
Packaging preserves LICENSE (MIT) for project-owned code and the independent third-party notices.
