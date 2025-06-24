#!/bin/bash
# 🏗️ Infrastructure Setup Script для Anonymeme Platform
# Автоматизация настройки инфраструктуры на VPS/Cloud servers

set -euo pipefail

# ===== CONFIGURATION =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENVIRONMENT="${ENVIRONMENT:-production}"

# Default configuration
DOCKER_COMPOSE_VERSION="2.21.0"
KUBECTL_VERSION="1.28.2"
HELM_VERSION="3.13.0"
TERRAFORM_VERSION="1.5.7"

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

# ===== SYSTEM REQUIREMENTS =====
check_system() {
    log_info "Checking system requirements..."
    
    # Check OS
    if [[ ! -f /etc/os-release ]]; then
        log_error "Cannot determine OS. This script supports Ubuntu 20.04+, CentOS 8+, RHEL 8+"
        exit 1
    fi
    
    source /etc/os-release
    
    case "$ID" in
        "ubuntu")
            if [[ $(echo "$VERSION_ID >= 20.04" | bc -l) -eq 0 ]]; then
                log_error "Ubuntu 20.04+ required. Current version: $VERSION_ID"
                exit 1
            fi
            ;;
        "centos"|"rhel")
            if [[ $(echo "$VERSION_ID >= 8" | bc -l) -eq 0 ]]; then
                log_error "CentOS/RHEL 8+ required. Current version: $VERSION_ID"
                exit 1
            fi
            ;;
        *)
            log_warning "Unsupported OS: $ID. Proceeding anyway..."
            ;;
    esac
    
    # Check RAM
    local ram_gb=$(free -g | awk 'NR==2{print $2}')
    if [[ $ram_gb -lt 8 ]]; then
        log_warning "Recommended RAM: 8GB+. Current: ${ram_gb}GB"
    fi
    
    # Check disk space
    local disk_gb=$(df / | awk 'NR==2{print int($4/1024/1024)}')
    if [[ $disk_gb -lt 50 ]]; then
        log_warning "Recommended disk space: 50GB+. Available: ${disk_gb}GB"
    fi
    
    # Check CPU cores
    local cpu_cores=$(nproc)
    if [[ $cpu_cores -lt 4 ]]; then
        log_warning "Recommended CPU cores: 4+. Current: $cpu_cores"
    fi
    
    log_success "System requirements checked"
}

# ===== PACKAGE INSTALLATION =====
install_base_packages() {
    log_info "Installing base packages..."
    
    source /etc/os-release
    
    case "$ID" in
        "ubuntu")
            export DEBIAN_FRONTEND=noninteractive
            apt-get update
            apt-get install -y \
                curl \
                wget \
                gnupg \
                lsb-release \
                ca-certificates \
                software-properties-common \
                apt-transport-https \
                unzip \
                jq \
                htop \
                git \
                vim \
                nano \
                net-tools \
                ufw \
                fail2ban \
                certbot \
                python3-certbot-nginx \
                bc
            ;;
        "centos"|"rhel")
            yum update -y
            yum install -y \
                curl \
                wget \
                gnupg \
                ca-certificates \
                unzip \
                jq \
                htop \
                git \
                vim \
                nano \
                net-tools \
                firewalld \
                fail2ban \
                certbot \
                python3-certbot-nginx \
                bc \
                epel-release
            ;;
    esac
    
    log_success "Base packages installed"
}

# ===== DOCKER INSTALLATION =====
install_docker() {
    log_info "Installing Docker..."
    
    # Check if Docker is already installed
    if command -v docker &> /dev/null; then
        log_warning "Docker is already installed"
        return
    fi
    
    source /etc/os-release
    
    case "$ID" in
        "ubuntu")
            # Add Docker's official GPG key
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
            
            # Add Docker repository
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
            
            # Install Docker
            apt-get update
            apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            ;;
        "centos"|"rhel")
            # Install Docker
            yum install -y yum-utils
            yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
            yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
            ;;
    esac
    
    # Start and enable Docker
    systemctl start docker
    systemctl enable docker
    
    # Add current user to docker group
    if [[ -n "${SUDO_USER:-}" ]]; then
        usermod -aG docker "$SUDO_USER"
        log_info "Added $SUDO_USER to docker group"
    fi
    
    # Configure Docker daemon
    mkdir -p /etc/docker
    cat > /etc/docker/daemon.json <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "100m",
    "max-file": "3"
  },
  "storage-driver": "overlay2",
  "features": {
    "buildkit": true
  },
  "default-ulimits": {
    "nofile": {
      "Name": "nofile",
      "Hard": 64000,
      "Soft": 64000
    }
  },
  "live-restore": true
}
EOF
    
    systemctl restart docker
    
    log_success "Docker installed and configured"
}

