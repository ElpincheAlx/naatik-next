# Evidencia de inspección Anki — 2026-10-20

- [Manifiesto local](inspection.json): SHA-256, coincidencias con el paquete de
  referencia y posiciones de símbolos, sobre fuentes de texto seleccionados.
- [Fuentes oficiales consultadas](official-sources.json): alcance de cada fuente,
  licencias verificadas y límites del acceso al paquete actual del mantenedor.
- [Diseño](../../ANKI-DESIGN.md): recorridos, pantallas propuestas, contratos y
  plan de pruebas.

Solo se leyeron fuentes y documentos. El análisis AST parsea texto Python sin
importarlo ni ejecutarlo. No se abrieron bases de JapaneseMining, archivos de
configuración personal, colecciones/perfiles de Anki, capturas, historial o logs
personales. No hubo HTTP local, conexión a AnkiConnect, exportación de colección,
arranque de servicios antiguos, instalación o envío de notas.

Se volvieron a comprobar los hashes de los fuentes seleccionados de JapaneseMining
y Next después de la revisión: sin cambios. La documentación de la referencia
se conserva como histórica; el diseño usa el código actual de Next y señala dónde
faltan adaptadores en lugar de trasladar afirmaciones antiguas.

Verificaciones de esta entrega: coherencia de referencias locales, JSON válido,
`git diff --check` y alcance documental del cambio. No se ejecutó la aplicación ni
se presentan pruebas offscreen, servidor simulado, instalación desde cero o Anki
real como realizadas. Su matriz es un **plan futuro**. Fallo de arranque cerrado y
Apariencia continúan pendientes; no se tocó código de ciclo de vida.

La licencia del archivo oficial histórico de AnkiConnect está verificada; la del
paquete actual no se pudo comprobar por el bloqueo de acceso a SourceHut. No se
sustituye ese requisito por una copia de terceros ni se hereda la licencia a
modelos, diccionarios, ejemplos o medios.
