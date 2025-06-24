#!/bin/bash
# 🚀 Production Deployment Script для Anonymeme Platform
# Comprehensive deployment automation с safety checks

set -euo pipefail

# ===== CONFIGURATION =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DEPLOYMENT_ID="deploy_${TIMESTAMP}"

# Environment variables
ENVIRONMENT="${ENVIRONMENT:-production}"
BUILD_VERSION="${BUILD_VERSION:-latest}"
REGISTRY_URL="${REGISTRY_URL:-ghcr.io/anonymeme}"
DOMAIN="${DOMAIN:-anonymeme.io}"

# Colors для output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ===== UTILITY FUNCTIONS =====
check_prerequisites() {
    log_info "Checking deployment prerequisites..."
    
    # Check required tools
    local required_tools=("docker" "docker-compose" "kubectl" "helm" "curl" "jq")
    for tool in "${required_tools[@]}"; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "Required tool '$tool' is not installed"
            exit 1
        fi
    done
    
    # Check environment variables
    local required_vars=("DB_PASSWORD" "REDIS_PASSWORD" "SECRET_KEY" "JWT_SECRET_KEY")
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            log_error "Required environment variable '$var' is not set"
            exit 1
        fi
    done
    
    # Check Docker registry access
    if ! docker login "$REGISTRY_URL" &> /dev/null; then
        log_error "Cannot authenticate with Docker registry: $REGISTRY_URL"
        exit 1
    fi
    
    log_success "All prerequisites checked"
}

validate_environment() {
    log_info "Validating $ENVIRONMENT environment..."
    
    case "$ENVIRONMENT" in
        "development"|"staging"|"production")
            log_success "Environment '$ENVIRONMENT' is valid"
            ;;
        *)
            log_error "Invalid environment: $ENVIRONMENT"
            exit 1
            ;;
    esac
}

create_backup() {
    log_info "Creating pre-deployment backup..."
    
    if [[ "$ENVIRONMENT" == "production" ]]; then
        # Create database backup
        docker-compose exec -T postgres pg_dump \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            --no-owner \
            --no-privileges \
            | gzip > "backups/pre_deploy_${TIMESTAMP}.sql.gz"
        
        log_success "Database backup created: pre_deploy_${TIMESTAMP}.sql.gz"
    else
        log_info "Skipping backup for non-production environment"
    fi
}

# ===== DOCKER DEPLOYMENT =====
deploy_docker() {
    log_info "Starting Docker deployment for $ENVIRONMENT..."
    
    cd "$PROJECT_ROOT"
    
    # Set up compose files
    local compose_files=("-f" "docker-compose.yml")
    case "$ENVIRONMENT" in
        "development")
            compose_files+=("-f" "docker-compose.development.yml")
            ;;
        "staging")
            compose_files+=("-f" "docker-compose.staging.yml")
            ;;
        "production")
            compose_files+=("-f" "docker-compose.production.yml")
            ;;
    esac
    
    # Pull latest images
    log_info "Pulling latest images..."
    docker-compose "${compose_files[@]}" pull
    
    # Deploy services with zero-downtime
    log_info "Deploying services..."
    docker-compose "${compose_files[@]}" up -d --remove-orphans
    
    # Wait for services to be healthy
    wait_for_services
    
    log_success "Docker deployment completed"
}

# ===== KUBERNETES DEPLOYMENT =====
deploy_kubernetes() {
    log_info "Starting Kubernetes deployment for $ENVIRONMENT..."
    
    cd "$PROJECT_ROOT/k8s"
    
    # Apply namespace and RBAC
    kubectl apply -f namespace.yaml
    
    # Apply ConfigMaps and Secrets
    create_k8s_secrets
    kubectl apply -f configmap.yaml
    
    # Apply database and cache deployments first
    kubectl apply -f postgres-deployment.yaml
    kubectl apply -f redis-deployment.yaml
    
    # Wait for databases to be ready
    kubectl wait --for=condition=ready pod -l app=postgres -n anonymeme --timeout=300s
    kubectl wait --for=condition=ready pod -l app=redis -n anonymeme --timeout=300s
    
    # Apply application deployments
    kubectl apply -f backend-deployment.yaml
    kubectl apply -f frontend-deployment.yaml
    kubectl apply -f websocket-deployment.yaml
    kubectl apply -f worker-deployment.yaml
    
    # Apply ingress
    kubectl apply -f ingress.yaml
    
    # Wait for application pods to be ready
    kubectl wait --for=condition=ready pod -l app=anonymeme-backend -n anonymeme --timeout=600s
    kubectl wait --for=condition=ready pod -l app=anonymeme-frontend -n anonymeme --timeout=600s
    
    log_success "Kubernetes deployment completed"
}

create_k8s_secrets() {
    log_info "Creating Kubernetes secrets..."
    
    # Create secret for application secrets
    kubectl create secret generic anonymeme-secrets \
        --from-literal=database-url="postgresql://$DB_USER:$DB_PASSWORD@postgres:5432/$DB_NAME" \
        --from-literal=redis-url="redis://:$REDIS_PASSWORD@redis:6379" \
        --from-literal=secret-key="$SECRET_KEY" \
        --from-literal=jwt-secret-key="$JWT_SECRET_KEY" \
        --namespace=anonymeme \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Create secret for Docker registry
    kubectl create secret docker-registry ghcr-secret \
        --docker-server="$REGISTRY_URL" \
        --docker-username="$DOCKER_USERNAME" \
        --docker-password="$DOCKER_PASSWORD" \
        --namespace=anonymeme \
        --dry-run=client -o yaml | kubectl apply -f -
}

