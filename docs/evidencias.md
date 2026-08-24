# Evidencias de despliegue — `workshops-dev` (us-east-2 / us-east-1)

Todas las evidencias de esta página fueron verificadas contra la cuenta AWS real
`590251390369` el 2026-08-24. Los comandos usados son reproducibles — cualquiera con
acceso a la cuenta puede volver a ejecutarlos para confirmar el estado actual.

## 1. CloudFront

```bash
$ aws cloudfront get-distribution --id E2HTY33SY7LJSP \
    --query "Distribution.{Id:Id,Status:Status,DomainName:DomainName,WebACLId:DistributionConfig.WebACLId}"
```

```json
{
    "Id": "E2HTY33SY7LJSP",
    "Status": "Deployed",
    "DomainName": "d2n2d0u48cj4r6.cloudfront.net",
    "WebACLId": "arn:aws:wafv2:us-east-1:590251390369:global/webacl/workshops-cf-waf-dev/35a9b5db-d464-4417-814e-299ca9dca832"
}
```

Frontend accesible públicamente:

```bash
$ curl -sI https://d2n2d0u48cj4r6.cloudfront.net/
HTTP/2 200
content-type: text/html
server: AmazonS3
x-cache: Miss from cloudfront
```

**URL pública**: <https://d2n2d0u48cj4r6.cloudfront.net>

## 2. WAF

### WAF regional (delante de API Gateway)

```bash
$ aws wafv2 list-web-acls --scope REGIONAL --region us-east-2
```

```json
{
    "WebACLs": [{
        "Name": "workshops-api-waf-dev",
        "Id": "a5beb753-e3b0-4977-80ab-42a83902ab16",
        "ARN": "arn:aws:wafv2:us-east-2:590251390369:regional/webacl/workshops-api-waf-dev/a5beb753-e3b0-4977-80ab-42a83902ab16"
    }]
}
```

Reglas activas: `RateLimitRule` (2000 req/5min por IP), `AWSManagedRulesCommonRuleSet`, `AWSManagedRulesSQLiRuleSet`.

### WAF de CloudFront (stack separado en us-east-1)

```bash
$ aws wafv2 list-web-acls --scope CLOUDFRONT --region us-east-1
```

```json
{
    "WebACLs": [{
        "Name": "workshops-cf-waf-dev",
        "Id": "35a9b5db-d464-4417-814e-299ca9dca832",
        "ARN": "arn:aws:wafv2:us-east-1:590251390369:global/webacl/workshops-cf-waf-dev/35a9b5db-d464-4417-814e-299ca9dca832"
    }]
}
```

Confirmado asociado a la distribución CloudFront (ver sección 1, campo `WebACLId`).

## 3. API Gateway

```bash
$ aws apigateway get-rest-apis --query "items[?name=='workshops-api-dev']"
```

```json
[{ "id": "jbd7ribj4i", "name": "workshops-api-dev", "createdDate": "2026-08-24T10:02:38-05:00" }]
```

Stage `dev` con X-Ray y access logs activos:

```bash
$ aws apigateway get-stages --rest-api-id jbd7ribj4i --query "item[?stageName=='dev']"
```

```json
[{
    "stageName": "dev",
    "tracingEnabled": true,
    "accessLogSetting": {
        "destinationArn": "arn:aws:logs:us-east-2:590251390369:log-group:/aws/apigateway/workshops-dev"
    }
}]
```

**API URL**: `https://jbd7ribj4i.execute-api.us-east-2.amazonaws.com/dev/`

## 4. Pruebas funcionales end-to-end (reales, contra la API desplegada)

```bash
$ curl -s https://jbd7ribj4i.execute-api.us-east-2.amazonaws.com/dev/healthz
{"status": "ok"}

$ curl -s -X POST .../workshops -H "Authorization: <admin-id-token>" -d '{...}'
HTTP 201 — taller creado: id=74f4217f-faa6-4865-a017-836693945f87

$ curl -s -X POST .../workshops/74f4217f.../register -H "Authorization: <student-id-token>"
HTTP 201 — {"workshopId": "74f4217f...", "userId": "616b6560...", "registeredAt": 1787587056}

$ curl -s -X POST .../workshops/74f4217f.../register -H "Authorization: <mismo-student-token>"
HTTP 409 — {"title": "Conflict", "detail": "Already registered for this workshop"}

$ curl -s -X POST .../workshops -H "Content-Type: application/json" -d '{"name":"test"}'   # sin token
HTTP 401
```

Confirma: rutas públicas accesibles sin auth, rutas admin protegidas, idempotencia de registro funcionando (segundo intento del mismo usuario → 409, no duplica).

## 5. Logs y trazas (CloudWatch + X-Ray)

Ejecución exitosa de `NotificationFunction` disparada por el evento `STUDENT_REGISTERED`:

```
2026-08-24T15:57:38 START RequestId: f4b0fd07-0be5-42f9-8e9c-e27c86f25244 Version: $LATEST
2026-08-24T15:57:38 END RequestId: f4b0fd07-0be5-42f9-8e9c-e27c86f25244
2026-08-24T15:57:38 REPORT ... Duration: 170.84 ms ... Status: (sin error)
XRAY TraceId: 1-6a8c69ef-2570cc2b3e4d14e3294a6c5a Sampled: true
```

