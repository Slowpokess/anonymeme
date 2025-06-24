#!/bin/bash
# 🔐 Secret Management Script для Anonymeme Platform
# Создает и управляет secrets для Docker Swarm и Kubernetes

set -euo pipefail

# ===== CONFIGURATION =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
SECRETS_DIR="$PROJECT_ROOT/secrets"
ENVIRONMENT="${ENVIRONMENT:-production}"

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
generate_random_string() {
    local length=${1:-32}
    openssl rand -base64 $length | tr -d "=+/" | cut -c1-$length
}

generate_jwt_secret() {
    openssl rand -base64 64 | tr -d "=+/"
}

generate_encryption_key() {
    openssl rand -base64 32
}

create_secrets_directory() {
    log_info "Creating secrets directory structure..."
    
    mkdir -p "$SECRETS_DIR/$ENVIRONMENT"
    chmod 700 "$SECRETS_DIR"
    chmod 700 "$SECRETS_DIR/$ENVIRONMENT"
    
    log_success "Secrets directory created"
}

# ===== SECRET GENERATION =====
generate_secrets() {
    log_info "Generating secrets for $ENVIRONMENT environment..."
    
    local secrets_env_file="$SECRETS_DIR/$ENVIRONMENT/secrets.env"
    
    # Generate all secrets
    cat > "$secrets_env_file" <<EOF
# 🔐 Generated Secrets для $ENVIRONMENT Environment
# Generated on: $(date)
# WARNING: Keep this file secure and never commit to version control

# Database passwords
DB_PASSWORD=$(generate_random_string 32)
DB_READONLY_PASSWORD=$(generate_random_string 32)

# Redis password
REDIS_PASSWORD=$(generate_random_string 32)

# Application secrets
SECRET_KEY=$(generate_random_string 64)
JWT_SECRET_KEY=$(generate_jwt_secret)
ENCRYPTION_KEY=$(generate_encryption_key)
PII_ENCRYPTION_KEY=$(generate_encryption_key)

# Solana keypairs (placeholder - replace with actual)
SOLANA_PRIVATE_KEY=PLACEHOLDER_REPLACE_WITH_ACTUAL_PRIVATE_KEY

# Monitoring passwords
GRAFANA_PASSWORD=$(generate_random_string 16)
PROMETHEUS_PASSWORD=$(generate_random_string 16)

# External service credentials
SMTP_PASSWORD=PLACEHOLDER_REPLACE_WITH_ACTUAL
DOCKER_PASSWORD=PLACEHOLDER_REPLACE_WITH_ACTUAL
AWS_SECRET_ACCESS_KEY=PLACEHOLDER_REPLACE_WITH_ACTUAL

# API Keys (placeholders)
ANALYTICS_ID=PLACEHOLDER_REPLACE_WITH_ACTUAL
SENTRY_DSN=PLACEHOLDER_REPLACE_WITH_ACTUAL
GOOGLE_ANALYTICS_ID=PLACEHOLDER_REPLACE_WITH_ACTUAL
MIXPANEL_TOKEN=PLACEHOLDER_REPLACE_WITH_ACTUAL
AMPLITUDE_API_KEY=PLACEHOLDER_REPLACE_WITH_ACTUAL

# Webhook URLs
SLACK_WEBHOOK_URL=PLACEHOLDER_REPLACE_WITH_ACTUAL
DISCORD_WEBHOOK_URL=PLACEHOLDER_REPLACE_WITH_ACTUAL

# Backup credentials
AWS_ACCESS_KEY_ID=PLACEHOLDER_REPLACE_WITH_ACTUAL
S3_BACKUP_BUCKET=${ENVIRONMENT}-anonymeme-backups
AWS_REGION=us-east-1

# Alert email
ALERT_EMAIL=alerts@anonymeme.io

# SMTP Configuration
SMTP_HOST=smtp.gmail.com
SMTP_USER=noreply@anonymeme.io
EOF

    chmod 600 "$secrets_env_file"
    log_success "Secrets generated and saved to $secrets_env_file"
}

