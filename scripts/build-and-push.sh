#!/bin/bash

# Simple build and push script for existing ECR repository
# Builds and pushes the Agentic AI Fraud Investigator to your existing ECR repo

set -e

# Configuration
AWS_REGION="us-east-1"
ECR_REPO_NAME="agentic-ai-fraud-investigator"
IMAGE_TAG="latest"

# Get AWS account ID and ECR registry
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
FULL_IMAGE_URI="${ECR_REGISTRY}/${ECR_REPO_NAME}:${IMAGE_TAG}"

echo "🚀 Building and pushing Agentic AI Fraud Investigator"
echo "Repository: ${ECR_REGISTRY}/${ECR_REPO_NAME}"
echo "Tag: ${IMAGE_TAG}"

# Login to ECR
echo "🔐 Logging into ECR..."
aws ecr get-login-password --region "${AWS_REGION}" | docker login --username AWS --password-stdin "${ECR_REGISTRY}"

# Build the Docker image
echo "🔨 Building Docker image..."
docker build \
    -f Dockerfile.production \
    -t "${ECR_REPO_NAME}:${IMAGE_TAG}" \
    -t "${FULL_IMAGE_URI}" \
    .

# Push the image
echo "📦 Pushing image to ECR..."
docker push "${FULL_IMAGE_URI}"

echo "✅ Successfully pushed image: ${FULL_IMAGE_URI}"

# Create simple deployment manifest
echo "📝 Creating deployment manifest..."
cat > deployment.yaml << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: fraud-investigator
  namespace: default
spec:
  replicas: 2
  selector:
    matchLabels:
      app: fraud-investigator
  template:
    metadata:
      labels:
        app: fraud-investigator
    spec:
      containers:
      - name: fraud-investigator
        image: ${FULL_IMAGE_URI}
        ports:
        - containerPort: 8000
        - containerPort: 8501
        env:
        - name: DATABASE_URL
          value: "postgresql://postgres:password@postgres:5432/fraud_investigator"
        - name: REDIS_URL
          value: "redis://redis:6379/0"
        - name: ENVIRONMENT
          value: "production"
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: fraud-investigator-api
spec:
  selector:
    app: fraud-investigator
  ports:
  - port: 8000
    targetPort: 8000
  type: ClusterIP

---
apiVersion: v1
kind: Service
metadata:
  name: fraud-investigator-dashboard
spec:
  selector:
    app: fraud-investigator
  ports:
  - port: 8501
    targetPort: 8501
  type: ClusterIP

---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: fraud-investigator-ingress
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internet-facing
spec:
  rules:
  - http:
      paths:
      - path: /api
        pathType: Prefix
        backend:
          service:
            name: fraud-investigator-api
            port:
              number: 8000
      - path: /
        pathType: Prefix
        backend:
          service:
            name: fraud-investigator-dashboard
            port:
              number: 8501
EOF

echo "✅ Created deployment.yaml manifest"
echo ""
echo "🎉 Build and push completed!"
echo ""
echo "📋 Next steps:"
echo "1. Deploy to your EKS cluster:"
echo "   kubectl apply -f deployment.yaml"
echo ""
echo "2. Check deployment status:"
echo "   kubectl get pods"
echo "   kubectl get services"
echo "   kubectl get ingress"
echo ""
echo "3. Access the application once the Load Balancer is ready"