## 6. Alarmas CloudWatch

```bash
$ aws cloudwatch describe-alarms --alarm-name-prefix workshops --query "MetricAlarms[].{Name:AlarmName,State:StateValue}"
```

| Alarma | Estado |
|---|---|
| `workshops-api-5xx-dev` | OK |
| `workshops-crud-errors-dev` | OK |
| `workshops-registration-errors-dev` | OK |
| `workshops-ddb-throttles-dev` | OK |
| `workshops-notifications-dlq-dev` | OK |

## 7. Dashboard CloudWatch

```bash
$ aws cloudwatch get-dashboard --dashboard-name workshops-dev --query "DashboardName"
"workshops-dev"
```

Métrica real capturada (`AWS/ApiGateway Count`, últimos 60 min de pruebas):

```json
[
  {"Timestamp": "2026-08-24T10:28:00-05:00", "Sum": 6.0},
  {"Timestamp": "2026-08-24T10:33:00-05:00", "Sum": 5.0},
  {"Timestamp": "2026-08-24T10:48:00-05:00", "Sum": 2.0},
  {"Timestamp": "2026-08-24T10:53:00-05:00", "Sum": 1.0}
]
```

**URL del dashboard**: `https://us-east-2.console.aws.amazon.com/cloudwatch/home?region=us-east-2#dashboards:name=workshops-dev`

## 8. AWS Budgets

```bash
$ aws budgets describe-budgets --account-id 590251390369 --query "Budgets[].{Name:BudgetName,Limit:BudgetLimit.Amount}"
```

```json
[{ "Name": "workshops-monthly-budget-dev", "Limit": "50.0" }]
```

Presupuesto de $50 USD/mes, filtrado por tag `Project=Workshops`, con alertas al 80% real y 100% proyectado configuradas al correo de contacto.

## 9. DynamoDB

```bash
$ aws dynamodb describe-table --table-name workshops-dev --query "Table.{Status:TableStatus,Billing:BillingModeSummary.BillingMode}"
{"Status": "ACTIVE", "Billing": "PAY_PER_REQUEST"}
```

## 10. Cognito

```bash
$ aws cognito-idp list-groups --user-pool-id us-east-2_nk3yNDaK0
```

Grupos `admin` y `student` creados. Usuario admin de prueba y usuario estudiante de prueba creados y verificados con flujo de login SRP real (vía `pycognito`), confirmando `cognito:groups: ["admin"]` presente en el ID token del admin.

## 11. EventBridge

```bash
$ aws events list-rules --event-bus-name workshops-bus-dev
```

```json
{
  "Rules": [{
    "Name": "workshops-notify-dev",
    "EventPattern": "{\"detail-type\":[\"WORKSHOP_CREATED\",\"STUDENT_REGISTERED\",\"WORKSHOP_REMINDER\",\"WORKSHOP_DELETED\"],\"source\":[\"workshops.api\"]}",
    "State": "ENABLED"
  }]
}
```

## Bugs reales encontrados y corregidos durante el despliegue

Documentados en detalle en [`operacion.md`](./operacion.md) y [`despliegue.md`](./despliegue.md):

1. **Estructura de la Lambda Layer** — el código fuente tenía un nivel de directorio `python/` de más dentro de `src/layers/common/`, que SAM duplicaba al construir, dejando `common` inaccesible (`No module named 'common'`). Corregido moviendo `common/` a la raíz de `ContentUri`.
2. **`FacadeSegmentMutationException` en X-Ray** — el bloque `except` de nivel superior en los routers (`workshops/app.py`, `registrations/app.py`) llamaba `tracer.put_annotation()` fuera de un contexto de tracer válido, enmascarando el error real bajo un 502 genérico. Corregido eliminando esa llamada.
3. **`Decimal` no serializable en eventos** — `common/events.py` usaba `json.dumps()` sin encoder para publicar a EventBridge, y los valores numéricos leídos de DynamoDB (`startAt`) llegan como `Decimal` vía boto3. Corregido reutilizando `DecimalEncoder` ya existente en `responses.py`.
4. **CodeDeploy no disponible en la cuenta** — ver decisión documentada en `arquitectura.md` (sección "Sin blue/green").
5. **WAF de CloudFront requiere us-east-1** — resuelto con un stack CloudFormation separado (`waf-cloudfront.yaml`).
6. **API Gateway requiere un rol de CloudWatch a nivel de cuenta** para habilitar access logs — agregado `AWS::ApiGateway::Account` + rol IAM dedicado.

Ninguno de estos bugs es cosmético: los tres primeros bloqueaban completamente las rutas
correspondientes (`/healthz`, `/workshops`, `/workshops/{id}/register`) en producción real
pese a que `sam deploy` reportaba éxito — quedan documentados como parte de la evidencia del
proceso de puesta en marcha, no solo el resultado final.
