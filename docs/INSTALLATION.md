> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# Instalar y preparar Na’atik Next

JapaneseMining no se necesita. El código soportado es una aplicación local Qt,
Tesseract y un adaptador MangaOCR con recursos configurables; PaddleOCR sigue
pendiente. Translator y OCR Phrase están implementados; Anki y móvil/historial siguen pendientes.
La traducción se prepara desde [Configurar traducción](TRANSLATION-SETUP.md).

Última evidencia: **PASS/0 externo**, 2026-10-19, instalación desde fuentes públicas
y MangaOCR CPU real en HOME/XDG nuevos. [Detalle y comando para abrir esa copia](EXTERNAL-PUBLIC-INSTALL-PASS.md).
No acredita máquina limpia ni interacción gráfica de esa instalación.

## Antes de empezar: equipo sin Python ni OCR

El objetivo implementado es **Fedora 44 KDE Plasma, x86_64**. El escritorio para
captura/atajo es **KDE/X11**, no Wayland. La base fue probada con Qt offscreen
sobre ese host; aún no se acredita una instalación en máquina/VM limpia.
No hay instalador acreditado para Ubuntu, Windows, macOS o ARM.

Necesitas una cuenta de usuario, acceso a Internet y permiso para instalar los
RPM del sistema (sudo). Obtén los **fuentes de Next** proporcionados por el proyecto
y extráelos en una carpeta de tu usuario. No se publicó un release en este paso
ni se debe usar el instalador del Na’atik anterior. JapaneseMining no se necesita.
Reserva varios GB libres (base Qt, runtime CPU, datos UniDic y pesos), y una
transferencia de aproximadamente 1.1 GB para la validación pública completa.
No necesitas GPU, CUDA, compilador C/C++ ni paquetes Python del usuario.

En una terminal de **Fedora 44**, instala primero Python/pip, certificados y OCR:

```bash
sudo dnf install python3 python3-pip python3-tkinter ca-certificates tesseract tesseract-langpack-eng tesseract-langpack-jpn tesseract-langpack-spa
```

Después de instalar esos requisitos, abre **launch --translator**. Si falta la
base Qt de Next, aparece el asistente Tk para prepararla con confirmación, progreso
y cancelación. Abre la sección **Traducción** para preparar motor/modelos en un solo recorrido.
No hace falta Argos global ni ejecutar pip manualmente. Tk es un requisito del
sistema solo para este arranque sin entorno; el resto de la aplicación sigue en Qt.
La instalación de RPM sigue siendo responsabilidad del usuario; Next no usa sudo.

