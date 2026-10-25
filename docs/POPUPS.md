> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# Translator, OCR Phrase y captura-copia

## Referencia y diferencias explícitas

Se siguieron en solo lectura los lanzadores materializados y sus destinos en
`~/Naatik-validation/japanesemining-workflow-review/`: `streamdeck_translate.sh`,
`streamdeck_phrase.sh`, `ui_service.py`, `translator_popup_qt.py`,
`phrase_popup_qt.py`, `phrase_engine.py` y `furigana_engine.py`. Sus siete hashes
coinciden con los fuentes originales de `${REFERENCE_ROOT}` al revisar este cambio.
También se consultó `FLUJO-ACTUAL.md`. No se importaron esos módulos ni se ejecutaron sus lanzadores, servicios
o puertos. La revisión visual posterior extrae únicamente métodos de presentación
en un arnés inerte, como documenta [POPUP-VISUAL-REVIEW.md](POPUP-VISUAL-REVIEW.md). **El comportamiento antiguo de esta tabla
se observa por código; no es una prueba interactiva del programa antiguo.**

| Comportamiento antiguo observado | Implementación de Next |
|---|---|
| Captura OCR independiente → portapapeles; Translator/Phrase no capturan | Tres acciones independientes: `--capture-copy`, `--translator`, `--phrase` |
| Ambos lanzadores leen portapapeles; vacío usa último OCR JSON, y sin texto abortan | Lee portapapeles Qt en cada acción, nunca ese JSON; vacío abre editor para escribir/pegar |
| Translator reutiliza editor, debounce 420 ms, Argos ja→en y Sudachi C | Reutiliza un popup editable, debounce 420 ms; Argos local con ruta directa/intermedia visible y elegible; lecturas opcionales Fugashi/UniDic propio |
| Fallo/ausencia Argos puede poner definiciones o texto en Translation | Error/recurso ausente explícito; traducción y definiciones en paneles separados, sin sustituciones |
| Phrase usa Fugashi/MeCab, lecturas, tokens, lookup por lema/superficie; abre otra ventana por petición | Análisis japonés Fugashi/UniDic propio, palabras seleccionables y consulta exacta por lema, luego superficie; una ventana reutilizable por acción |
| Furigana `superficie(lectura)`, reglas de conjugación/lecturas y tablas JLPT parciales | Anotación por palabra conservando espacios, con lecturas del léxico. Sin alineación inventada por kanji, reglas de gramática ni niveles JLPT |
| Lookup HTTP con nombres de diccionarios fijados y caché por ventana | Worker, Store y renderizador seguro existentes de Next, con diccionarios activos/prioridades importados por el usuario |
| Publicación móvil/historial automática en Phrase y acciones Anki | No hay envío, puertos, publicación ni historial de frases. Anki/móvil siguen pendientes |
| Servicios residentes y varios lanzadores | Un propietario Qt/IPC de Next; atajo, script, menú y `.desktop` despachan la misma acción interna |

Los popups reproducen la estructura visual de referencia: 720 × 840, sin marco,
cabecera arrastrable, tarjetas y pie fijo. Translator muestra el diccionario en
un tooltip de selección; Phrase lo muestra en tarjetas plegables por palabra.
Ver [comparación visual y diferencias deliberadas](POPUP-VISUAL-REVIEW.md).
Cerrar o Esc oculta y cancela el trabajo pendiente; la instancia permanece
residente. **Cerrar la ventana principal termina Next.**
No se necesita un OCR configurado para abrir ni usar los popups. Si después se
solicita captura en una instancia iniciada solo con popup, prepara entonces el OCR.

## Comandos

```bash
${PROJECT_ROOT}/launch --capture-copy
${PROJECT_ROOT}/launch --translator
${PROJECT_ROOT}/launch --phrase
${PROJECT_ROOT}/launch
```

