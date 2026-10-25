> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# Respaldo manual PaddleOCR — retirado

Se retiraron el adaptador opcional, su preparación, el comparador y sus workers,
la caché exclusiva de esa comparación y los controles de respaldo. La aplicación
no importa PaddleOCR ni utiliza su entorno o modelos instalados.

El entorno `.venv-paddleocr`, sus paquetes/lock locales y los modelos/cachés
propios que instaló el usuario permanecen en disco. No se desinstalan ni se borran
recursos o preferencias del usuario como efecto de esta retirada.

Se conserva la evidencia histórica de instalación, licencias, hashes y mediciones:

- [Informe y resultados](evidence/paddle-backup/README.md).
- [Inventario de paquetes](evidence/paddle-backup/installed-artifacts.json).
- [Lock archivado](evidence/paddle-backup/retired-requirements-paddle-cpu.lock).
- [Catálogo de modelos archivado](evidence/paddle-backup/retired-model-catalog.json).

Esos archivos documentan lo instalado; no son requisitos activos ni un instalador
actual. Se mantiene captura/copiar y Translator con su atajo, con procesamiento
local y sin pasos de selección/comparación adicionales.
