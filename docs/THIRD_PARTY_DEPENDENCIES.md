> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# Inventario de software y recursos de terceros

Revisión inicial: **2026-10-19**, sobre e24ed3b, conservada como evidencia histórica.
La actualización de instalación independiente al final de este documento modifica
los defaults y añade locks propios; distingue lo probado de lo pendiente. No es
autorización general de redistribución. Conserva el diagnóstico a249fea.

## Alcance, evidencia y mantenimiento

Se contrastaron imports (incluidos imports dentro de funciones), requirements.lock,
instalador, METADATA/Requires-Dist, archivos LICENSE/NOTICE, entornos instalados,
metadatos RPM y recursos locales. La evidencia reproducible de identidad está en
[third-party-audit.json](third-party-audit.json): rutas y SHA-256 de METADATA,
licencias locales, ruedas, modelos, datos, diccionarios y fuentes. No contiene
sus binarios. Los hashes identifican archivos observados; no certifican el origen
de una descarga ni la compatibilidad de licencias.

Los grafos declarados se separan de los imports observados. Una dependencia
transitiva declarada o un paquete presente **no equivale** a una necesidad de
la ruta de ejecución utilizada. Los extras de desarrollo/test de las bibliotecas
no se activaron. Next usa unittest de la biblioteca estándar, no requiere pytest,
ruff, spaCy, Stanza o todo el entorno del usuario para su ejecución normal.

Al integrar, actualizar o retirar una dependencia, actualizar **este archivo**,
la evidencia y el lock/manifiesto correspondiente en el mismo cambio. Revisar:
función/import real, D/T, uso, versión, origen, licencia propia y de recursos,
notices, hashes y distribución. Marcar lo no verificado; no convertir un pip freeze
en requirements. La regla también figura en [AGENTS.md](../AGENTS.md).

Convenciones (cada tabla hereda las condiciones de su ámbito):

- **D/T**: directa de Next / transitiva. Que Next use PySide6.QtWidgets no convierte
  todos los módulos Qt en dependencias directas.
- **R**: entorno base `.venv`, instalado por herramientas de Next. Ruedas en caché
  local `.wheelhouse`; **no se distribuyen en Git**. Una copia completa de estas
  carpetas sí contendría terceros y necesitaría conservar sus avisos.
- **M**: backend MangaOCR **integrado, opcional**, worker propio de Next usando el
  Python externo configurado. Bibliotecas/modelos externos, no distribuidos con Git.
- **Dg**: prueba/diagnóstico con el Python del usuario; no dependencia de ejecución
  de Next. No se distribuye con Next.
- **S**: software/datos del sistema Fedora; Next lo utiliza, no lo incluye.
- **P**: recurso o integración pendiente, no necesario para las funciones actuales.

### Condiciones de redistribución citadas por las tablas

Las combinaciones A + P requieren ambos grupos de avisos; A o P indica una
alternativa declarada, no una doble obligación. Son recordatorios de los textos
identificados, no una evaluación de un futuro
paquete completo. Conservar los LICENSE, NOTICE, COPYRIGHT y avisos de componentes
embebidos aplicables; no sustituirlos por esta tabla.

