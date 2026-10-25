> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# JMdict enriquecido y MangaOCR — 2026-10-19

El diagnóstico de traducción de a249fea y sus archivos se conservaron sin cambios.
No se introdujo un reemplazo de 日本 por una definición del diccionario.

## JMdict

Se inspeccionó el ZIP local `[Bilingual] JMdict (Recommended).zip`:
JMdict [2025-11-01], revisión JMdict.2025-11-01; 54 miembros, 513 033 filas,
392 879 definiciones structured-content. Los elementos encontrados fueron
li, ul, th, td, tr, span, a y table, con data/lang/style y referencias `?query=`.
No había archivos de medios. El index no declara lenguas: se siguen mostrando
como desconocidas, sin adivinarlas por el contenido.

Formato contrastado con el esquema primario de Yomitan:
https://github.com/yomidevs/yomitan/blob/master/ext/data/schemas/dictionary-term-bank-v3-schema.json

La base conserva JSON de los ocho campos de cada fila, el árbol íntegro de
significados, el index y la definición de tags. La representación de visualización
no sustituye al original. Columnas source_row y metadata se añaden si no existen;
las filas antiguas de texto siguen disponibles y no se reconstruyen.

El renderizador genera HTML propio a partir de elementos validados y texto
escapado; nunca pasa HTML, estilos, href o rutas originales al documento Qt.
Las tablas se muestran como tablas, ejemplos y lecturas siguen separados. Se
conservan las referencias y se muestran como texto, sin navegación. CSS arbitrario
no se interpreta; solo negrita, cursiva y alineación de una lista segura se
aplican. No se renderizan imágenes/medios ni nodos desconocidos. Las lecturas ruby
se muestran anotadas con paréntesis. El visor bloquea toda resolución de recursos.

Se mantienen los límites anteriores del ZIP y se añaden profundidad 32,
20 000 nodos por entrada y 2 millones de caracteres por lista de significados.
El árbol completo se valida dentro de la transacción antes de confirmar, con
rollback ante errores o cancelación. El borrado de un diccionario grande ahora
se ejecuta en un worker administrado para mantener operativa la ventana.

Comprobaciones reales:

- Importación a SQLite temporal: **513 033 filas**.
- Comparación semántica de **cada fila completa** con la original: correcta.
- Consulta 日本: cuatro resultados, dos lecturas にほん/にっぽん, Japan,
  ejemplos y tablas. Consulta por lectura también comprobada.
- Duplicados, activación, prioridad persistida al reabrir y eliminación: correctos.
- GUI offscreen: importación y visualización reales, borrado asíncrono y nueva
  importación cancelada tras comenzar a insertar, sin filas parciales.
- Temporizador Qt siguió activo durante la importación (1 986 ticks en la pasada
  registrada). Ninguna definición se colocó en el panel de traducción.
- ZIP original conservó SHA-256
  `677fb8b0cc5e4bef3b0bfab4540b374406688e78d4943b0f8460794ede108081`.

Evidencia: [jmdict-evidence.json](jmdict-evidence.json),
[jmdict-gui-evidence.json](jmdict-gui-evidence.json),
vista offscreen (referencia histórica no distribuida).

## MangaOCR

Recursos inspeccionados y utilizados explícitamente en modo de solo lectura:

- Python de `${REFERENCE_ROOT}/.venv-mangaocr/bin/python` (3.14).
- manga-ocr 0.1.16, torch 2.13.0, transformers 5.14.1, jaconv 0.5.0.
- Snapshot `aa6573bd10b0d446cbf622e29c3e084914df9741` de manga-ocr-base,
  con config, procesador, vocabulario, tokenizador y pytorch_model.bin.
- Había otro snapshot con solo safetensors, insuficiente por sí solo: no se
  confundió la presencia de ese archivo con un modelo completo/listo.
- El paquete MangaOCR instalado contiene ajustes de compatibilidad con
  Transformers; su archivo ocr.py y los modelos se identifican por SHA-256 en
  [manga-runtime.json](manga-runtime.json). No se modificó el paquete.

