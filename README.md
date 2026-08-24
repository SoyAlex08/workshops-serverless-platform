# Workshops — Plataforma Serverless de Talleres

Aplicación web serverless en AWS para gestionar talleres de formación profesional.

## Arquitectura

- **Frontend**: Angular 21 (standalone) servido desde S3 privado detrás de CloudFront (OAC).
- **API**: API Gateway (REST) + Lambda (Python 3.12) + Cognito JWT Authorizer.
- **Datos**: DynamoDB single-table (`PK`/`SK` + GSI1 por fecha + GSI2 por categoría).
- **Auth**: Cognito User Pool con grupos `admin` / `student`.
- **Eventos**: EventBridge (`WORKSHOP_CREATED`, `STUDENT_REGISTERED`, `WORKSHOP_REMINDER`, `WORKSHOP_DELETED`) → Lambda de notificaciones → SNS. DLQ en SQS.
- **Recordatorios**: EventBridge Scheduler (cada 15 min) revisa talleres que inician en ~24h.
- **Seguridad**: WAF (CloudFront + API Gateway), IAM least-privilege via políticas SAM, S3 privados, throttling en API.
- **Observabilidad**: CloudWatch Logs/Alarms + X-Ray + Dashboard.
- **Costos**: AWS Budgets con alerta por email, tagging `Project=Workshops`/`Env=<dev|prod>`.

## Estructura

```
backend/          SAM app (template.yaml, handlers Python, capa común, tests, OpenAPI)
frontend/workshops-web/   Angular app
scripts/          Scripts de deploy y smoke test
.github/workflows/  CI/CD (GitHub Actions)
```

## Requisitos previos

- AWS CLI configurado con credenciales (`aws sts get-caller-identity`).
- AWS SAM CLI (`brew install aws-sam-cli`).
- Python 3.12 (`brew install python@3.12`) — SAM lo necesita para empaquetar las Lambdas.
- Node.js 22+ y Angular CLI para el frontend.

## Despliegue manual

```bash
# 1. Backend
./scripts/deploy-backend.sh dev      # o prod

# 2. Frontend (lee outputs del stack y los inyecta en environment.prod.ts)
./scripts/deploy-frontend.sh dev

# 3. Smoke test
./scripts/smoke-test.sh dev
```

En el primer `sam deploy --guided` para cada ambiente, define `AlertEmail` con un correo real
(usado para alarmas de CloudWatch y AWS Budgets) y confirma la creación del User Pool.

## Crear el primer usuario admin

```bash
aws cognito-idp admin-create-user \
  --user-pool-id <UserPoolId> \
  --username admin@example.com \
  --user-attributes Name=email,Value=admin@example.com Name=email_verified,Value=true \
  --temporary-password 'Temp1234!'

aws cognito-idp admin-add-user-to-group \
  --user-pool-id <UserPoolId> \
  --username admin@example.com \
  --group-name admin
```

## CI/CD

- **PR a `main`/`dev`**: `ci.yml` corre tests backend, `sam validate --lint`, y build+test del frontend.
- **Push a `dev`**: `deploy-dev.yml` construye y despliega backend + frontend a `dev`, con smoke test.
- **Tag `v*`**: `deploy-prod.yml` despliega a `prod`, con aprobación manual vía GitHub Environment `production`.

Secrets requeridos en GitHub: `AWS_DEPLOY_ROLE_ARN` (rol OIDC con permisos least-privilege), `ALERT_EMAIL`.

## Modelo de datos (DynamoDB)

| Item        | PK                  | SK                 |
|-------------|---------------------|--------------------|
| Taller      | `WORKSHOP#<id>`     | `META`             |
| Inscripción | `WORKSHOP#<id>`     | `REG#USER#<userId>`|

- `GSI1`: `GSI1PK=WORKSHOP#ALL`, `GSI1SK=startAt` → listado cronológico.
- `GSI2`: `GSI2PK=CATEGORY#<cat>`, `GSI2SK=startAt` → filtro por categoría.

## API

Ver contrato completo en [backend/openapi/openapi.yaml](backend/openapi/openapi.yaml).

| Método | Ruta | Auth |
|---|---|---|
| GET | `/workshops` | Público |
| GET | `/workshops/{id}` | Público |
| POST | `/workshops` | Admin |
| PUT | `/workshops/{id}` | Admin |
| DELETE | `/workshops/{id}` | Admin |
| POST | `/workshops/{id}/register` | Estudiante autenticado (idempotente) |