# ===== DOCKER SWARM SECRETS =====
create_docker_secrets() {
    log_info "Creating Docker Swarm secrets for $ENVIRONMENT..."
    
    local secrets_env_file="$SECRETS_DIR/$ENVIRONMENT/secrets.env"
    
    if [[ ! -f "$secrets_env_file" ]]; then
        log_error "Secrets file not found: $secrets_env_file"
        exit 1
    fi
    
    # Source the secrets
    source "$secrets_env_file"
    
    # Create Docker secrets
    local secret_prefix="${ENVIRONMENT}_"
    
    # Database secrets
    echo -n "$DB_PASSWORD" | docker secret create "${secret_prefix}db_password" - 2>/dev/null || log_warning "Secret ${secret_prefix}db_password already exists"
    echo -n "$REDIS_PASSWORD" | docker secret create "${secret_prefix}redis_password" - 2>/dev/null || log_warning "Secret ${secret_prefix}redis_password already exists"
    
    # Application secrets
    echo -n "$SECRET_KEY" | docker secret create "${secret_prefix}secret_key" - 2>/dev/null || log_warning "Secret ${secret_prefix}secret_key already exists"
    echo -n "$JWT_SECRET_KEY" | docker secret create "${secret_prefix}jwt_secret" - 2>/dev/null || log_warning "Secret ${secret_prefix}jwt_secret already exists"
    echo -n "$ENCRYPTION_KEY" | docker secret create "${secret_prefix}encryption_key" - 2>/dev/null || log_warning "Secret ${secret_prefix}encryption_key already exists"
    
    # Solana secrets
    echo -n "$SOLANA_PRIVATE_KEY" | docker secret create "${secret_prefix}solana_private_key" - 2>/dev/null || log_warning "Secret ${secret_prefix}solana_private_key already exists"
    
    # Monitoring secrets
    echo -n "$GRAFANA_PASSWORD" | docker secret create "${secret_prefix}grafana_password" - 2>/dev/null || log_warning "Secret ${secret_prefix}grafana_password already exists"
    
    # AWS credentials для backup
    cat > /tmp/aws_credentials <<EOF
[default]
aws_access_key_id = $AWS_ACCESS_KEY_ID
aws_secret_access_key = $AWS_SECRET_ACCESS_KEY
region = $AWS_REGION
EOF
    docker secret create "${secret_prefix}aws_backup_credentials" /tmp/aws_credentials 2>/dev/null || log_warning "Secret ${secret_prefix}aws_backup_credentials already exists"
    rm -f /tmp/aws_credentials
    
    log_success "Docker Swarm secrets created"
}

# ===== KUBERNETES SECRETS =====
create_kubernetes_secrets() {
    log_info "Creating Kubernetes secrets for $ENVIRONMENT..."
    
    local secrets_env_file="$SECRETS_DIR/$ENVIRONMENT/secrets.env"
    
    if [[ ! -f "$secrets_env_file" ]]; then
        log_error "Secrets file not found: $secrets_env_file"
        exit 1
    fi
    
    # Source the secrets
    source "$secrets_env_file"
    
    # Create main application secrets
    kubectl create secret generic anonymeme-secrets \
        --from-literal=database-url="postgresql://anonymeme:$DB_PASSWORD@postgres:5432/anonymeme" \
        --from-literal=redis-url="redis://:$REDIS_PASSWORD@redis:6379" \
        --from-literal=secret-key="$SECRET_KEY" \
        --from-literal=jwt-secret-key="$JWT_SECRET_KEY" \
        --from-literal=encryption-key="$ENCRYPTION_KEY" \
        --from-literal=db-password="$DB_PASSWORD" \
        --from-literal=redis-password="$REDIS_PASSWORD" \
        --namespace=anonymeme \
        --dry-run=client -o yaml | kubectl apply -f - || log_warning "Secret anonymeme-secrets already exists"
    
    # Create Solana keypairs secret
    kubectl create secret generic anonymeme-keypairs \
        --from-literal=private-key="$SOLANA_PRIVATE_KEY" \
        --namespace=anonymeme \
        --dry-run=client -o yaml | kubectl apply -f - || log_warning "Secret anonymeme-keypairs already exists"
    
    # Create Docker registry secret
    kubectl create secret docker-registry ghcr-secret \
        --docker-server=ghcr.io \
        --docker-username="$DOCKER_USERNAME" \
        --docker-password="$DOCKER_PASSWORD" \
        --namespace=anonymeme \
        --dry-run=client -o yaml | kubectl apply -f - || log_warning "Secret ghcr-secret already exists"
    
    # Create monitoring secrets
    kubectl create secret generic monitoring-secrets \
        --from-literal=grafana-password="$GRAFANA_PASSWORD" \
        --from-literal=prometheus-password="$PROMETHEUS_PASSWORD" \
        --namespace=anonymeme \
        --dry-run=client -o yaml | kubectl apply -f - || log_warning "Secret monitoring-secrets already exists"
    
    # Create AWS backup credentials
    kubectl create secret generic aws-backup-credentials \
        --from-literal=access-key-id="$AWS_ACCESS_KEY_ID" \
        --from-literal=secret-access-key="$AWS_SECRET_ACCESS_KEY" \
        --from-literal=region="$AWS_REGION" \
        --from-literal=bucket="$S3_BACKUP_BUCKET" \
        --namespace=anonymeme \
        --dry-run=client -o yaml | kubectl apply -f - || log_warning "Secret aws-backup-credentials already exists"
    
    log_success "Kubernetes secrets created"
}

