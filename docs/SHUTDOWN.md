> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# Cierre ordenado de Next

## Evidencia y alcance

Antes del cambio (`5688b4e`), una QApplication offscreen con Window y QProcess
reales, IPC simulado y un worker sintético que escribía stderr reprodujo dos
`KeyboardInterrupt` en `_stderr`, salida por señal (-2) y
`QProcess: Destroyed while process ... is still running`. No se utilizó el
observador X11. Esto demuestra una ruta de cierre incompleta; **no reproduce ni
explica por sí solo la violación de segmento comunicada**. No se obtuvo un core
consultable. No se atribuye el fallo nativo a Qt, OCR o Xlib sin esa evidencia.

El mismo caso tras el cambio sale con 130, sin traceback ni proceso activo
al destruir QProcess. La matriz automatizada añade ocho escenarios (cuatro etapas
por SIGINT/SIGTERM), con señales repetidas y mezcladas al grupo de terminal:
carga, selector, inferencia y reposo. Worker, herramienta descendiente y
observador son procesos reales; las etapas OCR y selector son sintéticas. La
herramienta ignora SIGTERM para ejercitar la escalada y la espera/recolección.
Un noveno escenario hace que el propio worker ignore SIGTERM para comprobar
KILL al grupo completo tras la espera acotada.
Se verifica que no quedan descendientes vivos, que se libera el broker y que
no aparecen callbacks sobre objetos borrados ni advertencias de QProcess.

Además se ejecutaron seis casos con el MangaOCR CPU y el snapshot explícitamente
configurados: SIGINT/SIGTERM repetidos durante preparación, inferencia real de
`examples/nihon.png` y reposo después de copiar. Se observó el evento de inicio de
inferencia antes de interrumpir, sin esperar a su resultado. Los seis salieron con
130/143, sin traceback ni worker vivo. Se empleó una región fija y broker
inyectados y Qt offscreen; no se afirma haber validado Spectacle interactivo,
socket por nombre, foco, pegado externo ni XQueryPointer contra el escritorio.
El muestreo Xlib se prueba además mediante respuestas de biblioteca inyectadas.
Los resultados estructurados están en [shutdown.json](evidence/shutdown.json).
Son comprobaciones de cierre, **no muestras de velocidad**.

Todos los subprocesos recibieron XDG_CONFIG_HOME/DATA_HOME/STATE_HOME/CACHE_HOME
temporales antes de importar módulos de Next. La comprobación real copió al
perfil aislado únicamente la selección OCR y sus rutas guardadas; no escribió
las preferencias originales. Se verificaron las huellas del archivo de ajustes
y del script no versionado antes/después. No se modificaron JapaneseMining ni
la copia de validación independiente.

## Cambios

- SIGINT/SIGTERM solo registran la primera señal y despiertan Qt por un pipe no
  bloqueante. El cierre ocurre en el hilo principal mediante QSocketNotifier;
  ninguna señal levanta KeyboardInterrupt dentro de un slot. Las señales
  siguientes no vuelven a cerrar ni interrumpen la destrucción nativa. Código de
  salida: 128 + primera señal (130/143).
- Antes de esperar procesos, se invalida la captura, las generaciones y los
  callbacks, se detienen los temporizadores y se bloquean señales de QProcess.
  La recepción de una señal también impide aceptar nuevos resultados mientras
  aún está pendiente el evento Qt de cierre. No se copia ni consulta OCR tardío.
- Cada worker Linux tiene una sesión/grupo propio; sus herramientas permanecen
  dentro del grupo supervisado. Se envía TERM a todos primero, se espera con un
  presupuesto común y se escala a KILL si hace falta. QProcess recoge al worker;
  los workers desenrollan sus `finally` para recoger herramientas. También se
  eliminan descendientes residuales de un worker fallido. No se mata el grupo de
  la terminal ni procesos de otras instancias.
- La escalada de cancelación usa un QTimer propiedad del supervisor, que se
  detiene en el cierre; no queda una lambda independiente con un QProcess borrado.
  Cada callback valida el proceso emisor. Un Task cerrado no puede reiniciarse
  accidentalmente desde un callback; cambiar el intérprete en una ventana viva
  lo reabre expresamente después de terminar el anterior.
- El observador de tiempos X11 ya no deja un hilo daemon en llamadas nativas al
  salir Python. Su subproceso termina por EOF, se espera y se escala si no
  responde. El supervisor también controla su grupo si el worker queda bloqueado.
  Esto elimina ese riesgo de ciclo de vida; no demuestra que causara el core.
