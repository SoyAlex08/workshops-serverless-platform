#!/usr/bin/env bash
# Build the Angular app, injecting stack outputs as environment config, then sync to S3
# and invalidate the CloudFront distribution.
set -euo pipefail

ENV="${1:-dev}"
STACK_NAME="workshops-${ENV}"

cd "$(dirname "$0")/.."

get_output() {
  aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query "Stacks[0].Outputs[?OutputKey=='$1'].OutputValue" \
    --output text
}

API_URL=$(get_output ApiUrl)
BUCKET=$(get_output FrontendBucketName)
DISTRIBUTION_DOMAIN=$(get_output CloudFrontUrl)
USER_POOL_ID=$(get_output UserPoolId)
USER_POOL_CLIENT_ID=$(get_output UserPoolClientId)
REGION=$(echo "$API_URL" | sed -E 's#https://[^.]+\.execute-api\.([a-z0-9-]+)\.amazonaws\.com.*#\1#')

ENV_FILE="frontend/workshops-web/src/environments/environment.prod.ts"
cat > "$ENV_FILE" <<EOF
export const environment = {
  production: true,
  apiBaseUrl: '/api',
  cognito: {
    userPoolId: '${USER_POOL_ID}',
    userPoolClientId: '${USER_POOL_CLIENT_ID}',
    region: '${REGION}',
  },
};
EOF

echo "Wrote ${ENV_FILE} from stack outputs (API: ${API_URL})"

cd frontend/workshops-web
npm ci
npx ng build --configuration production

BUCKET_NAME="${BUCKET}"
aws s3 sync dist/workshops-web/browser "s3://${BUCKET_NAME}" --delete

DISTRIBUTION_ID=$(aws cloudfront list-distributions \
  --query "DistributionList.Items[?Origins.Items[?contains(DomainName, '${BUCKET_NAME}')]] | [0].Id" \
  --output text)

if [[ -n "$DISTRIBUTION_ID" && "$DISTRIBUTION_ID" != "None" ]]; then
  aws cloudfront create-invalidation --distribution-id "$DISTRIBUTION_ID" --paths "/*"
fi

echo "Frontend deployed. CloudFront URL: ${DISTRIBUTION_DOMAIN}"