# ===== SECRET ROTATION =====
rotate_secrets() {
    log_info "Rotating secrets for $ENVIRONMENT environment..."
    
    local backup_file="$SECRETS_DIR/$ENVIRONMENT/secrets.env.backup.$(date +%Y%m%d_%H%M%S)"
    local secrets_env_file="$SECRETS_DIR/$ENVIRONMENT/secrets.env"
    
    # Backup current secrets
    if [[ -f "$secrets_env_file" ]]; then
        cp "$secrets_env_file" "$backup_file"
        log_info "Current secrets backed up to $backup_file"
    fi
    
    # Generate new secrets
    generate_secrets
    
    # Update Docker secrets
    if command -v docker &> /dev/null && docker info &> /dev/null; then
        log_info "Updating Docker Swarm secrets..."
        # Remove old secrets
        local secret_prefix="${ENVIRONMENT}_"
        docker secret rm "${secret_prefix}secret_key" 2>/dev/null || true
        docker secret rm "${secret_prefix}jwt_secret" 2>/dev/null || true
        docker secret rm "${secret_prefix}encryption_key" 2>/dev/null || true
        
        # Create new secrets
        create_docker_secrets
    fi
    
    # Update Kubernetes secrets
    if command -v kubectl &> /dev/null; then
        log_info "Updating Kubernetes secrets..."
        kubectl delete secret anonymeme-secrets -n anonymeme 2>/dev/null || true
        kubectl delete secret monitoring-secrets -n anonymeme 2>/dev/null || true
        create_kubernetes_secrets
    fi
    
    log_success "Secret rotation completed"
    log_warning "Remember to restart all services to pick up new secrets"
}

# ===== SECRET VALIDATION =====
validate_secrets() {
    log_info "Validating secrets for $ENVIRONMENT environment..."
    
    local secrets_env_file="$SECRETS_DIR/$ENVIRONMENT/secrets.env"
    
    if [[ ! -f "$secrets_env_file" ]]; then
        log_error "Secrets file not found: $secrets_env_file"
        exit 1
    fi
    
    # Source the secrets
    source "$secrets_env_file"
    
    # Check required secrets
    local required_vars=(
        "DB_PASSWORD"
        "REDIS_PASSWORD"
        "SECRET_KEY"
        "JWT_SECRET_KEY"
        "ENCRYPTION_KEY"
    )
    
    local missing_vars=()
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" || "${!var}" == "PLACEHOLDER_REPLACE_WITH_ACTUAL" ]]; then
            missing_vars+=("$var")
        fi
    done
    
    if [[ ${#missing_vars[@]} -gt 0 ]]; then
        log_error "Missing or placeholder values for: ${missing_vars[*]}"
        log_error "Please update the secrets file: $secrets_env_file"
        exit 1
    fi
    
    # Validate secret strength
    if [[ ${#SECRET_KEY} -lt 32 ]]; then
        log_warning "SECRET_KEY is shorter than recommended (32+ characters)"
    fi
    
    if [[ ${#JWT_SECRET_KEY} -lt 64 ]]; then
        log_warning "JWT_SECRET_KEY is shorter than recommended (64+ characters)"
    fi
    
    log_success "All secrets validated successfully"
}

# ===== MAIN FUNCTIONS =====
show_help() {
    cat <<EOF
🔐 Secret Management Script для Anonymeme Platform

Usage: $0 [COMMAND] [OPTIONS]

Commands:
  generate     Generate new secrets
  docker       Create Docker Swarm secrets
  kubernetes   Create Kubernetes secrets
  rotate       Rotate existing secrets
  validate     Validate existing secrets
  help         Show this help message

Options:
  --environment, -e    Target environment (production/staging/development)

Examples:
  $0 generate --environment production
  $0 kubernetes --environment staging
  $0 rotate --environment production
  $0 validate --environment production

Environment Variables:
  ENVIRONMENT         Target environment (default: production)
  DOCKER_USERNAME     Docker registry username
  DOCKER_PASSWORD     Docker registry password

EOF
}

main() {
    local command="${1:-help}"
    
    case "$command" in
        "generate")
            create_secrets_directory
            generate_secrets
            ;;
        "docker")
            create_docker_secrets
            ;;
        "kubernetes")
            create_kubernetes_secrets
            ;;
        "rotate")
            rotate_secrets
            ;;
        "validate")
            validate_secrets
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        *)
            log_error "Unknown command: $command"
            show_help
            exit 1
            ;;
    esac
}

# ===== SCRIPT EXECUTION =====
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    # Parse command line arguments
    while [[ $# -gt 1 ]]; do
        case $2 in
            --environment|-e)
                ENVIRONMENT="$3"
                shift 2
                ;;
            *)
                break
                ;;
        esac
    done
    
    main "$@"
fi