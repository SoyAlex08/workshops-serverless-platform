# API — Workshops

Contrato completo en [`backend/openapi/openapi.yaml`](../backend/openapi/openapi.yaml) (OpenAPI 3.0).
Colección Postman en [`docs/postman/workshops-api.postman_collection.json`](./postman/workshops-api.postman_collection.json).

**Swagger UI navegable** (sin instalar nada): <https://claude.ai/code/artifact/3b43702e-0ae7-46c5-9dd8-1f19a05c0def>

Base URL (dev): `https://jbd7ribj4i.execute-api.us-east-2.amazonaws.com/dev/`
También accesible vía CloudFront: `https://d2n2d0u48cj4r6.cloudfront.net/api/*`

## Autenticación

Las rutas protegidas requieren el header `Authorization: <idToken>` con el **ID token** de Cognito (no el access token), ya que los handlers leen `cognito:groups` desde `requestContext.authorizer.claims`.

Para obtener un token de prueba:

```bash
aws cognito-idp initiate-auth \
  --client-id <UserPoolClientId> \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters USERNAME=admin@example.com,PASSWORD='TuPassword123!'
```

> Nota: `ALLOW_USER_PASSWORD_AUTH` no está habilitado en el User Pool Client (solo `ALLOW_USER_SRP_AUTH` y `ALLOW_REFRESH_TOKEN_AUTH`, más seguro para clientes web). Para pruebas por CLI, usa el SDK de Amplify/Cognito Identity JS (como hace el frontend) o habilita temporalmente `ALLOW_ADMIN_USER_PASSWORD_AUTH` y usa `admin-initiate-auth`.

## Endpoints

### `GET /workshops` — público

Lista talleres, paginado.

**Query params**: `category` (opcional), `limit` (default 20, máx 100), `nextToken` (opaco, base64 de `LastEvaluatedKey`).

```bash
curl "$API_URL/workshops?category=devops&limit=10"
```

```json
{
  "items": [
    {
      "id": "b3f1...",
      "name": "Taller de Terraform",
      "category": "devops",
      "location": "Panamá, sede central",
      "startAt": 1798000000,
      "endAt": 1798007200,
      "status": "scheduled",
      "capacity": 25
    }
  ],
  "nextToken": null
}
```

### `GET /workshops/{id}` — público

```bash
curl "$API_URL/workshops/b3f1..."
```

`404` con `problem+json` si no existe.

### `POST /workshops` — admin

```bash
curl -X POST "$API_URL/workshops" \
  -H "Authorization: $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Taller de Terraform",
    "description": "Introducción a IaC",
    "category": "devops",
    "location": "Panamá, sede central",
    "startAt": 1798000000,
    "endAt": 1798007200,
    "capacity": 25
  }'
```

Respuestas: `201` con el taller creado · `400` validación (`errors: [...]`) · `403` si no es admin.

### `PUT /workshops/{id}` — admin

Actualización parcial (solo se envían los campos a cambiar).

```bash
curl -X PUT "$API_URL/workshops/b3f1..." \
  -H "Authorization: $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "cancelled"}'
```

### `DELETE /workshops/{id}` — admin

```bash
curl -X DELETE "$API_URL/workshops/b3f1..." -H "Authorization: $ID_TOKEN"
```

`204` sin cuerpo · `404` si no existe.

### `POST /workshops/{id}/register` — estudiante autenticado

Idempotente: un segundo intento del mismo usuario devuelve `409 Conflict` (condición `attribute_not_exists` en DynamoDB), no crea duplicados.

```bash
curl -X POST "$API_URL/workshops/b3f1.../register" -H "Authorization: $ID_TOKEN"
```

Respuestas: `201` inscripción creada · `401` sin JWT válido · `404` taller no existe · `409` ya inscrito o taller cancelado.

### `GET /healthz` — público, sin auth

Usado por el smoke test post-deploy (`scripts/smoke-test.sh`).

```json
{"status": "ok"}
```

## Formato de errores

Todos los errores siguen [RFC 7807 (`problem+json`)](https://www.rfc-editor.org/rfc/rfc7807):

```json
{
  "type": "about:blank",
  "title": "Bad Request",
  "status": 400,
  "detail": "Validation failed",
  "errors": ["'name' is required", "'capacity' must be a positive integer"]
}
```

## Swagger UI

Para explorar el contrato interactivamente sin instalar nada, pega el contenido de
`backend/openapi/openapi.yaml` en <https://editor.swagger.io>, o sirve localmente:

```bash
docker run -p 8080:8080 -e SWAGGER_JSON=/openapi.yaml \
  -v "$(pwd)/backend/openapi/openapi.yaml:/openapi.yaml" swaggerapi/swagger-ui
```

Luego abre `http://localhost:8080`.
