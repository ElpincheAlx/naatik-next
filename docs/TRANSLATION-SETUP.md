> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# Preparar traducción

1. Abre **Traducción** en la ventana principal. Desde el popup sin recursos,
   **Preparar traducción** abre directamente esa sección.
2. Elige **Origen** y **Destino** y pulsa **Preparar traducción**. Next detecta lo
   instalado, consulta el catálogo si faltan modelos y presenta la ruta y los
   componentes necesarios. Si hay un idioma intermedio, lo explica antes de
   confirmar. Muestra tamaños disponibles; los desconocidos se indican como tales.
3. Confirma la propuesta. Next prepara el motor CPU que falte, instala los modelos
   necesarios y comprueba inferencia real. **Cancelar** interrumpe el recorrido;
   **Reparar** permite reintentar un error. Solo después de inferencia aparece
   **Listo**. Abre **Acciones → Translator** para volver al popup y traducir.

No hay que ejecutar detección, instalación o prueba por separado. Sin modelos no
se indica Listo; rechazar la confirmación no descarga componentes. Consultar el
catálogo y los tamaños es parte del recorrido iniciado por el usuario. Los modelos
existentes se conservan; una ruta instalada se prueba sin consultar la red.
La ruta preparada explícitamente se guarda como predeterminada. Una elección
previa de ruta en un popup se conserva; puedes cambiarla en su selector visible.
Las rutas se actualizan tras importar/instalar y al detectar cambios en los modelos
mientras el popup está visible, sin pulsar Revisar modelos.

**Opciones avanzadas** agrupa **Importar modelo local**, el inventario instalado y
el diagnóstico. La importación pide confirmación y después comprueba las rutas.
No acredita por sí sola la licencia del archivo ni prepara automáticamente un
motor ausente. Si falta el motor, continúa con el botón principal.

Los perfiles nuevos usan únicamente los directorios de Next y su runtime CPU;
no descubren Argos global, JapaneseMining ni cachés personales. No se distribuyen
modelos en Git. Versiones, licencias, directorios y diagnósticos históricos:
[recursos](TRANSLATION-RESOURCES.md), [inventario](THIRD_PARTY_DEPENDENCIES.md).
Para instalar la aplicación sin entorno Python preparado, usa `./launch` y su
asistente inicial: [requisitos e instalación](INSTALLATION.md).

## Comprobar en la sesión gráfica

Desde una terminal de tu escritorio, para el perfil habitual:

```bash
cd ${PROJECT_ROOT}
./launch
```

Cierra previamente cualquier Next que siga ejecutando el código anterior.
Abre la pestaña **Traducción** y sigue los tres pasos. Para comprobar sin recursos
ni cambios en tu perfil habitual, abre una terminal nueva y ejecuta:

```bash
cd ${PROJECT_ROOT}
review_profile=$(mktemp -d /tmp/HISTORICAL-REVIEW)
export XAUTHORITY="${XAUTHORITY:-$HOME/.Xauthority}"
export HOME="$review_profile/home"
export XDG_CONFIG_HOME="$review_profile/config"
export XDG_DATA_HOME="$review_profile/data"
export XDG_CACHE_HOME="$review_profile/cache"
export XDG_STATE_HOME="$review_profile/state"
mkdir -p "$HOME" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_CACHE_HOME" "$XDG_STATE_HOME"
./launch --translator
```

Se reutiliza el entorno propio de esta copia de Next; HOME y los datos están
vacíos. No es una instalación de runtime desde cero. Se conserva el acceso de la
sesión gráfica y no se modifica `XDG_RUNTIME_DIR`.

- En el popup, pulsa **Preparar traducción**: debe abrir **Traducción**.
- Elige japonés/español, pulsa el botón principal y revisa componentes/ruta.
  Rechaza primero: no debe instalar nada ni mostrar Listo. Repite y confirma
  solo si quieres descargar. Durante la operación pulsa **Cancelar** y reintenta.
- Con una conexión interrumpida, debe aparecer **Requiere atención** y **Reparar**.
  Restablece la conexión y reintenta. Un parcial no debe aparecer como Listo.
- Alternativamente importa tus `.argosmodel` desde **Opciones avanzadas**.
  Tras carga e inferencia, debe aparecer **Listo** con la ruta y una salida real.
- Abre **Acciones → Translator**, elige una ruta instalada y escribe una frase.
  Cierra y vuelve a abrir: debe conservar recursos y selección, sin descargas.

Para una copia completa sin entorno/cachés previos, ejecuta
`.venv/bin/python tools/translation_setup_check.py`; el asistente gráfico pide las
confirmaciones necesarias. Esa validación con descarga queda pendiente en esta
revisión.

## Evidencia de esta revisión

[Informe y capturas](evidence/translation-journey/README.md).
Las pruebas de confirmación, instalación encadenada y fallo de red son simuladas.
Las capturas Qt son **offscreen**, porque no se pudo conectar al display `:0`.
La importación local, la carga e inferencia CPU y el regreso al popup se probaron
realmente con HOME/XDG aislados y el venv existente de Next. No hubo descargas,
instalación nueva del runtime, captura global ni prueba en una VM limpia.
