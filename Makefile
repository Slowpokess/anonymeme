# 🚀 Crypto Pump Anon - Development Commands

.PHONY: help setup build test deploy clean

# Default target
help:
	@echo "🚀 Crypto Pump Anon Development Commands"
	@echo ""
	@echo "Setup Commands:"
	@echo "  setup-all     - Setup entire project (contracts + backend + frontend)"
	@echo "  setup-contracts - Setup Solana/Anchor environment"
	@echo "  setup-backend - Setup Python backend"
	@echo "  setup-frontend - Setup Next.js frontend"
	@echo ""
	@echo "Development Commands:"
	@echo "  dev-all       - Start all services in development mode"
	@echo "  dev-contracts - Start local Solana validator"
	@echo "  dev-backend   - Start backend development server"
	@echo "  dev-frontend  - Start frontend development server"
	@echo ""
	@echo "Build Commands:"
	@echo "  build-all     - Build all components"
	@echo "  build-contracts - Build Solana contracts"
	@echo "  build-backend - Build backend Docker image"
	@echo "  build-frontend - Build frontend for production"
	@echo ""
	@echo "Test Commands:"
	@echo "  test-all      - Run all tests"
	@echo "  test-contracts - Run contract tests"
	@echo "  test-backend  - Run backend tests"
	@echo "  test-frontend - Run frontend tests"
	@echo ""
	@echo "Deploy Commands:"
	@echo "  deploy-dev    - Deploy to development environment"
	@echo "  deploy-staging - Deploy to staging environment"
	@echo "  deploy-prod   - Deploy to production environment"

# === SETUP COMMANDS ===
setup-all: setup-contracts setup-backend setup-frontend
	@echo "✅ Full project setup completed!"

setup-contracts:
	@echo "🔧 Setting up Solana/Anchor environment..."
	cd contracts/pump-core && anchor build
	cd contracts/pump-core && npm install

setup-backend:
	@echo "🔧 Setting up Python backend..."
	cd backend && python -m venv venv
	cd backend && source venv/bin/activate && pip install -r requirements.txt

setup-frontend:
	@echo "🔧 Setting up Next.js frontend..."
	cd frontend && npm install

# === DEVELOPMENT COMMANDS ===
dev-all:
	docker-compose up -d

dev-contracts:
	cd contracts/pump-core && solana-test-validator

dev-backend:
	cd backend && source venv/bin/activate && uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

# === BUILD COMMANDS ===
build-all: build-contracts build-backend build-frontend

build-contracts:
	cd contracts/pump-core && anchor build

build-backend:
	docker build -t crypto-pump-anon/backend ./backend

build-frontend:
	cd frontend && npm run build

# === TEST COMMANDS ===
test-all: test-contracts test-backend test-frontend

test-contracts:
	cd contracts/pump-core && anchor test

test-backend:
	cd backend && source venv/bin/activate && pytest

test-frontend:
	cd frontend && npm run test

# === DEPLOY COMMANDS ===
deploy-dev:
	@echo "🚀 Deploying to development environment..."
	cd contracts/pump-core && anchor deploy --provider.cluster devnet

deploy-contracts:
	cd contracts/pump-core && anchor deploy

# === UTILITY COMMANDS ===
clean:
	@echo "🧹 Cleaning build artifacts..."
	cd contracts/pump-core && anchor clean
	cd frontend && rm -rf .next node_modules
	cd backend && rm -rf __pycache__ .pytest_cache
	docker system prune -f

logs:
	docker-compose logs -f

reset-db:
	docker-compose down -v
	docker-compose up -d postgres redis

# === SECURITY COMMANDS ===
security-scan:
	@echo "🔍 Running security scans..."
	cd contracts/pump-core && anchor audit
	cd backend && bandit -r .
	cd frontend && npm audit

generate-keys:
	@echo "🔑 Generating development keypairs..."
	mkdir -p keypairs
	solana-keygen new --outfile keypairs/admin.json --no-bip39-passphrase
	solana-keygen new --outfile keypairs/treasury.json --no-bip39-passphrase
	@echo "✅ Keypairs generated in ./keypairs/"