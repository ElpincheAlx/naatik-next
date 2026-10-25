> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# Diseño de esta entrega

La referencia de JapaneseMining aporta captura, OCR, diccionarios, traducción y
UI Qt. No se trasladan sus servicios, endpoints ni contratos internos. No se
implementan Anki, minado, furigana o gramática analítica en esta primera entrega.

- `app.py`: widgets Qt únicamente en el hilo principal, selección explícita de
  motor/ruta, procedencia de texto y estados de tareas.
- `processes.py`: QProcess asíncrono con protocolo JSON privado por pipes, timeout,
  terminación y escalado a kill. El proceso Argos permanece cargado entre solicitudes.
- `worker.py`: despacho privado de tareas, independiente del proceso GUI.
- `ocr.py`: adaptadores separados, identidad y prueba de inferencia de Tesseract;
  detección preliminar de MangaOCR sin acreditar disponibilidad por archivos;
  PaddleOCR sigue sin inferencia integrada. `manga_worker.py` carga/prueba MangaOCR
  local en un proceso persistente administrado de Next, sin red ni servicios antiguos.
  Spectacle 6/KDE X11 con directorio único privado, timeout y limpieza en finally.
- `translation.py`: descubrimiento de paquetes Argos, prueba de cada enlace y BFS
  para rutas más cortas reales; modelos CTranslate2 retenidos. Sin red ni fallback.
- `storage.py`: SQLite propio, cascada de borrado, activación y prioridad; settings
  JSON atómico con fsync y replace. Importación dentro de una transacción.

ZIP: snapshot acotado para evitar cambios entre hash e importación; nunca se
extraen rutas al filesystem. Se inspecciona todo el directorio del archivo antes
de escribir filas. Límites: ZIP 512 MiB, 10 000 miembros, 32 MiB por miembro,
512 MiB descomprimidos, relación 300:1, 2 millones de entradas. Se rechazan
traversal, rutas absolutas/Windows, barras invertidas, enlaces, cifrado y nombres
duplicados. La validación por entrada ocurre en la transacción; fallo o cancelación
revierte todas las filas. Duplicados por SHA-256 y por título/revisión.
El borrado solo conoce el ID de las filas administradas; nunca la ruta original.

Cancelación: los workers reciben SIGTERM, revierten SQLite y terminan el hijo
externo en finally. El supervisor escala a kill si no responden. Captura y OCR
tienen timeout interno y externo; Argos puede necesitar kill durante código nativo.
Una operación ya confirmada antes de que llegue la cancelación puede haber acabado.
Una sola instancia GUI por usuario evita lanzar capturas duplicadas desde Next.
No se toma control de instancias Spectacle o servicios de otras aplicaciones.

Las imágenes se normalizan a PNG en snapshots únicos. Cambiar de imagen durante
OCR no permite aplicar un resultado viejo a la imagen nueva. El texto OCR original
se conserva separado de la versión editable. Una traducción queda marcada como
anterior cuando se cambia el texto o la ruta.

Contenido enriquecido: `dictionary_content.py` valida árboles acotados y genera
HTML seguro; `dictionary_view.py` impide navegación y toda carga de recursos.
SQLite conserva árboles originales, ocho campos y metadatos mediante migración
aditiva. Consulta de diccionario y traducción permanecen independientes.
