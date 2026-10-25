> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# Apariencia

La sección **Apariencia** configura la ventana principal, los diálogos de Next,
Translator y OCR Phrase. No requiere instalar ni descargar fuentes o temas.

- **Sistema**, **Claro** y **Oscuro**. Sistema toma los colores de la paleta de Qt
  y atiende sus cambios durante la sesión; la integración concreta con KDE depende
  de lo que comunique el entorno Qt.
- Fuente de interfaz y fuente de lectura independientes, con tamaños en puntos.
  **Del sistema** usa la familia predeterminada. Las listas muestran fuentes
  instaladas; si falta una familia guardada se utiliza la del sistema y se avisa.
  Qt conserva su fallback para caracteres que una fuente no incluya.
- Colores de fondo, paneles/campos, texto, texto secundario, acento, bordes y
  selección. Cada color puede volver al valor del tema con **Del tema**.
  Cambiar de tema restablece los colores personalizados del borrador.
- Vista previa local con texto japonés y español, campos, acciones y estado
  deshabilitado. Se puede seleccionar texto de muestra para ver el resaltado.
  La muestra no reconoce, traduce, consulta diccionarios ni envía notas.

Los controles cambian únicamente la muestra hasta pulsar **Guardar y aplicar**.
Ese botón guarda en las preferencias XDG del perfil de Next y actualiza la
interfaz y los popups ya abiertos; los nuevos usan la misma configuración.
No modifica texto, selección, resultados, borradores de Anki ni revisiones del
análisis. La configuración vuelve a aplicarse al iniciar Next, también en modo
popup. No modifica el tema del escritorio ni las preferencias de Anki.

**Cancelar cambios** vuelve a la última configuración guardada. **Restablecer
valores** carga Sistema, fuentes del sistema, interfaz de 10 pt, lectura de 18 pt
y colores sin personalizar en la muestra; todavía requiere guardar para aplicarse.
Cambiar de pestaña conserva el borrador. Salir sin guardar lo descarta.
Si falla la escritura de preferencias, conserva el borrador y la apariencia activa.

Se muestra aviso cuando el contraste entre texto/fondo o texto secundario/panel
es inferior a 4,5:1; no se reemplazan los colores elegidos automáticamente. El
texto sobre acento o selección usa un color claro u oscuro según contraste.
Las fuentes de lectura se aplican a editores, traducción, lecturas y diccionario;
se conservan jerarquías de tamaño en los popups. Los títulos mantienen su jerarquía.
El contenido enriquecido de diccionarios puede conservar estilos propios: esta
configuración no reescribe sus datos ni plantillas de terceros.

## Validación

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest tests.test_appearance -q
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -q
QT_QPA_PLATFORM=offscreen .venv/bin/python -m tools.appearance_review
```

Las pruebas usan HOME/XDG temporales. Cubren muestra aislada, cancelar,
restablecer, persistencia/reapertura, ambos popups, texto/revisiones intactos,
fuentes ausentes, colores inválidos, contraste y fallo al guardar.
[Capturas sintéticas y resultados](evidence/appearance/README.md).

La revisión gráfica es offscreen. Sigue pendiente comprobar en KDE real:
abrir Apariencia, cambiar tema/fuentes/colores, cancelar, guardar, abrir ambos
popups, seleccionar texto y reiniciar. Revisar también escalado de pantalla,
selector de color/fuentes y notificación del cambio de paleta del sistema.
No se acredita ese recorrido por las capturas ni por pruebas simuladas.
