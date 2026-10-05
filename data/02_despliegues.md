# Proceso de despliegue a producción

Este documento define cómo se lleva un cambio desde el repositorio hasta producción en Kuntur Pay. El proceso aplica a todos los servicios sin excepción, incluidos los cambios de configuración y las migraciones de base de datos.

## Flujo de ramas y revisión de código

El equipo trabaja con desarrollo basado en tronco (trunk-based development). La rama principal se llama `main` y siempre debe estar en condiciones de desplegarse. Las ramas de trabajo deben tener una vida corta: si una rama lleva más de tres días sin integrarse a `main`, el equipo debe dividir el cambio en partes más pequeñas.

Todo cambio llega a `main` mediante un pull request. Cada pull request necesita la aprobación de al menos un revisor del equipo dueño del servicio. Si el cambio toca payments-core o ledger, se necesitan dos aprobaciones, y una de ellas debe ser de un ingeniero senior.

Antes de poder integrarse, el pull request debe pasar el pipeline de integración continua, que ejecuta en este orden: el análisis estático del código, las pruebas unitarias, las pruebas de integración contra bases de datos efímeras y el escaneo de dependencias en busca de vulnerabilidades conocidas. La cobertura mínima de pruebas exigida es del 80 % para el código nuevo.

## Entornos

Existen tres entornos:

- **dev**: se despliega automáticamente con cada integración a `main`. Puede romperse sin consecuencias.
- **staging**: replica la configuración de producción con datos sintéticos. Allí se ejecutan las pruebas de extremo a extremo y las pruebas de carga.
- **producción**: el entorno real, con datos y dinero de los comercios.

Un cambio solo puede llegar a producción si estuvo al menos 2 horas en staging sin generar alertas.

## Despliegue canario

Los despliegues a producción son graduales y usan la estrategia canaria. Las etapas son las siguientes:

1. La nueva versión recibe el 5 % del tráfico durante 30 minutos.
2. Si las métricas son normales, pasa al 25 % durante otros 30 minutos.
3. Luego pasa al 50 % durante 15 minutos.
4. Finalmente recibe el 100 % del tráfico.

En cada etapa, el sistema de despliegue compara automáticamente la versión nueva con la versión anterior. Si la tasa de errores de la versión nueva supera en más de un 0,5 % a la de la versión anterior, o si la latencia del percentil 99 aumenta más de un 20 %, el despliegue se revierte automáticamente sin intervención humana.

El despliegue completo de un servicio, desde el 5 % hasta el 100 %, demora como mínimo 75 minutos. No está permitido saltear etapas, salvo en el caso de una corrección urgente aprobada por el ingeniero de guardia y por un integrante del comité de arquitectura.

## Ventanas de congelamiento

Hay períodos en los que no se permiten despliegues a producción, llamados ventanas de congelamiento:

- Todos los viernes desde las 16:00 hasta el lunes a las 09:00, hora de Buenos Aires.
- Los días feriados nacionales de Brasil, Chile y Argentina.
- Desde el 20 de noviembre hasta el 2 de diciembre, por el Black Friday y el Cyber Monday, que son los días de mayor volumen de transacciones del año.
- Desde el 20 de diciembre hasta el 3 de enero, por las fiestas de fin de año.

Durante una ventana de congelamiento solo se pueden desplegar correcciones de incidentes de severidad SEV1 o SEV2, y siempre con la aprobación explícita del director de ingeniería.

## Migraciones de base de datos

Las migraciones de base de datos se ejecutan con la herramienta Flyway y deben ser compatibles hacia atrás. Esto significa que la versión anterior del servicio tiene que poder seguir funcionando con el esquema nuevo, porque durante el despliegue canario conviven ambas versiones.

Para eliminar una columna se usa el patrón de expansión y contracción, que tiene tres pasos separados en despliegues distintos: primero se deja de escribir en la columna, luego se deja de leerla y recién en un tercer despliegue se elimina. Nunca se renombra una columna directamente: se crea una columna nueva, se copian los datos y se elimina la anterior siguiendo el mismo patrón.

Las migraciones que bloquean una tabla con más de un millón de filas deben ejecutarse fuera del horario pico, entre las 02:00 y las 05:00, hora de Buenos Aires.

## Reversión

Cualquier ingeniero puede revertir un despliegue en cualquier momento, sin pedir permiso, si sospecha que está causando un problema. La reversión se hace desde la consola de despliegues con el comando `kuntur rollback <servicio>` y tarda menos de 3 minutos en completarse. El equipo considera que revertir de más es mucho más barato que dejar un problema en producción, y por eso ninguna reversión preventiva se considera un error.
