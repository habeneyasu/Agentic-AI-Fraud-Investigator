# AWS App Runner — example configuration

Use this as a checklist when creating a service from your **ECR** image. Replace placeholders with your account values; do not commit real image URIs or secrets to a public repository.

## Image

- **Image URI**: `YOUR_ACCOUNT_ID.dkr.ecr.YOUR_REGION.amazonaws.com/YOUR_REPO:YOUR_TAG`
- **Port**: match your container (e.g. **8080** for App Runner defaults, or the port your image exposes).
- **Runtime**: container image from ECR.

## Environment variables

Set via App Runner console or Secrets Manager references:

- **ENVIRONMENT** — e.g. `production`
- **DATABASE_URL**, **REDIS_URL** — from secrets, not plain text in the repo
- **CEREBRAS_API_KEY**, **GEMINI_API_KEY** / **GOOGLE_API_KEY**, **API_KEY**, **SECRET_KEY** — as required by your deployment

## Health check

- Align path and port with your image (e.g. `/health` on the API port, or Streamlit’s health path if you expose only the UI).

## Security

- IAM role: ECR pull, CloudWatch logs, optional Secrets Manager.
- Security groups: outbound HTTPS as needed.

## Steps (high level)

1. Create an App Runner service from **Container image**.
2. Enter your **Image URI** and port.
3. Configure environment variables and health checks.
4. Review and deploy.
