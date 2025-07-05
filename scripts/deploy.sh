#!/bin/bash

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${ENVIRONMENT:-staging}"
NAMESPACE="bdren-${ENVIRONMENT}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
KUBECTL_TIMEOUT="300s"

# Functions
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✅ $1${NC}"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠️  $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ❌ $1${NC}"
}

check_prerequisites() {
    log "Checking prerequisites..."

    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        error "kubectl is not installed"
        exit 1
    fi

    # Check if helm is installed
    if ! command -v helm &> /dev/null; then
        error "helm is not installed"
        exit 1
    fi

    # Check if docker is installed
    if ! command -v docker &> /dev/null; then
        error "docker is not installed"
        exit 1
    fi

    # Check kubectl connection
    if ! kubectl cluster-info &> /dev/null; then
        error "Cannot connect to Kubernetes cluster"
        exit 1
    fi

    success "Prerequisites check passed"
}

create_namespace() {
    log "Creating namespace: $NAMESPACE"

    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        warning "Namespace $NAMESPACE already exists"
    else
        kubectl create namespace "$NAMESPACE"
        kubectl label namespace "$NAMESPACE" environment="$ENVIRONMENT"
        success "Namespace $NAMESPACE created"
    fi
}

deploy_secrets() {
    log "Deploying secrets..."

    # Check if secrets exist
    if kubectl get secret db-credentials -n "$NAMESPACE" &> /dev/null; then
        warning "Database secrets already exist"
    else
        # Create database secrets
        kubectl create secret generic db-credentials \
            --from-literal=username="${DB_USERNAME:-postgres}" \
            --from-literal=password="${DB_PASSWORD:-postgres}" \
            --from-literal=database="${DB_NAME:-student_data_db}" \
            --from-literal=url="postgresql://${DB_USERNAME:-postgres}:${DB_PASSWORD:-postgres}@${DB_HOST:-postgres}:5432/${DB_NAME:-student_data_db}" \
            -n "$NAMESPACE"
        success "Database secrets created"
    fi

    if kubectl get secret redis-credentials -n "$NAMESPACE" &> /dev/null; then
        warning "Redis secrets already exist"
    else
        # Create Redis secrets
        kubectl create secret generic redis-credentials \
            --from-literal=password="${REDIS_PASSWORD:-}" \
            --from-literal=url="redis://${REDIS_HOST:-redis}:6379" \
            -n "$NAMESPACE"
        success "Redis secrets created"
    fi

    if kubectl get secret app-secrets -n "$NAMESPACE" &> /dev/null; then
        warning "Application secrets already exist"
    else
        # Create application secrets
        kubectl create secret generic app-secrets \
            --from-literal=secret-key="${SECRET_KEY:-change-me-in-production}" \
            --from-literal=jwt-secret="${JWT_SECRET:-change-me-in-production}" \
            --from-literal=encryption-key="${ENCRYPTION_KEY:-change-me-in-production}" \
            -n "$NAMESPACE"
        success "Application secrets created"
    fi
}

deploy_configmap() {
    log "Deploying ConfigMap..."

    envsubst < "$PROJECT_ROOT/deploy/kubernetes/configmap.yaml" | kubectl apply -f -
    success "ConfigMap deployed"
}

deploy_database() {
    log "Deploying PostgreSQL database..."

    # Deploy PostgreSQL using Helm
    if helm list -n "$NAMESPACE" | grep -q postgres; then
        warning "PostgreSQL already deployed, upgrading..."
        helm upgrade postgres bitnami/postgresql \
            --namespace "$NAMESPACE" \
            --set auth.postgresPassword="${DB_PASSWORD:-postgres}" \
            --set auth.database="${DB_NAME:-student_data_db}" \
            --set primary.persistence.size=20Gi \
            --set metrics.enabled=true \
            --wait --timeout="$KUBECTL_TIMEOUT"
    else
        helm install postgres bitnami/postgresql \
            --namespace "$NAMESPACE" \
            --set auth.postgresPassword="${DB_PASSWORD:-postgres}" \
            --set auth.database="${DB_NAME:-student_data_db}" \
            --set primary.persistence.size=20Gi \
            --set metrics.enabled=true \
            --wait --timeout="$KUBECTL_TIMEOUT"
    fi

    success "PostgreSQL deployed"
}

