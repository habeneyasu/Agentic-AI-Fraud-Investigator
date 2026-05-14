#!/bin/bash

# Build and push the unified **one-app** image (Dockerfile default target) to ECR.

set -e

AWS_REGION="us-east-1"
ECR_REPO_NAME="agentic-ai-fraud-investigator"
IMAGE_TAG="latest"

AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
FULL_IMAGE_URI="${ECR_REGISTRY}/${ECR_REPO_NAME}:${IMAGE_TAG}"

echo "🚀 Building and pushing Agentic AI Fraud Investigator (one-app image)"
echo "Repository: ${ECR_REGISTRY}/${ECR_REPO_NAME}"
echo "Tag: ${IMAGE_TAG}"

echo "🔐 Logging into ECR..."
aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${ECR_REGISTRY}"

echo "🔨 Building Docker image (Dockerfile, default target = Streamlit + internal API)..."
docker build \
    -f Dockerfile \
    -t "${ECR_REPO_NAME}:${IMAGE_TAG}" \
    -t "${FULL_IMAGE_URI}" \
    .

echo "📦 Pushing image to ECR..."
docker push "${FULL_IMAGE_URI}"

echo "✅ Successfully pushed image: ${FULL_IMAGE_URI}"

echo "📝 Syncing deployment.yaml from repo template (edit image URI if needed)..."
# deployment.yaml in repo is maintained as source of truth; only image line may differ per account.
if [[ -f deployment.yaml ]]; then
  echo "   (deployment.yaml already present — update image: if your ECR URI changed)"
else
  echo "   No deployment.yaml in cwd; copy from repository root before kubectl apply."
fi

echo ""
echo "🎉 Build and push completed!"
echo ""
echo "📋 Next steps:"
echo "  kubectl apply -f deployment.yaml"
echo "  kubectl get pods"