# ===== DOCKER SWARM SETUP =====
setup_docker_swarm() {
    log_info "Setting up Docker Swarm..."
    
    # Initialize swarm if not already done
    if ! docker info | grep -q "Swarm: active"; then
        local ip_address=$(hostname -I | awk '{print $1}')
        docker swarm init --advertise-addr "$ip_address"
        log_success "Docker Swarm initialized"
    else
        log_warning "Docker Swarm already initialized"
    fi
    
    # Create overlay networks
    docker network create --driver overlay --attachable anonymeme-prod-network 2>/dev/null || log_warning "Network anonymeme-prod-network already exists"
    docker network create --driver overlay --attachable anonymeme-staging-network 2>/dev/null || log_warning "Network anonymeme-staging-network already exists"
    
    log_success "Docker Swarm setup completed"
}

# ===== KUBERNETES INSTALLATION =====
install_kubernetes() {
    log_info "Installing Kubernetes tools..."
    
    # Install kubectl
    if ! command -v kubectl &> /dev/null; then
        curl -LO "https://dl.k8s.io/release/v${KUBECTL_VERSION}/bin/linux/amd64/kubectl"
        chmod +x kubectl
        mv kubectl /usr/local/bin/
        log_success "kubectl installed"
    else
        log_warning "kubectl already installed"
    fi
    
    # Install Helm
    if ! command -v helm &> /dev/null; then
        curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
        chmod 700 get_helm.sh
        ./get_helm.sh --version "v${HELM_VERSION}"
        rm get_helm.sh
        log_success "Helm installed"
    else
        log_warning "Helm already installed"
    fi
    
    # Install kind (Kubernetes in Docker) для local development
    if ! command -v kind &> /dev/null; then
        curl -Lo ./kind "https://kind.sigs.k8s.io/dl/v0.20.0/kind-linux-amd64"
        chmod +x ./kind
        mv ./kind /usr/local/bin/kind
        log_success "kind installed"
    else
        log_warning "kind already installed"
    fi
    
    log_success "Kubernetes tools installed"
}

# ===== NGINX INSTALLATION =====
install_nginx() {
    log_info "Installing and configuring NGINX..."
    
    source /etc/os-release
    
    case "$ID" in
        "ubuntu")
            apt-get update
            apt-get install -y nginx
            ;;
        "centos"|"rhel")
            yum install -y nginx
            ;;
    esac
    
    # Configure NGINX
    systemctl start nginx
    systemctl enable nginx
    
    # Create basic configuration
    cat > /etc/nginx/conf.d/anonymeme.conf <<EOF
# Anonymeme Platform NGINX Configuration
upstream backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

upstream frontend {
    server 127.0.0.1:3000;
    keepalive 32;
}

upstream websocket {
    server 127.0.0.1:8001;
    keepalive 32;
}

# Rate limiting zones
limit_req_zone \$binary_remote_addr zone=api:10m rate=100r/m;
limit_req_zone \$binary_remote_addr zone=auth:10m rate=10r/m;

server {
    listen 80 default_server;
    server_name _;
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name anonymeme.io www.anonymeme.io;
    
    # SSL configuration will be added by certbot
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;
    add_header Content-Security-Policy "default-src 'self' http: https: data: blob: 'unsafe-inline'" always;
    
    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/xml
        text/javascript
        application/json
        application/javascript
        application/xml+rss
        application/atom+xml
        image/svg+xml;
    
    # API routes
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
    
    # Auth routes with stricter rate limiting
    location /api/v1/auth/ {
        limit_req zone=auth burst=5 nodelay;
        proxy_pass http://backend;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # WebSocket routes
    location /ws/ {
        proxy_pass http://websocket;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 86400;
    }
    
    # Frontend routes
    location / {
        proxy_pass http://frontend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
    
    # Static file caching
    location ~* \\.(jpg|jpeg|png|gif|ico|css|js|woff|woff2|ttf|svg)\$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header X-Cache-Status "STATIC";
    }
}
EOF
    
    # Test NGINX configuration
    nginx -t
    systemctl reload nginx
    
    log_success "NGINX installed and configured"
}

