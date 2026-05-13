# AWS App Runner Configuration Guide

## Image Configuration
- **Image URI**: 523476390411.dkr.ecr.us-east-1.amazonaws.com/agentic-ai-fraud-investigator:apprunner
- **Port**: 8080 (App Runner default)
- **Runtime**: Python

## Environment Variables
Add these environment variables in App Runner:

### Required Variables
- **ENVIRONMENT**: production
- **API_BASE_URL**: (Optional - for external API calls)

### Optional Variables (for external services)
- **DATABASE_URL**: postgresql://user:pass@host:5432/db
- **REDIS_URL**: redis://host:6379/0
- **OPENAI_API_KEY**: Your OpenAI API key
- **ANTHROPIC_API_KEY**: Your Anthropic API key
- **CEREBRAS_API_KEY**: Your Cerebras API key
- **SECRET_KEY**: Your JWT secret key

## Instance Configuration
- **CPU**: 0.25 vCPU (minimum)
- **Memory**: 0.5 GB (minimum)
- **Auto-scaling**: Enable for production

## Health Check
- **Path**: /_stcore/health (Streamlit health check)
- **Protocol**: HTTP
- **Interval**: 30 seconds
- **Timeout**: 5 seconds
- **Healthy threshold**: 1
- **Unhealthy threshold**: 3

## Security
- **IAM Role**: Create a role with permissions to:
  - Access ECR repositories
  - Access CloudWatch logs
  - Access Secrets Manager (if using secrets)

## Networking
- **VPC**: Default VPC or custom VPC
- **Security Groups**: Allow outbound HTTP/HTTPS

## Observability
- **Logging**: Enable CloudWatch logs
- **Metrics**: Enable App Runner metrics

## Deployment Steps
1. Go to AWS App Runner console
2. Click "Create service"
3. Select "Container image"
4. Enter the Image URI above
5. Configure environment variables
6. Set port to 8080
7. Review and create
