> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# Preparación guiada de recursos

En el primer inicio se abre el asistente. También se puede abrir desde
Preferencias y diagnóstico → Asistente de idioma y preparación OCR.

1. Elige el motor. Con Tesseract, elige el idioma e instala el ejecutable y sus
   datos mediante el gestor de paquetes del sistema. El asistente explica este
   paso, pero no instala paquetes del sistema. Pulsa Comprobar requisitos y
   revisa los idiomas disponibles: una prueba con otro idioma no acredita el elegido.
2. Con MangaOCR, prepara primero el entorno CPU propio y después descarga el
   modelo verificado o selecciona un modelo local completo. Cada preparación
   requiere confirmación. Comprueba carga e inferencia antes de guardar.
3. Guarda el OCR y prueba una imagen en Captura y resultado. Guardar conserva
   las elecciones; no garantiza por sí solo que los recursos estén listos.
4. Para traducción, abre Preparar traducción local desde el asistente. En la
   pestaña Traducción elige origen y destino, pulsa Preparar traducción y revisa
   los componentes antes de confirmar. Listo exige inferencia comprobada.
5. Para diccionarios, abre Importar diccionarios desde el asistente y pulsa
   Agregar diccionarios. Aporta ZIP compatibles con Yomitan, revisa los avisos y
   confirma los seleccionados. No se incluye un catálogo de descarga de diccionarios.

Abrir otra sección cierra el asistente sin guardar las elecciones OCR pendientes.
No permite salir hacia otra sección mientras haya una preparación en curso.
Los recursos de traducción y diccionarios son opcionales para usar OCR.

Validación local: `QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest
 tests.test_setup_dialog tests.test_setup tests.test_translation_setup` (26 pruebas).
Incluye cambio de motor, idioma faltante, navegación sin descargar ni guardar,
preparación ocupada, integridad de descargas y preparación de traducción con
recursos simulados. No acredita una instalación real con red, captura global ni
una máquina limpia. No se cambiaron dependencias ni recursos de terceros.