Los dos comandos de texto abren únicamente su popup y leen el portapapeles al
recibir la acción. No simulan teclas, no capturan y no leen imágenes/temporales OCR.
El primero captura/copia y no abre ningún popup de texto. El último muestra la
ventana principal para configuración. Si ya existe un propietario del perfil,
las llamadas reutilizan su instancia, sin ventanas principales duplicadas.
Si no existe, el comando inicial permanece en ejecución: usa otra terminal o un
lanzador Detached para las acciones siguientes. No pulses Ctrl+C entre acciones;
SIGINT/SIGTERM solicitan el cierre ordenado del propietario.

Cada popup conserva su editor mientras está abierto. Una nueva invocación vuelve
a leer el portapapeles y reemplaza el texto de **ese** popup. Las ediciones rápidas
se agrupan; cada worker admite un trabajo y una petición pendiente más reciente.
La edición, cambio de ruta, nueva selección, cancelación y cierre invalidan
respuestas antiguas. Cancelar la captura principal no cancela los trabajos de un
popup, ni cancelar un popup cancela la captura; salir de Next termina todos los
workers mediante el supervisor común. No se copian automáticamente correcciones ni traducciones.
**Copiar texto** copia únicamente el contenido actual de su editor.

## Preparar recursos

### Traducción local

El selector visible permite intercambiar rutas instaladas. Si faltan recursos,
**Preparar traducción** abre la sección **Traducción** de la ventana principal.
Allí un solo recorrido detecta, propone componentes/ruta, pide confirmación,
instala y comprueba inferencia. Las rutas del popup se actualizan automáticamente.
La importación local y el diagnóstico están en **Opciones avanzadas**.

[Guía de preparación desde cero, licencia, directorios, evidencia y comprobación
de escritorio](TRANSLATION-SETUP.md). La descarga/inferencia neural nueva sigue
sin validarse por el bloqueo DNS de este entorno; el recorrido se prueba con
respuestas y paquetes sintéticos, sin descargar recursos del usuario.

### Lecturas y palabras

**Opciones → Preparar lecturas…** ofrece instalar con confirmación Fugashi 1.5.2 y UniDic
Lite 1.0.8 en `.venv-phrase` de Next. Son recursos opcionales compartidos entre
ambos popups; no dependen del entorno OCR. El Tagger usa el léxico propio y
`-r /dev/null`, sin configuración MeCab externa. También puede prepararse
explícitamente desde terminal:

```bash
cd ${PROJECT_ROOT}
./tools/install.sh --phrase
```

El lock incluye hashes públicos y un sdist UniDic de unos 47 MB comprimidos;
las herramientas de construcción se fijan en el lock compartido. Con una
`.wheelhouse-phrase` completa o `NAATIK_NEXT_WHEELHOUSE` puede instalarse sin red
(`NAATIK_NEXT_OFFLINE=1`). La GUI no descarga nada antes de confirmar. Las
preparaciones simultáneas del mismo proyecto se excluyen con un bloqueo local.

Lecturas y segmentación proceden del léxico y pueden ser ambiguas. Por ejemplo,
UniDic 2.1.2 puede segmentar 日本語 en 日本 + 語 y dar にっぽん a 日本; no se aplican
las sustituciones heurísticas del programa antiguo. Las palabras desconocidas
no reciben una lectura inventada. No hay gramática/JLPT sin recursos acreditados.
Sin léxico, Phrase permite editar y consultar el texto exacto en diccionarios,
mientras indica cómo preparar el análisis. Traducción Argos sigue siendo independiente.

### Diccionarios

Abre **Configuración → Diccionarios** e importa tus ZIP Yomitan. Activa y ordena
sus prioridades. Phrase consulta al abrir la tarjeta de una palabra; ambos
popups consultan una selección del editor automáticamente tras 180 ms o con
**Consultar selección**. El worker utiliza coincidencia exacta por lema, y si no
hay resultado prueba superficie. Sin recursos lingüísticos solo consulta el texto
completo exacto, sin inventar segmentación. Sin coincidencias/sin diccionarios
activos se muestra ese estado. Tras cambiar activación/prioridad, vuelve a consultar.

## Atajos y lanzadores independientes

