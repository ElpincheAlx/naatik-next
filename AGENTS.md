# Instrucciones de mantenimiento de Na’atik Next

Conservar el trabajo y los diagnósticos existentes salvo cambio explícitamente
solicitado. No modificar repositorios, entornos ni servicios antiguos.

Al integrar, actualizar o retirar software/modelos/datos/fuentes de terceros:

- Actualizar `docs/THIRD_PARTY_DEPENDENCIES.md` y su evidencia en el mismo cambio.
- Contrastar imports, declaraciones, lock y uso real; separar ejecución,
  herramientas, diagnóstico y opcionales pendientes. No convertir todo un entorno
  instalado en dependencias necesarias de Next.
- Registrar versión/origen, reproducción, licencia con fuente, distribución,
  avisos y hashes disponibles. No heredar la licencia del motor a sus recursos;
  indicar expresamente lo no verificado.
- No añadir ruedas, modelos, diccionarios o entornos a Git sin autorización explícita.
  No eliminar archivos de caché como parte de una auditoría de inventario.

## Instalación independiente (requisito permanente)

JapaneseMining y los paquetes de revisión son referencias funcionales, nunca
prerrequisitos ni fuentes automáticas de entornos, modelos, configuración o datos.
Los perfiles nuevos solo usan directorios propios XDG y entornos de Next.
Conservar rutas explícitamente guardadas por usuarios anteriores; no migrarlas ni
borrarlas en silencio. No descubrir ni reutilizar automáticamente otros proyectos.

Todo cambio de dependencias debe mantener instalación por versiones/hashes,
variante CPU sin CUDA obligatorio, preparación de modelos explícita, y evidencia
de HOME/XDG/venv aislados sin paquetes del usuario. Declarar separadamente gates
sin red, display o máquina/VM limpia; un test offscreen no valida captura global.
No escribir rutas personales en lanzadores versionados ni instalar fuentes/modelos
sin origen/licencia e integridad. No borrar datos del usuario al desinstalar.
El alcance futuro confirmado (ambos popups, análisis automático, Anki, móvil/
historial) sigue pendiente y no autoriza introducir dependencias del sistema viejo.
