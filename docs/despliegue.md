# Despliegue

IaC: **AWS SAM**. Dos stacks CloudFormation por ambiente:

1. `workshops-waf-cloudfront-<env>` — WAFv2 WebACL para CloudFront (obligatorio en `us-east-1`).
2. `workshops-<env>` — todo el resto del backend (us-east-2) + frontend (S3/CloudFront).

## Requisitos previos

```bash
brew install aws-sam-cli
brew install python@3.12   # SAM empaqueta las Lambdas con este intérprete exacto
aws configure              # credenciales con permisos sobre los servicios usados
```

Permisos IAM necesarios en la cuenta de despliegue (mínimo, ver `arquitectura.md` para el detalle):
CloudFormation, S3, DynamoDB, Cognito, API Gateway, Lambda, EventBridge, SNS, SQS,
Scheduler, WAFv2, CloudFront, CloudWatch (Logs/Alarms/Dashboards), Budgets, IAM
(para crear los roles de ejecución de las Lambdas).

## 1. Desplegar el WAF de CloudFront (una vez por ambiente)

```bash
cd backend
sam deploy \
  --template-file waf-cloudfront.yaml \
  --stack-name workshops-waf-cloudfront-dev \
  --region us-east-1 \
  --parameter-overrides EnvName=dev \
  --resolve-s3 --capabilities CAPABILITY_IAM --no-confirm-changeset
```

Anota el `WebAclArn` del output — se usa en el paso 2.

## 2. Desplegar el stack principal

```bash
cd backend
sam build
sam deploy --config-env dev \
  --parameter-overrides \
    EnvName=dev \
    AlertEmail=tu-correo@ejemplo.com \
    ApiThrottleRateLimit=50 \
    ApiThrottleBurstLimit=100 \
    "CloudFrontWebAclArn=arn:aws:wafv2:us-east-1:<account>:global/webacl/workshops-cf-waf-dev/<id>"
```

O usando el script incluido (asume que ya tienes el WAF ARN guardado en tu shell):

```bash
./scripts/deploy-backend.sh dev
```

Para `prod`, repite ambos pasos con `EnvName=prod` y `--config-env prod`.

### Outputs relevantes

| Output | Uso |
|---|---|
| `ApiUrl` | Base URL de la API REST |
| `CloudFrontUrl` | URL pública del frontend (y proxy `/api/*`) |
| `UserPoolId` / `UserPoolClientId` | Config de Cognito para el frontend |
| `FrontendBucketName` | Bucket S3 donde se sube el build de Angular |
| `TableName` | Tabla DynamoDB |
| `DashboardUrl` | Dashboard de CloudWatch |

## 3. Crear el primer usuario admin

```bash
aws cognito-idp admin-create-user \
  --user-pool-id <UserPoolId> \
  --username admin@ejemplo.com \
  --user-attributes Name=email,Value=admin@ejemplo.com Name=email_verified,Value=true \
  --temporary-password 'Temporal1234!' \
  --message-action SUPPRESS

aws cognito-idp admin-add-user-to-group \
  --user-pool-id <UserPoolId> \
  --username admin@ejemplo.com \
  --group-name admin
```

El usuario deberá cambiar la contraseña temporal en su primer login (flujo `FORCE_CHANGE_PASSWORD` estándar de Cognito, gestionado por el SDK `amazon-cognito-identity-js` en el frontend).

## 4. Desplegar el frontend

El script lee los outputs del stack, genera `environment.prod.ts`, construye con Angular CLI y sincroniza a S3:

```bash
./scripts/deploy-frontend.sh dev
```

Equivalente manual:

```bash
cd frontend/workshops-web
npm ci
npx ng build --configuration production
aws s3 sync dist/workshops-web/browser s3://<FrontendBucketName> --delete
aws cloudfront create-invalidation --distribution-id <DistId> --paths "/*"
```

## 5. Smoke test

```bash
./scripts/smoke-test.sh dev
```

Verifica `GET /healthz` y `GET /workshops` contra la API desplegada.

## Pipeline CI/CD (GitHub Actions)

