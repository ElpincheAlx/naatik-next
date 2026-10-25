# Revisión del recorrido de Traducción — 2026-10-20

Resultado: **186 pruebas aprobadas** con
`QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -q`.
[Salida completa](tests.txt). La última comprobación dirigida de popups/backend
pasó con **39 pruebas** después de los ajustes del mensaje, la huella de
modelos y la selección de idiomas sin catálogo ([salida](focused-tests.txt)).

Las pruebas automatizadas usan perfiles HOME/XDG temporales. Cubren catálogo,
ruta intermedia, tamaños, rechazo de consentimiento sin instalar, preparación
encadenada del runtime y modelos, cancelación y resultados tardíos, error y
reintento, recursos instalados sin descarga, conservación de selección/modelos,
retorno al popup y actualización de rutas tras cambios/eliminación. El backend
rechaza descargar un componente antes instalado que desapareció después de la
propuesta: necesita nueva confirmación.

El driver visual además **importó archivos locales y ejecutó inferencia CPU real**
con HOME/XDG aislados, utilizando el venv existente de esta copia de Next. No usó
modelos del perfil normal, recursos de otros proyectos ni descargas. El control de
inferencias de preparación bloqueó conexiones Python. [Resultado, hashes y versiones](evidence.json).
La salida comprobada fue «Estoy estudiando japonés todos los días.» en `ja → en → es`;
esto acredita ejecución, no exactitud o conservación de todas las frases. Se
conserva la limitación de calidad del modelo, sin reemplazos de diccionario.

La conexión al escritorio `:0` falló (`could not connect to display`). Todas las
capturas son **renders Qt offscreen**, no fotografías de una sesión gráfica.
No se acreditan descarga real, instalación nueva del runtime, máquina/VM limpia,
captura global, accesibilidad o comportamiento del gestor de ventanas KDE.

| Captura | Qué acredita |
|---|---|
| Sin configurar (referencia histórica no distribuida) | Detección real sin modelos en perfil aislado |
| Popup sin modelos (referencia histórica no distribuida) | Botón que abre la sección Traducción |
| Preparando (referencia histórica no distribuida) | Worker real iniciado, sin descarga |
| Propuesta (referencia histórica no distribuida) | Ruta intermedia y componentes con datos **simulados**, confirmación rechazada |
| Cancelado (referencia histórica no distribuida) | Cancelación del worker real de detección |
| Error recuperable (referencia histórica no distribuida) | Error **inyectado**, muestra Reparar |
| Listo (referencia histórica no distribuida) | Carga e inferencia CPU reales con archivos locales |
| Opciones avanzadas (referencia histórica no distribuida) | Inventario real importado y diagnóstico |
| Popup listo (referencia histórica no distribuida) | Traducción real en el popup después de preparar |

Reproducción visual automatizada, suministrando explícitamente tus propios archivos
locales (no descarga; crea otro perfil temporal; no modifica el perfil habitual):

```bash
cd ${PROJECT_ROOT}
QT_QPA_PLATFORM=offscreen .venv/bin/python tools/translation_journey_review.py \
  --model /ruta/al/modelo-ja-en.argosmodel \
  --model /ruta/al/modelo-en-es.argosmodel \
  --output /tmp/HISTORICAL-REVIEW
```

[Pasos exactos desde la sesión gráfica, perfil habitual y perfil vacío](../../TRANSLATION-SETUP.md#comprobar-en-la-sesión-gráfica).
La descarga y preparación completa desde cero requieren esa comprobación gráfica
con consentimiento del usuario y red disponible; no se marcan como PASS por las
pruebas simuladas.
