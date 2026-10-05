# API pública y políticas de seguridad

Este documento resume cómo los comercios se integran con la API pública de Kuntur Pay y cuáles son las políticas de seguridad que el equipo de ingeniería debe respetar al construir y operar la plataforma.

## Autenticación

La API pública usa autenticación por claves de API. Cada comercio tiene dos tipos de claves:

- **Claves de prueba**: empiezan con el prefijo `kp_test_` y solo funcionan contra el entorno sandbox, donde no se mueve dinero real.
- **Claves productivas**: empiezan con el prefijo `kp_live_` y procesan pagos reales.

Las claves se envían en el encabezado HTTP `Authorization` con el esquema `Bearer`. Las claves productivas deben rotarse como máximo cada 90 días; el panel de comercios avisa por correo electrónico 15 días antes del vencimiento. Durante la rotación, la clave anterior y la nueva conviven durante 24 horas para que el comercio pueda actualizar sus sistemas sin cortes.

Si el sistema detecta una clave productiva publicada en un repositorio público de código, la revoca automáticamente en menos de 10 minutos y notifica al comercio.

## Límites de tráfico

El gateway aplica límites de tráfico por comercio usando el algoritmo de cubeta de tokens (token bucket) implementado sobre Redis:

- Plan Estándar: 100 solicitudes por minuto.
- Plan Avanzado: 1.000 solicitudes por minuto.
- Plan Corporativo: 5.000 solicitudes por minuto, ampliable a pedido.

Cuando un comercio supera su límite, la API responde con el código HTTP 429 e incluye el encabezado `Retry-After`, que indica cuántos segundos debe esperar antes de reintentar. Los endpoints de consulta de reportes tienen un límite separado de 10 solicitudes por minuto en todos los planes, porque son consultas costosas.

## Idempotencia

Todas las solicitudes que crean o modifican recursos aceptan el encabezado `Idempotency-Key`. Si un comercio envía dos solicitudes con la misma clave de idempotencia dentro de un período de 24 horas, la segunda solicitud no se procesa de nuevo: la API devuelve exactamente la misma respuesta que dio la primera vez. Esto evita cobros duplicados cuando hay cortes de red y el comercio reintenta.

## Webhooks

La plataforma notifica a los comercios los cambios de estado de sus pagos mediante webhooks. Cada webhook se firma con HMAC-SHA256 usando un secreto propio del comercio, y la firma se envía en el encabezado `Kuntur-Signature`. Los comercios deben verificar la firma y rechazar los webhooks con más de 5 minutos de antigüedad para evitar ataques de repetición.

Si el servidor del comercio no responde con un código 2xx en menos de 10 segundos, el webhook se reintenta con espera exponencial: a los 1, 5, 30 minutos, a las 2 horas y a las 12 horas. Después de 5 reintentos fallidos, el webhook se marca como fallido y queda visible en el panel de comercios, desde donde se puede reenviar manualmente durante 30 días.

## Protección de datos de tarjetas

Kuntur Pay está certificada como proveedor de servicios PCI DSS de nivel 1. Para mantener la certificación, los números de tarjeta completos nunca se almacenan en las bases de datos de los servicios. El servicio payments-core reemplaza cada número de tarjeta por un token apenas lo recibe, y el número real se guarda únicamente en una bóveda de tokenización aislada, con acceso restringido a un grupo de cuatro personas del equipo de seguridad.

El código de seguridad de la tarjeta (CVV) no se almacena nunca, ni siquiera cifrado, ni en la bóveda de tokenización. Se usa solo durante la autorización y se descarta inmediatamente después.

## Acceso a producción

Ningún ingeniero tiene acceso permanente a los servidores ni a las bases de datos de producción. El acceso se solicita a través de la herramienta interna de acceso temporal, indicando el motivo y el número de ticket o de incidente asociado. El acceso se concede por un máximo de 4 horas y todas las sesiones quedan grabadas.

El acceso de lectura a las bases de datos de producción requiere la aprobación del líder técnico del equipo. El acceso de escritura requiere además la aprobación de una persona del equipo de seguridad, salvo durante un incidente SEV1, en el que basta con la aprobación del comandante del incidente.

## Secretos

Las contraseñas, claves y certificados se guardan en HashiCorp Vault. Está prohibido guardar secretos en el código fuente, en variables de entorno definidas en los repositorios o en los archivos de configuración versionados. El pipeline de integración continua ejecuta un escáner de secretos en cada pull request y bloquea la integración si encuentra alguno.
