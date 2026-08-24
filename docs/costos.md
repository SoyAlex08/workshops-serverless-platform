# Costos

## Estimación mensual (uso bajo — entorno de bootcamp/dev, us-east-2)

Supuestos: ~1,000 requests/día a la API, ~50 talleres, ~500 usuarios registrados, tráfico de frontend bajo.

| Servicio | Costo estimado/mes | Notas |
|---|---|---|
| Lambda (4 funciones) | $0 – $1 | Dentro del free tier (1M requests + 400,000 GB-s gratis/mes) |
| API Gateway (REST) | $0 – $2 | $3.50/millón de requests tras el free tier del primer año |
| DynamoDB (on-demand) | $0 – $2 | Free tier: 25 GB almacenamiento + 25 WCU/RCU reservados; on-demand cobra por request tras eso |
| Cognito | $0 | Free hasta 10,000 MAU (monthly active users) |
| S3 (frontend + evidencias) | < $1 | Storage mínimo, GET requests baratos |
| CloudFront | $0 – $1 | Free tier: 1 TB de transferencia + 10M requests/mes (primer año) |
| WAF (2 WebACLs: API + CloudFront) | ~$10 | $5/mes por WebACL + $1/regla + $0.60/millón de requests evaluados — **no tiene free tier** |
| EventBridge | < $1 | $1/millón de eventos publicados; bus custom sin costo adicional |
| SNS | < $1 | Free tier: 1,000 emails/mes |
| SQS (DLQ) | ~$0 | Prácticamente vacía en operación normal |
| CloudWatch (Logs + Alarms + Dashboard) | $1 – $3 | 5 alarmas (~$0.10 c/u) + ingestión de logs (~$0.50/GB) + 1 dashboard ($3/mes tras los primeros 3 gratis) |
| EventBridge Scheduler | $0 | Free tier generoso, $1/millón de invocaciones |
| X-Ray | < $1 | Free tier: 100,000 trazas/mes |
| AWS Budgets | $0 | Las primeras 2 acciones de budget son gratis |
| **Total estimado (dev)** | **~$12 – $20/mes** | El WAF es el componente dominante en cargas bajas |

> Con tráfico real de producción (decenas de miles de requests/día), Lambda/API Gateway/DynamoDB crecen proporcionalmente pero siguen siendo marginales frente al costo fijo del WAF.

## Cómo bajar costos

1. **WAF es el mayor costo fijo en cargas bajas.** Si el entorno es solo para desarrollo/pruebas internas (sin exposición pública real), se puede desplegar sin los WebACLs (dejar `CloudFrontWebAclArn` vacío — ya soportado por el template — y quitar `ApiWebAclAssociation`/`ApiWebAcl` del stack) y reactivarlos solo en `prod`.
2. **CloudWatch Dashboard**: los primeros 3 dashboards por cuenta son gratis; si ya existen otros 3+ en la cuenta, este empieza a costar $3/mes — evaluar si vale la pena vs. ver las métricas directamente en las consolas de cada servicio.
3. **Retención de logs**: `LogRetentionDays` está en 30 días por defecto; bajarlo a 7-14 días en dev reduce el costo de ingestión/almacenamiento de CloudWatch Logs sin perder observabilidad reciente.
4. **DynamoDB on-demand vs. provisioned**: on-demand es más barato para tráfico bajo/impredecible (el caso de este módulo). Si el tráfico se vuelve estable y alto, evaluar cambiar a capacidad provisionada + auto-scaling, que puede ser más económico a partir de cierto volumen sostenido.
5. **CloudFront price class**: ya configurado en `PriceClass_100` (solo edge locations de US/Canada/Europa) en vez de `PriceClass_All`, evitando el costo de las regiones más caras (Asia/Sudamérica) — ajustar si el público real está fuera de esas regiones.
6. **X-Ray**: activo en `Active` tracing mode en ambos ambientes; se puede desactivar (`Tracing: PassThrough`) en dev si no se está depurando activamente, ya que el volumen de trazas no es el cuello de botella pero sigue sumando marginalmente.
7. **EventBridge Scheduler cada 15 min**: es prácticamente gratis, pero si se quisiera reducir aún más la huella, correr cada 30-60 min sigue cumpliendo la ventana de tolerancia de recordatorio de 24h (`WINDOW_TOLERANCE_SECONDS` en `scheduler/app.py` debe ajustarse en consecuencia).

## Gobernanza de costos ya implementada

- **Tagging obligatorio**: todos los recursos llevan `Project=Workshops` y `Env=<dev|prod>` (vía `Globals.Function.Tags`, `Globals.Api.PropagateTags`, y tags explícitos en S3/DynamoDB/SNS/SQS/CloudFront).
- **AWS Budgets**: presupuesto mensual de $50 USD (`MonthlyBudget`, filtrado por tag `Project=Workshops`) con dos alertas:
  - Email cuando el gasto **real** supera el 80% del presupuesto.
  - Email cuando el gasto **proyectado** (forecast) supera el 100%.
- Para ajustar el límite o los umbrales, editar `MonthlyBudget` en `backend/template.yaml` (`BudgetLimit.Amount`, `Threshold`).

## Cómo verificar el gasto real

```bash
aws ce get-cost-and-usage \
  --time-period Start=$(date -v-30d +%Y-%m-%d),End=$(date +%Y-%m-%d) \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --filter '{"Tags":{"Key":"Project","Values":["Workshops"]}}'
```

O en consola: **AWS Cost Explorer** → filtrar por tag `Project = Workshops`.