| Workflow | Trigger | Acción |
|---|---|---|
| `.github/workflows/ci.yml` | PR a `main`/`dev` | Tests backend (pytest), `sam validate --lint`, build+test frontend |
| `.github/workflows/deploy-dev.yml` | Push a `dev` | Tests → `sam deploy` a `workshops-dev` → smoke test → deploy frontend |
| `.github/workflows/deploy-prod.yml` | Tag `v*` | Igual que dev, pero con `environment: production` (aprobación manual en GitHub) |

**Secrets requeridos** en el repo de GitHub: `AWS_DEPLOY_ROLE_ARN` (rol OIDC, no llaves estáticas), `ALERT_EMAIL`.

**Aprobación manual de prod**: configurar en GitHub → Settings → Environments → `production` → "Required reviewers".

## Actualizar el stack (cambios posteriores)

```bash
cd backend
sam build
sam deploy --config-env dev   # reutiliza los parámetros guardados en samconfig.toml
```

Si cambian parámetros (p. ej. `AlertEmail`), pásalos explícitamente con `--parameter-overrides`.

## Rollback

CloudFormation hace rollback automático si el deploy falla. Para revertir un deploy exitoso pero problemático:

```bash
aws cloudformation cancel-update-stack --stack-name workshops-dev   # si aún está in-progress
# o, para volver a una versión anterior del código:
git checkout <commit-anterior> -- backend/
cd backend && sam build && sam deploy --config-env dev
```

## Eliminar el stack (cuidado: destructivo)

```bash
aws cloudformation delete-stack --stack-name workshops-dev --region us-east-2
aws cloudformation delete-stack --stack-name workshops-waf-cloudfront-dev --region us-east-1
```

DynamoDB tiene `PointInTimeRecoverySpecification` habilitado, pero **no** `DeletionPolicy: Retain` —
si necesitas conservar los datos, exporta la tabla (ver `operacion.md` → backup/restore) antes de borrar el stack.

## Limitación conocida: cambios que solo tocan la Lambda Layer

`AutoPublishAlias` en SAM calcula si debe publicar una nueva versión de una función
basándose en el hash del **código de la función**, no en el contenido de las layers que
referencia. Si modificas únicamente `backend/src/layers/common/` (sin tocar el código de
`app.py` de ninguna función), `sam deploy` actualiza la `LayerVersion` pero **no** publica
una nueva versión de las funciones ni mueve el alias `live` — el alias sigue apuntando a la
versión vieja, que referencia el ARN de la layer vieja, y `$LATEST` queda con la nueva.
Esto puede producir un `Runtime.ImportModuleError` en producción con un deploy que reportó éxito.

**Mitigación aplicada**: tras cualquier cambio que afecte solo a `src/layers/common/`,
forzar publicación y re-apuntar el alias manualmente:

```bash
for FN in workshops-crud-dev workshops-registration-dev; do
  aws lambda publish-version --function-name "$FN" --description "layer update"
  VERSION=$(aws lambda list-versions-by-function --function-name "$FN" \
    --query "Versions[-1].Version" --output text)
  aws lambda update-alias --function-name "$FN" --name live --function-version "$VERSION"
done
```

Alternativa más robusta a futuro: quitar `AutoPublishAlias`/aliases y que API Gateway
invoque siempre `$LATEST` (pierde el versionado explícito, pero evita este problema de raíz),
o incluir el hash de la layer como parte de un comentario/variable de entorno dummy en cada
función para forzar que SAM detecte el cambio también en el código de la función.

## Nota sobre blue/green (CodeDeploy)

El template incluye el patrón `AutoPublishAlias: live` en las funciones Lambda, pero **sin**
`DeploymentPreference` porque la cuenta de despliegue usada no tiene el servicio CodeDeploy
suscrito (`SubscriptionRequiredException`). Si tu cuenta sí lo tiene habilitado, puedes
reactivar el despliegue canary agregando de nuevo en `template.yaml`:

```yaml
DeploymentPreference:
  Type: Canary10Percent5Minutes
  Alarms:
    - !Ref WorkshopsFunctionErrorAlarm
```

en cada función bajo `AWS::Serverless::Function`.