# ===== FIREWALL CONFIGURATION =====
configure_firewall() {
    log_info "Configuring firewall..."
    
    source /etc/os-release
    
    case "$ID" in
        "ubuntu")
            # Configure UFW
            ufw --force reset
            ufw default deny incoming
            ufw default allow outgoing
            
            # Allow SSH
            ufw allow 22/tcp
            
            # Allow HTTP/HTTPS
            ufw allow 80/tcp
            ufw allow 443/tcp
            
            # Allow Docker Swarm ports
            ufw allow 2377/tcp  # Cluster management
            ufw allow 7946/tcp  # Node communication
            ufw allow 7946/udp  # Node communication
            ufw allow 4789/udp  # Overlay network
            
            # Allow monitoring ports (restricted)
            ufw allow from 10.0.0.0/8 to any port 9090  # Prometheus
            ufw allow from 10.0.0.0/8 to any port 3001  # Grafana
            
            ufw --force enable
            ;;
        "centos"|"rhel")
            # Configure firewalld
            systemctl start firewalld
            systemctl enable firewalld
            
            # Configure zones
            firewall-cmd --permanent --zone=public --add-service=ssh
            firewall-cmd --permanent --zone=public --add-service=http
            firewall-cmd --permanent --zone=public --add-service=https
            
            # Docker Swarm ports
            firewall-cmd --permanent --zone=public --add-port=2377/tcp
            firewall-cmd --permanent --zone=public --add-port=7946/tcp
            firewall-cmd --permanent --zone=public --add-port=7946/udp
            firewall-cmd --permanent --zone=public --add-port=4789/udp
            
            firewall-cmd --reload
            ;;
    esac
    
    log_success "Firewall configured"
}

# ===== SECURITY HARDENING =====
configure_security() {
    log_info "Applying security hardening..."
    
    # Configure fail2ban
    cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
    
    cat > /etc/fail2ban/jail.d/anonymeme.conf <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = 22
filter = sshd
logpath = /var/log/auth.log
maxretry = 3

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/error.log

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 10

[nginx-botsearch]
enabled = true
filter = nginx-botsearch
port = http,https
logpath = /var/log/nginx/access.log
maxretry = 2
EOF
    
    systemctl restart fail2ban
    systemctl enable fail2ban
    
    # Configure SSH hardening
    if [[ -f /etc/ssh/sshd_config ]]; then
        cp /etc/ssh/sshd_config /etc/ssh/sshd_config.backup
        
        # Apply SSH hardening
        sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
        sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
        sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config
        sed -i 's/#AuthorizedKeysFile/AuthorizedKeysFile/' /etc/ssh/sshd_config
        echo "MaxAuthTries 3" >> /etc/ssh/sshd_config
        echo "ClientAliveInterval 300" >> /etc/ssh/sshd_config
        echo "ClientAliveCountMax 2" >> /etc/ssh/sshd_config
        
        systemctl restart sshd
    fi
    
    # Set up automatic security updates
    source /etc/os-release
    case "$ID" in
        "ubuntu")
            apt-get install -y unattended-upgrades
            dpkg-reconfigure -plow unattended-upgrades
            ;;
        "centos"|"rhel")
            yum install -y yum-cron
            systemctl enable yum-cron
            systemctl start yum-cron
            ;;
    esac
    
    # Configure kernel parameters
    cat > /etc/sysctl.d/99-anonymeme-security.conf <<EOF
# Network security
net.ipv4.ip_forward = 1
net.ipv4.conf.all.rp_filter = 1
net.ipv4.conf.default.rp_filter = 1
net.ipv4.conf.all.accept_source_route = 0
net.ipv4.conf.default.accept_source_route = 0
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.conf.all.secure_redirects = 0
net.ipv4.conf.default.secure_redirects = 0
net.ipv4.conf.all.send_redirects = 0
net.ipv4.conf.default.send_redirects = 0
net.ipv4.icmp_echo_ignore_broadcasts = 1
net.ipv4.icmp_ignore_bogus_error_responses = 1
net.ipv4.tcp_syncookies = 1

# Performance tuning
net.core.somaxconn = 65535
net.core.netdev_max_backlog = 5000
net.ipv4.tcp_max_syn_backlog = 65535
net.ipv4.tcp_fin_timeout = 30
net.ipv4.tcp_keepalive_time = 1200
net.ipv4.tcp_max_tw_buckets = 400000

# Memory management
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5

# File limits
fs.file-max = 2097152
EOF
    
    sysctl -p /etc/sysctl.d/99-anonymeme-security.conf
    
    log_success "Security hardening applied"
}

