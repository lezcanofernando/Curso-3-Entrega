# Arquitectura de la plataforma Kuntur Pay

Kuntur Pay es una plataforma de procesamiento de pagos para comercios medianos de América Latina. Este documento describe la arquitectura técnica vigente desde la versión 4.0 de la plataforma, lanzada en marzo de 2025, y es de lectura obligatoria para todo el equipo de ingeniería durante su primera semana.

## Visión general

La plataforma está organizada como un conjunto de microservicios que se comunican mediante dos mecanismos: llamadas síncronas gRPC para las operaciones que necesitan una respuesta inmediata, y eventos asíncronos publicados en Apache Kafka para todo lo demás. La regla general del equipo es simple: si el usuario final está esperando la respuesta en pantalla, se usa gRPC; si no, se publica un evento.

Existen siete servicios principales:

- **gateway**: punto de entrada único para la API pública. Valida las credenciales, aplica los límites de tráfico y enruta cada solicitud al servicio correspondiente.
- **payments-core**: procesa las autorizaciones y capturas de pago. Es el servicio más crítico de la plataforma y el único que se comunica directamente con las redes de tarjetas.
- **ledger**: mantiene el libro contable de doble entrada. Cada movimiento de dinero genera al menos dos asientos, uno de débito y uno de crédito, que deben sumar cero.
- **risk-engine**: evalúa el riesgo de fraude de cada transacción en menos de 80 milisegundos. Combina reglas fijas definidas por el equipo de riesgo con un modelo de gradient boosting que se reentrena todas las semanas.
- **merchant-service**: administra los datos de los comercios, sus cuentas bancarias de liquidación y sus configuraciones.
- **notifier**: envía los webhooks a los comercios y los correos electrónicos transaccionales.
- **settlement**: calcula y ejecuta las liquidaciones diarias a las cuentas bancarias de los comercios.

## Lenguajes y tecnologías

Los servicios payments-core, ledger y gateway están escritos en Go 1.22. El servicio risk-engine está escrito en Python 3.12 y utiliza FastAPI para exponer su interfaz interna. Los servicios merchant-service, notifier y settlement están escritos en Kotlin sobre el framework Ktor.

La base de datos principal es PostgreSQL 16. Cada servicio tiene su propia base de datos lógica y está prohibido que un servicio lea o escriba directamente en la base de datos de otro servicio. Si un servicio necesita datos de otro, debe pedirlos por gRPC o consumir los eventos que el otro publica.

Redis 7 se usa como caché y para implementar los límites de tráfico del gateway. Nunca se debe usar Redis como fuente de verdad: todo dato almacenado en Redis tiene que poder reconstruirse a partir de PostgreSQL.

Apache Kafka funciona como bus de eventos. Los tópicos siguen la convención `dominio.entidad.evento`, por ejemplo `payments.charge.captured` o `merchants.account.updated`. Los eventos se serializan en formato Protobuf y sus esquemas se registran en el Schema Registry interno antes de poder publicarse.

## Regiones y disponibilidad

La plataforma opera en dos regiones activas: una ubicada en São Paulo, que es la región primaria, y otra en Santiago de Chile, que es la región secundaria. Ambas regiones reciben tráfico de producción en todo momento. El balanceador global distribuye las solicitudes de manera que la región de São Paulo atiende aproximadamente el 70 % del tráfico y Santiago el 30 % restante.

La base de datos de payments-core usa replicación síncrona entre ambas regiones, de modo que ninguna transacción confirmada puede perderse si una región completa falla. El resto de las bases de datos usa replicación asíncrona con un retraso objetivo menor a 5 segundos.

El objetivo de disponibilidad (SLO) de la API de pagos es del 99,95 % mensual, lo que equivale a unos 21 minutos de indisponibilidad permitida por mes. Para el resto de las APIs, como la de consulta de comercios o la de reportes, el objetivo es del 99,9 % mensual.

## Observabilidad

Todos los servicios deben emitir tres tipos de señales: métricas en formato Prometheus, trazas distribuidas con OpenTelemetry y logs estructurados en formato JSON. Los logs nunca deben contener números de tarjeta completos, códigos de seguridad ni contraseñas; cuando se necesita registrar una tarjeta se muestran únicamente los últimos cuatro dígitos.

Los tableros operativos se construyen en Grafana. Cada servicio tiene un tablero estándar con cuatro paneles obligatorios, conocidos internamente como las "cuatro señales doradas": latencia, tráfico, tasa de errores y saturación.

Las trazas se conservan durante 7 días, las métricas durante 13 meses y los logs durante 30 días en almacenamiento caliente. Pasado ese plazo, los logs se archivan comprimidos y se conservan durante 5 años por requisitos regulatorios del sector financiero.

## Decisiones de arquitectura

Cualquier cambio que afecte a más de un servicio, que agregue una tecnología nueva o que modifique un contrato gRPC existente requiere un documento de decisión de arquitectura, llamado ADR (Architecture Decision Record). El ADR se presenta en la reunión de arquitectura de los jueves y necesita la aprobación de al menos dos integrantes del comité de arquitectura, que está formado por cinco ingenieros principales.

Los ADR aprobados se guardan en el repositorio `kuntur-adr` y nunca se borran. Si una decisión queda obsoleta, se escribe un ADR nuevo que la reemplaza y se marca el anterior con el estado "reemplazado".
