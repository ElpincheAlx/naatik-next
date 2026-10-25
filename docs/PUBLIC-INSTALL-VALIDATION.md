> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# Validación pública independiente después de 586a7fb

Estado más reciente: **PASS/0 externo registrado**, 2026-10-19, en
`public-install-U6n9VjIW`. Instalación pública, descarga íntegra e inferencia CPU
quedaron acreditadas; [evidencia y límites](EXTERNAL-PUBLIC-INSTALL-PASS.md).

Lo que sigue conserva el intento anterior del agente, **BLOCKED por DNS**, como
evidencia histórica; sus gates de red fueron superados por la ejecución externa.
Esta revisión no ejecuta JapaneseMining ni toca su entorno/servicios. El perfil normal de Next se conservó.

## Intento histórico del agente

Se ejecutó `./tools/validate-public-install.sh`. Creó
`~/Naatik-validation/public-install-6xtQshMN/` con HOME/XDG/cachés/temporales nuevos
y copia de fuentes sin venv, wheelhouse ni modelos. Creó bootstrap venv con pip
sembrado por ensurepip, no con paquetes del usuario. Tesseract host y datos eng
estaban presentes. Primera consulta:

`https://pypi.org/pypi/argostranslate/1.11.0/json`

Resultado: `Temporary failure in name resolution`. El proceso terminó con
**código 2**, `summary.txt`/`result.json` dicen BLOCKED y la comparación de hashes
del perfil normal resultó **sin cambios**. Las comprobaciones HTTPS directas de
PyPI, índice CPU PyTorch y archivo del modelo Hugging Face también fallaron por DNS.
Los logs originales quedan en esa carpeta; resumen versionado:
[public-install-evidence.json](public-install-evidence.json).

No hay un éxito nuevo de OCR CPU ni un éxito público de instalación oculto detrás
de las pruebas unitarias. La evidencia con ruedas de desarrollo de la entrega
anterior permanece histórica en INDEPENDENCE-VALIDATION.md.

## Qué comprobará el único comando desde la terminal del usuario

`${PROJECT_ROOT}/tools/validate-public-install.sh`

- Preflight de Python estándar 3.14/Linux x86_64, Tesseract y eng. Si falta Python,
  informa el comando de Fedora para obtenerlo, sin ejecutar sudo.
- Copia nueva de Next y HOME/XDG/cachés nuevos. No lee las venvs ni modelos del
  usuario ni `.wheelhouse`; únicamente toma huellas de archivos del perfil normal.
- Contrasta **cada hash permitido** en los tres locks con PyPI y el índice CPU
  oficial. Un hash no publicado, retirado o incompatible no se sustituye por otro.
- Registra metadatos y una matriz de Python 3.11–3.14 basada en Requires-Python y
  tags públicos. Esa matriz es un filtro, no acreditación de inferencia.
- En la copia de revisión convierte los pins a URLs públicas auditadas. Solo
  instala esos artefactos con hash, sin resolver paquetes ajenos ni recurrir a
  caché. Los locks originales del usuario permanecen intactos.
- Instala base, herramientas de construcción fijadas y runtime CPU propio. UniDic
  usa su **sdist oficial**, no una rueda local no publicada. Ejecuta `pip check`
  del runtime CPU y comprueba que torch sea `+cpu`, sin CUDA.
- Comprueba bibliotecas nativas y base Qt **offscreen**, primer/segundo inicio y
  Tesseract real sobre la muestra sintética «Hello world».
- Descarga los seis archivos del modelo desde la revisión fijada; verifica tamaño
  y SHA-256 de cada uno. Usa únicamente el destino XDG nuevo.
- Ejecuta el worker real de Next con `.venv-mangaocr` propio: carga, probe 日本,
  inferencia 日本 sin edición, cancelación y recarga. Registra identidad CPU,
  descriptor y latidos del event loop Qt. No consulta diccionarios como traducción.
- Repite la preparación del modelo con red rechazada para comprobar reutilización
  íntegra; verifica que el perfil normal no cambió y conserva todos los logs.

