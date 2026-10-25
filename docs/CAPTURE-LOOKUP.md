> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# Captura al soltar y consulta exacta automática

## Opción verificada

En esta máquina se consultaron, sin abrir selector:

```bash
QT_QPA_PLATFORM=offscreen spectacle --version
QT_QPA_PLATFORM=offscreen spectacle --help
```

Versión: `spectacle 6.7.5`. Su ayuda documenta:

```text
-k, --release-capture   Accept region selection on click-and-release
```

Invocación del adaptador (la ruta de salida es temporal y privada):

```bash
spectacle --new-instance --region --release-capture --background --nonotify --output region.png
```

Se exige que la ayuda anuncie esa opción antes de capturar. No se escriben
preferencias globales ni se simulan teclas/clics. No se añaden dependencias ni un
selector propio: Spectacle proporciona el comportamiento por invocación.

Fuentes oficiales de la versión instalada:

- [CommandLineOptions.h de KDE 6.7.5](https://github.com/KDE/spectacle/blob/v6.7.5/src/CommandLineOptions.h): opción y descripción.
- [SpectacleCore.cpp de KDE 6.7.5](https://github.com/KDE/spectacle/blob/v6.7.5/src/SpectacleCore.cpp): `ReleaseCapture` llama a `forceReleaseCapture(true)`; `autoExportActions()` en modo background con salida explícita guarda y no aplica las preferencias globales de copia.

El adaptador no pasa `--copy-image` ni `--copy-path`. Next recibe un PNG y deja
intactas sus dimensiones: no convierte coordenadas, escalas ni posiciones entre
monitores. Selección, composición y coordenadas quedan a cargo de Spectacle,
incluido Esc. Sin archivo o con archivo vacío se cancela; una imagen inválida no
llega al OCR. El soporte continúa limitado a KDE/X11.

## Consulta

Un resultado OCR vigente y no vacío conserva el original, actualiza el editor,
copia mediante Qt en el hilo principal si la preferencia está activa y consulta
el texto completo mediante el worker `lookup_selection` y `render_results`.
La consulta usa igualdad exacta, incluidos espacios/saltos, y respeta activación
y prioridad. No hay segmentación ni traducción automática.

Se reutiliza el worker de consulta con una sola petición pendiente (la más
reciente). Una nueva captura/OCR, cancelación, edición o selección invalida la
identidad anterior; las respuestas antiguas no actualizan el panel. La selección
manual sigue permitiendo consultar una palabra. Fallo, cancelación o resultado
OCR vacío no consultan el texto anterior ni escriben en el portapapeles.

## Evidencia automatizada y límites

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -q
```

- `test_capture_release.py`: comando Spectacle inyectado, opción requerida,
  salida ausente/vacía y conservación de dimensiones PNG.
- `test_ocr_clipboard.py`: botón, atajo y acción externa, ambos motores simulados,
  copia opcional y consulta automática del texto sin selección.
- `test_automatic_dictionary.py`: OCR inyectado, worker real y SQLite temporal;
  prioridad/activación, copia desactivada, ausencia de diccionarios/coincidencias,
  frase completa sin segmentación, cancelación, captura inválida, respuestas
  obsoletas y consulta manual posterior.
- `test_selection_lookup.py`: consulta manual, cola y descarte tras editar.

Resultado de la suite en este cambio: **100 pruebas, OK**.

Son pruebas offscreen, no captura real al soltar el ratón, inferencia OCR real ni
pegado entre aplicaciones. No se pudo abrir el display desde el entorno de
herramientas. Falta validar en KDE/X11 el arrastre y soltado, Esc/clic sin área,
varios monitores con posiciones negativas, regiones entre monitores y escalado
mixto. Seguir la prueba manual de README y comprobar el recorte mostrado antes
de dar por validada la geometría en ese escritorio.