En **Integraciones** selecciona **Acción**: Capturar y copiar, Translator, OCR Phrase
o Abrir ventana principal. Un único bloque **Atajo de teclado** ofrece Guardar y
Desactivar; cada acción mantiene combinación/estado independientes. El atajo
anterior de capturar/reconocer permanece en Detalles → Compatibilidad, sin migrarlo.
El estado distingue preferencia guardada de registro efectivo en X11.

**Script y acceso directo** reúne Crear script, Copiar comando y Crear acceso
directo. Muestra la ubicación y Abrir carpeta tras generar; Copiar ruta es secundario.
Comando completo y perfil XDG quedan en Detalles. La ayuda de KDE/StreamController
está en Cómo configurarlo. [Guía única y comprobación](INTEGRATIONS.md).
Los scripts existentes requieren confirmación para sobrescribir; el lanzador y los
enlaces están protegidos. Ningún archivo cambia al alternar acciones.

No se cambian botones, atajos KDE ni inicio automático. La configuración de KDE
permite arrancar Next cerrado; el registro interno solo funciona mientras reside.

## Validación y prueba manual

Evidencia estructurada: [popups.json](evidence/popups.json). El análisis real se
instaló **sin red**, con artefactos de caché que coinciden con los hashes públicos,
en un entorno nuevo propio. Se probó tokenización/lecturas con texto sintético,
reutilización del PID y un popup Phrase real con diccionarios sintéticos importados.
La copia nueva de fuentes, sin `.venv-phrase` ni modelos, arrancó con HOME/XDG
nuevos y mostró preparación comprensible. Usó el intérprete Qt propio existente
como herramienta de prueba; no es una instalación completa en otra máquina.

Las pruebas Qt son **offscreen**. La elección propietario/cliente se prueba con
broker inyectado, locks entre procesos y sockets Unix heredados. El intento de
QLocalServer por nombre sigue bloqueado con `Unknown error 1` en este entorno.
Los `.desktop` se validaron y ejecutaron con Gio del sistema contra un lanzador
sintético y rutas con espacios, comillas, dólar, `%` y barra inversa; esto no
acredita el menú KDE ni el botón físico. Los atajos usan backend X11 inyectado,
no un registro real en el escritorio. Las señales repetidas se probaron también
con ambos popups y workers reales, sin callbacks sobre objetos destruidos ni
workers vivos al salir. La causa exacta del segfault antiguo sigue sin core
reproducible; no se le atribuye un componente nuevo.

Prueba manual en KDE/X11, después de cerrar una vez la instancia anterior:

1. Copia una frase japonesa y ejecuta `launch --translator`. Solo debe aparecer
   Translator. Sin modelos, comprueba el aviso; con un `.argosmodel` importado,
   revisa la ruta visible y la traducción. Edita rápido y cambia ruta: solo debe
   aparecer el resultado de la versión actual. Copiar texto no copia definiciones.
2. Ejecuta `launch --phrase` desde otra terminal. Con las lecturas preparadas,
   verifica frase/furigana, listado de palabras y consulta de una palabra. Sin
   diccionarios activos debe indicarlo; con un término ausente, indicar sin
   coincidencias. Edita y cancela/Esc durante el trabajo; no debe aparecer una
   respuesta anterior ni alterarse el portapapeles.
3. Vacía el portapapeles y repite ambos comandos: deben abrir editores vacíos.
   Pulsa varias veces: debe mantenerse una ventana por acción. Cierra el popup;
   la instancia debe seguir disponible. Abre `launch` para configurar.
4. Asigna combinaciones distintas a las tres acciones, reinicia Next y verifica
   persistencia. Prueba duplicar una combinación y una ocupada por KDE: debe
   informar el conflicto. Desactiva una y comprueba que las otras siguen activas.
5. Genera tres scripts/accesos en una ruta con espacios; rehúsa primero una
   sobrescritura. Asígnalos por separado en KDE/StreamController y prueba con
   Next abierto y cerrado. Captura-copia debe seguir copiando sin abrir popups.
