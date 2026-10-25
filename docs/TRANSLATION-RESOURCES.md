> Documento técnico/histórico. Para instalar esta copia, sigue [README](../README.md) desde la raíz. Las rutas históricas son ilustrativas; no se distribuyen los logs, capturas o muestras locales citados.

# Recursos y evidencia histórica de traducción

La guía de uso vigente está en [TRANSLATION-SETUP.md](TRANSLATION-SETUP.md).

## Japonés → español, origen y licencia

En el [índice oficial consultado el 2026-10-20](https://raw.githubusercontent.com/argosopentech/argospm-index/main/index.json)
se observó **ja→en 1.1** (Argos ≥1.1) y **en→es 1.0** (Argos ≥1.0), sin un modelo
directo ja→es. Por eso la propuesta correspondiente es **ja → en → es**, indicando
**inglés como idioma intermedio**. Next vuelve a consultar el catálogo cuando se
solicita; si aparece un directo compatible, lo ofrece. El filtro de versión no
sustituye la prueba real de carga/inferencia. En la revisión inicial no se acreditó la inferencia por el bloqueo de red.
La revisión del recorrido unificado sí comprobó inferencia con archivos locales,
sin acreditar una descarga nueva.

El catálogo es [MIT o CC0](https://github.com/argosopentech/argospm-index/blob/main/README.md).
Los registros observados no incluyen tamaño, hash ni licencia individual. La GUI
indica esta ausencia y enlaza la [declaración del mantenedor sobre binarios
MIT/CC0](https://github.com/argosopentech/argos-translate/issues/533). No hereda la
licencia del motor al modelo sin esa procedencia ni acredita términos de corpus
individuales. Si un catálogo futuro declara licencia, muestra el campo recibido.
No se distribuyen binarios, datos ni modelos en el repositorio.

El catálogo autenticado por HTTPS no publica SHA-256 por modelo: Next registra
el hash local del archivo recibido y del índice, origen y licencia declarada.
Comprueba ZIP/CRC, límites, extracción segura y luego carga/inferencia. **Ese hash
local no es una comparación con un hash oficial**. No se aceptan comandos o URLs
arbitrarios por IPC; la descarga selecciona claves del catálogo oficial guardado.

## Datos propios y uso offline

- Preferencias: `$XDG_CONFIG_HOME/naatik-next/settings.json`, rutas persistentes
  `translation_route` predeterminada; `translator_route` y `phrase_route`
  conservan las elecciones explícitas de cada popup.
- Modelos: `$XDG_DATA_HOME/naatik-next/argos/packages`.
- Catálogo y descargas/parciales: `$XDG_DATA_HOME/naatik-next/argos/`.
- Entorno opcional: `$XDG_DATA_HOME/naatik-next/argos/runtime`.
- Prueba reproducible con frase sintética fija: `argos/validation.json`; no guarda
  el texto privado del editor ni un historial de traducciones.

Con los recursos completos, abrir, traducir y comprobar rutas no consulta el
catálogo ni la red. Los modelos permanecen entre sesiones. Reintentar conserva
paquetes/descargas completos y recupera parciales; el entorno vuelve a instalar
las versiones fijadas si no se completó. La comprobación de imports de base y
del entorno usa la API de directorios privados de Next, sin crear preferencias
Argos globales ni descubrir otros proyectos.

La prueba usa:

> 私は毎日日本語を勉強しています。今日は図書館で本を読みます。

Después puede probarse otro texto completo en Translator y editar rápidamente.
El resultado de **日本 aislado** del modelo anterior sigue siendo una limitación
documentada: no se oculta con sustituciones, diccionarios ni reglas inventadas.


## Diagnósticos conservados

La primera revisión, la instalación sin entorno y los límites de red se conservan
en [la evidencia anterior](evidence/translation-setup/validation.json),
[perfil nuevo](evidence/translation-setup/fresh-profile.json) y
[HTTP 403](evidence/translation-setup/http403.json). HEAD puede fallar y dejar el
tamaño desconocido sin acreditar una descarga. Un error HTTP no identifica si
lo emite el proveedor o un intermediario. No se usan espejos ni se altera el agente
HTTP para ocultarlo. Importar archivos obtenidos explícitamente por el usuario
sigue disponible en Opciones avanzadas. No promete evitar restricciones de red.