- El cierre normal, la señal y `finally` comparten una operación idempotente.
  El bloqueo de instancia se libera después de terminar los workers.

Suite completa: **137 pruebas, OK**. La selección del último propietario en el
informe también se comprobó con eventos numéricos inyectados de dos instancias.

## Reproducir las pruebas aisladas

Desde la raíz del proyecto:

```bash
profile=$(mktemp -d /tmp/HISTORICAL-REVIEW)
XDG_CONFIG_HOME="$profile/config" XDG_DATA_HOME="$profile/data" \
XDG_STATE_HOME="$profile/state" XDG_CACHE_HOME="$profile/cache" \
QT_QPA_PLATFORM=offscreen PYTHONDONTWRITEBYTECODE=1 \
.venv/bin/python -m unittest tests.test_shutdown tests.test_processes tests.test_capture_latency -v
```

El perfil se establece en el entorno antes de arrancar Python. Esta orden prueba
señales reales y etapas inyectadas; no inicia el OCR neural real. La suite
completa usa el mismo aislamiento exterior con `-m unittest discover -v`.

Para medir sin cerrar el propietario: terminal A, con Next previamente cerrado,
`${PROJECT_ROOT}/launch --capture-copy --timings`; delimita la región y espera la
copia. Deja esa terminal ocupada. En terminal B ejecuta el mismo comando tres
veces, esperando cada copia antes del siguiente. Después ejecuta en B:

```bash
cd ${PROJECT_ROOT}
.venv/bin/python tools/capture_timings.py --last-process
```

Conserva el propietario durante la lectura y el pegado de prueba. Para terminar,
abre `${PROJECT_ROOT}/launch` y cierra su ventana. Ctrl+C/SIGTERM son ahora rutas
controladas de salida; durante una operación la invalidan y el informe la excluye.

## Aviso `QLocalSocket.abort()` al repetir capturas

Se comunicó `addMetaMethod: Cannot add dynamic method "abort()" ... No Wrapper
found`. El timeout del servidor conectaba directamente con `socket.abort`, y la
conexión dejaba de retenerse al empezar a responder, antes de desconectar. Se
elimina ese registro dinámico: ahora un `@Slot` del servidor atiende el timeout,
el socket y su temporizador permanecen retenidos hasta desconectar y la limpieza
es idempotente. Las conexiones que aún vacían su respuesta también cuentan en
el límite de conexiones y se abortan al cerrar. Si el handler cierra el servidor,
la respuesta ya no escribe en un socket descartado.

Regresión: cuarenta intercambios por socket Unix heredado, recolección Python y
DeferredDelete de Qt, timeout de trama parcial, cierre repetido y cierre desde
el handler; sin avisos de wrappers y sin conexiones/temporizadores retenidos.
Suite completa aislada: 137 pruebas OK. El aviso exacto del escritorio no se
reprodujo en este transporte de prueba; falta verificar esta corrección con el
socket por nombre y la instancia residente del escritorio. No se atribuye a
este aviso la violación de segmento anterior.

`--timing` se acepta actualmente como abreviatura de argparse; no se identifica
como origen del aviso. Usa la forma documentada `--timings`. Para aplicar esta
corrección debes cerrar una vez la instancia anterior (abre la GUI con `launch`
y ciérrala), y arrancar la nueva. Después deja la terminal propietaria ocupada
y solicita las otras capturas desde otra terminal o Stream Deck, sin Ctrl+C.


La extensión Translator/OCR Phrase conserva este supervisor y añade pruebas de
SIGINT/SIGTERM repetidos con los dos popups y sus workers reales. Se invalidan
sus revisiones/colas y se paran sus temporizadores antes del cierre común.
Evidencia actualizada de esa ampliación: [popups.json](evidence/popups.json).
No se vuelve a atribuir ni se da por reproducido el core original.

## Recuperación del propietario terminado inesperadamente

La revisión de [arranque](STARTUP.md) añade un supervisor Linux de biblioteca
estándar entre QProcess y el worker. Tiene sesión propia y termina/recoge el
grupo del worker al observar la muerte del GUI, incluso SIGKILL. Se reprodujo
el huérfano antes y su limpieza después con procesos reales y trabajo sintético.
No sustituye la prueba de OCR/escritorio; [evidencia y límites](evidence/startup/README.md).