PASS/0 solo tras todas esas etapas; BLOCKED/2 para requisito/red/proveedor; FAIL/1
para errores de locks, integridad, instalación o inferencia. El script conserva
los directorios incluso al fallar. No manda capturas/texto a servicios externos,
no inicia capturas ni envía notas a Anki. Cada intento empieza sin modelos y no
reutiliza los pesos de intentos anteriores. Los archivos descargados no van a Git.

## Python 3.14: restricción investigada, no cambio apresurado

METADATA real de la base propia: NumPy 2.5.2 exige >=3.12; PySide6 6.11.1 acepta
>=3.10,<3.15, Pillow 12.3.0 >=3.10 y CTranslate2 4.8.1 >=3.9. Los 20 módulos de
Next se analizaron sintácticamente con Python **3.12.15 y 3.13.16**, sin importar
las bibliotecas. Esto indica que exigir 3.14 no es una necesidad demostrada del
código ni de esos mínimos; sí reduce las opciones de instalación.

Se conserva 3.14 porque los locks actuales contienen hashes cp314 y aún no hay
prueba de cierre binario/inferencia en 3.12/3.13. El índice oficial de PyTorch
ofrece archivos CPU para varios intérpretes, pero eso solo no acredita todo el
runtime. No se cambia una condición del instalador para aceptar ruedas distintas.
La matriz pública y las pruebas reales de otro lock son el paso necesario antes
de ampliar la compatibilidad. La red bloqueó aquí la matriz pública completa.

Referencias primarias:
[PySide6](https://pypi.org/project/PySide6/6.11.1/),
[NumPy](https://pypi.org/pypi/numpy/2.5.2/json),
[CTranslate2](https://pypi.org/project/ctranslate2/4.8.1/),
[índice CPU](https://download.pytorch.org/whl/cpu/torch/).
El detalle de METADATA inspeccionado está en la evidencia JSON; no se presenta
ese METADATA local como una instalación nueva desde Internet.

## Revisión de la guía e instaladores

Se corrigió el RPM de Python: Fedora 44 usa **python3**, que proporciona
`/usr/bin/python3.14`, según el catálogo oficial y rpm del host. La guía explica
cómo instalar Python/pip/CA/Tesseract/datos y bibliotecas Qt/xcb sin suponerlos
presentes, separa Spectacle y el escritorio KDE/X11, y no ofrece comandos para
plataformas no acreditadas. El instalador informa Python ausente, usa el índice
PyPI explícito y permite forzar fuentes públicas aunque exista `.wheelhouse`.

Se retiró del lock el hash privado de la rueda local UniDic Lite. El sdist público
con SHA-256 oficial sigue fijado; build tools permanecen fijadas en su lock. No se
cambió el paquete o modelo para hacer pasar una inferencia.

Suite: **85 pruebas** pasan (76 existentes y 9 casos nuevos del validador).
Los casos nuevos usan respuestas públicas/DNS **inyectadas** y prueban rechazo de
un hash privado aunque otro sea válido, origen CPU, ausencia de versión, fallo de
red, copia sin artefactos, timeout/errores de procesos, huella del perfil y
separación entre mínimo Python y ABI de ruedas. No representan instalaciones/descargas reales exitosas.

## Gates del intento anterior y resolución posterior

1. **Superado externamente:** hashes públicos, instalación, descarga completa,
   inferencia CPU propia, cancelación/recarga y reutilización sin red.
2. **Pendiente:** máquina/VM limpia Fedora 44. HOME/venv aislados siguen usando
   Tesseract, Python, glibc y bibliotecas nativas del host.
3. **Pendiente para esta instalación:** captura, atajo, foco, apertura de menú e
   IPC interactivos. Qt offscreen no los acredita.
4. **Pendiente:** reanudación real de descarga interrumpida, otros Python y GPU.
   La matriz pública fue completada, pero no equivale a inferencia en 3.12/3.13.

Además se ejecutó el preflight con un nombre de Python inexistente: BLOCKED/2,
summary.txt y result.json creados, sin acceder al perfil normal.