| Código | Condiciones y avisos a conservar | Fuente primaria |
| --- | --- | --- |
| P | MIT/BSD/ISC/PSF/CNRI y afines: copyright, permiso, condiciones y descargo; BSD-3 además prohíbe usar nombres como aval. Respetar el texto exacto de cada variante. | LICENSE/COPYING y METADATA por paquete en la evidencia; [MIT](https://opensource.org/license/mit), [BSD-3](https://opensource.org/license/bsd-3-clause). |
| A | Apache-2.0: copia de licencia, avisos aplicables, NOTICE si existe y avisos de cambios al redistribuir archivos modificados. | [Apache §4](https://www.apache.org/licenses/LICENSE-2.0). |
| M | MPL-2.0, o combinación MPL/MIT: conservar avisos y cumplir obligaciones de fuente de los archivos cubiertos si se redistribuyen. No atribuir MPL automáticamente a toda Next. | LICENSE local de certifi/tqdm; [MPL-2.0](https://www.mozilla.org/en-US/MPL/2.0/). |
| Q | PySide/Shiboken: alternativas LGPL/GPL declaradas; para LGPL conservar textos/avisos y permitir modificación/reemplazo/relink de la biblioteca, con obligaciones de fuente de la biblioteca. Los módulos Qt y componentes internos tienen condiciones propias. No se ha verificado una licencia comercial para esta instalación. | METADATA instalado; [Qt for Python](https://doc.qt.io/qtforpython-6/licenses.html), [obligaciones LGPL Qt](https://www.qt.io/licensing/open-source-lgpl-obligations). |
| G | AGPL-3.0: conservar avisos/licencia y evaluar fuente correspondiente y condiciones de interacción por red cuando apliquen a lo que se distribuya/ejecute. MiniSBD no se incorpora al runtime mínimo de Next. | LICENSE local de MiniSBD; [fuente del proyecto](https://github.com/LibreTranslate/MiniSBD/blob/main/LICENSE). |
| N | Licencia específica NVIDIA: conservar EULA/avisos y comprobar qué archivos permite redistribuir. No asumir permiso MIT/Apache a partir de Torch o de repositorios de código relacionados. | METADATA y LICENSE específicos por rueda en la evidencia. |
| ? | Licencia o condiciones exactas no verificadas; presencia local no acredita permiso de redistribución. | Se indica el documento o la carencia concreta. |

## 1. Ejecución base y herramientas de instalación (R)

Procedencia: ruedas preexistentes en la caché pip del usuario; no se acreditó su
URL histórica de descarga. Versiones, plataformas y SHA-256 coinciden con el lock.
Instalación reproducible del conjunto actualmente fijado:

```bash
cd ${PROJECT_ROOT}
python3.14 -m venv .venv
.venv/bin/python -m pip install --no-index --find-links .wheelhouse \
  --no-deps --require-hashes -r requirements.lock
```

El bootstrap CPython/ensurepip es del sistema, no una rueda del lock. La plataforma
comprobada es CPython 3.14 / Fedora x86_64; los tags se verificaron, sin prometer
compatibilidad universal. Cada fila cita su METADATA/archivo de licencia local
mediante `python_groups.base` del [registro](third-party-audit.json).

| Dependencia y versión instalada | Relación | Función / uso | Licencia acreditada o declarada | Avisos |
| --- | --- | --- | --- | --- |
| argostranslate 1.11.0 | D | descubrimiento de paquetes y tokenizadores | MIT (LICENSE local; METADATA dice UNKNOWN) | P |
| click 8.4.2 | T | CLI de sacremoses; rama BPE | BSD-3-Clause | P |
| ctranslate2 4.8.1 | D | inferencia de traducción | MIT | P |
| joblib 1.5.3 | T | soporte de sacremoses/BPE | BSD-3-Clause | P |
| numpy 2.5.2 | T | arrays nativos de CTranslate2 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | P |
| packaging 26.3 | T | versiones de paquetes Argos | Apache-2.0 OR BSD-2-Clause | A o P |
| pillow 12.3.0 | D | imágenes y ejemplo OCR | MIT-CMU | P |
| PySide6 6.11.1 | D | API Qt y metapaquete | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | Q |
| PySide6_Addons 6.11.1 | T | dependencia del metapaquete; no importada por Next | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | Q |
| PySide6_Essentials 6.11.1 | T | QtCore/QtGui/QtWidgets; QtNetwork para IPC local (§10) | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | Q |
| PyYAML 6.0.3 | T | dependencia declarada de CTranslate2 | MIT | P |
| regex 2026.7.19 | T | sacremoses/BPE | Apache-2.0 AND CNRI-Python | A + P |
| sacremoses 0.1.1 | T | tokenización BPE opcional de paquetes Argos | MIT (declarada) | P |
| sentencepiece 0.2.2 | D | tokenizadores de modelos ja_en/en_es | Apache-2.0 | A |
| setuptools 84.0.0 | T | dependencia declarada de CTranslate2; instalación | MIT | P |
| shiboken6 6.11.1 | T | enlace de objetos Qt/Python | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only | Q |
| tqdm 4.70.0 | T | progreso de sacremoses/BPE | MPL-2.0 AND MIT | M |
| pip 26.0.1 | herramienta | instalación; bootstrap no fijado en lock | MIT | P |

Argos se usa por `package` y `tokenizer`, con CTranslate2; no se importa su módulo
completo `translate` en producción. Su METADATA declara MiniSBD, spaCy y Stanza,
pero el instalador usa `--no-deps` de forma deliberada. `pip check` confirma esas
**tres ausencias**; no se ocultan ni se incorporan automáticamente. Véase
[DEPENDENCIES.md](DEPENDENCIES.md). Los modelos actuales usan SentencePiece;
sacremoses y su cadena se reservan para el backend BPE admitido, no se observó su
uso con ja_en/en_es. setuptools es declarado por CTranslate2, no un nuevo import
directo de Next. PySide6_Addons no se importa, pero el metapaquete lo declara.

PySide6/Essentials/Addons incluyen binarios Qt **6.11.1** (qVersion observado),
no dependen solamente del Qt instalado por Fedora. Las ruedas locales revisadas
de PySide6, Shiboken, CTranslate2 y SentencePiece no incluyen archivos con nombres
LICENSE/NOTICE/COPYING detectables. Sus declaraciones de licencia no reemplazan
los textos: obtener avisos completos de la versión y de los componentes embebidos
antes de redistribuir esos binarios. CTranslate2 declara MIT y se contrasta con
[su LICENSE](https://github.com/OpenNMT/CTranslate2/blob/master/LICENSE);
SentencePiece declara Apache-2.0 y tiene [LICENSE upstream](https://github.com/google/sentencepiece/blob/master/LICENSE).
No se considera resuelta la auditoría de todos los componentes nativos de Qt,
Chromium incluido en módulos no usados, codecs o bibliotecas vendorizadas.

## 2. MangaOCR: backend integrado y opcional (M)

No es un motor pendiente: d6390fb integró carga, inferencia CPU, cancelación y
cierre reales. A diferencia de Tesseract/S, usa bibliotecas Python externas en
`${REFERENCE_ROOT}/.venv-mangaocr`, sin modificar ese entorno ni sus servicios.
El modelo se conserva en un proceso de Next; no se ejecutan scripts antiguos.

Origen de la instalación histórica no verificado. [manga-runtime.json](manga-runtime.json)
fija versiones observadas y hashes de código/modelos. El paquete contiene ajustes
locales para Transformers: **reinstalar solo manga-ocr==0.1.16 no reproduce esos
cambios**. No hay lock de reconstrucción completa ni ruedas de ese entorno en
`.wheelhouse`. Hasta fijar fuente/parches, ruedas y hashes propios, la reproducción
exacta de ese entorno externo está pendiente; no se promete con tools/install.sh.
Un entorno alternativo se configura explícitamente y solo se acredita tras carga
e inferencia reales. No se instalan paquetes ni descargan modelos automáticamente.

Se reconstruyó el grafo de Requires-Dist para manga-ocr/torch en Linux/Python 3.14:
62 distribuciones declaradas, más pip/wheel observados como herramientas. Se
registró qué distribuciones se importan en la sonda de Next y qué bibliotecas
aparecen en `/proc/self/maps`. **CPU no significa rueda Torch sin CUDA**: la
compilación instalada mapea cuBLAS, cuDNN, CUDA runtime y otras bibliotecas NVIDIA.
No se califican de sobrantes. Tampoco se declara imprescindible cada extra CLI:
fire/pyperclip son declarados por MangaOCR, pero su ruta CLI no se utiliza.

Fuentes de licencia/versión por fila: `python_groups.manga` del registro (METADATA
exacto, LICENSE/NOTICE existentes y sus hashes); código MangaOCR
[Apache-2.0](https://github.com/kha-white/manga-ocr/blob/master/LICENSE).
La columna función indica los padres declarantes; «no importada» no demuestra
que sea seguro retirar una dependencia binaria o declarada sin otra comprobación.
Todas estas filas son externas M, no redistribuidas con Next.

| Dependencia y versión | Relación / uso observado o declarado | Función: soporte de / requerida por | Licencia / fuente local | Avisos |
| --- | --- | --- | --- | --- |
| annotated-doc 0.0.5 | T; M declarada; no importada en la sonda | typer | MIT | P |
| anyio 4.14.2 | T; M importada | httpx | MIT | P |
| certifi 2026.7.22 | T; M importada | httpcore, httpx | MPL-2.0 | M |
| click 8.4.2 | T; M importada | huggingface-hub | BSD-3-Clause | P |
| cuda-bindings 13.3.1 | T; M importada | torch | LicenseRef-NVIDIA-SOFTWARE-LICENSE | N |
| cuda-pathfinder 1.6.0 | T; M importada | cuda-bindings | Apache-2.0 | A |
| cuda-toolkit 13.0.3.0 | T; M metapaquete de la compilación instalada | torch | NO VERIFICADA | ? |
| filelock 3.32.2 | T; M importada | huggingface-hub, torch | MIT | P |
| fire 0.7.1 | T; M declarada; no importada en la sonda | manga-ocr | Apache-2.0 | A |
| fsspec 2026.7.0 | T; M declarada; no importada en la sonda | huggingface-hub, torch | BSD-3-Clause | P |
| fugashi 1.5.2 | T; M importada | manga-ocr | MIT AND BSD-3-Clause | P |
| h11 0.16.0 | T; M importada | httpcore | MIT | P |
| hf-xet 1.5.2 | T; M declarada; no importada en la sonda | huggingface-hub | Apache-2.0 | A |
| httpcore 1.0.9 | T; M importada | httpx | BSD-3-Clause | P |
| httpx 0.28.1 | T; M importada | huggingface-hub | BSD-3-Clause | P |
| huggingface_hub 1.26.0 | T; M importada | tokenizers, transformers | Apache-2.0 | A |
| idna 3.18 | T; M importada | anyio, httpx | BSD-3-Clause | P |
| jaconv 0.5.0 | T; M importada | manga-ocr | MIT License | P |
| Jinja2 3.1.6 | T; M importada | torch | BSD (variante no normalizada; ver LICENSE) | P |
| loguru 0.7.3 | T; M importada | manga-ocr | MIT (declarada) | P |
| manga-ocr 0.1.16 | D; M importada | OCR japonés (raíz) | Apache-2.0 | A |
| markdown-it-py 4.2.0 | T; M declarada; no importada en la sonda | rich | MIT (declarada) | P |
| MarkupSafe 3.0.3 | T; M importada | jinja2 | BSD-3-Clause | P |
| mdurl 0.1.2 | T; M declarada; no importada en la sonda | markdown-it-py | MIT (declarada) | P |
| mpmath 1.3.0 | T; M importada | sympy | BSD | P |
| networkx 3.6.1 | T; M declarada; no importada en la sonda | torch | BSD-3-Clause | P |
| numpy 2.5.1 | T; M importada | manga-ocr, transformers | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | P |
| nvidia-cublas 13.1.1.3 | T; M binaria declarada por Torch; ver mapas | cuda-toolkit, nvidia-cudnn-cu13, nvidia-cusolver | LicenseRef-NVIDIA-Proprietary | N |
| nvidia-cuda-cupti 13.0.85 | T; M binaria declarada por Torch; ver mapas | cuda-toolkit | LicenseRef-NVIDIA-Proprietary | N |
| nvidia-cuda-nvrtc 13.0.88 | T; M binaria declarada por Torch; ver mapas | cuda-toolkit, nvidia-cublas | LicenseRef-NVIDIA-Proprietary | N |
| nvidia-cuda-runtime 13.0.96 | T; M binaria declarada por Torch; ver mapas | cuda-toolkit | LicenseRef-NVIDIA-Proprietary | N |
| nvidia-cudnn-cu13 9.20.0.48 | T; M binaria declarada por Torch; ver mapas | torch | LicenseRef-NVIDIA-Proprietary | N |
| nvidia-cufft 12.0.0.61 | T; M binaria declarada por Torch; ver mapas | cuda-toolkit | LicenseRef-NVIDIA-Proprietary | N |
| nvidia-cufile 1.15.1.6 | T; M binaria declarada por Torch; ver mapas | cuda-toolkit | LicenseRef-NVIDIA-Proprietary | N |
| nvidia-curand 10.4.0.35 | T; M binaria declarada por Torch; ver mapas | cuda-toolkit | LicenseRef-NVIDIA-Proprietary | N |
| nvidia-cusolver 12.0.4.66 | T; M binaria declarada por Torch; ver mapas | cuda-toolkit | LicenseRef-NVIDIA-Proprietary | N |
| nvidia-cusparse 12.6.3.3 | T; M binaria declarada por Torch; ver mapas | cuda-toolkit, nvidia-cusolver | LicenseRef-NVIDIA-Proprietary | N |
| nvidia-cusparselt-cu13 0.8.1 | T; M binaria declarada por Torch; ver mapas | torch | NVIDIA Proprietary Software | N |
| nvidia-nccl-cu13 2.29.7 | T; M binaria declarada por Torch; ver mapas | torch | LicenseRef-NVIDIA-Proprietary | N |
| nvidia-nvjitlink 13.3.33 | T; M binaria declarada por Torch; ver mapas | cuda-toolkit, nvidia-cufft, nvidia-cusolver, nvidia-cusparse | LicenseRef-NVIDIA-Proprietary | N |
| nvidia-nvshmem-cu13 3.4.5 | T; M binaria declarada por Torch; ver mapas | torch | LicenseRef-NVIDIA-Proprietary | N |
| nvidia-nvtx 13.0.85 | T; M binaria declarada por Torch; ver mapas | cuda-toolkit | Apache 2.0 | A |
| packaging 26.2 | T; M importada | huggingface-hub, transformers | Apache-2.0 OR BSD-2-Clause | A o P |
| pillow 12.3.0 | D; M importada | manga-ocr | MIT-CMU | P |
| pip 26.2 | herramienta; instalación externa; no necesaria en inferencia | fuera del grafo; herramienta instalada | MIT | P |
| Pygments 2.20.0 | T; M importada | rich | BSD-2-Clause | P |
| pyperclip 1.11.0 | T; M declarada; no importada en la sonda | manga-ocr | BSD | P |
| PyYAML 6.0.3 | T; M importada | huggingface-hub, transformers | MIT | P |
| regex 2026.7.19 | T; M importada | transformers | Apache-2.0 AND CNRI-Python | A + P |
| rich 15.0.0 | T; M importada | typer | MIT | P |
| safetensors 0.8.0 | T; M importada | transformers | Apache-2.0 (declarada) | A |
| setuptools 83.0.0 | T; M importada | torch | MIT | P |
| shellingham 1.5.4 | T; M declarada; no importada en la sonda | typer | ISC License | P |
| sympy 1.14.0 | T; M importada | torch | BSD | P |
| termcolor 3.3.0 | T; M declarada; no importada en la sonda | fire | MIT | P |
| tokenizers 0.22.2 | T; M importada | transformers | Apache-2.0 (declarada) | A |
| torch 2.13.0 | D; M importada | manga-ocr | Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT | A + P |
| tqdm 4.70.0 | T; M importada | huggingface-hub, transformers | MPL-2.0 AND MIT | M |
| transformers 5.14.1 | T; M importada | manga-ocr | Apache 2.0 License | A |
| triton 3.7.1 | T; M importada | torch | MIT (declarada) | P |
| typer 0.27.0 | T; M declarada; no importada en la sonda | transformers | MIT | P |
| typing_extensions 4.16.0 | T; M importada | huggingface-hub, torch | PSF-2.0 | P |
| unidic-lite 1.0.8 | T; M importada | manga-ocr | MIT (declarada) | P |
| wheel 0.47.0 | herramienta; instalación externa; no necesaria en inferencia | fuera del grafo; herramienta instalada | MIT | P |

Torch contiene además sus propios terceros (98 archivos de avisos/licencias en
esta instalación), y NumPy/fugashi/setuptools también contienen componentes o
avisos adicionales: se enumeran y hashean en la evidencia. La licencia principal
no sustituye a esas licencias. El dato UniDic se inventaría aparte más abajo.

## 3. Diagnóstico oficial de Argos (Dg), no runtime de Next

`tools/diagnose_translation.py --official-python /usr/bin/python3` usa Argos
oficial con Stanza local y descargas deshabilitadas. La comparación de a249fea
sigue siendo diagnóstica: no obliga a instalar Stanza/Torch/spaCy/MiniSBD en .venv.
MiniSBD/spaCy se importan por la implementación general de Argos, pero el
segmentador elegido para aquella comparación fue Stanza; no se afirma haber
probado inferencia MiniSBD o modelos spaCy.

Procedencia: paquetes del Python del usuario y del sistema, leídos de sus
METADATA. No hay lock/hashes de ruedas para reconstruir todo este entorno; la
repetibilidad exacta fuera de esta máquina está **pendiente**. Registrar sus
versiones no convierte ese entorno completo en requisito del producto.

La tabla es el **grafo declarado** de Argos/Stanza para esta plataforma, no todo
el pip freeze del usuario ni una afirmación de necesidad/import de cada paquete.
Campos, licencias locales y fuentes: `python_groups.diagnostic` del registro.
Versiones compartidas con M/R se repiten cuando pertenecen a otro entorno:
no deben mezclarse, por ejemplo NumPy 2.3.5/Dg frente a 2.5.2/R y 2.5.1/M.
Todos son Dg, externos, con los avisos indicados si algún día se redistribuyen.

| Dependencia y versión | Relación / uso | Función: soporte de / requerida por | Licencia / fuente local | Avisos |
| --- | --- | --- | --- | --- |
| annotated-doc 0.0.5 | T; diagnóstico (grafo declarado) | typer | MIT | P |
| annotated-types 0.8.0 | T; diagnóstico (grafo declarado) | pydantic | MIT | P |
| anyio 4.13.0 | T; diagnóstico (grafo declarado) | httpx | MIT | P |
| argostranslate 1.11.0 | D; diagnóstico (grafo declarado) | API oficial / segmentación (raíz) | MIT (LICENSE local; METADATA dice UNKNOWN) | P |
| blis 1.3.3 | T; diagnóstico (grafo declarado) | thinc | BSD | P |
| catalogue 2.0.10 | T; diagnóstico (grafo declarado) | spacy, srsly, thinc | MIT | P |
| certifi 2026.1.4 | T; diagnóstico (grafo declarado) | httpcore, httpx | MPL-2.0 | M |
| charset-normalizer 3.4.4 | T; diagnóstico (grafo declarado) | requests | MIT | P |
| click 8.4.2 | T; diagnóstico (grafo declarado) | sacremoses | BSD-3-Clause | P |
| cloudpathlib 0.24.0 | T; diagnóstico (grafo declarado) | weasel | MIT (declarada) | P |
| confection 1.3.3 | T; diagnóstico (grafo declarado) | spacy, thinc, weasel | MIT | P |
| ctranslate2 4.8.1 | D; diagnóstico (grafo declarado) | argostranslate | MIT | P |
| cuda-bindings 13.3.1 | T; diagnóstico (grafo declarado) | torch | LicenseRef-NVIDIA-SOFTWARE-LICENSE | N |
| cuda-pathfinder 1.6.0 | T; diagnóstico (grafo declarado) | cuda-bindings | Apache-2.0 | A |
| cuda-toolkit 13.0.3.0 | T; diagnóstico (grafo declarado) | torch | NO VERIFICADA | ? |
| cymem 2.0.13 | T; diagnóstico (grafo declarado) | preshed, spacy, thinc | MIT | P |
| emoji 2.15.0 | T; diagnóstico (grafo declarado) | stanza | BSD (variante no normalizada; ver LICENSE) | P |
| filelock 3.32.0 | T; diagnóstico (grafo declarado) | minisbd, torch | MIT | P |
| flatbuffers 25.12.19 | T; diagnóstico (grafo declarado) | onnxruntime | Apache 2.0 | A |
| fsspec 2026.7.0 | T; diagnóstico (grafo declarado) | torch | BSD-3-Clause | P |
| h11 0.16.0 | T; diagnóstico (grafo declarado) | httpcore | MIT | P |
| httpcore 1.0.9 | T; diagnóstico (grafo declarado) | httpx | BSD-3-Clause | P |
| httpx 0.28.1 | T; diagnóstico (grafo declarado) | weasel | BSD-3-Clause | P |
| idna 3.18 | T; diagnóstico (grafo declarado) | anyio, httpx, requests | BSD-3-Clause | P |
| Jinja2 3.1.6 | T; diagnóstico (grafo declarado) | spacy, torch | BSD (variante no normalizada; ver LICENSE) | P |
| joblib 1.5.3 | T; diagnóstico (grafo declarado) | sacremoses | BSD-3-Clause | P |
| markdown-it-py 4.2.0 | T; diagnóstico (grafo declarado) | rich | MIT (declarada) | P |
| MarkupSafe 3.0.2 | T; diagnóstico (grafo declarado) | jinja2 | ver LICENSE local; expresión no normalizada | ? |
| mdurl 0.1.2 | T; diagnóstico (grafo declarado) | markdown-it-py | MIT (declarada) | P |
| minisbd 0.9.5 | T; diagnóstico (grafo declarado) | argostranslate | AGPL-3.0 (texto; opción posterior no verificada) | G |
| mpmath 1.3.0 | T; diagnóstico (grafo declarado) | sympy | BSD | P |
| murmurhash 1.0.15 | T; diagnóstico (grafo declarado) | preshed, spacy, thinc | MIT | P |
| networkx 3.6.1 | T; diagnóstico (grafo declarado) | stanza, torch | BSD-3-Clause | P |
| numpy 2.3.5 | T; diagnóstico (grafo declarado) | blis, ctranslate2, minisbd, onnxruntime, spacy, stanza, thinc | ver LICENSE local; expresión no normalizada | ? |
| nvidia-cublas 13.1.1.3 | T; diagnóstico (grafo declarado) | cuda-toolkit, nvidia-cudnn-cu13, nvidia-cusolver | LicenseRef-NVIDIA-Proprietary | N |
| nvidia-cuda-cupti 13.0.85 | T; diagnóstico (grafo declarado) | cuda-toolkit | LicenseRef-NVIDIA-Proprietary | N |
| nvidia-cuda-nvrtc 13.0.88 | T; diagnóstico (grafo declarado) | cuda-toolkit, nvidia-cublas | LicenseRef-NVIDIA-Proprietary | N |
| nvidia-cuda-runtime 13.0.96 | T; diagnóstico (grafo declarado) | cuda-toolkit | LicenseRef-NVIDIA-Proprietary | N |
| nvidia-cudnn-cu13 9.20.0.48 | T; diagnóstico (grafo declarado) | torch | LicenseRef-NVIDIA-Proprietary | N |
| nvidia-cufft 12.0.0.61 | T; diagnóstico (grafo declarado) | cuda-toolkit | LicenseRef-NVIDIA-Proprietary | N |
| nvidia-cufile 1.15.1.6 | T; diagnóstico (grafo declarado) | cuda-toolkit | LicenseRef-NVIDIA-Proprietary | N |
| nvidia-curand 10.4.0.35 | T; diagnóstico (grafo declarado) | cuda-toolkit | LicenseRef-NVIDIA-Proprietary | N |
| nvidia-cusolver 12.0.4.66 | T; diagnóstico (grafo declarado) | cuda-toolkit | LicenseRef-NVIDIA-Proprietary | N |
| nvidia-cusparse 12.6.3.3 | T; diagnóstico (grafo declarado) | cuda-toolkit, nvidia-cusolver | LicenseRef-NVIDIA-Proprietary | N |
| nvidia-cusparselt-cu13 0.8.1 | T; diagnóstico (grafo declarado) | torch | NVIDIA Proprietary Software | N |
| nvidia-nccl-cu13 2.29.7 | T; diagnóstico (grafo declarado) | torch | LicenseRef-NVIDIA-Proprietary | N |
| nvidia-nvjitlink 13.3.33 | T; diagnóstico (grafo declarado) | cuda-toolkit, nvidia-cufft, nvidia-cusolver, nvidia-cusparse | LicenseRef-NVIDIA-Proprietary | N |
| nvidia-nvshmem-cu13 3.4.5 | T; diagnóstico (grafo declarado) | torch | LicenseRef-NVIDIA-Proprietary | N |
| nvidia-nvtx 13.0.85 | T; diagnóstico (grafo declarado) | cuda-toolkit | Apache 2.0 | A |
| onnxruntime 1.28.0 | T; diagnóstico (grafo declarado) | minisbd | MIT License | P |
| packaging 25.0 | T; diagnóstico (grafo declarado) | argostranslate, onnxruntime, spacy, thinc, weasel | Apache/BSD (relación no verificada) | P |
| preshed 3.0.13 | T; diagnóstico (grafo declarado) | spacy, thinc | MIT | P |
| protobuf 7.35.1 | T; diagnóstico (grafo declarado) | onnxruntime, stanza | 3-Clause BSD License | P |
| pydantic 2.13.4 | T; diagnóstico (grafo declarado) | spacy, thinc, weasel | MIT | P |
| pydantic_core 2.46.4 | T; diagnóstico (grafo declarado) | pydantic | MIT | P |
| Pygments 2.20.0 | T; diagnóstico (grafo declarado) | rich | BSD-2-Clause | P |
| PyYAML 6.0.2 | T; diagnóstico (grafo declarado) | ctranslate2 | MIT | P |
| regex 2026.9.10 | T; diagnóstico (grafo declarado) | sacremoses | Apache-2.0 AND CNRI-Python | A + P |
| requests 2.33.1 | T; diagnóstico (grafo declarado) | spacy, stanza | Apache-2.0 | A |
| rich 15.0.0 | T; diagnóstico (grafo declarado) | typer | MIT | P |
| sacremoses 0.1.1 | T; diagnóstico (grafo declarado) | argostranslate | MIT (declarada) | P |
| sentencepiece 0.2.2 | T; diagnóstico (grafo declarado) | argostranslate | Apache-2.0 | A |
| setuptools 80.10.2 | T; diagnóstico (grafo declarado) | ctranslate2, spacy, thinc, torch | MIT | P |
| shellingham 1.5.4 | T; diagnóstico (grafo declarado) | typer | ISC License | P |
| smart_open 8.0.1 | T; diagnóstico (grafo declarado) | weasel | MIT (declarada) | P |
| spacy 3.8.13 | T; diagnóstico (grafo declarado) | argostranslate | MIT | P |
| spacy-legacy 3.0.12 | T; diagnóstico (grafo declarado) | spacy | MIT | P |
| spacy-loggers 1.0.5 | T; diagnóstico (grafo declarado) | spacy | MIT | P |
| srsly 2.5.3 | T; diagnóstico (grafo declarado) | spacy, thinc, weasel | MIT | P |
| stanza 1.10.1 | D; diagnóstico (grafo declarado) | argostranslate | Apache License 2.0 | A |
| sympy 1.14.0 | T; diagnóstico (grafo declarado) | torch | BSD | P |
| thinc 8.3.13 | T; diagnóstico (grafo declarado) | spacy | MIT | P |
| torch 2.13.0 | T; diagnóstico (grafo declarado) | stanza | Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT | A + P |
| tqdm 4.70.0 | T; diagnóstico (grafo declarado) | sacremoses, spacy, stanza | MPL-2.0 AND MIT | M |
| triton 3.7.1 | T; diagnóstico (grafo declarado) | torch | MIT (declarada) | P |
| typer 0.27.0 | T; diagnóstico (grafo declarado) | spacy, weasel | MIT | P |
| typing-inspection 0.4.2 | T; diagnóstico (grafo declarado) | pydantic | MIT | P |
| typing_extensions 4.16.0 | T; diagnóstico (grafo declarado) | pydantic, pydantic-core, torch, typing-inspection | PSF-2.0 | P |
| urllib3 2.8.0 | T; diagnóstico (grafo declarado) | requests | MIT | P |
| wasabi 1.1.3 | T; diagnóstico (grafo declarado) | spacy, thinc, weasel | MIT | P |
| weasel 1.0.0 | T; diagnóstico (grafo declarado) | spacy | MIT | P |
| wrapt 2.3.0 | T; diagnóstico (grafo declarado) | smart-open | BSD-2-Clause | P |

## 4. PaddleOCR: opcional pendiente (P)

Solo se inspeccionan metadatos/rutas; no hay adaptador de inferencia de Next ni
prueba de carga disponible que lo acredite listo. No está en requirements.lock.
No se incluyen sus transitivas como necesidades de Next.

| Dependencia | Función / relación / uso | Procedencia y reproducción | Licencia y fuente | Distribución / avisos |
| --- | --- | --- | --- | --- |
| PaddleOCR 3.7.0 | Motor OCR; candidato directo, P | `${REFERENCE_ROOT}/.venv-paddleocr`, Python 3.12; instalación histórica sin lock de Next, reproducción pendiente | Apache-2.0, METADATA y LICENSE locales (`python_groups.paddle`) | Externo, no distribuido; A |
| PaddlePaddle 3.3.1 | Backend transitivo del candidato, P | Mismo entorno; no instalado/importado por Next | Apache-2.0, METADATA y LICENSE local | Externo; A; componentes nativos completos no auditados |

## 5. Sistema, desarrollo y componentes nativos

Procedencia S: RPM instalados de Fedora 44 x86_64/noarch. Las versiones NEVRA y
licencias declaradas completas están en `system_rpm` del registro; la fuente de
cada declaración es `rpm -q --qf '%{NAME} %{VERSION}-%{RELEASE} %{LICENSE}'` y los
textos de `/usr/share/licenses/<paquete>/`. Reconstruirlos exige un repositorio o
archivo RPM que conserve esas versiones y su cierre de dependencias; **no se
promete que el repositorio corriente aún las sirva**. No se modificaron paquetes.

| Software y versión RPM observada | Función / relación / uso | Licencia / fuente | Distribución / avisos |
| --- | --- | --- | --- |
| CPython 3.14.8-1.fc44 | D, ejecución e instalación; stdlib incluye unittest, sqlite3, zipfile, json, logging, etc. | Python-2.0.1; python3-libs tiene avisos adicionales, ver RPM | S, no incluido; P y avisos específicos |
| SQLite 3.51.2-2.fc44 | T por sqlite3, ejecución de base propia | blessing, RPM; [declaración SQLite](https://sqlite.org/copyright.html) | S; conservar declaración al empaquetar |
| Bash 5.3.9-3.fc44 | D, lanzamiento e instalación | GPL-3.0-or-later, RPM | S; licencia/fuente correspondiente si se redistribuye |
| Spectacle 6.7.5-1.fc44 | D, ejecución de captura KDE/X11 | GPL-2.0-only, RPM | S; GPL/avisos/fuente si se incluye, sin validar captura interactiva aquí |
| Tesseract 5.5.3-2.fc44 | D, motor OCR integrado, ejecución | Apache-2.0, RPM y [LICENSE](https://github.com/tesseract-ocr/tesseract/blob/main/LICENSE) | S; A; datos de idioma separados |
| Leptonica 1.87.0-4.fc44 | T de Tesseract, imágenes | Leptonica, declaración RPM | S; conservar licencia propia, no reemplazar por Apache de Tesseract |
| Git 2.56.0-1.fc44 | D, desarrollo/commits; no requerido para reconocer/traducir | Combinación BSD/GPL/LGPL/MIT, expresión exacta RPM | S; obligaciones por componente si se redistribuye |
| desktop-file-utils 0.28-5.fc44 | D, validación de .desktop, desarrollo/prueba | GPL-2.0-or-later, RPM | S; no runtime de Next; GPL si se distribuye |
| python3-pip 26.0.1-3.fc44 | T, bootstrap/desarrollo; pip de usuario 26.2 también observado | MIT más terceros, expresión exacta RPM; pip de .venv 26.0.1 en tabla R | S/externo; no confundir los tres intérpretes; conservar avisos vendorizados |

Transitivas nativas del sistema observadas por RPM, sin vendorización en Next:
glibc 2.43-9.fc44, libstdc++ 16.2.1-2.fc44, libxcb 1.17.0-7.fc44, libX11
1.8.13-3.fc44, libglvnd 1.7.0-9.fc44, mesa-libGL 26.2.4-1.fc44, fontconfig
2.17.0-4.fc44, FreeType 2.14.3-1.fc44, libpng 1.6.58-1.fc44, libjpeg-turbo
3.1.3-1.fc44 y zlib-ng-compat 2.3.3-3.fc44. Función: ABI, C/C++, plataforma
X11/OpenGL, fuentes y codecs de los programas/bindings. Uso S/T de ejecución,
no dependencias Python directas. Sus expresiones de licencia completas (incluidas
excepciones GCC y terceros) figuran **individualmente** en `system_rpm`. Conservar
los avisos por RPM si se empaquetan; no aplicar la licencia de la GUI a esas libs.
Esto no es un cierre de todos los paquetes del escritorio KDE.

Las bibliotecas accesibles desde Pillow pueden proceder de ruedas o del sistema
y sus versiones pueden diferir. Pillow.features observó las siguientes capacidades;
son rutas transitivas para lectura/render según el formato, no imports directos
ni todas necesarias. No se ha certificado origen/licencia de cada binario
embebido: mantener pendientes los avisos exactos de esa compilación.

| Componente en Pillow 12.3.0 | Versión observada | Función / uso | Licencia del binario y avisos |
| --- | --- | --- | --- |
| FreeType | 2.14.3 | fuentes, ejecución/pruebas | No verificada por componente en rueda; no hereda MIT-CMU |
| LittleCMS2 | 2.19 | color, ejecución condicional | No verificada; conservar avisos propios |
| libwebp | 1.6.0 | WebP, ejecución condicional | No verificada; conservar avisos propios |
| libavif | 1.4.2 | AVIF, no usado por el selector actual | No verificada; instalado no implica necesidad |
| Raqm / FriBidi / HarfBuzz | 0.10.5 / 1.0.16 / 14.2.1 | composición de texto/fuentes | No verificadas; licencias independientes |
| libjpeg-turbo | 3.1.4.1 | JPEG, ejecución | No verificada en rueda; distinta versión del RPM |
| zlib-ng | 2.3.3 (API zlib 1.3.1.zlib-ng) | compresión de imágenes | No verificada en rueda; no duplicar alias API como otro motor |
| OpenJPEG | 2.5.4 | JPEG2000, no usado por selector | No verificada; instalado no implica necesidad |
| libtiff | 4.7.1 | TIFF, no usado por selector | No verificada |
| Tcl/Tk accesible desde Pillow | tkinter 9.0 declarado por features | ruta ImageTk/stdlib no usada por Next; no asumir que viene en la rueda | Origen/licencia binaria no verificados; no dependencia GUI Qt |

Las versiones y licencias de todos los componentes internos de Qt/Chromium,
CTranslate2/OpenMP, BLAS/Fortran y Torch/libgomp no están cerradas en un SBOM nativo.
No se adjudica a esos componentes la licencia del paquete envolvente. Los avisos
que sí existen se conservan referenciados y hasheados; completar los faltantes
antes de ofrecer un paquete binario redistribuible es un pendiente documentado.

## 6. Modelos (separados del software)

No se distribuyen pesos en Git ni se descargan automáticamente. La existencia
local no prueba licencia ni disponibilidad; uso y prueba se indican por modelo.
Los SHA-256 completos, incluidos config/tokenizadores, están en `resources` del
registro y, para los modelos ya probados, en los manifiestos anteriores.

| Modelo / versión | Función / relación / uso | Procedencia y reproducción | Licencia propia y fuente | Distribución / avisos |
| --- | --- | --- | --- | --- |
| Argos ja_en, package_version 1.1 | Datos D de traducción ja→en, ejecución y diagnóstico | `~/.local/share/argos-translate/packages/ja_en`; metadata y archivos hasheados. Falta .argosmodel original/URL fijada para reconstruir una instalación limpia idéntica | **No verificada para estos pesos**: README atribuye OPUS, Wiktionary/Wiktextract y Stanza, pero no trae licencia de pesos. No inferir MIT del motor | Externo; conservar README y créditos; aclarar condiciones antes de redistribuir |
| Argos en_es, package_version 1.0 | Datos D de traducción en→es, ejecución y diagnóstico | Directorio en_es y hashes; mismo límite de reproducción | **No verificada para pesos**; README menciona OpenSubtitles, ParaCrawl, UNPC/OPUS y Stanza. Esas menciones no acreditan una licencia única del modelo | Externo; conservar créditos de corpus/modelos, no redistribuir suponiendo MIT |
| Manga OCR base, snapshot aa6573bd10b0d446cbf622e29c3e084914df9741 | Modelo D del backend M integrado; carga/inferencia reales | Snapshot local completo en caché HF. [manifiesto](manga-runtime.json) y hashes. Sin descarga ni reinstalación en esta revisión | **Apache-2.0 declarada en la ficha del modelo de esa revisión**, comprobada independientemente del código: [model card fijada](https://huggingface.co/kha-white/manga-ocr-base/blob/aa6573bd10b0d446cbf622e29c3e084914df9741/README.md) | Externo; A, conservar ficha/avisos, identificar cambios. Corpus de entrenamiento Manga109s mencionado no se descarga ni se incluye como recurso de Next |
| Manga snapshot 82c77fb84369e0fce0d6e8f0ad96fa82646d0346 | P, solo model.safetensors local; no seleccionado ni cargado por Next | Caché HF, incompleto como snapshot autónomo. SHA-256 en registro | Ficha/licencia específica de esta revisión no contrastada; no extrapolar automáticamente de aa6573… | Externo; condiciones específicas pendientes |
| Stanza ja/gsd.pt, en/ewt.pt, en/combined.pt y en/mwt/combined.pt, incluidos en Argos | Datos T de Dg; segmentación del contraste oficial, no ejecución normal | Subdirectorios stanza de ja_en/en_es; resources.json, pesos y hashes inventariados. Versión exacta de pesos no identificada; versión del código Stanza 1.10.1 no la sustituye | **No verificadas por peso/dataset**; enlace al código Stanza en README no acredita la licencia de cada modelo | Externos; conservar recursos/README y verificar licencia de datos antes de redistribuir |

El vocabulario/configuración de BERT que acompaña MangaOCR se conserva con el
snapshot; no se descarga por separado cl-tohoku/bert-base-japanese-char-v2. No se
infiere una licencia de un hipotético checkpoint BERT separado.

Modelos Paddle encontrados en `~/.paddlex/official_models`, todos **P, sin cargar ni
validar por Next**: PP-OCRv5_mobile_det, japan_PP-OCRv3_mobile_rec,
PP-OCRv6_medium_det, PP-OCRv6_medium_rec, PP-LCNet_x1_0_doc_ori, UVDoc y
PP-LCNet_x1_0_textline_ori. Cada README local declara **Apache-2.0** de forma
independiente del motor; hashes de cada README/config/inference.json/yml/pdiparams
en `resources.paddle_pending`. La familia del nombre no acredita revisión exacta
de pesos; esa revisión y el origen de descarga están pendientes. No hay instalación
reproducible fijada por Next. No se distribuyen; conservar fichas, licencia A y
avisos particulares antes de incluirlos. No se hace inferencia sobre otras cachés
ajenas (Whisper, etc.) que Next no usa.

## 7. Datos de idioma y tokenización

| Recurso / versión | Función / relación / uso | Origen y reproducción | Licencia propia / fuente | Distribución y avisos |
| --- | --- | --- | --- | --- |
| Tesseract eng, jpn, jpn_vert, spa: RPM 4.1.0-12.fc44 | D, reconocimiento por idioma en Tesseract, ejecución | `/usr/share/tesseract/tessdata/*.traineddata`; hashes en registro. RPM tesseract-langpack-* identifica tessdata_fast; reinstalar RPM exactos si siguen disponibles | Apache-2.0 declarada por esos RPM y [tessdata_fast/LICENSE](https://github.com/tesseract-ocr/tessdata_fast/blob/main/LICENSE), independiente del motor | S, no incluidos; A |
| UniDic Lite, paquete 1.0.8; datos basados en UniDic 2.1.2 según upstream | T del tokenizador japonés M; configuración del snapshot pide mecab/unidic_lite | dicdir del entorno MangaOCR; todos sus archivos hasheados. Reconstrucción exacta debe coincidir con esos hashes, no solo con el nombre | Código del paquete MIT local. **Datos: BSD-3 según LICENSE.unidic**; dicdir/COPYING ofrece GPL/LGPL/BSD. [Fuente del empaquetador](https://github.com/polm/unidic-lite/blob/master/README.md) diferencia ambas licencias | Externos, no incluidos; mantener copyright UniDic Consortium y condiciones BSD si se elige esa alternativa |
| Vocabularios SentencePiece de ja_en/en_es | T de traducción R; tokenización | Incluidos en paquetes Argos; SHA-256 por archivo | Licencia específica no acreditada por LICENSE del motor; mismo pendiente que los modelos Argos | Externos; no sustituir licencia de vocabulario por Apache de SentencePiece |

Hashes de idioma exactos: `resources.tesseract_languages`; no se encontró un archivo
osd.traineddata que Next deba inventariar como disponible. No se equipara idioma
OCR con idioma destino de traducción.

## 8. Diccionarios

Procedencia común: ZIP ya existentes en `${REFERENCE_ROOT}/dictionaries`, solo
leídos. No se copia ningún ZIP ni base SQLite a Git. Importación del usuario es
explícita; SQLite administrado no elimina derechos sobre el contenido. El formato
Yomitan es una referencia de estructura, no una dependencia de su extensión JS.
Los índices y SHA-256 están en `resources.dictionaries` del registro.

| Diccionario / revisión real | Función / relación / uso | Licencia y fuente propia | Reproducción / distribución / avisos |
| --- | --- | --- | --- |
| JMdict [2025-11-01], JMdict.2025-11-01 | D de consulta opcional, importación real 513 033 filas | Núcleo JMdict japonés/inglés: **CC-BY-SA-4.0**, [EDRDG](https://www.edrdg.org/edrdg/licence.html), citado en index.attribution. **Licencia/procedencia específica de los ejemplos y de toda esta conversión ZIP no cerrada**: no atribuir una única licencia a todos sus contenidos | ZIP local y hash permiten repetir el ensayo; index.downloadUrl es latest, no fija bytes. No incluido. Conservar reconocimiento a James William Breen/EDRDG, licencia/enlaces, avisos y cambios de derivados; compartir adaptaciones cubiertas bajo condiciones compatibles. La documentación EDRDG añade reconocimiento/documentación y actualización de datos. No impone por ello CC a todo el código de Next |
| 新和英, Shinwaei1 | D opcional de consulta/pruebas; 152 202 filas probadas | **No verificada**: index no acredita editor, permiso ni licencia | Origen de descarga no registrado; repetir con ZIP/hash existente. No incluido; no deducir libre redistribución por estar en ZIP Yomitan |
| 日本語文法辞典(全集), DOJG_v1.01;2022-04-30;better formatting | D opcional de consulta; pruebas reales, 535 filas | **No verificada**: index atribuye DOJG/nihongobongo; atribución no equivale a permiso | ZIP/hash reproducen prueba local; no incluido. Conservar atribución y verificar permiso antes de redistribuir |
| アクセント辞典, pitch1 (archivo v2) | D opcional de consulta; importación real de 327 037 registros de acento | **No verificada**, index.author Sayash sin licencia | ZIP/hash y ensayo completo en local-dictionaries-evidence.json; externo/no distribuido, licencia pendiente |
| KANJIDIC [2025-345], kanjidic2.2025-345 | D opcional de consulta; importación real de 10 383 kanji | Núcleo KANJIDIC2: CC-BY-SA-4.0 según EDRDG; códigos SKIP y otras contribuciones tienen condiciones específicas allí descritas. Derechos completos de esta conversión no verificados | ZIP/hash identificado; latest no fija revisión. No incluido; conservar créditos EDRDG/contribuyentes y condiciones particulares, no asumir permiso uniforme |

Reconocimiento conservado: las pruebas de Next usan material de JMdict,
creado/mantenido por James William Breen y Electronic Dictionary Research and
Development Group, con [documentación/licencia EDRDG](https://www.edrdg.org/edrdg/licence.html).
Los fragmentos y ejemplos ya presentes en docs/jmdict-evidence.json y su captura
son **contenido de terceros**, no datos originales de Next. Esta revisión no añade
nuevas definiciones. Una redistribución de datos/importaciones debe conservar sus
licencias y atribuciones; el soporte de importación no acredita esos permisos.

## 9. Fuentes y activos gráficos

| Fuente / versión | Función / relación / uso | Procedencia, reproducción y hash | Licencia propia / avisos | Distribución |
| --- | --- | --- | --- | --- |
| Noto Sans CJK variable, RPM 2.004-11.fc44, NotoSansCJK-VF.ttc | Recurso D de desarrollo: se usó para generar examples/nihon.png. El worker lee ese PNG y no necesita regenerarlo | `/usr/share/fonts/google-noto-sans-cjk-vf-fonts/`; SHA-256 en registro; RPM exacto si se necesita regenerar | OFL-1.1, `/usr/share/licenses/google-noto-sans-cjk-vf-fonts/LICENSE`. Conservar texto, copyright y nombres reservados al distribuir/modificar fuentes | Fuente S no incluida; PNG de prueba sí está en Git, no contiene el archivo de fuente |
| Noto Sans Regular, RPM 20251201-2.fc44, NotoSans-Regular.ttf | Fuente candidata del sistema (`fc-match sans`); no se impone una familia a Qt ni se convierte en requisito duro | `/usr/share/fonts/google-noto/`, hash en registro | OFL-1.1 según RPM google-noto-sans-fonts; conservar OFL/avisos si se copia | S opcional, no incluida; familia exacta usada por cada sesión gráfica no certificada |
| Aileron Regular, subset embebido en Pillow 12.3.0; name table **1.102** | T de pruebas y sonda Tesseract mediante ImageFont.load_default | Bytes embebidos en ImageFont; SHA-256 del subset en registro. Versionado diferente al 0.102 mostrado en la web del autor, no se equiparan | name table dice **No Rights Reserved**, coincidente con [declaración del autor](https://dotcolon.net/fonts/aileron/). **No asignar OFL, CC0 ni SPDX sin acreditación** | Embebida en Pillow/R, no como fuente en Git; examples/hello.png es un raster generado |

Los iconos de la entrada .desktop se resuelven desde el tema del sistema
(`accessories-dictionary`); Next no incluye ese archivo gráfico. Archivo concreto,
versión y licencia del tema seleccionado no verificados; no se presupone Breeze.
Los diagramas/capturas de Qt en docs son imágenes de pruebas, no redistribución de
la implementación de Qt; sus contenidos de diccionario/fuentes se distinguen arriba.

## 10. Auditoría de .wheelhouse: 17 GB históricos frente al estado actual

**Ahora hay 17 archivos, 324 350 767 bytes (309.33 MiB, du redondea a 310M).**
La cifra de 17 GB correspondía a la recopilación inicial de 381 ruedas de caché,
anterior a esta solicitud. DEPENDENCIES.md ya registraba que solo se conservaron
las 17 del lock. En esta revisión no se eliminó ni añadió ningún archivo allí.

Se verificó: nombres/versiones, SHA-256 contra requirements.lock, tags compatibles
con el Python actual, correspondencia con el entorno instalado y ausencia de
archivos extra. Las 17 tienen nlink=2: son enlaces duros, no se debe sumar ese
tamaño como espacio nuevo garantizado frente a la caché pip. El inventario no
modificó la caché ni los enlaces.

**Necesarias para reconstruir el conjunto exacto declarado:** todas las ruedas de
la tabla siguiente. **Sobrantes respecto a ese lock: ninguno.** No hay ruedas
Torch/CUDA, modelos, ZIP ni ruedas de otras versiones/plataformas en esta carpeta.
Eso no significa que todas se importen en cada uso. PySide6_Addons y la rama BPE
son candidatas a estudiar en un futuro rediseño del conjunto mínimo, pero no se
pueden retirar y seguir afirmando que se reconstruye el lock actual. No se
realizó esa reducción ni se cambió el instalador.

| Archivo necesario para el lock actual | Bytes | SHA-256 |
| --- | ---: | --- |
| argostranslate-1.11.0-py3-none-any.whl | 41551 | `a89b42d82f40843900338f9ac60d4c82fda590b6898247f5d0c15d46731ca7df` |
| click-8.4.2-py3-none-any.whl | 119243 | `e6f9f66136c816745b9d65817da91d61d957fb16e02e4dcd0552553c5a197b76` |
| ctranslate2-4.8.1-cp314-cp314-manylinux_2_27_x86_64.whl | 39494736 | `e3e3aef4670a6c8dcea367401675f82b49b02c18f5837221bcd7cca90b1707a8` |
| joblib-1.5.3-py3-none-any.whl | 309071 | `5fc3c5039fc5ca8c0276333a188bbd59d6b7ab37fe6632daa76bc7f9ec18e713` |
| numpy-2.5.2-cp314-cp314-manylinux_2_27_x86_64.whl | 16713701 | `318b9a4c845dbea06708a29c84ee429cc3065048db34cdb799047643492050ee` |
| packaging-26.3-py3-none-any.whl | 129956 | `d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c` |
| pillow-12.3.0-cp314-cp314-manylinux_2_27_x86_64.whl | 6936962 | `251bf95b67017e27b13d82f5b326234ca62d70f9cf4c2b9032de2358a3b12c7b` |
| pyside6-6.11.1-cp310-abi3-manylinux_2_34_x86_64.whl | 572102 | `b1fc521ba2bb5109425ab8add06bddbdd524abcad06cfa012cc39a22a189feb2` |
| pyside6_addons-6.11.1-cp310-abi3-manylinux_2_34_x86_64.whl | 175063224 | `8e6c65fbd73a512d6f72cda8d8277444a85a34dc99dd1dae9c21d35b8671bb1f` |
| pyside6_essentials-6.11.1-cp310-abi3-manylinux_2_34_x86_64.whl | 79908535 | `e3ef7027b41e4e55fadb56e3b3257dc8ee92154b639fe67fc4c8e05e9d976c60` |
| pyyaml-6.0.3-cp314-cp314-manylinux_2_17_x86_64.whl | 794175 | `c458b6d084f9b935061bc36216e8a69a7e293a2f1e68bf956dcd9e6cbcd143f5` |
| regex-2026.7.19-cp314-cp314-manylinux_2_17_x86_64.whl | 801275 | `7322ec6cc9fba9d49ab888bb82d67ac5625627aa168f0165139b17018df3fb8a` |
| sacremoses-0.1.1-py3-none-any.whl | 897476 | `31e04c98b169bfd902144824d191825cd69220cdb4ae4bcf1ec58a7db5587b1a` |
| sentencepiece-0.2.2-cp314-cp314-manylinux_2_27_x86_64.whl | 1398138 | `8d44b20234905ff022b7d535f79d1f823ad7670c9851cc4f03cdc34787cdb3ab` |
| setuptools-84.0.0-py3-none-any.whl | 818216 | `51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670` |
| shiboken6-6.11.1-cp310-abi3-manylinux_2_34_x86_64.whl | 272222 | `9a8bccfafc8805254cabcfa1edfaf55cd52889f4998c91ad0d9a4433fb1bcdbe` |
| tqdm-4.70.0-py3-none-any.whl | 80184 | `7f585706bfddbdebf89daac705b2dfcc16890130727d3197ca62c732b4310953` |

La caché es suficiente para reinstalar las 17 distribuciones base con los hashes
fijados, junto con el bootstrap/sistema correspondiente; **no reconstruye** el
entorno MangaOCR, el diagnóstico completo, paquetes RPM ni recursos del usuario.
No se hizo otra instalación ni se cambiaron entornos para esta revisión.

## 11. Cómo repetir y actualizar la inspección

Comandos de solo lectura (rutas de ejemplo referidas a este checkout):

```bash
cd ${PROJECT_ROOT}
rg '(^|[[:space:]])(from|import) ' naatik_next tools tests
cat requirements.lock
.venv/bin/python -m pip list --format=json
.venv/bin/python -m pip check
ls -lh .wheelhouse
du -sh .wheelhouse
sha256sum .wheelhouse/*.whl
rpm -q --qf '%{NAME} %{VERSION}-%{RELEASE} %{LICENSE}\n' \
  python3 spectacle tesseract tesseract-langpack-jpn
```

Consultar metadatos de los intérpretes por separado, sin instalar ni ejecutar
scripts encontrados durante detección. Seguir los padres Requires-Dist aplicando
markers de plataforma/extras; registrar importaciones/ELF observadas sin equiparar
«no observado» a «seguro de borrar». Contrastar cada hash de recurso con el
registro existente. Una nueva versión exige volver a revisar licencias y notices,
no copiar la licencia del motor al modelo/diccionario.

Pendientes concretos: permisos de pesos/vocabularios Argos y Stanza, procedencia
precisa de ejemplos JMdict y otros diccionarios, avisos nativos ausentes en varias
ruedas, versiones/licencias de todos los componentes embebidos y reconstrucción
fijada de los entornos externos. No se afirma compatibilidad legal de un paquete
binario futuro ni se altera la validación pendiente de captura interactiva.

## 9. Actualización: atajo global KDE/X11 (2026-10-19)

`naatik_next.hotkey` añade un uso **directo** de libX11, anteriormente observado
solo como transitiva nativa del escritorio. No se añaden ruedas ni imports Python
externos: `ctypes` es parte del CPython existente; QKeySequenceEdit,
QKeySequence y QSocketNotifier pertenecen a PySide6 ya inventariado.
El lock y los recursos/modelos/diccionarios permanecen iguales.
Evidencia incremental de RPM y SHA-256 de los archivos utilizados:
[hotkey-dependency-evidence.json](hotkey-dependency-evidence.json).

| Nombre y versión instalada utilizada | Función / D o T / uso | Procedencia y reproducción | Licencia y fuente | Distribución y avisos |
| --- | --- | --- | --- | --- |
| libX11 1.8.13-3.fc44.x86_64, SONAME libX11.so.6 | D; ejecución opcional del atajo X11 (integrado, validación global pendiente) | RPM Fedora 44; `dnf install libX11-1.8.13-3.fc44.x86_64` si ese NEVRA sigue disponible; fuente `libX11-1.8.13-3.fc44.src.rpm` | `MIT AND X11`, acreditada por `rpm -qi/-qf`; [COPYING upstream de la versión](https://gitlab.freedesktop.org/xorg/lib/libx11/-/blob/libX11-1.8.13/COPYING), enlace no accesible en esta auditoría | S, no se distribuye. Conservar copyright, permisos, condiciones y descargos MIT/X11 al redistribuir; texto completo y avisos específicos **no verificados**: no hubo COPYING instalado accesible. |
| xdpyinfo 1.3.4-4.fc44.x86_64 | D; diagnóstico/prueba del display, no runtime de Next | RPM del sistema; `dnf install xdpyinfo-1.3.4-4.fc44.x86_64`, sujeto a disponibilidad del NEVRA | `MIT`, declaración RPM en evidencia; [proyecto oficial](https://gitlab.freedesktop.org/xorg/app/xdpyinfo) | S, no distribuido. Conservar avisos MIT si se incluye; no se verificó el COPYING completo. |
| Xorg 21.1.24-1.fc44.x86_64 | D; intento de diagnóstico en servidor aislado; no runtime ni requisito de instalación | `xorg-x11-server-Xorg` del sistema, fuente `xorg-x11-server-21.1.24-1.fc44.src.rpm`; mismo NEVRA para reproducir, sin instalarlo en esta tarea | Expresión RPM completa en evidencia, incluye MIT/X11/BSD/HPND/ISC/ICU y otras; [fuente oficial](https://gitlab.freedesktop.org/xorg/xserver) | S, no distribuido. Conservar todos los avisos por componente al empaquetar; revisión de textos completos pendiente. El intento no pudo iniciar el servidor. |
| xorg-x11-drv-dummy 0.4.1-8.fc44.x86_64 | T del intento de diagnóstico Xorg; no runtime de Next | RPM instalado; mismo NEVRA y `xorg-x11-drv-dummy-0.4.1-8.fc44.src.rpm`, sin instalaciones nuevas | `MIT AND X11`, declaración RPM en evidencia; [fuente oficial](https://gitlab.freedesktop.org/xorg/driver/xf86-video-dummy) | S, no distribuido. Conservar avisos MIT/X11 si se incluye; textos completos no verificados. |

Hash observado de `/usr/lib64/libX11.so.6.4.0`:
`95b9ecfbde1b73c7f7380ae643e8ade9555234607a47d7e131ae6365a9899244`.
No se instalaron dependencias ni se añadieron binarios, modelos, fuentes o datos.
El registro aceptado por X11 no equivale a verificación global del recorrido:
[alcance y APIs oficiales](GLOBAL-HOTKEY.md).

## 10. Actualización: IPC local e integración Stream Deck (2026-10-19)

No se añaden paquetes Python, ruedas, modelos, diccionarios ni fuentes. El import
nuevo `PySide6.QtNetwork` usa componentes ya instalados/fijados por el mismo
`requirements.lock`. Se contrastó el módulo, biblioteca Qt, METADATA, versiones y
hashes. argparse, shlex, uuid, stat, hashlib y json son biblioteca estándar del
CPython ya inventariado. Las pruebas usan además socket/subprocess/unittest,
no nuevas dependencias. Evidencia: [stream-deck-dependency-evidence.json](stream-deck-dependency-evidence.json).

| Componente / versión utilizada u observada | D/T y uso | Procedencia / reproducción | Licencia / fuente | Distribución y condiciones |
| --- | --- | --- | --- | --- |
| PySide6.QtNetwork 6.11.1, por PySide6_Essentials 6.11.1 | Módulo D de ejecución para QLocalServer/QLocalSocket; paquete Essentials T del PySide6 ya declarado | Mismo lock y `tools/install.sh`; hash de módulo/METADATA en evidencia | LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only, METADATA local | R, no se distribuye en Git. Condiciones Q del inventario, conservar avisos/textos y obligaciones de fuente/reemplazo aplicables. |
| libQt6Network.so.6, Qt 6.11.1 de la rueda | T nativa de QtNetwork, ejecución IPC Unix; no servidor HTTP | Suministrada por la rueda PySide6_Essentials existente, no por Qt 6.11.2 del sistema; hash en evidencia | Alternativas LGPLv3/GPLv2/comercial documentadas para [Qt Network 6.11](https://doc.qt.io/qt-6.11/qtnetwork-index.html). No se acredita licencia comercial; revisión exhaustiva de avisos internos del binario 6.11.1 no realizada | R, no en Git. Conservar licencia/avisos Qt y de componentes embebidos aplicables si se distribuye la rueda; la página 6.11 puede referirse al parche 6.11.2 y no prueba inventario interno exacto de este binario. |
| StreamController 1.5.0-beta.16, Flatpak commit `061386f4596d1e7711ae85aca7469b41e7921c4d381ba1b85ecc7c6358f4cb34` | Externo opcional del recorrido de usuario; no dependencia de ejecución de Next ni import | `flatpak info` instalado, origen flathub, instalación system; para reproducir esa versión se requiere el commit indicado disponible en el remoto, sin ejecutar instalación/actualización aquí | GPL-3.0-or-later, metadatos Flatpak; [proyecto oficial](https://github.com/StreamController/StreamController) | No distribuido ni modificado. Conservar GPL/avisos y fuente correspondiente si se redistribuye. No se inventarían todos sus paquetes como dependencias de Next. |
| OSPlugin / RunCommand, manifest 1.0.0 y VERSION `b7c719b2ec7e9424cf182d7682c3189772f4dbd2` | Externo opcional; código solo leído para diagnóstico/configuración manual | Instalación existente bajo `~/.var/app/com.core447.StreamController/data/plugins/com_core447_OSPlugin`; hashes de manifest/VERSION/acción/licencias en evidencia. Historia de descarga y correspondencia exacta de VERSION con upstream no verificadas | `GPL-3.0` en attribution.json y LICENSE GPLv3 local; variante exacta only/or-later no acreditada. [Repositorio oficial](https://github.com/StreamController/OSPlugin) | No distribuido, ejecutado ni modificado. Si se redistribuye, conservar GPLv3/atribuciones y fuente correspondiente. No se instaló como dependencia de Next; prueba con hardware pendiente. |

Los modelos y recursos de OCR/traducción mantienen su inventario y licencias
propias. El script generado es código de Next: no incluye código del plugin ni
modelos/diccionarios. El uso de sockets Qt locales no añade una dependencia de
HTTP ni servicios de escritorio adicionales.


## Actualización: cinco ZIP locales y bancos adicionales (2026-10-19)

No se añaden dependencias de software: sqlite3, zipfile, json, hashlib, tempfile
son biblioteca estándar; el diálogo y worker reutilizan PySide6 y procesos
existentes. No se incorporan módulos de Yomitan al runtime ni se instalan paquetes
de validación. Se aplican validadores locales del subconjunto documentado de
sus esquemas oficiales. Modelos OCR/Argos y sus licencias permanecen separados.

La sección 8 se actualizó para reflejar el soporte funcional de KANJIDIC y pitch.
Inventario nuevo por archivo, título/revisión literal de index.json, bancos,
procedencia y SHA-256 completos: [local-dictionaries-evidence.json](local-dictionaries-evidence.json).
Tabla y límites: [LOCAL-DICTIONARIES.md](LOCAL-DICTIONARIES.md). Cada ZIP se importó
en SQLite aislada y se comparó cada fila con el original: 1 003 190 filas en total.
No se importó en el perfil normal ni se distribuyen ZIP/bases con Next.

Procedencia: descargas anteriores del usuario, historia/URL efectiva de descarga
no acreditada. Los index de JMdict y KANJIDIC declaran yomitan-import y enlaces
latest de yomidevs/jmdict-yomitan; esos enlaces no fijan los bytes de estas revisiones.
Para reproducir se usan los ZIP observados y se verifican sus hashes. Nueva
verificación de [licencia EDRDG](https://www.edrdg.org/edrdg/licence.html): núcleo
JMdict japonés/inglés y KANJIDIC2 bajo CC-BY-SA-4.0; conservar reconocimientos,
licencia, documentación y condiciones de contribuyentes/derivados. No se acredita
una licencia uniforme para ejemplos/conversión ni códigos especiales.

新和英 no declara autor/licencia; DOJG declara nihongobongo/DOJG; アクセント辞典
declara Sayash. Ninguno trae un archivo de licencia en estos ZIP: sus permisos
siguen **no verificados**. La compatibilidad técnica/importación local no acredita
redistribución. Se conservan index, tags, filas y atribuciones en SQLite. No hay
imágenes ni audio locales en ninguno de los cinco archivos; no se inventarían
medios ausentes. Frecuencia/IPA ajenos al alcance no se transforman en dependencias
necesarias: se declaran con recuento como contenido no importado al revisar un ZIP mixto.

## Instalación independiente — actualización 2026-10-19

Las descripciones anteriores del runtime externo son evidencia histórica del
entorno de desarrollo, no requisitos nuevos. Los perfiles nuevos ya no descubren
JapaneseMining ni su entorno; usan `.venv-mangaocr` propio y modelos bajo XDG.
Rutas externas explícitamente guardadas siguen respetándose para no romper perfiles.
No se distribuyen modelos/diccionarios con el código.

La base mantiene `requirements.lock` y sus versiones/hashes comprobados. Se añade
`requirements-manga-cpu.lock`: cierre curado de 43 paquetes, no volcado de un
entorno. Python 3.14/Linux x86_64; torch **2.13.0+cpu**, sin CUDA/NVIDIA/ROCm,
transformers 5.14.1 y manga-ocr 0.1.16. No incorpora torchvision/torchaudio ni Stanza.
Este runtime CPU está **acreditado por instalación pública e inferencia real**
en la ejecución externa `public-install-U6n9VjIW` (PASS/0), con entorno propio.
No modifica el perfil normal ni acredita GPU, máquina limpia o interacción gráfica.

Fuentes oficiales contrastadas:
[instalación CPU PyTorch](https://pytorch.org/get-started/locally/),
[índice CPU](https://download.pytorch.org/whl/cpu/torch/),
[MangaOCR 0.1.16](https://pypi.org/project/manga-ocr/0.1.16/),
[ficha del modelo fijada](https://huggingface.co/kha-white/manga-ocr-base/blob/aa6573bd10b0d446cbf622e29c3e084914df9741/README.md).
El hash de torch cp314 procede del enlace del índice oficial conservado en caché;
no es un hash de la rueda cp313 ni de la variante CUDA. Rueda esperada: 191822516
bytes, SHA-256 `d20fa53ee744502fa4c69818a720b05ca0d37abd055d4f6e66cae155114bc691`.

Evidencia por paquete, versiones, origen, hashes, licencia declarada y tamaño:
[manga-cpu-lock-evidence.json](manga-cpu-lock-evidence.json).
Las licencias proceden de METADATA de ruedas; donde falten o sean ambiguas no se
ha acreditado la redistribución. Se conservan LICENSE/NOTICE dentro de las ruedas
instaladas; al redistribuir binarios deben acompañarse sus avisos/licencias y
cumplirse sus condiciones. Next no incorpora esas ruedas a Git ni publica bundle.

### Cierre del runtime MangaOCR CPU (opcional, PASS/0 externo)

Todos se instalan en el entorno propio, desde PyPI salvo torch (índice CPU oficial),
con versión/hash del lock. No se incluyen en Git. Función y licencia declarada:

| Nombre / versión | Relación y función | Uso | Licencia y fuente |
|---|---|---|---|
| annotated-doc 0.0.5 | Transitiva: anotaciones CLI | Ejecución opcional; cierre probado externamente | MIT; [METADATA/origen](https://pypi.org/project/annotated-doc/0.0.5/) |
| anyio 4.14.2 | Transitiva: I/O asíncrono del cliente HTTP | Ejecución opcional; cierre probado externamente | MIT; [METADATA/origen](https://pypi.org/project/anyio/4.14.2/) |
| certifi 2026.7.22 | Transitiva: certificados CA del cliente HTTP | Ejecución opcional; cierre probado externamente | MPL-2.0; [METADATA/origen](https://pypi.org/project/certifi/2026.7.22/) |
| click 8.4.2 | Transitiva: parser de CLI | Ejecución opcional; cierre probado externamente | BSD-3-Clause; [METADATA/origen](https://pypi.org/project/click/8.4.2/) |
| filelock 3.32.3 | Transitiva: bloqueos de archivos de caché | Ejecución opcional; cierre probado externamente | MIT; [METADATA/origen](https://pypi.org/project/filelock/3.32.3/) |
| fire 0.7.1 | Transitiva: CLI declarada por manga-ocr | Ejecución opcional; cierre probado externamente | Apache-2.0; [METADATA/origen](https://pypi.org/project/fire/0.7.1/) |
| fsspec 2026.7.0 | Transitiva: abstracción de archivos | Ejecución opcional; cierre probado externamente | BSD-3-Clause; [METADATA/origen](https://pypi.org/project/fsspec/2026.7.0/) |
| fugashi 1.5.2 | Transitiva: tokenizador MeCab del tokenizer japonés | Ejecución opcional; cierre probado externamente | MIT AND BSD-3-Clause; [METADATA/origen](https://pypi.org/project/fugashi/1.5.2/) |
| h11 0.16.0 | Transitiva: protocolo HTTP/1.1 | Ejecución opcional; cierre probado externamente | MIT; [METADATA/origen](https://pypi.org/project/h11/0.16.0/) |
| hf-xet 1.6.0 | Transitiva: transporte Hub/Xet upstream; offline en inferencia | Ejecución opcional; cierre probado externamente | Apache-2.0; [METADATA/origen](https://pypi.org/project/hf-xet/1.6.0/) |
| httpcore 1.0.9 | Transitiva: transporte HTTP | Ejecución opcional; cierre probado externamente | BSD-3-Clause; [METADATA/origen](https://pypi.org/project/httpcore/1.0.9/) |
| httpx 0.28.1 | Transitiva: cliente HTTP de Hub (no usado por descarga propia) | Ejecución opcional; cierre probado externamente | BSD-3-Clause; [METADATA/origen](https://pypi.org/project/httpx/0.28.1/) |
| huggingface-hub 1.26.0 | Transitiva: resolución local de archivos de transformers; offline en inferencia | Ejecución opcional; cierre probado externamente | Apache-2.0; [METADATA/origen](https://pypi.org/project/huggingface-hub/1.26.0/) |
| idna 3.18 | Transitiva: dominios internacionales | Ejecución opcional; cierre probado externamente | BSD-3-Clause; [METADATA/origen](https://pypi.org/project/idna/3.18/) |
| jaconv 0.5.0 | Transitiva: normalización kana/ASCII del OCR | Ejecución opcional; cierre probado externamente | MIT License; [METADATA/origen](https://pypi.org/project/jaconv/0.5.0/) |
| jinja2 3.1.6 | Transitiva: plantillas requeridas por torch | Ejecución opcional; cierre probado externamente | not specified; review notices; [METADATA/origen](https://pypi.org/project/jinja2/3.1.6/) |
| loguru 0.7.3 | Transitiva: logging del motor | Ejecución opcional; cierre probado externamente | not specified; review notices; [METADATA/origen](https://pypi.org/project/loguru/0.7.3/) |
| manga-ocr 0.1.16 | Directa: motor OCR | Ejecución opcional; cierre probado externamente | Apache License; [METADATA/origen](https://pypi.org/project/manga-ocr/0.1.16/) |
| markdown-it-py 4.2.0 | Transitiva: Markdown CLI | Ejecución opcional; cierre probado externamente | not specified; review notices; [METADATA/origen](https://pypi.org/project/markdown-it-py/4.2.0/) |
| markupsafe 3.0.3 | Transitiva: escape de plantillas | Ejecución opcional; cierre probado externamente | BSD-3-Clause; [METADATA/origen](https://pypi.org/project/markupsafe/3.0.3/) |
| mdurl 0.1.2 | Transitiva: URLs de Markdown | Ejecución opcional; cierre probado externamente | not specified; review notices; [METADATA/origen](https://pypi.org/project/mdurl/0.1.2/) |
| mpmath 1.3.0 | Transitiva: aritmética para sympy | Ejecución opcional; cierre probado externamente | BSD; [METADATA/origen](https://pypi.org/project/mpmath/1.3.0/) |
| networkx 3.6.1 | Transitiva: grafos requeridos por torch | Ejecución opcional; cierre probado externamente | BSD-3-Clause; [METADATA/origen](https://pypi.org/project/networkx/3.6.1/) |
| numpy 2.5.2 | Transitiva: arrays de imágenes | Ejecución opcional; cierre probado externamente | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0; [METADATA/origen](https://pypi.org/project/numpy/2.5.2/) |
| packaging 26.3 | Transitiva: versiones y requisitos | Ejecución opcional; cierre probado externamente | Apache-2.0 OR BSD-2-Clause; [METADATA/origen](https://pypi.org/project/packaging/26.3/) |
| pillow 12.3.0 | Transitiva: lectura y transformación de imágenes | Ejecución opcional; cierre probado externamente | MIT-CMU; [METADATA/origen](https://pypi.org/project/pillow/12.3.0/) |
| pygments 2.21.0 | Transitiva: resaltado CLI | Ejecución opcional; cierre probado externamente | BSD-2-Clause; [METADATA/origen](https://pypi.org/project/pygments/2.21.0/) |
| pyperclip 1.11.0 | Transitiva: portapapeles de CLI upstream; Next no usa esa CLI | Ejecución opcional; cierre probado externamente | BSD; [METADATA/origen](https://pypi.org/project/pyperclip/1.11.0/) |
| pyyaml 6.0.3 | Transitiva: metadatos YAML | Ejecución opcional; cierre probado externamente | MIT; [METADATA/origen](https://pypi.org/project/pyyaml/6.0.3/) |
| regex 2026.7.19 | Transitiva: expresiones regulares | Ejecución opcional; cierre probado externamente | Apache-2.0 AND CNRI-Python; [METADATA/origen](https://pypi.org/project/regex/2026.7.19/) |
| rich 15.0.0 | Transitiva: salida CLI | Ejecución opcional; cierre probado externamente | MIT; [METADATA/origen](https://pypi.org/project/rich/15.0.0/) |
| safetensors 0.8.0 | Transitiva: lectura de pesos en formato seguro | Ejecución opcional; cierre probado externamente | not specified; review notices; [METADATA/origen](https://pypi.org/project/safetensors/0.8.0/) |
| setuptools 84.0.0 | Transitiva: runtime declarado por torch | Ejecución opcional; cierre probado externamente | MIT; [METADATA/origen](https://pypi.org/project/setuptools/84.0.0/) |
| shellingham 1.5.4 | Transitiva: detección shell CLI | Ejecución opcional; cierre probado externamente | ISC License; [METADATA/origen](https://pypi.org/project/shellingham/1.5.4/) |
| sympy 1.14.0 | Transitiva: operaciones simbólicas requeridas por torch | Ejecución opcional; cierre probado externamente | BSD; [METADATA/origen](https://pypi.org/project/sympy/1.14.0/) |
| termcolor 3.3.0 | Transitiva: color CLI | Ejecución opcional; cierre probado externamente | MIT; [METADATA/origen](https://pypi.org/project/termcolor/3.3.0/) |
| tokenizers 0.22.2 | Transitiva: backend de tokenización | Ejecución opcional; cierre probado externamente | not specified; review notices; [METADATA/origen](https://pypi.org/project/tokenizers/0.22.2/) |
| torch 2.13.0+cpu | Transitiva: inferencia tensorial CPU | Ejecución opcional; cierre probado externamente | Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT; [METADATA/origen](https://download.pytorch.org/whl/cpu/torch/) |
| tqdm 4.70.0 | Transitiva: progreso upstream | Ejecución opcional; cierre probado externamente | MPL-2.0 AND MIT; [METADATA/origen](https://pypi.org/project/tqdm/4.70.0/) |
| transformers 5.14.1 | Transitiva: procesador de imagen, tokenizer y generación | Ejecución opcional; cierre probado externamente | Apache 2.0 License; [METADATA/origen](https://pypi.org/project/transformers/5.14.1/) |
| typer 0.27.1 | Transitiva: CLI del Hub | Ejecución opcional; cierre probado externamente | MIT; [METADATA/origen](https://pypi.org/project/typer/0.27.1/) |
| typing-extensions 4.16.0 | Transitiva: tipos de compatibilidad | Ejecución opcional; cierre probado externamente | PSF-2.0; [METADATA/origen](https://pypi.org/project/typing-extensions/4.16.0/) |
| unidic-lite 1.0.8 | Transitiva: datos UniDic para MeCab (datos separados de licencia del motor) | Ejecución opcional; cierre probado externamente | not specified; review notices; [METADATA/origen](https://pypi.org/project/unidic-lite/1.0.8/) |

### Modelo y datos (separados del software)

`kha-white/manga-ocr-base`, revisión `aa6573bd10b0d446cbf622e29c3e084914df9741`:
OCR japonés. Ficha del modelo declara Apache-2.0; se comprobó esa ficha, sin inferir
licencia del motor. Descarga directa opcional y confirmada desde Hugging Face;
sin redistribución del modelo en Git. Tamaños/hashes por archivo en
[`model-catalog.json`](../naatik_next/model-catalog.json). Hashes calculados del
snapshot local auditado y usados como allowlist estricta para nuevas descargas.
La ficha menciona entrenamiento con Manga109-s; no se redistribuye el dataset.
Si se redistribuye el modelo, conservar licencia, atribuciones y avisos aplicables;
esta entrega no publica un paquete de pesos.

Tesseract/traineddata y fuentes permanecen dependencias del sistema: no se copian
de este host. La prueba usa la fuente por defecto de Pillow; Qt usa las fuentes
instaladas por el usuario/sistema. No se añade una fuente personal. Diccionarios
siguen siendo archivos importados por el usuario; no se descargan ni se empaquetan.
Argos sin modelos informa rutas ausentes, no usa modelos de JapaneseMining.

### Datos UniDic y construcción (no confundir con licencia de MangaOCR)

UniDic Lite **1.0.8** empaqueta **UniDic 2.1.2**, datos de idioma requeridos por el
tokenizer japonés, no diccionario importado de usuario. Procedencia:
[PyPI oficial](https://pypi.org/pypi/unidic-lite/1.0.8/json). El sdist publicado
mide 47356746 bytes y tiene SHA-256
`db9d4572d9fdd4d00a97949d4b0741ec480ee05a7e7e2e32f547500dae27b245`.
El lock actual admite solo ese sdist público; el hash de la rueda local queda
únicamente como evidencia histórica y ya no es una alternativa de instalación. Wrapper MIT/WTFPL por elección, datos UniDic
BSD según LICENSE.unidic; se inspeccionaron COPYING, LICENSE y LICENSE.unidic de
la rueda. Conservar copyright, condiciones y descargo de los datos al redistribuir;
no atribuirle licencia Apache del motor. No se añade el recurso a Git.

Construcción: `requirements-manga-build.lock` fija **setuptools 84.0.0**,
**packaging 26.3** (ya inventariados) y **wheel 0.47.0**, este último uso directo
solo de construcción, licencia MIT según dist-info/licenses/LICENSE.txt. Se
instalan en el entorno propio antes de construir el sdist sin build-isolation
que descargue herramientas sin fijar. Hash/origen en la evidencia; instalación
completa y construcción desde sdist acreditadas por el log externo cpu-install.log;
no se amplía por ello la licencia o redistribución de los datos.


## Validación desde fuentes públicas — continuación de 586a7fb

No se cambian versiones del runtime ni se añaden dependencias de ejecución.
`validate-public-install.sh` usa Bash y Python stdlib del sistema, venv/ensurepip y
el `packaging` vendorizado por pip **solo para diagnóstico de tags**, sin promover
esas herramientas a dependencias del producto. Instala desde URLs públicas cuyos
hashes contrasta con PyPI/índice CPU, con cachés nuevas y sin `.wheelhouse`.
La excepción UniDic construida localmente se retiró del lock: solo queda el SHA-256
del sdist oficial. LICENSE/avisos y versiones previamente inventariadas se conservan.

El intento anterior del agente devolvió **BLOCKED por DNS** en la primera consulta
PyPI; ese intento no acreditó instalación pública/CPU/modelo. La posterior ejecución
externa PASS/0 sí los acredita con los límites registrados al final.
Fuentes y resultados: [PUBLIC-INSTALL-VALIDATION.md](PUBLIC-INSTALL-VALIDATION.md),
[public-install-evidence.json](public-install-evidence.json). No se distribuyen
ruedas, modelos, diccionarios ni paquetes instalados con estos cambios.


## Registro externo PASS/0 — public-install-U6n9VjIW

Se leyeron logs del usuario sin ejecutar ni descargar nada. **63 registros** de
artefactos públicos verificados; SHA-256 de los tres locks originales coinciden
con los actuales. La base y runtime CPU se instalaron públicamente, UniDic desde
sdist, y `pip check` del runtime pasó. Versiones: torch 2.13.0+cpu (CUDA null),
transformers 5.14.1 y manga-ocr 0.1.16, con OCR real 日本 y cancelación/recarga.
Las filas del inventario acreditan el cierre completo, no todas las APIs de cada
paquete. El uso sigue siendo opcional; no se convierte todo el host en dependencia.

Los seis archivos del modelo fijado fueron descargados íntegramente y sus
SHA-256 coincidieron con el catálogo. Reutilización sin red acreditada; reanudación
real de una descarga interrumpida sigue pendiente. No se distribuyen pesos con
Next ni se modifican las conclusiones de licencia por haber pasado la inferencia.

El log de Transformers usa `ViTImageProcessorPil` por ausencia de torchvision;
la prueba real pasó así. No se añade torchvision, GPU, PaddleOCR ni Stanza como
requisito. No hubo diccionarios ni modelos Argos preparados en ese perfil.

[Detalle documental](EXTERNAL-PUBLIC-INSTALL-PASS.md) y
[resumen, hashes de logs y artefactos públicos](external-public-install-pass.json).
Los anteriores BLOCKED por DNS permanecen históricos. Pendientes: máquina/VM
limpia e interacción gráfica de esta instalación, otros Python/arquitecturas/GPU.


### Captura al soltar (Spectacle existente)

No se añaden ni actualizan paquetes, modelos o recursos. El adaptador de Spectacle
6.7.5 ahora exige y usa `--release-capture` por invocación, junto con salida PNG
explícita y modo background. Ver ayuda local, fuentes oficiales KDE 6.7.5,
alcance y evidencia inyectada en [CAPTURE-LOOKUP.md](CAPTURE-LOOKUP.md).
No cambia el inventario ni su distribución/licencia; captura interactiva y
geometría con varios monitores/escalado siguen sin acreditarse por offscreen.


### Medición de latencia: ampliación del uso de componentes existentes

No se añaden/actualizan paquetes, modelos ni datos. Captura y OCR usan workers
residentes; la comprobación de Spectacle existente se conserva por proceso con
invalidación del ejecutable. La preparación seleccionada y las pruebas explícitas
reutilizan los mismos adaptadores CPU, modelo y recursos configurados.

`naatik_next.selection_timing` amplía el uso directo opcional de **libX11.so.6**
(1.8.13-3.fc44.x86_64 observado de nuevo con `rpm -q libX11`) al diagnóstico
opt-in del intervalo de arrastre mediante XOpenDisplay/XQueryPointer/XCloseDisplay.
Es la misma biblioteca, origen, licencia MIT AND X11, hash y condiciones de
redistribución ya inventariados arriba; no se redistribuye ni se añade una nueva
biblioteca. `ctypes`, `subprocess`, `select`, `signal`, reloj, JSON y caché son biblioteca estándar.
Solo consulta Button1 mientras se ejecuta el selector y con diagnóstico activado;
no registra coordenadas/teclas ni genera eventos. Fuente de API:
[Xlib oficial](https://www.x.org/releases/current/doc/libX11/libX11/libX11.html).
Spectacle observado: 6.7.5-1.fc44.x86_64, sin actualización ni cambios globales.
Uso, evidencia de CPU, muestras y límites:
[CAPTURE-LATENCY.md](CAPTURE-LATENCY.md) y [JSON numérico](evidence/capture-latency.json).
No constituye otra calificación de instalación independiente del intérprete/modelo
explícitamente configurados por el usuario; los defaults propios de Next siguen
intactos, sin descubrir recursos de otros proyectos.

### Corrección de cierre (2026-10-20)

Sin nuevas dependencias ni cambios de versiones/recursos. El observador X11
optativo se ejecuta ahora en un subproceso acotado, con su propia conexión Xlib,
en vez de un hilo daemon durante la destrucción de Python. Conserva las APIs,
licencia, origen, hash y condiciones de libX11 inventariados arriba. La GUI usa
`signal.set_wakeup_fd` de Python y QSocketNotifier de PySide6 ya instalado;
QProcess usa `UnixProcessFlag.CreateNewSession` de Qt 6.11.1 en Linux para
supervisar el grupo de cada worker y sus herramientas. No instala un servicio.
Evidencia sin contenido: [shutdown.json](evidence/shutdown.json).
APIs: [Python signal](https://docs.python.org/3/library/signal.html#signal.set_wakeup_fd),
[Qt QProcess](https://doc.qt.io/qtforpython-6/PySide6/QtCore/QProcess.html).

## 14. Translator y OCR Phrase: runtime lingüístico propio (2026-10-20)

El código de JapaneseMining se consultó como referencia en solo lectura; no se
copió ni importa como biblioteca. Los popups usan PySide6/Qt 6.11.1, el supervisor
QProcess y el worker/renderizador de diccionarios existentes. Traducción mantiene
el adaptador Argos/CTranslate2 CPU del lock base, sin importar el módulo de
segmentación `argostranslate.translate`. No se añaden Sudachi, pykakasi, tablas
JLPT/gramática, AnkiConnect, servicios HTTP ni dependencias móviles.

Cambia el **uso directo** de componentes ya inventariados, ahora en un entorno
opcional separado `.venv-phrase`; no se extraen del runtime MangaOCR ni de otro
proyecto. `requirements-phrase.lock` fija sus artefactos públicos. La construcción
de UniDic comparte `requirements-manga-build.lock`: setuptools 84.0.0, packaging
26.3 y wheel 0.47.0, solo herramientas, sin instalar Torch/MangaOCR.

| Componente | Uso/relación y versión | Procedencia y reproducción | Licencia y avisos | Distribución |
|---|---|---|---|---|
| Fugashi 1.5.2 | D opcional: segmentación, POS, lema ortográfico y lectura; runtime de ambos popups | [PyPI](https://pypi.org/project/fugashi/1.5.2/), rueda cp314 Linux x86_64; SHA-256 `71c0027aa11747adcb3753d31663290c53fea8007371f0b080c53c192918ceb9`; `tools/install.sh --phrase` | MIT para wrapper, comprobada en dist-info/licenses/LICENSE. Mantener copyright Paul O'Leary McCann, permiso y descargo. [Upstream](https://github.com/polm/fugashi) | No se incluye binario en Git; pip descarga o usa artefacto offline verificado |
| MeCab incluido en rueda Fugashi | Transitiva nativa de Fugashi; no requiere MeCab de otro proyecto ni configuración de sistema | Mismo artefacto/hash; binarios propios registrados en la evidencia | BSD-3-Clause en LICENSE.mecab local, copyright Taku Kudo/NTT; conservar avisos, condiciones y descargo, sin aval de titulares | Incluido por upstream en la rueda, no por el repositorio de Next |
| UniDic Lite 1.0.8, wrapper | D opcional: localiza el léxico propio para Fugashi | [PyPI](https://pypi.org/project/unidic-lite/1.0.8/); sdist 47 356 746 bytes, SHA-256 `db9d4572d9fdd4d00a97949d4b0741ec480ee05a7e7e2e32f547500dae27b245`; construcción sin build-isolation con herramientas fijadas | MIT comprobada en LICENSE local; mantener copyright Paul McCann y permiso/descargo. No se deduce la licencia de los datos de esta licencia | No se incluye paquete ni rueda construida en Git; hash de construcción local no se acepta como artefacto PyPI |
| Datos UniDic 2.1.2 empaquetados en UniDic Lite | Recurso lingüístico de Fugashi: léxico/matriz de tokenización, no diccionario Yomitan del usuario | Mismo sdist; dicdir propio explícito, sin descarga posterior ni búsqueda automática. Hashes por archivo en evidencia | BSD-3-Clause según LICENSE.unidic y alternativa BSD en dicdir/COPYING/BSD. Copyright UniDic Consortium; conservar condiciones, copyright y descargo; no atribuir licencia MIT del wrapper. [Fuente de licencia](https://github.com/polm/unidic-lite/blob/master/LICENSE.unidic) | Solo instalación explícita, con confirmación desde GUI. No se redistribuyen datos en Git |

Los modelos Argos ahora se descubren exclusivamente en el directorio de Next,
no en la instalación global ni en servicios/entornos anteriores. La importación
local registra SHA-256 y licencia **no verificada**; la licencia de Argos o
CTranslate2 no acredita modelos, vocabularios ni corpus. No se distribuyen modelos
ni diccionarios del usuario. La importación no llama al instalador de Argos que
importaría el backend SBD; valida rutas/tamaños y publica mediante staging propio.
No se descargó un modelo neural: la prueba de traducción real queda pendiente
por indicación del usuario. El analizador lingüístico real sí se probó.

Herramientas externas de validación (T, no requisitos de ejecución de Next):
`desktop-file-utils` 0.28-5.fc44 (validador, GPL-2.0-or-later según RPM),
`python3-gobject-base` 3.56.3-1.fc44 (Gio mediante introspección, LGPL-2.1-or-later
según RPM), GLib/Gio 2.88.4-1.fc44 (LGPL-2.1-or-later según RPM). Se usan solo
para validar/ejecutar un `.desktop` sintético, sin distribuirlos ni añadirlos a
requirements.lock. Confirmación RPM exacta y fuentes en la evidencia; condiciones
completas por componente no se reauditaban aquí. La entrada Exec aplica las dos
capas de escaping de la [especificación freedesktop](https://specifications.freedesktop.org/desktop-entry-spec/latest/exec-variables.html).

Evidencia de hashes, licencias locales, instalación offline, referencia estática,
pruebas offscreen, señales y límites: [popups.json](evidence/popups.json).
No se considera una nueva calificación del escritorio ni de una máquina limpia.


## 15. Presentación de popups (2026-10-20)

La recreación visual usa únicamente los widgets PySide6/Qt ya inventariados y
la biblioteca estándar (AST/JSON/hashlib/tempfile para diagnóstico). No añade
paquetes, fuentes, modelos, puertos ni dependencias de ejecución. Las familias
Noto Sans, Noto Sans JP y Noto Serif CJK JP son preferencias de estilo con fallback
del sistema; no se instalan ni distribuyen fuentes nuevas. Locks sin cambios.

JapaneseMining sigue siendo referencia de diseño de solo lectura. La aplicación
no importa ni lee sus archivos. La herramienta opcional
`tools/popup_visual_review.py` recibe explícitamente una copia de revisión y
extrae solo métodos UI permitidos para un render sintético sin backends; no
incorpora esos archivos fuente ni ejecuta servicios/imports originales. Las capturas de
comparación contienen únicamente datos sintéticos. Hashes y alcance en
[evidencia visual](evidence/popup-visual/visual-review.json) y
[revisión](POPUP-VISUAL-REVIEW.md); no acreditan licencia de redistribución de los
fuentes originales ni incorporan sus recursos al producto.

## 16. Preparación gráfica de traducción (2026-10-20)

`requirements-translation.lock` contiene **12 paquetes**, subconjunto exacto de
versiones y hashes de `requirements.lock`: argostranslate 1.11.0, click 8.4.2,
ctranslate2 4.8.1 CPU, joblib 1.5.3, numpy 2.5.2, packaging 26.3, PyYAML 6.0.3,
regex 2026.7.19, sacremoses 0.1.1, sentencepiece 0.2.2, setuptools 84.0.0 y
tqdm 4.70.0. Sus orígenes, licencias propias, D/T y avisos son los de la sección 1.
No cambian versiones ni hashes ni se añade SBD, Torch, CUDA, Stanza o spaCy.
Se omite Qt/Pillow porque este entorno solo ejecuta workers. La GUI permanece en
la base Qt de Next. La preparación usa pip aislado, PyPI oficial, binarios,
`--no-deps --require-hashes --no-cache-dir`, en un venv sin paquetes del sistema.
El auditor/copiador de instalación pública incorpora el nuevo lock. El entorno
se sitúa en datos XDG propios y no se distribuye en Git.

La nueva dependencia de sistema **solo del arranque sin Qt** es Tkinter/Tk. La
interfaz Qt habitual no lo importa. Metadatos observados mediante RPM en Fedora:

| Componente | D/T y ámbito | Versión observada | Licencia declarada por RPM / origen |
|---|---|---|---|
| python3-tkinter | D, bootstrap gráfico del sistema | 3.14.8-1.fc44 | Python-2.0.1; RPM oficial Fedora, biblioteca Tkinter de CPython |
| tk | T de Tkinter, widgets nativos | 9.0.2-2.fc44 | TCL AND HPND-Pbmplus AND CC-BY-SA-3.0 AND MIT-open-group AND MIT; RPM Fedora |
| tcl | T de Tk, intérprete | 9.0.2-2.fc44 | TCL AND GPL-3.0-or-later WITH Bison-exception-2.2 AND BSD-3-Clause; RPM Fedora |

Esto describe paquetes del sistema, no una licencia única inferida para todos sus
archivos. El usuario los instala con el gestor de Fedora; Next no redistribuye
esos binarios ni los instala con sudo. Python 3.14/pip/venv, certificados y las
bibliotecas Qt/X11 siguen siendo requisitos externos. Las versiones RPM son del
host observado, no una acreditación de una VM vacía ni soporte de otras plataformas.
[CPython Tkinter](https://docs.python.org/3/library/tkinter.html),
[paquete Fedora](https://packages.fedoraproject.org/pkgs/python3.14/python3-tkinter/).

### Catálogo y modelos opcionales

Se consulta explícitamente el [índice oficial Argos](https://raw.githubusercontent.com/argosopentech/argospm-index/main/index.json),
cuya [licencia es MIT o CC0](https://github.com/argosopentech/argospm-index/blob/main/README.md).
Observación por herramienta web, 2026-10-20: ja→en modelo 1.1 / Argos ≥1.1 y
en→es modelo 1.0 / Argos ≥1.0, con URLs HTTPS en argos-net.com; no se observó un
directo ja→es. El catálogo se reconsulta por elección del usuario, no se congela
como promesa de disponibilidad. **No se descargó ningún modelo en esta revisión.**
Compatibilidad de metadatos no equivale a carga/inferencia real acreditada.

Los registros consultados no publican tamaño, SHA-256 ni licencia individual.
La GUI muestra tamaño de HEAD si existe o «no disponible», y declara MIT/CC0
**según la [respuesta del mantenedor sobre los binarios](https://github.com/argosopentech/argos-translate/issues/533)**,
sin atribuirles automáticamente la licencia del motor. Licencia individual/corpus
y contenido exacto del paquete quedan sin inspeccionar mientras no se descargue.
Importaciones locales conservan el aviso de licencia no verificada. No se añaden
modelos, ruedas ni diccionarios al repositorio.

Tras consentimiento, la procedencia local registra URL, hash del catálogo y hash
recibido del paquete; **no es verificación contra un hash oficial inexistente**.
Se verifican HTTPS, estructura/CRC ZIP, límites, rutas/idiomas y luego carga e
inferencia CPU con conexiones Python bloqueadas. No hay APIs remotas de traducción.
La selección de la ruta sigue siendo explícita y persistente.

Evidencia: [validation.json](evidence/translation-setup/validation.json),
[preparación nueva sin cachés](evidence/translation-setup/fresh-profile.json),
[guía](TRANSLATION-SETUP.md). Se conserva como **BLOCKED por DNS/red** la instalación
pública nueva, y **NO VALIDADA** la inferencia neural real/reutilización neural
offline. Las pruebas con paquetes ficticios y UI offscreen no convierten esos
gates en PASS. Hay una sola comprobación gráfica opcional para la sesión del
usuario; no es un paso obligatorio de la preparación habitual.

### Diagnóstico HTTP 403 y apertura explícita del enlace oficial

Sin nuevas dependencias, modelos ni orígenes: se reutiliza QDesktopServices de Qt
para abrir, tras confirmar, los enlaces HTTPS ya revisados del catálogo. No se
añaden espejos ni se modifican licencias/versiones/agentes HTTP. El usuario puede
importar manualmente un archivo obtenido por su navegador; sigue pasando por la
misma validación y no se atribuye licencia por haberlo descargado. Abrir un enlace
no acredita transferencia ni inferencia. El 403 del usuario y el bloqueo DNS local
se mantienen separados en [http403.json](evidence/translation-setup/http403.json).

## 17. Recorrido unificado de Traducción (2026-10-20)

La sección Traducción reutiliza el backend, los 12 paquetes y los locks anteriores;
no añade ni cambia dependencias, versiones, fuentes o licencias. La importación,
el inventario y el diagnóstico quedan en Opciones avanzadas. La apertura de enlaces
descrita en el diagnóstico histórico anterior ya no es un control del recorrido.
Se conserva su evidencia histórica. Guía vigente: [TRANSLATION-SETUP.md](TRANSLATION-SETUP.md).

Para la validación se importaron explícitamente dos archivos locales en un perfil
HOME/XDG temporal, sin copiar recursos de JapaneseMining ni modificar los datos
normales de Next. Paquetes observados: ja→en 1.1 y en→es 1.0. La procedencia de la
descarga original y su licencia individual **no se verificaron en esta ejecución**;
no se hereda una licencia del motor ni se redistribuyen esos archivos. Sus SHA-256,
las versiones del runtime propio utilizado y el resultado están en
[evidence.json](evidence/translation-journey/evidence.json). El repositorio incluye
solo código, informe y capturas de interfaz; no modelos, ruedas ni entornos.

La carga e inferencia CPU local y el regreso al popup pasan con red Python
bloqueada en la comprobación. Esto actualiza únicamente el gate de inferencia con
archivos locales: no acredita descargas nuevas, preparación de un venv nuevo ni
instalación en máquina/VM limpia. Las pantallas son Qt offscreen; la sesión gráfica
real quedó sin validar por falta de conexión al display `:0`. Las pruebas de
catálogo, consentimiento, instalación encadenada y errores de red son simuladas.
[Informe, capturas y reproducción](evidence/translation-journey/README.md).

## 18. Anki: requisitos externos propuestos, sin integración (2026-10-20)

Solo inspección/diseño: [ANKI-DESIGN.md](ANKI-DESIGN.md). No se añade un paquete a
los requirements/locks, no se importa software antiguo, no se instala Anki ni su
complemento, y no hay comunicación con la colección personal. El cliente futuro
propone la biblioteca estándar HTTP/JSON y PySide6/Task existentes.

Anki y AnkiConnect son requisitos externos opcionales futuros, **no dependencias
instaladas o capacidades operativas de Next**. La [licencia oficial de Anki](https://raw.githubusercontent.com/ankitects/anki/main/LICENSE)
indica AGPL-3.0-or-later con excepciones/componentes diferenciados. La
[licencia del archivo oficial de AnkiConnect](https://raw.githubusercontent.com/FooSoft/anki-connect/master/LICENSE)
indica GPL-3.0-or-later para ese código histórico; el mantenedor trasladó el
proyecto a SourceHut. El acceso al origen actual quedó bloqueado, por lo que no
se acredita versión, licencia ni compatibilidad del paquete actual. Se deberán
verificar con el artefacto oficial exacto antes de implementarlo/instalarlo.
No se distribuyen copias de código, complementos, binarios ni datos de terceros.

[Registro de fuentes oficiales y límites](evidence/anki-design/official-sources.json).
No hay hashes de paquetes nuevos porque no se descargó ninguno. Los hashes de
fuentes locales inspeccionados están en [inspection.json](evidence/anki-design/inspection.json),
como evidencia de lectura, no autorización de redistribución. Los recursos
lingüísticos conservan sus licencias propias; este diseño no autoriza descargar,
exportar o redistribuir ejemplos, diccionarios, imágenes ni audio.

## 19. Cliente Anki propio (2026-10-21)

[Implementación y validación](ANKI.md): `http.client`, JSON, hashes, UUID y
persistencia con biblioteca estándar Python; UI y worker usan PySide6/Task ya
inventariados. No hay nuevos requirements/locks, SDK, modelos, paquetes o código
de terceros incorporados. Anki/AnkiConnect son requisitos externos opcionales
para enviar; no se instalaron ni redistribuyeron. No hay hashes de artefactos
nuevos porque no se descargaron paquetes. Se preservan las licencias y límites
de la sección 18 para las referencias históricas.

El 2026-10-21 se volvieron a consultar ficha AnkiWeb, repositorio oficial archivado
y manual oficial de archivos. La ficha exige JavaScript y SourceHut deniega
el acceso de esta herramienta; el shell no resuelve ese host. No se acredita
versión, licencia del artefacto actual ni combinación Anki/AnkiConnect probada.
Las pruebas de protocolo usan respuestas sintéticas y no sustituyen esa
verificación pendiente antes de instalar el complemento en la base de prueba.
No se accede a la colección personal. [Evidencia](evidence/anki-implementation/README.md).

## 20. Preparación y comparación OCR — retirada (2026-10-21)

Estado actual: se eliminaron controles, adaptadores, workers, pruebas y herramientas
de este flujo por solicitud del usuario. El texto siguiente registra la etapa
histórica; no declara funciones ni dependencias activas.

Flujo de revisión (referencia histórica no distribuida): reutiliza Pillow, PySide6, Tesseract y el runtime
MangaOCR ya inventariados. No añade versiones, requirements/locks, modelos,
diccionarios ni servicios externos. Pillow prepara copias temporales; Task supervisa
workers propios. MangaOCR usa exclusivamente las rutas guardadas explícitamente,
sin descubrir entornos ni modificar los existentes, y mantiene su modo offline.
No se redistribuyen imágenes del usuario, software ni pesos nuevos.

Se contrastó [la advertencia oficial de MangaOCR sobre texto inventado](https://github.com/kha-white/manga-ocr#usage-tips).
La inferencia de diagnóstico utilizó MangaOCR 0.1.16 CPU del runtime configurado
y Tesseract del sistema; no es una instalación independiente desde cero ni una
mejora de precisión acreditada. Evidencia (referencia histórica no distribuida).
Un modelo alternativo nuevo sigue sin seleccionarse/instalarse y no se atribuyen
licencias ni compatibilidad a pesos no inspeccionados.

## 21. Respaldo PaddleOCR CPU — retirado (2026-10-21)

Estado actual: PaddleOCR dejó de ser una integración de Next. No hay imports,
workers ni instalación accesible desde la aplicación. Se conservaron el entorno,
modelos y cachés instalados por el usuario. El lock y catálogo se archivaron en
`docs/evidence/paddle-backup/retired-requirements-paddle-cpu.lock` y
`docs/evidence/paddle-backup/retired-model-catalog.json`. El inventario y las fichas
de licencia permanecen como evidencia de recursos presentes, no de requisitos
activos. Los párrafos siguientes describen exclusivamente la incorporación retirada.

[Preparación y uso](PADDLE-BACKUP.md). Instalación CPU completada por el usuario;
inferencia real, métricas y flujo Qt offscreen verificados después en HOME/XDG
nuevos, sin conexiones salientes ni paquetes heredados. No se modifica la base
Python 3.14 ni se incluye software/pesos de terceros en Git.

| Componente | Origen, licencia y evidencia |
|---|---|
| PaddleOCR 3.3.2 | [PyPI oficial](https://pypi.org/project/paddleocr/3.3.2/), Apache-2.0 del proyecto; API contrastada con el tag y runtime instalado. |
| PaddlePaddle 3.2.2 CPU | [PyPI oficial](https://pypi.org/project/paddlepaddle/3.2.2/), Apache-2.0 del proyecto; CPython 3.13 aislado, import y CPU comprobados. |
| PP-OCRv5_mobile_det | [Ficha oficial](https://huggingface.co/PaddlePaddle/PP-OCRv5_mobile_det), Apache-2.0 propia de ese artefacto; commit `0d63e78e2b680928f6b1747d76a08db6e645efb7`. |
| PP-OCRv5_mobile_rec | [Ficha oficial](https://huggingface.co/PaddlePaddle/PP-OCRv5_mobile_rec), Apache-2.0 propia de ese artefacto; commit `682f20538d8c086cb2128e5cfac775e6c4904e85`. |
| Transitivos (62 distribuciones contando SDK/core) | [Inventario exacto](evidence/paddle-backup/installed-artifacts.json), con URLs, versiones, hashes de ruedas, declaraciones/clasificadores de licencia y hashes de avisos instalados. No se les atribuye la licencia del SDK. |

`requirements-paddle-cpu.lock` publica el cierre realmente instalado para CPython
3.13/Linux x86_64. Las preparaciones nuevas copian ese lock y usan
`--require-hashes --no-deps`; se conserva un lock local anterior. Ya no se vuelve
a resolver automáticamente el conjunto transitorio. `pip check` pasa; no contiene
paquetes NVIDIA/CUDA. `naatik_next/paddle-models.json` fija revisión, URL, tamaño y
SHA-256 de los seis archivos de inferencia y de ambas fichas. La preparación usa
esos commits, verifica los bytes, conserva fichas/recibo y no reemplaza destinos
existentes. No hay pesos ni ruedas versionados. No se borran caches ni datos.

Inventario/licencias: algunas distribuciones no rellenan `License` ni
`License-Expression`; sus clasificadores y avisos instalados se registran aparte.
`safetensors` declara clasificación Apache; `wcwidth`, MIT; `python-bidi`, LGPL,
con `COPYING`, `COPYING.LESSER` y `LICENSE-THIRD-PARTY.yml`. No se afirma aprobación
de redistribución de todo el conjunto por el éxito de la instalación.

Runtime propio y modelos/cachés pertenecen a Next. El SDK se carga en worker
opcional y los recursos lingüísticos antiguos no se descubren. Durante inferencia
se bloquean conexiones; no se envían imágenes a servicios. El usuario completó
la descarga externa; la validación posterior no sustituye una segunda instalación
en máquina limpia. Precisión general, segunda muestra y escritorio real siguen
pendientes. [Pruebas y mediciones](evidence/paddle-backup/README.md).

## Adaptación Fedora tutorial / Español-English (2026-10-23)

Revalidación 2026-10-24: sin cambios de dependencias, versiones ni locks;
[hashes conservados](evidence/fedora-bilingual/2026-10-24/preservation.json).
La captura real usó el Spectacle nativo existente (6.7.5-1.fc44,
GPL-2.0-only según RPM Fedora). Para automatizar exclusivamente el diagnóstico
de selección/Escape y un atajo temporal se usó el xdotool ya instalado
(3.20211022.1-10.fc44, LicenseRef-Callaway-BSD según RPM;
origen declarado por RPM: https://github.com/jordansissel/xdotool).
No se instala, distribuye ni requiere xdotool para ejecutar Next. No se añadió
ningún paquete del sistema ni recurso opcional. La licencia textual de xdotool
no se verificó de forma independiente. Véanse
[metadatos y alcance](evidence/fedora-bilingual/2026-10-24/native-tools.txt) y
[validación](evidence/fedora-bilingual/2026-10-24/README.md).

No se añadieron ni actualizaron dependencias, modelos, diccionarios ni fuentes de
terceros para esta adaptación. Los catálogos, tutorial y selector de idioma son
código y textos propios; se reutilizan Qt, Tk opcional y los asistentes existentes.
Los locks conservan exactamente sus bytes y SHA-256 iniciales; evidencia:
[evidence/fedora-bilingual/preservation.json](evidence/fedora-bilingual/preservation.json).
Instalación base offline en venv nueva con HOME/XDG aislados y hashes fijados:
evidence/fedora-bilingual/install-en.log (referencia histórica no distribuida).
La red/PyPI real, VM limpia y recursos opcionales no quedan acreditados por esa
prueba offline; conservan las versiones, licencias, orígenes y pendientes de este
inventario. No se distribuyen ruedas, modelos, diccionarios ni entornos en el
paquete de código Fedora.

## Preparación de fuentes para publicación — 2026-10-24

Esta copia conserva las versiones, locks, catálogos de recursos, fuentes públicas,
metadatos de licencia y hashes registrados. No añade ni distribuye paquetes,
fuentes tipográficas, modelos o diccionarios externos. Las rutas documentales
identificables se anonimizaron; los hashes identifican los artefactos históricos,
no una descarga nueva ni una concesión de licencia de redistribución. Se omitieron
logs, capturas y muestras del usuario, sin borrar sus originales.

La validación de la publicación usó el Bubblewrap existente del sistema
(0.12.0-1.fc44, LGPL-2.1-or-later según metadatos RPM Fedora; proyecto declarado
https://github.com/containers/bubblewrap/). Solo herramienta de diagnóstico:
no se instala, incluye ni requiere para ejecutar Next. No se verificó
independientemente su texto de licencia ni se copió su binario. Se ocultaron
/home y temporales anteriores y se deshabilitó la red. La venv se creó desde
ruedas separadas previamente, con los hashes actuales. El entorno instalado
no se reutilizó ni se incluyó en esta copia.

[Resumen reproducible y límites](publication-validation.json),
[informe de publicación](../PUBLICATION_REPORT.md),
[estado de la licencia propia](../LICENSE-STATUS.md). No se atribuyen las
licencias de dependencias al código propio.

## Decisión de licencia propia — 2026-10-24

El titular autorizó [MIT](../LICENSE) para el código propio, con Copyright (c)
2026 ElpincheAlx. Esta decisión no cambia las licencias ni avisos independientes
inventariados para terceros, sus fuentes, hashes o pendientes. No se incorpora,
actualiza ni retira ninguna dependencia ni recurso en este cambio de licencia.
[Estado actual e histórico](../LICENSE-STATUS.md).
