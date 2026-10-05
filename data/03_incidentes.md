# Gestión de incidentes y guardias

Este documento describe cómo Kuntur Pay clasifica, atiende y analiza los incidentes de producción, y cómo se organizan las guardias del equipo de ingeniería.

## Niveles de severidad

Todo incidente se clasifica en uno de cuatro niveles de severidad apenas se detecta. Si hay dudas entre dos niveles, se elige siempre el más grave; la severidad se puede bajar después, pero declarar un incidente de menos retrasa la respuesta.

- **SEV1**: la API de pagos está caída o rechaza más del 10 % de las transacciones, o hay pérdida o exposición de datos de tarjetas. El tiempo máximo de respuesta es de 5 minutos.
- **SEV2**: degradación importante, por ejemplo latencias del percentil 99 por encima de 2 segundos, o una funcionalidad crítica caída para un grupo de comercios, como las liquidaciones o los webhooks. El tiempo máximo de respuesta es de 15 minutos.
- **SEV3**: problema que afecta a una funcionalidad secundaria y tiene una alternativa, como los reportes del panel de comercios. El tiempo máximo de respuesta es de 4 horas hábiles.
- **SEV4**: problema menor sin impacto en los comercios, como un error en una herramienta interna. Se atiende dentro de los 5 días hábiles.

## Roles durante un incidente

En los incidentes SEV1 y SEV2 se asignan tres roles, que deben estar ocupados por personas distintas:

- **Comandante del incidente**: coordina la respuesta, toma las decisiones y define prioridades. No debe ponerse a investigar ni a escribir código, porque su función es mantener la visión global.
- **Responsable de comunicaciones**: actualiza la página de estado pública cada 30 minutos y mantiene informado al equipo de atención a comercios.
- **Investigadores**: uno o más ingenieros que diagnostican el problema y aplican la mitigación.

La primera prioridad durante un incidente es siempre mitigar el impacto, no encontrar la causa raíz. Si revertir el último despliegue puede detener el problema, se revierte primero y se investiga después.

Toda la coordinación ocurre en un canal de chat dedicado que se crea automáticamente con el nombre `#inc-AAAAMMDD-descripcion`. Las conversaciones por mensaje privado no están permitidas durante un incidente, porque la información tiene que quedar registrada para el análisis posterior.

## Guardias (on-call)

Cada equipo dueño de un servicio mantiene una rotación de guardia. Las guardias duran una semana completa, empiezan los martes a las 10:00 y terminan el martes siguiente a la misma hora. Se eligió el martes para que el traspaso no coincida con el fin de semana ni con los lunes, que suelen tener mucha actividad.

Cada guardia tiene un ingeniero primario y uno secundario. Si el primario no reconoce una alerta en 5 minutos, la alerta escala automáticamente al secundario. Si el secundario tampoco la reconoce en otros 5 minutos, escala al líder técnico del equipo.

Para poder entrar en la rotación de guardia, un ingeniero debe tener al menos tres meses en la empresa, haber completado la capacitación de respuesta a incidentes y haber participado como observador en al menos dos guardias completas.

Ningún ingeniero puede hacer más de una guardia cada cuatro semanas. Después de una noche en la que haya tenido que atender una alerta entre la medianoche y las 06:00, el ingeniero de guardia puede empezar su jornada siguiente a partir del mediodía.

Las alertas que despiertan a alguien deben ser accionables. Si una alerta suena y no requiere ninguna acción, el ingeniero de guardia debe abrir un ticket para ajustarla o eliminarla antes de que termine su semana.

## Análisis posterior al incidente (postmortem)

Todo incidente SEV1 o SEV2 requiere un postmortem escrito, que debe publicarse dentro de los 5 días hábiles posteriores a la resolución. El postmortem lo redacta el comandante del incidente con ayuda de los investigadores.

Los postmortems siguen una cultura sin culpables (blameless): se analizan los sistemas y los procesos que permitieron el error, nunca a las personas. Está prohibido escribir nombres propios en la sección de causas.

Cada postmortem debe incluir: una línea de tiempo detallada, el impacto medido en cantidad de transacciones afectadas y en minutos de indisponibilidad, la causa raíz, los factores que contribuyeron, lo que funcionó bien durante la respuesta y una lista de acciones correctivas. Cada acción correctiva tiene un responsable y una fecha límite, y se registra como ticket con la etiqueta `postmortem`.

Los postmortems se presentan en la revisión mensual de incidentes, que se realiza el primer miércoles de cada mes y a la que asiste todo el equipo de ingeniería.