deploy_redis() {
    log "Deploying Redis cache..."

    # Deploy Redis using Helm
    if helm list -n "$NAMESPACE" | grep -q redis; then
        warning "Redis already deployed, upgrading..."
        helm upgrade redis bitnami/redis \
            --namespace "$NAMESPACE" \
            --set auth.password="${REDIS_PASSWORD:-}" \
            --set master.persistence.size=8Gi \
            --set metrics.enabled=true \
            --wait --timeout="$KUBECTL_TIMEOUT"
    else
        helm install redis bitnami/redis \
            --namespace "$NAMESPACE" \
            --set auth.password="${REDIS_PASSWORD:-}" \
            --set master.persistence.size=8Gi \
            --set metrics.enabled=true \
            --wait --timeout="$KUBECTL_TIMEOUT"
    fi

    success "Redis deployed"
}

deploy_application() {
    log "Deploying application..."

    # Update image tag in deployment
    export IMAGE_TAG
    envsubst < "$PROJECT_ROOT/deploy/kubernetes/app-deployment.yaml" | kubectl apply -f -

    # Wait for deployment to be ready
    kubectl rollout status deployment/student-analytics -n "$NAMESPACE" --timeout="$KUBECTL_TIMEOUT"

    success "Application deployed"
}

deploy_hpa() {
    log "Deploying Horizontal Pod Autoscaler..."

    kubectl apply -f "$PROJECT_ROOT/deploy/kubernetes/hpa.yaml"
    success "HPA deployed"
}

deploy_network_policy() {
    log "Deploying Network Policy..."

    kubectl apply -f "$PROJECT_ROOT/deploy/kubernetes/network-policy.yaml"
    success "Network Policy deployed"
}

deploy_monitoring() {
    log "Deploying monitoring stack..."

    # Create monitoring namespace
    if ! kubectl get namespace monitoring &> /dev/null; then
        kubectl create namespace monitoring
    fi

    # Deploy Prometheus using Helm
    if ! helm list -n monitoring | grep -q prometheus; then
        helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
        helm repo update

        helm install prometheus prometheus-community/kube-prometheus-stack \
            --namespace monitoring \
            --set prometheus.prometheusSpec.retention=30d \
            --set prometheus.prometheusSpec.storageSpec.volumeClaimTemplate.spec.resources.requests.storage=50Gi \
            --set grafana.adminPassword="${GRAFANA_PASSWORD:-admin}" \
            --wait --timeout="$KUBECTL_TIMEOUT"
    fi

    success "Monitoring stack deployed"
}

deploy_logging() {
    log "Deploying logging stack..."

    # Create logging namespace
    if ! kubectl get namespace logging &> /dev/null; then
        kubectl create namespace logging
    fi

    # Deploy ELK stack
    kubectl apply -f "$PROJECT_ROOT/deploy/logging/"

    success "Logging stack deployed"
}

run_database_migrations() {
    log "Running database migrations..."

    # Create a job to run migrations
    kubectl create job --from=deployment/student-analytics migration-$(date +%s) -n "$NAMESPACE"
    kubectl patch job migration-$(date +%s) -n "$NAMESPACE" -p '{"spec":{"template":{"spec":{"containers":[{"name":"student-analytics","command":["alembic","upgrade","head"]}]}}}}'

    # Wait for migration job to complete
    kubectl wait --for=condition=complete job/migration-$(date +%s) -n "$NAMESPACE" --timeout="$KUBECTL_TIMEOUT"

    success "Database migrations completed"
}

