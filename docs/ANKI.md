> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# Anki: configuración guiada y revisión antes de enviar

Implementación local del diseño [cb5d115](ANKI-DESIGN.md), 2026-10-21.
La validación con Anki/AnkiConnect reales sigue pendiente. La configuración de
temas, fuentes, colores y vista previa se implementa en el trabajo posterior de
[Apariencia](APPEARANCE.md).

Abre **Anki** en la ventana principal. La guía empieza con instalación oficial de
Anki y preparación de AnkiConnect, sin instalar software ni cambiar perfiles.
**Comprobar conexión** pide acceso y consulta versión, mazos y tipos del perfil
abierto; no crea notas. Elige explícitamente mazo y tipo, y asigna las fuentes a
sus campos reales. Puedes combinar varios bloques con rótulos. Guardar conserva
configuración y firma de campos, sin crear una nota de prueba. Cancelar conserva
la configuración guardada. Dirección local y clave están en Opciones avanzadas;
la clave solo vive en memoria durante la sesión.

**Agregar a Anki** en Translator u OCR Phrase captura una instantánea editable del
editor, selección o token elegido y resultados vigentes. Sin selección/token,
propone Frase. Si falta configuración, conserva el borrador mientras la preparas;
**Volver a la previsualización** permite recuperarlo. Cerrar el compositor lo
oculta y conserva la edición durante esta sesión. Salir de Next descarta el texto
del borrador, que nunca se guarda automáticamente en disco.

Los campos finales se editan como texto literal: HTML escrito por el usuario se
escapa, no se ejecuta. La vista muestra contenido, no las plantillas/CSS de Anki.
Traducción y definiciones requieren inclusión explícita. Las entradas de
diccionario se eligen, conservando título y revisión; no se reconsultan al enviar.
Las lecturas de tokens se identifican como léxicas, no como lecturas verificadas.
Cambiar bloques no reemplaza los campos editados: **Aplicar fuentes incluidas**
es una acción explícita que vuelve a componerlos. Un cambio de destino exige
adoptar y revisar el nuevo mapeo. Sin recursos se puede escribir Texto manual.
OCR original/corrección no se atribuyen a un popup por igualdad de textos.
Acentos, ejemplos tipados, audio, imagen, JLPT y gramática general no están
habilitados como fuentes de exportación en esta entrega. El contenido de una
entrada puede contener ejemplos como parte de su definición literal, sin afirmar
emparejamiento tipado. Los tipos cloze se rechazan; las plantillas condicionales
deben comprobarse en Anki y no se promete reproducción exacta.

Antes de enviar, confirma el perfil abierto y revisa destino y campos. Se
revalidan firma, mazo, plantillas y `canAddNotes`, solo con texto; después se hace
un único `addNote`, con `allowDuplicate: false`. La regla de duplicados de Anki
depende del tipo y primer campo, no de equivalencia semántica.

El registro `$XDG_STATE_HOME/naatik-next/anki-attempts/` contiene UUID, digest,
mazo/tipo, estado y posible ID; no texto de campos ni claves. Se escribe y
sincroniza antes de enviar. Un bloqueo del registro impide envíos equivalentes.
Los errores antes de `addNote` son rechazo sin envío; tras despachar `addNote`,
un error o respuesta inválida queda **Envío sin confirmar**. No se reenvía,
incluso tras reiniciar o cuando una búsqueda devuelve cero.

La recuperación exige comprobar conexión y confirmar el mismo perfil, busca solo
la etiqueta `naatik_tx_<uuid>`, consulta esos IDs y sus tarjetas y compara
contenido, tipo y mazo. Varias notas, cambios o cero coincidencias conservan la
incertidumbre. Nunca borra ni actualiza notas. Ni URL ni nombres de mazo prueban
identidad del perfil: la comprobación humana sigue siendo necesaria.

## Validación reproducible

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest tests.test_anki tests.test_popups -q
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -q
QT_QPA_PLATFORM=offscreen .venv/bin/python -m tools.anki_ui_review
```

[Informe y capturas sintéticas](evidence/anki-implementation/README.md).
Las pruebas usan HOME/XDG temporales; la prueba de HTTP abre únicamente un puerto
loopback efímero. Nunca solicita el puerto 8765 personal. En este sandbox el
listener está bloqueado: esa prueba se marca SKIP, no PASS.

## Pendiente: escritorio y Anki reales en una base separada

No hay ejecutable `anki` disponible en este entorno. Tampoco se descargó ni instaló
un complemento. El paquete actual debe verificarse desde la ficha oficial y el
origen del mantenedor antes de acreditar compatibilidad de una versión concreta.

Realiza el recorrido de la sección 8 de [ANKI-DESIGN.md](ANKI-DESIGN.md): base de
Anki independiente con `anki -b /ruta/de/prueba`, HOME/XDG de Next separados,
complemento instalado solo allí, sin sincronización, sin instancia personal activa
y puerto explícito de prueba distinto de 8765. Un perfil en la misma base no
separa complementos. La opción `-b` figura en el
[manual oficial](https://docs.ankiweb.net/manual/files).
Crea allí un mazo/tipo sintéticos y prueba ambos popups, cancelación, edición,
un envío, duplicado y recuperación. No abrir, copiar, exportar ni enumerar la
colección personal. No se acredita esta prueba por los resultados offscreen.