El paquete se llama **python3**, aunque proporciona `/usr/bin/python3.14`:
[paquete oficial Fedora 44](https://packages.fedoraproject.org/pkgs/python3.14/python3/fedora-44.html).
Se contrastó también con `rpm --whatprovides` en el host. No ejecutes pip con sudo.
Comprueba los requisitos antes del instalador:

```bash
python3 --version
python3 -m pip --version
python3 -m venv --help
tesseract --version
tesseract --list-langs
```

El Python de esta entrega debe ser **3.14 estándar**, no free-threaded. Tesseract
necesita `eng` para la prueba reproducible y `jpn` para japonés; `spa` es opcional.
`jpn_vert` solo debe elegirse si aparece en la lista. Los datos son paquetes del
sistema, no vienen con el código Python de Next.

Las ruedas Qt incluyen Qt, pero necesitan bibliotecas nativas del sistema. En
Fedora KDE normalmente ya están instaladas; en un sistema mínimo prepáralas:

```bash
sudo dnf install glib2 fontconfig freetype libX11 libX11-xcb libXext libXrender libSM libICE libxcb libxkbcommon libxkbcommon-x11 xcb-util xcb-util-wm xcb-util-image xcb-util-keysyms xcb-util-renderutil xcb-util-cursor libglvnd-glx mesa-libGL
```

Nombres contrastados con los RPM instalados en Fedora 44; **no** se ejecutó este
aprovisionamiento en una VM vacía. Referencia de bibliotecas:
[requisitos X11/xcb oficiales de Qt](https://doc.qt.io/qt-6/linux-requirements.html).
Si Qt indica una biblioteca ausente, conserva el error y usa `dnf provides` para
identificar su RPM; no lo soluciones copiando bibliotecas de otro proyecto.
Para capturar regiones instala además `sudo dnf install spectacle` y usa una
sesión KDE/X11 disponible en tu sistema. El script de validación no instala RPM,
no inicia sesión gráfica ni acredita captura/atajo global.

## Por qué sigue fijado Python 3.14

El código no demuestra necesitar 3.14: sus 20 módulos se analizaron sin errores
de sintaxis con 3.12.15 y 3.13.16, **sin** importar dependencias ni probar inferencia.
El METADATA inspeccionado de la base exige como máximo un mínimo 3.12 (NumPy);
PySide6 declara >=3.10,<3.15, Pillow >=3.10 y CTranslate2 >=3.9. Eso hace razonable
investigar 3.12/3.13, pero no acredita la aplicación con esos intérpretes.

Los hashes actuales de varias ruedas son **cp314**. Usar Python 3.12/3.13 exige
otros hashes, cierre de dependencias compatible y pruebas de carga/inferencia,
no basta cambiar una condición del instalador. Por ello se mantiene 3.14. El
validador genera una matriz 3.11–3.14 desde Requires-Python y ruedas públicas;
la matriz no sustituye pruebas reales, y Torch CPU tiene un índice separado.
Consulta [la evidencia actual](PUBLIC-INSTALL-VALIDATION.md).

| Función | Implementación | Acreditación |
|---|---|---|
| Abrir imagen, editor, diccionarios, preparación | Qt/Pillow, sin selector de pantalla | Probado offscreen en Fedora 44 x86_64 con entorno nuevo |
| Tesseract | Ejecutable/datos de idioma del sistema | Inferencia real Hello world en entorno nuevo |
| Captura | Spectacle 6 en KDE/X11 | Caso previo del usuario acreditado; no revalidado en esta entrega |
| Atajo global | libX11.so.6, KDE/X11, Qt xcb | Pruebas automatizadas; interacción global pendiente |
| Entrada de menú e IPC | .desktop XDG y QLocalServer/Socket | Menú generado aislado; activación global/IPC real pendiente |
| MangaOCR CPU propio | Python 3.14, torch 2.13.0+cpu, transformers 5.14.1, manga-ocr 0.1.16 | PASS/0 externo: instalación pública, modelo verificado e inferencia real 日本; GUI offscreen |
| GPU, Wayland, otras distribuciones, ARM, Windows/macOS | Sin ruta acreditada por esta entrega | No anunciar compatibilidad |

## Instalar

Obtén una copia de los fuentes de Next en una carpeta de tu usuario. No hay un
release publicado en este paso. Ejemplo, desde esa carpeta:

```bash
./tools/install.sh
./launch
```

El instalador funciona desde cualquier directorio, usando su propia ubicación;
no exige `${PROJECT_ROOT}`. Si Python tiene otro nombre, usa
`NAATIK_NEXT_PYTHON=/ruta/a/python3.14 ./tools/install.sh`.
Crea `.venv` sin paquetes de usuario/sistema y una entrada propia **Na’atik Next**
en el menú XDG; no escribe rutas personales en archivos versionados.
El instalador no inicia la app ni cambia preferencias/diccionarios.

Con red, pip usa explícitamente PyPI, sin caché pip, y los hashes de `requirements.lock`. Con ruedas aprobadas:

```bash
NAATIK_NEXT_OFFLINE=1 NAATIK_NEXT_WHEELHOUSE=/ruta/a/ruedas ./tools/install.sh
```

Si `.wheelhouse` existe, la base usa modo offline automáticamente. Para forzar
fuentes públicas incluso en ese caso: `NAATIK_NEXT_ONLINE=1 ./tools/install.sh`. Falta de rueda,
versión/arquitectura incompatible, hash o dependencia producen error visible;
no se usa otro entorno. La caché no está en Git. Ruedas base: ~310 MiB en este host.
No copiar todo el entorno del desarrollador. El lock de base conserva una integración
mínima Argos por paquete/tokenizer/CTranslate2: excluye backends de segmentación y
no pretende que `pip check` completo de Argos pase; ver DEPENDENCIES.md.

## Primer inicio y OCR

El asistente pregunta por **idioma de trabajo OCR**, no promete una interfaz
traducida: la interfaz actual es española. Elige Tesseract/idioma explícitamente,
comprueba requisitos y guarda. Si faltan datos, instálalos con el gestor del
sistema o elige explícitamente un idioma disponible. Nunca se cambia el motor
para ocultar un fallo. El asistente puede cerrarse/reabrirse en Preferencias;
si aún no guardaste, vuelve a aparecer en el siguiente inicio.

MangaOCR (japonés fijo, sin selector de dirección) requiere su entorno opcional:

```bash
./tools/install.sh --manga-cpu
```

También se puede solicitar en el asistente con confirmación. Usa solamente
`.venv-mangaocr` de esta instalación, CPU sin CUDA; ~301 MB de ruedas, más espacio
de instalación. GPU no es necesaria ni se prepara automáticamente. Si hay una
caché propia completa: `NAATIK_NEXT_OFFLINE=1 NAATIK_NEXT_WHEELHOUSE=/ruta/ruedas-manga
./tools/install.sh --manga-cpu` (en una línea). El cierre CPU cp314 se instaló y probó desde fuentes públicas en la ejecución
externa PASS/0; `pip check` pasó, y el worker cargó/reconoció 日本. Se mantiene
la variante CPU exacta, sin sustituir por cp313/CUDA ni por JapaneseMining.

Después elige un snapshot local completo o **Descargar modelo verificado**.
La confirmación muestra origen Hugging Face, revisión inmutable, bytes y licencia
Apache-2.0 declarada en su propia ficha. La descarga va a
`$XDG_DATA_HOME/naatik-next/models/manga-ocr-base` (por defecto
`~/.local/share/naatik-next/models/…`), con timeout por petición de 20 s y total
15 min por archivo, límites de tamaño, SHA-256 y publicación por reemplazo.
Cancelar/cerrar conserva `.part`; reintentar reanuda si servidor admite Range,
reinicia ese archivo si lo ignora y elimina un parcial con hash incorrecto.
Los archivos completos verificados se reutilizan sin red. No hay modelos en Git.

Pulsa **Comprobar requisitos / carga e inferencia** y luego guarda. El worker
local solo acredita Listo tras cargar el modelo y reconocer la muestra 日本.
Una descarga verificada por sí sola no acredita disponibilidad. Next no envía
capturas/textos durante preparación ni inferencia. La red se bloquea en el worker
MangaOCR. Perfiles existentes conservan recursos explícitamente guardados; para
independizar uno, prepara el entorno/modelo propios y selecciona esas rutas.
No se migra ni copia el recurso antiguo automáticamente.

Argos: sin modelos no hay rutas y se informa desde GUI. Puedes preparar paquetes
`.argosmodel` explícitamente con las herramientas oficiales de Argos para este
usuario; Next todavía no tiene instalador gráfico de modelos de traducción.
No usar un comando que importe backends de diagnóstico en la base mínima; consulta
DEPENDENCIES.md antes de ampliar ese entorno. Diccionarios: importa tus ZIP desde
Diccionarios; no se distribuyen ni se descargan automáticamente.

## Actualizar y desinstalar

Cierra Next. Conserva tus datos XDG, actualiza los fuentes mediante el mecanismo
con que obtuviste la copia y repite `./tools/install.sh`; si utilizas MangaOCR,
repite `./tools/install.sh --manga-cpu`. Se reaplican versiones/hashes y la entrada
del menú. No hay actualización automática, migración de entornos entre versiones
de Python ni descarga automática de modelos. No actualices con trabajos activos.

`./tools/uninstall.sh` retira solamente la entrada del menú que pertenece a esta
instalación. Conserva preferencias, diccionarios, logs, modelos y entornos. Después
de cerrar puedes borrar manualmente la carpeta de fuentes y sus venvs. Si deseas
borrar datos, elige explícitamente qué directorios XDG de **naatik-next** eliminar;
el desinstalador no tiene una opción destructiva implícita ni elimina ZIP originales.

## Qué falta antes de declarar una distribución completa

Ya se acreditaron instalación pública del cierre CPU cp314, descarga completa
con SHA-256, carga/inferencia, cancelación/recarga del worker y reutilización sin
red en la ejecución externa. Siguen pendientes la reanudación real de una descarga
interrumpida y una máquina/VM limpia con paquetes del sistema; apertura desde menú, captura,
cancelación, atajo e IPC en escritorio real. La prueba con HOME/XDG y venv nuevos
no elimina ejecutables ni bibliotecas del host. Evidencia de esta entrega:
[INDEPENDENCE-VALIDATION.md](INDEPENDENCE-VALIDATION.md).

UniDic Lite es un dato de idioma transitivo del tokenizer: PyPI publica un sdist.
El instalador fija el hash del sdist público y prepara previamente setuptools/packaging/wheel con
`requirements-manga-build.lock`; no descarga herramientas de build sin fijar.
Para instalación offline completa incluye también el sdist oficial
y las herramientas de construcción. El lock ya no admite una rueda local
no publicada como alternativa. La licencia
BSD de los datos se registra por separado de la licencia del motor.


## Un único comando para validar desde tu terminal

Después de instalar los RPM anteriores, ejecuta:

```bash
${PROJECT_ROOT}/tools/validate-public-install.sh
```

Si los fuentes están en otra carpeta, usa la ruta absoluta a ese mismo script.
Su ejecución autoriza la instalación de dependencias y descarga del modelo
fijado **solo en el área aislada**, sin preguntas adicionales. Lee primero la
licencia del modelo enlazada arriba. No necesita sudo ni instala nada en el
perfil normal. No arranca Next por su canal IPC ni toca servicios anteriores.

Crea un directorio nuevo `~/Naatik-validation/public-install-XXXXXXXX/`, copia
fuentes sin `.venv`, `.wheelhouse` o pesos y configura HOME, XDG, cachés y temporales
propios. No lee cachés del desarrollador. Comprueba **todos** los hashes permitidos
contra PyPI/índice CPU oficial y falla si alguno no se publica o fue retirado.
Instala las URLs públicas auditadas con hashes en la copia, nunca reescribe tus
locks originales. Construye UniDic desde su sdist oficial con build tools fijadas.

Después prueba base Qt/Tesseract real, primer/segundo inicio, runtime CPU propio,
descarga completa de los seis archivos con SHA-256, carga/inferencia **日本** sin
editar texto, cancelación/reinicio y reutilización del modelo sin red. Qt es
**offscreen**, no captura interactiva. Conserva los archivos descargados y todos
los logs; cada ejecución empieza desde un área nueva y puede necesitar varios
minutos. No instala diccionarios ni modelos Argos y no envía datos personales.

Resultado en `summary.txt` y `result.json`:

- **PASS / código 0**: pasaron estas etapas reales; aún no equivale a máquina limpia
  ni valida el escritorio.
- **BLOCKED / código 2**: falta un requisito o la red/proveedor impide continuar.
- **FAIL / código 1**: lock no público, hash incorrecto, instalación/inferencia u
  otra comprobación falló. No se cambia de versión/motor para ocultarlo.

Logs por etapa en `logs/`, metadatos públicos en `public-metadata/`, auditoría de
locks y matriz Python en JSON cuando se pudieron completar; evidencias de descarga
`model-download.json` y de inferencia `cpu-inference.json` solo si esas etapas
pasaron. Un resultado BLOCKED temprano no acredita las etapas restantes.
Cierra Next antes de la prueba si quieres evitar que actividad concurrente cambie
las preferencias/base normales durante la comparación de hashes. No hay restauración
automática que pueda sobrescribir cambios tuyos. Para compartir resultados basta
`result.json`, `summary.txt` y el log de la etapa fallida; no adjuntes pesos/venvs.

Para abrir **la instalación ya validada** en tu escritorio sin tocar el perfil
normal, usa el comando completo de [EXTERNAL-PUBLIC-INSTALL-PASS.md](EXTERNAL-PUBLIC-INSTALL-PASS.md#instalación-y-perfil-que-se-validaron).
No repitas la validación para simplemente abrir esa copia. Sus preferencias
actuales son Tesseract/eng; selecciona MangaOCR explícitamente en OCR para revisarlo.


## Recursos opcionales de los popups

Translator/OCR Phrase pueden abrirse sin OCR configurado ni recursos lingüísticos.
Para lecturas/palabras usa **Preparar lecturas…** (confirmación) o
`./tools/install.sh --phrase`: `.venv-phrase`, Fugashi/UniDic con hashes fijados,
sin Torch ni entornos antiguos. Modelos Argos: sección **Traducción** o **Opciones avanzadas → Importar modelo local**
para un archivo local; no se descargan automáticamente ni se buscan en Argos global.
La ruta nueva es `$XDG_DATA_HOME/naatik-next/argos/packages`. No se migran/borran
modelos de otros lugares. Diccionarios: importación explícita por el usuario.

El controlador de validación pública ahora también copia/audita
`requirements-phrase.lock` y prepara el runtime de frase. No se ha vuelto a
calificar ese recorrido completo desde red en esta entrega, ni se ha cambiado
la copia independiente previamente validada. El entorno lingüístico nuevo se
instaló y probó sin red con artefactos públicos verificados de caché, HOME/XDG
nuevos y sin paquetes del usuario. Evidencia, límites y uso: [POPUPS.md](POPUPS.md).
