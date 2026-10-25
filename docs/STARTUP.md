> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# Arranque, reutilización y salida

Los atajos internos requieren Next ejecutándose. Un script, comando o acceso
puede iniciarlo cerrado. Para asignar una acción con Next cerrado usa **Integraciones
→ Acción → Copiar comando / Crear acceso directo…**, y las instrucciones de KDE
bajo **Cómo configurarlo**. Next no modifica KDE, StreamController ni el inicio automático.

## Qué significa cerrar

- Cerrar la ventana principal o **Acciones → Salir de Next** termina la aplicación,
  cancela workers y libera el canal y bloqueo propios.
- **Acciones → Ocultar en bandeja** conserva el proceso. Si no hay bandeja disponible,
  informa y mantiene la ventana visible. La bandeja ofrece abrir, acciones y salir.
- Cerrar Translator/Phrase conserva la instancia residente. Capturar y copiar
  también conserva al propietario del portapapeles después de copiar. No cierres
  ese proceso antes de pegar en otra aplicación.
- Ctrl+C y SIGTERM ejecutan cierre ordenado (130/143). SIGKILL no permite ese cierre;
  el supervisor Linux vigila la muerte del propietario y termina sus workers.

## Diagnóstico y correcciones

Se reprodujo una excepción por rutas IPC largas antes de interpretar la acción:
acababa en un diálogo modal sin diagnóstico de terminal, incluso en offscreen.
Ahora se determina primero la acción, se informa en stderr/log y, en escritorio,
en un diálogo. Offscreen no queda esperando un diálogo invisible. Las rutas largas
usan un transporte privado corto; configuración, modelos y perfil no se trasladan.

El endpoint dependía de XDG_RUNTIME_DIR: dos invocaciones del mismo perfil con
runtime diferente buscaban sockets diferentes. El propietario publica ahora un
localizador privado y atómico en el estado del perfil. Los clientes lo usan para
contactar al propietario. QLockFile sigue arbitrando la propiedad; no se borran
bloqueos vivos. Solo se retira un socket propio obsoleto después de comprobar que
no acepta conexiones. Archivos ajenos, enlaces o estado ambiguo producen error.
Los reintentos conservan el identificador para evitar repetir una petición.

Se reprodujo además un worker real QProcess superviviente al SIGKILL del GUI
(trabajo sintético). Un supervisor de biblioteca estándar Linux recoge la familia
del worker al morir el propietario. No importa motores ni configuración. Los
fallos/rechazos IPC dejan de parecer invocaciones exitosas.

Estos defectos están corregidos y cubiertos por pruebas, pero **el fallo completo
reportado no está acreditado como resuelto en escritorio**: el entorno de revisión
rechaza bind AF_UNIX con EPERM. Las cuatro entradas reales, scripts y accesos llegan
al perfil correcto y presentan ese error; no llegan a ejecutar la acción. No se
atribuye ese bloqueo ambiental al equipo del usuario. Ver [evidencia](evidence/startup/README.md).

## Prueba manual breve en sesión gráfica

Cierra una vez la versión anterior desde su ventana o bandeja. No borres locks ni
sockets. En una terminal gráfica prepara un perfil aislado **antes** de lanzar Python:

```bash
repo="$HOME/Naatik-next"
profile=$(mktemp -d /tmp/HISTORICAL-REVIEW)
export HOME="$profile/home"
export XDG_CONFIG_HOME="$profile/config" XDG_DATA_HOME="$profile/data"
export XDG_STATE_HOME="$profile/state" XDG_CACHE_HOME="$profile/cache"
mkdir -p "$HOME" "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_STATE_HOME" "$XDG_CACHE_HOME"
unset QT_QPA_PLATFORM NAATIK_SUPERVISED NAATIK_OWNER_PID
cd /
"$repo/launch"
```

Conserva DISPLAY/Wayland/DBus/XDG_RUNTIME_DIR de la sesión. No necesitas modelos
para comprobar apertura; prepara OCR/traducción explícitamente desde configuración
para comprobar inferencia/copia. No reutilices recursos personales automáticamente.

1. Cierra la principal. Ejecuta separadamente `"$repo/launch --translator"`,
   `"$repo/launch --phrase"` y `"$repo/launch --capture-copy"`, saliendo completamente
   entre casos mediante bandeja o abriendo la principal y cerrándola. Cada entrada
   debe mostrar solo su acción; si faltan recursos debe explicar su preparación.
2. Con Translator/Phrase abierto, cambia el texto del portapapeles en otra aplicación
   y repite su comando: debe leer el texto nuevo en el mismo popup. Repite desde
   otra terminal con las mismas variables del perfil. No debe abrir otra instancia.
3. Capturar y copiar: comprueba selector único, OCR y pegado externo; deja el proceso
   residente. Oculta la principal en bandeja, vuelve a abrirla y finalmente sal.
4. Desde Integraciones crea scripts y accesos para las cuatro acciones en una carpeta
   con espacios. Ejecútalos desde `/`, cerrada y abierta. Deben usar el perfil elegido.
   Rechaza una sobrescritura y verifica que conserva el archivo anterior.
5. Con Next cerrado lanza dos veces Translator simultáneamente desde terminales con
   ese perfil: un propietario y un popup. Dos peticiones distintas son legítimas;
   un reintento de la misma petición no debe repetir su acción.
6. En una invocación propietaria foreground pulsa Ctrl+C durante un worker activo;
   vuelve a lanzar. Repite enviando SIGTERM **al PID de ese perfil de prueba**.
   Para recuperación inesperada repite con SIGKILL: espera la limpieza del worker y
   vuelve a lanzar. Nunca mates procesos identificados solo por un nombre genérico.
7. Comprueba que no aparece QProcess destruido activo, que la invocación nueva abre
   y que el perfil normal y el script anterior permanecen intactos.

El script no versionado `naatik-next-capturar.sh` se conserva byte por byte. Usa la
acción antigua `--capture`, que abre el recorrido con resultado en la principal;
no equivale a `--capture-copy`. Para la acción nueva genera otro archivo desde
Integraciones sin sobrescribir el anterior. No se cambian sus rutas guardadas.

Automatización reproducible: `.venv/bin/python tools/startup_review.py --output
/tmp/HISTORICAL-REVIEW`. Usa HOME/XDG aislados antes de importar Next y la venv
existente; no valida una instalación limpia ni OCR real. Anki y Apariencia siguen pendientes.