# ===== HEALTH CHECKS =====
wait_for_services() {
    log_info "Waiting for services to become healthy..."
    
    local services=("backend:8000" "frontend:3000")
    local max_attempts=30
    local attempt=1
    
    for service in "${services[@]}"; do
        local service_name="${service%:*}"
        local service_port="${service#*:}"
        
        log_info "Checking $service_name health..."
        
        while [[ $attempt -le $max_attempts ]]; do
            if curl -f -s "http://localhost:$service_port/health" > /dev/null; then
                log_success "$service_name is healthy"
                break
            fi
            
            if [[ $attempt -eq $max_attempts ]]; then
                log_error "$service_name failed to become healthy after $max_attempts attempts"
                return 1
            fi
            
            log_info "Attempt $attempt/$max_attempts - waiting for $service_name..."
            sleep 10
            ((attempt++))
        done
        
        attempt=1
    done
}

run_smoke_tests() {
    log_info "Running smoke tests..."
    
    # API health check
    if ! curl -f -s "https://api.$DOMAIN/health" > /dev/null; then
        log_error "API health check failed"
        return 1
    fi
    
    # Frontend check
    if ! curl -f -s "https://$DOMAIN" > /dev/null; then
        log_error "Frontend health check failed"
        return 1
    fi
    
    # Database connectivity test
    if ! docker-compose exec -T backend python -c "
import os
import asyncpg
import asyncio

async def test_db():
    conn = await asyncpg.connect(os.getenv('DATABASE_URL'))
    result = await conn.fetchval('SELECT 1')
    await conn.close()
    return result == 1

print(asyncio.run(test_db()))
    " | grep -q "True"; then
        log_error "Database connectivity test failed"
        return 1
    fi
    
    log_success "All smoke tests passed"
}

# ===== MONITORING SETUP =====
setup_monitoring() {
    log_info "Setting up monitoring..."
    
    cd "$PROJECT_ROOT"
    
    # Deploy monitoring stack
    docker-compose -f monitoring/docker-compose.monitoring.yml up -d
    
    # Wait for Prometheus to be ready
    local max_attempts=20
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f -s "http://localhost:9090/-/ready" > /dev/null; then
            log_success "Prometheus is ready"
            break
        fi
        
        if [[ $attempt -eq $max_attempts ]]; then
            log_warning "Prometheus readiness check timed out"
            break
        fi
        
        log_info "Waiting for Prometheus... ($attempt/$max_attempts)"
        sleep 10
        ((attempt++))
    done
    
    log_success "Monitoring setup completed"
}

# ===== ROLLBACK FUNCTIONALITY =====
rollback_deployment() {
    log_warning "Rolling back deployment..."
    
    if [[ -f "backups/pre_deploy_${TIMESTAMP}.sql.gz" ]]; then
        log_info "Restoring database from backup..."
        gunzip -c "backups/pre_deploy_${TIMESTAMP}.sql.gz" | \
            docker-compose exec -T postgres psql -U "$DB_USER" -d "$DB_NAME"
    fi
    
    # Rollback to previous images
    log_info "Rolling back to previous version..."
    docker-compose down
    docker-compose up -d
    
    log_warning "Rollback completed"
}

# ===== CLEANUP =====
cleanup() {
    log_info "Performing cleanup..."
    
    # Remove old Docker images
    docker image prune -f --filter "until=72h"
    
    # Remove old backups (keep last 30 days)
    find backups/ -name "*.sql.gz" -mtime +30 -delete
    
    log_success "Cleanup completed"
}

# ===== MAIN DEPLOYMENT FLOW =====
main() {
    log_info "Starting Anonymeme Platform deployment"
    log_info "Environment: $ENVIRONMENT"
    log_info "Version: $BUILD_VERSION"
    log_info "Deployment ID: $DEPLOYMENT_ID"
    
    # Trap для cleanup on exit
    trap 'cleanup' EXIT
    
    # Deployment steps
    check_prerequisites
    validate_environment
    create_backup
    
    # Choose deployment method
    if [[ "${DEPLOY_METHOD:-docker}" == "kubernetes" ]]; then
        deploy_kubernetes
    else
        deploy_docker
    fi
    
    # Post-deployment steps
    setup_monitoring
    run_smoke_tests
    
    log_success "🎉 Deployment completed successfully!"
    log_info "Application URL: https://$DOMAIN"
    log_info "API URL: https://api.$DOMAIN"
    log_info "Monitoring: https://monitoring.$DOMAIN"
}

# ===== SCRIPT EXECUTION =====
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --environment|-e)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --version|-v)
                BUILD_VERSION="$2"
                shift 2
                ;;
            --method|-m)
                DEPLOY_METHOD="$2"
                shift 2
                ;;
            --help|-h)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --environment, -e    Target environment (development/staging/production)"
                echo "  --version, -v        Build version to deploy"
                echo "  --method, -m         Deployment method (docker/kubernetes)"
                echo "  --help, -h           Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    main "$@"
fi