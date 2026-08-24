# Operación

## Alarmas configuradas

| Alarma | Métrica | Umbral | Acción |
|---|---|---|---|
| `workshops-api-5xx-<env>` | `AWS/ApiGateway 5XXError` | ≥5 en 5 min | Notifica `AlarmsTopic` (email) |
| `workshops-crud-errors-<env>` | `AWS/Lambda Errors` (WorkshopsFunction) | ≥3 en 5 min | Notifica `AlarmsTopic` |
| `workshops-registration-errors-<env>` | `AWS/Lambda Errors` (RegistrationFunction) | ≥3 en 5 min | Notifica `AlarmsTopic` |
| `workshops-ddb-throttles-<env>` | `AWS/DynamoDB ThrottledRequests` | ≥1 en 5 min | Notifica `AlarmsTopic` |
| `workshops-notifications-dlq-<env>` | `AWS/SQS ApproximateNumberOfMessagesVisible` | ≥1 en 5 min | Notifica `AlarmsTopic` — indica notificaciones fallidas tras 3 reintentos |

Todas envían a `AlarmsTopic` (SNS), suscrito al `AlertEmail` configurado en el deploy.
Ver el dashboard en `DashboardUrl` (output del stack) para TPS, latencia P95, errores y consumo de capacidad de DynamoDB.

## Runbooks

### 1. Alarma `workshops-api-5xx-<env>`

1. Abrir CloudWatch Logs → `/aws/apigateway/workshops-<env>` (access logs) para identificar qué ruta falla.
2. Revisar logs de la Lambda correspondiente (`/aws/lambda/workshops-crud-<env>` o `workshops-registration-<env>`) con X-Ray habilitado — buscar el `requestId` correlacionado.
3. Si es un error de permisos IAM o de config (no de código), verificar el rol de ejecución de la función en la consola de Lambda.
4. Si es un bug de código, revertir al commit anterior (`git checkout <sha> -- backend/` → `sam build && sam deploy`) mientras se corrige.

### 2. Alarma `workshops-ddb-throttles-<env>`

DynamoDB está en modo on-demand (`PAY_PER_REQUEST`), así que un throttle sostenido normalmente indica un patrón de acceso muy concentrado (hot partition) más que falta de capacidad.

1. Revisar CloudWatch → métricas de `WorkshopsTable` por índice (`GSI1`/`GSI2`) para ver cuál está saturado.
2. Si es `GSI1` (`WORKSHOP#ALL`): es una partición única por diseño (listado global). Si el tráfico de lectura crece mucho, considerar cachear `GET /workshops` en CloudFront (ya tiene `CachingOptimized` policy) o añadir sharding de la PK del GSI.
3. Confirmar que no hay un loop de reintentos en algún cliente (revisar `ApiAccessLogGroup`).

### 3. Alarma `workshops-notifications-dlq-<env>`

1. Inspeccionar mensajes en la cola: `aws sqs receive-message --queue-url <NotificationsDLQ-url>`.
2. Cada mensaje es un evento de EventBridge que falló 3 veces contra `NotificationFunction`. Revisar `/aws/lambda/workshops-notify-<env>` en el mismo rango de tiempo.
3. Causas comunes: el tópico SNS no existe/fue borrado, o el email de suscripción no fue confirmado (`SubscriptionArn` en estado `PendingConfirmation`).
4. Tras corregir la causa, reprocesar manualmente el mensaje (`aws sqs send-message` reinyectándolo al bus, o invocar la Lambda directamente con el payload de la DLQ) y luego purgar el mensaje de la DLQ.

### 4. La API responde 403 en rutas de escritura para un usuario que debería ser admin

1. Verificar que el usuario esté en el grupo `admin`: `aws cognito-idp admin-list-groups-for-user --user-pool-id <id> --username <email>`.
2. Si no está, añadirlo: `aws cognito-idp admin-add-user-to-group --user-pool-id <id> --username <email> --group-name admin`.
3. **Importante**: el usuario debe volver a iniciar sesión para obtener un nuevo ID token con el claim `cognito:groups` actualizado — los tokens ya emitidos no se refrescan automáticamente con el nuevo grupo.

### 5. Recordatorios (24h) no llegan

1. Revisar que `ReminderSchedule` (EventBridge Scheduler) esté `ENABLED`: `aws scheduler get-schedule --name workshops-reminder-check-<env>`.
2. Revisar logs de `/aws/lambda/workshops-scheduler-<env>` — el handler reporta `workshopsChecked` y `remindersSent` en su return value (visible en CloudWatch Logs Insights).
3. Confirmar que el taller tiene `status: scheduled` (los cancelados se excluyen) y que hay registros (`REG#USER#...`) asociados.

## Backup / Restore (DynamoDB)

La tabla tiene **Point-in-Time Recovery (PITR)** habilitado desde el template (`PointInTimeRecoverySpecification: Enabled`), lo que permite restaurar a cualquier segundo de los últimos 35 días.

### Restaurar a un punto en el tiempo

```bash
aws dynamodb restore-table-to-point-in-time \
  --source-table-name workshops-dev \
  --target-table-name workshops-dev-restored \
  --restore-date-time 2026-08-20T12:00:00Z
```

Esto crea una **tabla nueva** (no sobrescribe la original). Para promoverla:

1. Verificar los datos en `workshops-dev-restored`.
2. Actualizar `TABLE_NAME` en las Lambdas (o renombrar tablas) — recomendado hacerlo vía un cambio de parámetro en el stack, no manualmente, para que quede versionado.

### Backup on-demand (snapshot manual, independiente de PITR)

```bash
aws dynamodb create-backup \
  --table-name workshops-dev \
  --backup-name workshops-dev-manual-$(date +%Y%m%d)
```

Restaurar desde un backup on-demand:

```bash
aws dynamodb restore-table-from-backup \
  --target-table-name workshops-dev-restored \
  --backup-arn <BackupArn>
```

### Exportar a S3 (para análisis o migración)

```bash
aws dynamodb export-table-to-point-in-time \
  --table-arn <WorkshopsTable-arn> \
  --s3-bucket <bucket-de-analitica> \
  --export-format DYNAMODB_JSON
```

## Logs

| Recurso | Log group |
|---|---|
| API Gateway access logs | `/aws/apigateway/workshops-<env>` |
| Lambda workshops CRUD | `/aws/lambda/workshops-crud-<env>` |
| Lambda registrations | `/aws/lambda/workshops-registration-<env>` |
| Lambda notifications | `/aws/lambda/workshops-notify-<env>` |
| Lambda scheduler | `/aws/lambda/workshops-scheduler-<env>` |

Retención configurada vía parámetro `LogRetentionDays` (default 30 días) — aplica solo al log group de acceso de la API; los log groups de Lambda usan la retención por defecto de CloudWatch (indefinida) salvo que se ajuste manualmente.

## Seguridad operativa — CORS en producción

En `dev`, `AllowOrigin` está en `'*'` para facilitar pruebas. Antes de promover a `prod`, restringir en `template.yaml`:

```yaml
Cors:
  AllowOrigin: "'https://<dominio-cloudfront-o-custom>'"
```

y redesplegar.