verify_deployment() {
    log "Verifying deployment..."

    # Check if all pods are running
    if kubectl get pods -n "$NAMESPACE" | grep -v Running | grep -v Completed; then
        warning "Some pods are not in Running state"
        kubectl get pods -n "$NAMESPACE"
    else
        success "All pods are running"
    fi

    # Check service endpoints
    log "Checking service endpoints..."
    kubectl get endpoints -n "$NAMESPACE"

    # Test application health
    log "Testing application health..."
    if kubectl get service student-analytics -n "$NAMESPACE" &> /dev/null; then
        # Port forward to test health endpoint
        kubectl port-forward service/student-analytics 8080:80 -n "$NAMESPACE" &
        PF_PID=$!
        sleep 5

        if curl -f http://localhost:8080/health &> /dev/null; then
            success "Application health check passed"
        else
            warning "Application health check failed"
        fi

        kill $PF_PID 2>/dev/null || true
    fi

    success "Deployment verification completed"
}

cleanup_failed_deployment() {
    log "Cleaning up failed deployment..."

    # Delete failed pods
    kubectl delete pods --field-selector=status.phase=Failed -n "$NAMESPACE" 2>/dev/null || true

    # Restart failed deployments
    kubectl rollout restart deployment/student-analytics -n "$NAMESPACE" 2>/dev/null || true

    success "Cleanup completed"
}

show_deployment_info() {
    log "Deployment Information:"
    echo "=========================="
    echo "Environment: $ENVIRONMENT"
    echo "Namespace: $NAMESPACE"
    echo "Image Tag: $IMAGE_TAG"
    echo "=========================="

    log "Services:"
    kubectl get services -n "$NAMESPACE"

    log "Pods:"
    kubectl get pods -n "$NAMESPACE"

    log "Ingress:"
    kubectl get ingress -n "$NAMESPACE" 2>/dev/null || echo "No ingress found"
}

main() {
    log "Starting deployment to $ENVIRONMENT environment..."

    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --environment|-e)
                ENVIRONMENT="$2"
                NAMESPACE="bdren-${ENVIRONMENT}"
                shift 2
                ;;
            --image-tag|-t)
                IMAGE_TAG="$2"
                shift 2
                ;;
            --skip-db)
                SKIP_DB=true
                shift
                ;;
            --skip-monitoring)
                SKIP_MONITORING=true
                shift
                ;;
            --cleanup)
                cleanup_failed_deployment
                exit 0
                ;;
            --info)
                show_deployment_info
                exit 0
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  -e, --environment ENV    Set environment (staging/production)"
                echo "  -t, --image-tag TAG      Set Docker image tag"
                echo "  --skip-db               Skip database deployment"
                echo "  --skip-monitoring       Skip monitoring deployment"
                echo "  --cleanup               Cleanup failed deployments"
                echo "  --info                  Show deployment information"
                echo "  -h, --help              Show this help message"
                exit 0
                ;;
            *)
                error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Validate environment
    if [[ ! "$ENVIRONMENT" =~ ^(staging|production)$ ]]; then
        error "Environment must be 'staging' or 'production'"
        exit 1
    fi

    # Check prerequisites
    check_prerequisites

    # Create namespace
    create_namespace

    # Deploy secrets and config
    deploy_secrets
    deploy_configmap

    # Deploy infrastructure
    if [[ "${SKIP_DB:-false}" != "true" ]]; then
        deploy_database
        deploy_redis
    fi

    # Deploy application
    deploy_application
    deploy_hpa
    deploy_network_policy

    # Run migrations
    if [[ "${SKIP_DB:-false}" != "true" ]]; then
        run_database_migrations
    fi

    # Deploy monitoring
    if [[ "${SKIP_MONITORING:-false}" != "true" ]]; then
        deploy_monitoring
        deploy_logging
    fi

    # Verify deployment
    verify_deployment

    # Show deployment info
    show_deployment_info

    success "Deployment completed successfully!"
    log "Access your application at: https://${ENVIRONMENT}-analytics.education.gov.bd"
}

# Trap errors and cleanup
trap 'error "Deployment failed at line $LINENO"' ERR

# Run main function
main "$@"
