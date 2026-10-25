> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# Validación externa registrada: PASS/0

El usuario ejecutó `tools/validate-public-install.sh` y confirmó PASS/0. Se leyeron
los artefactos existentes de `~/Naatik-validation/public-install-U6n9VjIW`, sin
repetir instalaciones, descargas ni pruebas. Ejecución: **2026-10-19, 22:36:59–22:38:17
UTC−06:00**. Resumen verificable, resultados y SHA-256 de logs:
[external-public-install-pass.json](external-public-install-pass.json).
La ejecución anterior BLOCKED por DNS se conserva como evidencia histórica.

## Acreditado por los logs

Las **11 etapas** de `result.json` figuran PASS y `normal_profile_unchanged` es true.
Host Fedora 44 x86_64, glibc 2.43, CPython 3.14.8 del sistema.

| Etapa | Evidencia leída | Resultado acreditado |
|---|---|---|
| Copia aislada / bootstrap | result.json | Fuentes sin venv, wheelhouse o recursos previos; bootstrap propio |
| Locks públicos | public-lock-audit.json | 63 registros verificados; los SHA-256 de los tres locks originales coinciden con los actuales |
| Matriz Python | python-matrix.json | Metadatos/tags públicos; no prueba instalación/inferencia en otros Python |
| Base desde fuentes públicas | logs/base-install.log | Instalación del cierre base en .venv propia |
| Bibliotecas nativas | logs/native-libraries.log | Carga de bibliotecas comprobadas para KDE/X11; sin interacción con display |
| Primer/segundo inicio y Tesseract | logs/base-smoke.log | GUI offscreen, persistencia y OCR real **Hello world**; event loop operativo |
| Runtime CPU | logs/cpu-install.log | Instalación de paquetes, UniDic construido desde sdist oficial, `pip check`: No broken requirements found |
| Modelo completo | model-download.json | Seis archivos descargados desde revisión fijada; tamaño y SHA-256 correctos |
| MangaOCR real | cpu-inference.json | torch **2.13.0+cpu**, CUDA null, manga-ocr **0.1.16**; carga y OCR **日本** sin editar |
| Cancelación/recarga | cpu-inference.json | Cancelación del worker y recarga reales; 758 latidos Qt durante la prueba |
| Reutilización | model-reuse.json | Todos los archivos verificados y reutilizados con red rechazada |

El modelo es `kha-white/manga-ocr-base`, revisión
`aa6573bd10b0d446cbf622e29c3e084914df9741`. Sus hashes de descarga coinciden con
[model-catalog.json](../naatik_next/model-catalog.json); el peso principal mide
444135475 bytes. Esto acredita descarga completa y reutilización sin red, **no**
una reanudación real tras interrumpir la descarga. Licencias y redistribución
siguen teniendo el alcance del inventario, no se amplían por pasar las pruebas.

El log registra que Transformers usa `ViTImageProcessorPil` al no estar instalado
torchvision. La inferencia real pasó con esa ruta PIL. No se añade torchvision ni
se presenta su ausencia como un motor OCR alternativo. Stanza y PaddleOCR no se
convierten en dependencias funcionales por esta ejecución.

La matriz pública no encuentra incompatibilidad Requires-Python en 3.12/3.13 para
los paquetes PyPI analizados; UniDic se publica como sdist. NumPy excluye 3.11.
No se ejecutó el cierre con 3.12/3.13 ni se acreditó su inferencia; Python 3.14 se
mantiene como versión del lock probado. Torch CPU tiene índice separado.

## Instalación y perfil que se validaron

Bajo `~/Naatik-validation/public-install-U6n9VjIW/`:

- Lanzador: `Next con espacios/launch`.
- Base: `Next con espacios/.venv`; runtime CPU: `Next con espacios/.venv-mangaocr`.
- HOME: `home`; configuración: `xdg/config/naatik-next/settings.json`.
- Datos: `xdg/data/naatik-next`; estado/log: `xdg/state/naatik-next`.
- Modelo: `xdg/data/naatik-next/models/manga-ocr-base`.
- Preferencias actuales: Tesseract/eng, asistente completado. Las rutas MangaOCR
  apuntan al runtime/modelo de esta misma instalación. No hay diccionarios ni
  modelos Argos en este perfil según la prueba de inicio.

**No abras únicamente `launch` sin estas variables:** usaría los XDG de tu terminal.
Desde tu terminal en el escritorio, usa exactamente:

```bash
review="$HOME/Naatik-validation/public-install-U6n9VjIW"
env -u QT_QPA_PLATFORM -u PYTHONPATH -u PYTHONHOME \
  HOME="$review/home" \
  XDG_CONFIG_HOME="$review/xdg/config" \
  XDG_DATA_HOME="$review/xdg/data" \
  XDG_STATE_HOME="$review/xdg/state" \
  XDG_CACHE_HOME="$review/xdg/cache" \
  HF_HOME="$review/hf-cache" TMPDIR="$review/tmp" \
  XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}" \
  XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}" \
  "$review/Next con espacios/launch"
```

Conserva DISPLAY, la sesión y autenticación de tu terminal; elimina un posible
`QT_QPA_PLATFORM=offscreen` para abrir en pantalla. El endpoint IPC distingue
perfiles por la ruta de estado; no se envía la acción a la instancia del perfil
normal. El comando no instala, migra ni copia recursos y no usa JapaneseMining.
La apertura escribirá únicamente preferencias/logs del perfil aislado y su socket
privado. El comando se contrastó con rutas/configuración/código, **no se ejecutó
contra el escritorio** en este registro documental.

Para la revisión manual: en **OCR**, selecciona **MangaOCR — listo**; abre
`Next con espacios/examples/nihon.png` con **Abrir imagen** y pulsa **Reconocer**.
No se cambia el motor automáticamente. Traducción/diccionarios requieren preparar
recursos en este perfil; no se toman del normal. Después prueba captura/cancelación,
atajo e IPC si deseas acreditar esos casos interactivos por separado.

## Pendientes conservados

- Máquina/VM limpia: los ejecutables y bibliotecas nativas siguen siendo del host.
- Interacción gráfica de **esta instalación**: abrir desde menú/escritorio, foco,
  captura y su cancelación/limpieza, atajo global e IPC real. Qt fue offscreen.
- Reanudación real de una descarga interrumpida (los tests inyectados no la acreditan).
- Otros Python/plataformas/arquitecturas, GPU y preparación de Argos/diccionarios
  en el perfil aislado. El alcance futuro de popups/Anki/móvil sigue pendiente.

No se modificó el perfil normal ni la instalación validada al registrar esta
información. No se añadieron logs completos, pesos, venvs o datos personales a Git.