Next ejecuta **su propio módulo** `naatik_next.manga_worker` con el intérprete
indicado, no un servidor ni script de JapaneseMining. La GUI mantiene sus
bibliotecas aisladas en .venv. El Python alternativo importa su biblioteca
MangaOCR ya instalada. No se copiaron dependencias ni se instalaron paquetes;
el entorno opcional exacto utilizado queda registrado en el manifiesto. Cambiarlo
requiere volver a cargar/probar. Se puede configurar otro Python dedicado y otro
snapshot desde Preferencias.

Antes de importar bibliotecas, el proceso deshabilita la red/telemetría y las
resoluciones DNS/conexiones. Usa una ruta local completa y no admite auto_map de
código remoto. PYTHONDONTWRITEBYTECODE se establece antes de arrancar Python.
No se cambian servicios, unidades, puertos ni archivos de JapaneseMining.

La presencia de archivos solo produce **detectado**. Se verifica identidad del
paquete/configuración, se carga en CPU y se ejecuta el ejemplo japonés propio de
Next `examples/nihon.png`. Solo una inferencia real que devuelve 日本 permite
**listo**. Fallos quedan como recursos faltantes, incompatible o error. Las
configuraciones/archivos corruptos no pasan por resultados simulados.

El proceso queda residente entre peticiones para conservar el modelo. No hay
selector de dirección ni idioma: este adaptador es japonés fijo. Cambiar a él no
borra el idioma previamente elegido para Tesseract. Una cancelación termina el
proceso, lo escala a kill si hace falta, invalida su estado y requiere redetección;
no se envía la imagen a otro motor. También se detecta una caída en reposo.
Al cerrar la app se terminan los procesos y se liberan modelos.

Comprobaciones reales en GUI offscreen:

- Carga y reconocimiento de 日本 correctos.
- Se reutilizó el PID del proceso entre detección e inferencia.
- Cancelación de una petición real y liberación del proceso; selección MangaOCR
  conservada, sin fallback. Redetección, nueva carga e inferencia correctas.
- Temporizador Qt activo durante las operaciones, selección guardada y selector
  de idioma deshabilitado. Todos los procesos detenidos al cerrar.
- PaddleOCR sigue **incompatible/pendiente**, sin inferencia integrada.

Evidencia: [manga-evidence.json](manga-evidence.json).

## Pruebas y límites

28 tests de unidades, almacenamiento, renderizado y procesos. Las entradas de
prueba falsas se etiquetan como fixtures, no como OCR/diccionarios reales. Las
pruebas reales separadas y sus comandos figuran en el README.

Las pruebas anteriores no validan la interacción con Spectacle en el escritorio
real ni recuperan el OCR original de las capturas históricas. No se cambió
ninguna preferencia o diccionario persistente del usuario durante las pruebas.
No hay soporte general para todo ZIP Yomitan, PaddleOCR, captura Wayland ni
traducción semánticamente corregida por diccionarios.


## Actualización: consulta normal y evidencia manual del usuario

La nueva consulta dirigida del agente encontró JMdict ya importado y activo en
los datos normales (513 033 filas, prioridad 0). El mismo worker de la GUI devolvió
cuatro resultados de 日本; el visor Qt offscreen mostró Japan, にほん/にっぽん,
ejemplos y dos tablas, identificados como diccionario y separados del panel Argos.
Los hashes de la base y las preferencias fueron idénticos antes/después. No hubo
importación ni modificación de datos normales; no se repitieron pruebas completas.
Véase registro nuevo (referencia histórica no distribuida) y el último apartado de
[VALIDATION.md](VALIDATION.md).

Separadamente, **el usuario confirmó Capturar región → MangaOCR → 日本 en su
sesión real, sin editar el OCR**. Esta evidencia manual de un caso no valida
cancelación, limpieza, timeout ni todos los casos de captura. Las comprobaciones
Qt realizadas por el agente siguen siendo offscreen.
