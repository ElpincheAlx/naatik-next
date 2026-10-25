> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# Integraciones

Abre `${PROJECT_ROOT}/launch` y entra en la pestaña existente **Integraciones**.
Selecciona **Acción**: Capturar y copiar, Translator, OCR Phrase o Abrir ventana
principal. Los datos y los borradores de cada acción son independientes; cambiar
el selector no guarda, activa ni genera nada.

## Atajo de teclado

Pulsa una combinación con Ctrl, Alt o Meta en el campo y elige **Guardar**.
**Desactivar** libera el registro y conserva la combinación guardada para después.
Cada acción conserva su combinación y activación entre sesiones. Ninguna nueva
acción se activa automáticamente.

Lee el estado: **Registrado en X11** solo aparece cuando el backend acepta el
registro; una preferencia activada en disco no significa que esté registrado.
Conflictos o plataformas no compatibles aparecen como **No registrado**. Los
atajos internos requieren Next abierto o en la bandeja, KDE/X11 y Qt xcb. No están
implementados en Wayland u offscreen. Usar la misma combinación para dos acciones
de Next, incluido el atajo antiguo, se rechaza.

El atajo previo **capturar y reconocer** sigue en **Detalles → Compatibilidad**.
Conserva `capture_shortcut` y su activación, sin migrarlos a Capturar y copiar.
Su captura muestra imagen/resultado en la ventana principal; Capturar y copiar
conserva el recorrido de copia en segundo plano. Puedes editar o desactivar el
atajo previo desde ese mismo lugar. No hay controles de atajos en Preferencias.

## Script y acceso directo

- **Crear script…** pide una ubicación y genera un archivo ejecutable. Después
  muestra su ruta y **Abrir carpeta**; **Copiar ruta** es una acción secundaria.
- **Copiar comando** copia el comando completo escapado: si hay un script guardado,
  copia su invocación; si todavía no hay script, copia el lanzador con las variables
  XDG necesarias. Puedes pegarlo sin añadir comillas. El texto completo está en
  **Detalles**; allí también se ve el perfil para nuevos scripts/comandos directos.
- **Crear acceso directo…** genera un `.desktop` independiente para la acción;
  propone `$XDG_DATA_HOME/applications` y recuerda la ubicación elegida.

Script/acceso directo puede iniciar Next cerrado. Si Next está abierto, reutiliza
su instancia mediante IPC. Abrir ventana principal usa `launch --show`; los otros
lanzadores conservan `--capture-copy`, `--translator` y `--phrase`.

Se conservan rutas, archivos y perfil XDG existentes. Seleccionar una acción no
reescribe scripts. Cada sobrescritura pide confirmación; enlaces simbólicos y el
lanzador/acceso principal de Next están protegidos. Un archivo que aparezca entre
el diálogo y la escritura tampoco se reemplaza sin consentimiento.
Los scripts existentes conservan el perfil con el que se generaron; los nuevos
fijan config, datos, estado, caché y runtime de la GUI. No se migran perfiles ni se
buscan recursos de otros proyectos.

## Cómo configurarlo

Esta ayuda también está plegada dentro de **Cómo configurarlo** en Integraciones.

**KDE:** Preferencias del sistema → Teclado → Atajos. Crea una acción con el script
o acceso directo y asigna una combinación libre. Esa acción puede iniciar Next
cerrado. Evita registrar la misma combinación en KDE y dentro de Next.

**StreamController:** en el botón elegido añade **OS → Run Command**, pega
**Copiar comando**, activa **Detached/Separado** y deja la repetición automática en
**0**. Usa un botón por acción. Next no modifica botones, atajos KDE ni inicio
automático. Los detalles y diagnósticos previos se conservan en
[STREAM-DECK.md](STREAM-DECK.md) y [GLOBAL-HOTKEY.md](GLOBAL-HOTKEY.md).

## Comprobar en el escritorio

1. Cierra cualquier instancia que ejecute la versión anterior. Abre `./launch`
   desde `${PROJECT_ROOT}` y ve a Integraciones. Selecciona cada acción y comprueba
   que aparecen sus valores previos. Cambia un borrador, alterna acciones y vuelve:
   debe conservar el borrador sin guardarlo en disco.
2. Guarda una combinación libre en una acción. Comprueba el estado **Registrado
   en X11** y pulsa la combinación con otra aplicación enfocada. Prueba Guardar
   otra combinación, Desactivar y cerrar/reabrir para comprobar persistencia.
   Guardar con éxito no acredita por sí solo la activación global.
3. Intenta asignar la misma combinación a otra acción: debe rechazarla. Para
   comprobar un conflicto X11 real, usa el probe temporal siguiente; no hace
   falta cambiar atajos KDE ni ocupar una combinación ajena.
4. Crea scripts para varias acciones en rutas diferentes con espacios. Alterna
   acciones, copia sus comandos y ejecútalos desde otra carpeta. Comprueba también
   Next cerrado y abierto. Rechaza primero una sobrescritura: el archivo anterior
   debe conservarse. Repite con accesos `.desktop`.

Probe opcional desde una terminal KDE/X11: registra temporalmente
`Ctrl+Alt+Shift+F12`, intenta el mismo registro desde una segunda conexión para
comprobar conflicto y libera ambos. También prueba el registro Qt en un perfil
HOME/XDG temporal. No envía pulsaciones ni cambia configuraciones del escritorio:

```bash
cd ${PROJECT_ROOT}
QT_QPA_PLATFORM=xcb .venv/bin/python tools/integrations_review.py \
  --probe-x11 --output /tmp/HISTORICAL-REVIEW
```

Comprueba `evidence.json`: la prueba de registro y conflicto es distinta de una
pulsación global y del recorrido de captura. Si no puede abrir el display, no se
acredita el registro.

## Evidencia de esta revisión

[Capturas, resultado y límites](evidence/integrations/README.md). Las pruebas de
interfaz y conflictos con backend inyectado son offscreen. Se ejecutaron scripts y
accesos de prueba reales contra un lanzador sintético para comprobar argumentos,
escapado y perfil, sin cambiar KDE/StreamController. El intento real con libX11 no
pudo abrir `:0`; registro, conflicto real y activación global siguen sin validar
para el escritorio del usuario. La reorganización no resuelve ni acredita ese
fallo por sí sola.

Para distinguir cerrar, ocultar en bandeja y salir, y comprobar los cuatro
arranques desde cero, consulta [Arranque y salida](STARTUP.md). El registro del
atajo interno no acredita el arranque con Next cerrado.
