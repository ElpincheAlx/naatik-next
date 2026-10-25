> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# Entorno y decisión de traducción

`.venv` no hereda site-packages del usuario ni del sistema. El lanzador elimina
PYTHONPATH/PYTHONHOME y establece PYTHONNOUSERSITE. No reutiliza entornos de Na’atik
ni de JapaneseMining. Las ruedas locales se identificaron por sus metadatos
WHEEL en la caché pip existente y se enlazaron a `.wheelhouse`; no se alteró la
caché. Solo se conservaron las 17 ruedas del lock (aproximadamente 324 MB).
El lock fija todas las distribuciones instaladas de ejecución y sus hashes.
`tools/install.sh` puede reproducir la instalación sin red con esa wheelhouse.

Argos Translate 1.11 incluye backends generales de segmentación que requieren
Stanza, spaCy, Torch y otros recursos. Esta primera entrega usa solamente su API
`argostranslate.package.get_installed_packages` y los tokenizadores de sus paquetes,
con CTranslate2 en CPU para inferencia. Nunca importa `argostranslate.translate`
ni sus segmentadores. La unidad de traducción es una línea corta; no se afirma
segmentación lingüística completa ni equivalencia con toda la aplicación Argos.
Se respetan los prefijos de destino cuando constan en el paquete.

Por esa selección explícita se instala Argos con `--no-deps`, junto con el cierre
de dependencias requerido por el adaptador, fijado en requirements.lock. `pip check`
señalará dependencias opcionales para esta ruta que la distribución Argos declara
como generales; no se debe usar esta venv como instalación completa de Argos CLI.
Las pruebas de importación e inferencia real validan la ruta utilizada.

Modelos: Next consulta únicamente su directorio propio
`$XDG_DATA_HOME/naatik-next/argos/packages`. Se importan explícitamente desde un
`.argosmodel` local con confirmación, validación de rutas y procedencia SHA-256.
No se buscan modelos en otros proyectos ni en la instalación Argos global, y no
se descargan automáticamente. Los modelos antes compartidos deben importarse
expresamente para usarlos en Next; no se migran ni se borran. La GUI
muestra las rutas probadas; el worker mantiene modelos cargados hasta cancelación,
redetección o cierre. Un cambio de modelo necesita volver a revisar Argos.

Fuentes técnicas primarias consultadas:
- https://github.com/yomidevs/yomitan/blob/master/docs/making-yomitan-dictionaries.md
- https://github.com/yomidevs/yomitan/blob/master/ext/data/schemas/dictionary-term-bank-v3-schema.json
- https://argos-translate.readthedocs.io/en/stable/index.html
- Código local instalado de argostranslate 1.11: package.py, tokenizer.py,
  settings.py, translate.py (inspección de APIs y riesgo de descargar segmentadores).
- `spectacle --help` y `--version` de la instalación local, consultados con
  QT_QPA_PLATFORM=offscreen porque no hay conexión al display.


## Runtime opcional de MangaOCR

La base y el runtime MangaOCR usan entornos propios separados. El cierre CPU de
`requirements-manga-cpu.lock`, con build tools fijadas en
`requirements-manga-build.lock`, se instaló desde fuentes públicas en la copia
`public-install-U6n9VjIW`: `pip check` correcto, torch 2.13.0+cpu sin CUDA,
manga-ocr 0.1.16, descarga íntegra del modelo y OCR real 日本. Evidencia externa:
[EXTERNAL-PUBLIC-INSTALL-PASS.md](EXTERNAL-PUBLIC-INSTALL-PASS.md).

Los perfiles nuevos apuntan a `.venv-mangaocr` de Next y al modelo bajo XDG.
`tools/install.sh --manga-cpu` prepara el entorno; el asistente permite seleccionar
o descargar el modelo explícitamente. El worker pertenece a Next, usa CPU y
red deshabilitada. Listo exige carga e inferencia, no encontrar archivos.

La prueba antigua con `${REFERENCE_ROOT}/.venv-mangaocr/bin/python` permanece como
historia en [manga-runtime.json](manga-runtime.json), no como requisito de producto.
Se conservan rutas externas explícitamente guardadas para no romper preferencias,
pero no se descubren ni reutilizan automáticamente. El registro del PASS externo
no modifica esas preferencias ni migra el perfil normal. Máquina limpia e
interacción gráfica de la copia validada continúan pendientes.


## Runtime opcional de OCR Phrase / lecturas de Translator

`tools/install.sh --phrase` prepara `.venv-phrase` independiente: Fugashi 1.5.2
(wrapper MeCab) y UniDic Lite 1.0.8 (datos UniDic 2.1.2). Los hashes públicos
están en `requirements-phrase.lock`; se reutiliza el lock de herramientas de
construcción de UniDic `requirements-manga-build.lock` (solo setuptools,
packaging y wheel, sin motor ni modelo OCR). No requiere MangaOCR, Torch,
JapaneseMining ni servicios locales. `NAATIK_NEXT_OFFLINE=1` y
`NAATIK_NEXT_WHEELHOUSE` permiten suministrar los artefactos fijados sin red;
se incluye el sdist público de UniDic, no una rueda reconstruida con otro hash.
La GUI solicita confirmación antes de preparar/descargar estos recursos.

El Tagger se inicializa con el diccionario propio explícito y `-r /dev/null`;
no descubre MeCab de sistema. Produce segmentación, lema ortográfico, POS y
lecturas disponibles. No aporta JLPT ni análisis gramatical general. Los
resultados ambiguos se etiquetan como lecturas léxicas; desconocidos no reciben
lecturas inventadas. Licencias por código, MeCab y datos, hashes y evidencia:
[THIRD_PARTY_DEPENDENCIES.md](THIRD_PARTY_DEPENDENCIES.md).

## Preparación gráfica de traducción

La ventana principal incluye la sección **Traducción**. Puede reutilizar el adaptador de la
base propia o preparar el subconjunto CPU de `requirements-translation.lock`
(12 paquetes con las mismas versiones/hashes), en datos XDG propios. El catálogo
se consulta durante el recorrido y los componentes requieren confirmación; no se incluyen binarios.
El arranque sin `.venv` necesita el RPM **python3-tkinter** además de los requisitos
externos de [INSTALLATION.md](INSTALLATION.md); después usa la GUI Qt normal.
No usa un Python preparado globalmente ni entornos/cachés de otro proyecto.
[Recorrido y límites de validación](TRANSLATION-SETUP.md),
[inventario detallado](THIRD_PARTY_DEPENDENCIES.md#16-preparación-gráfica-de-traducción-2026-10-20).