# ===== MONITORING SETUP =====
setup_monitoring() {
    log_info "Setting up basic monitoring..."
    
    # Install node_exporter for Prometheus
    if ! command -v node_exporter &> /dev/null; then
        cd /tmp
        wget https://github.com/prometheus/node_exporter/releases/download/v1.6.1/node_exporter-1.6.1.linux-amd64.tar.gz
        tar xvf node_exporter-1.6.1.linux-amd64.tar.gz
        cp node_exporter-1.6.1.linux-amd64/node_exporter /usr/local/bin/
        
        # Create systemd service
        cat > /etc/systemd/system/node_exporter.service <<EOF
[Unit]
Description=Node Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple
ExecStart=/usr/local/bin/node_exporter
Restart=always

[Install]
WantedBy=multi-user.target
EOF
        
        # Create user and start service
        useradd --no-create-home --shell /bin/false node_exporter
        systemctl daemon-reload
        systemctl start node_exporter
        systemctl enable node_exporter
        
        log_success "Node Exporter installed"
    fi
    
    # Configure log rotation
    cat > /etc/logrotate.d/anonymeme <<EOF
/var/log/anonymeme/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 root root
    sharedscripts
    postrotate
        /bin/systemctl reload nginx > /dev/null 2>&1 || true
    endscript
}

/var/log/docker/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    copytruncate
}
EOF
    
    log_success "Monitoring setup completed"
}

# ===== SSL CERTIFICATE SETUP =====
setup_ssl() {
    log_info "Setting up SSL certificates..."
    
    local domain="${1:-anonymeme.io}"
    local email="${2:-admin@${domain}}"
    
    # Install certbot if not already installed
    if ! command -v certbot &> /dev/null; then
        source /etc/os-release
        case "$ID" in
            "ubuntu")
                apt-get install -y certbot python3-certbot-nginx
                ;;
            "centos"|"rhel")
                yum install -y certbot python3-certbot-nginx
                ;;
        esac
    fi
    
    # Get SSL certificate
    if [[ ! -f "/etc/letsencrypt/live/${domain}/fullchain.pem" ]]; then
        certbot --nginx -d "$domain" -d "www.$domain" -d "api.$domain" -d "ws.$domain" --email "$email" --agree-tos --non-interactive
        log_success "SSL certificate obtained for $domain"
    else
        log_warning "SSL certificate already exists for $domain"
    fi
    
    # Set up automatic renewal
    crontab -l 2>/dev/null | grep -v "certbot renew" | crontab -
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -
    
    log_success "SSL certificate auto-renewal configured"
}

# ===== MAIN FUNCTIONS =====
show_help() {
    cat <<EOF
🏗️ Infrastructure Setup Script для Anonymeme Platform

Usage: $0 [COMMAND] [OPTIONS]

Commands:
  all          Install and configure everything
  system       Check system requirements
  packages     Install base packages
  docker       Install and configure Docker
  swarm        Setup Docker Swarm
  kubernetes   Install Kubernetes tools
  nginx        Install and configure NGINX
  firewall     Configure firewall
  security     Apply security hardening
  monitoring   Setup basic monitoring
  ssl          Setup SSL certificates
  help         Show this help message

Options:
  --environment, -e    Target environment (production/staging/development)
  --domain, -d         Domain name (for SSL setup)
  --email, -m          Email for SSL certificates

Examples:
  $0 all --environment production --domain anonymeme.io --email admin@anonymeme.io
  $0 docker
  $0 ssl --domain anonymeme.io --email admin@anonymeme.io

Requirements:
  - Ubuntu 20.04+ or CentOS/RHEL 8+
  - 8GB+ RAM (recommended)
  - 50GB+ disk space (recommended)
  - 4+ CPU cores (recommended)
  - Root or sudo access

EOF
}

main() {
    local command="${1:-help}"
    local domain=""
    local email=""
    
    # Parse command line arguments
    shift
    while [[ $# -gt 0 ]]; do
        case $1 in
            --environment|-e)
                ENVIRONMENT="$2"
                shift 2
                ;;
            --domain|-d)
                domain="$2"
                shift 2
                ;;
            --email|-m)
                email="$2"
                shift 2
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root or with sudo"
        exit 1
    fi
    
    case "$command" in
        "all")
            check_system
            install_base_packages
            install_docker
            setup_docker_swarm
            install_kubernetes
            install_nginx
            configure_firewall
            configure_security
            setup_monitoring
            if [[ -n "$domain" && -n "$email" ]]; then
                setup_ssl "$domain" "$email"
            fi
            log_success "🎉 Infrastructure setup completed!"
            ;;
        "system")
            check_system
            ;;
        "packages")
            install_base_packages
            ;;
        "docker")
            install_docker
            ;;
        "swarm")
            setup_docker_swarm
            ;;
        "kubernetes")
            install_kubernetes
            ;;
        "nginx")
            install_nginx
            ;;
        "firewall")
            configure_firewall
            ;;
        "security")
            configure_security
            ;;
        "monitoring")
            setup_monitoring
            ;;
        "ssl")
            if [[ -n "$domain" && -n "$email" ]]; then
                setup_ssl "$domain" "$email"
            else
                log_error "SSL setup requires --domain and --email parameters"
                exit 1
            fi
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
    main "$@"
fi