#!/bin/bash
# PDF Translation Service Deployment Script
# Supports local development, Docker, and Kubernetes deployments

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Default values
DEPLOYMENT_TYPE="local"
ENVIRONMENT="development"
NAMESPACE="pdf-translator"
IMAGE_TAG="latest"
REGISTRY="ghcr.io/yourusername"
DOMAIN="pdf-translator.local"

# Help function
show_help() {
    echo -e "${BLUE}PDF Translation Service Deployment Script${NC}"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -t, --type TYPE       Deployment type (local|docker|k8s) [default: local]"
    echo "  -e, --env ENV         Environment (development|staging|production) [default: development]"
    echo "  -n, --namespace NS    Kubernetes namespace [default: pdf-translator]"
    echo "  -i, --image IMAGE     Docker image tag [default: latest]"
    echo "  -r, --registry REG    Docker registry [default: ghcr.io/yourusername]"
    echo "  -d, --domain DOMAIN   Domain name for ingress [default: pdf-translator.local]"
    echo "  -h, --help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                      # Local development setup"
    echo "  $0 -t docker                          # Docker deployment"
    echo "  $0 -t k8s -e staging                  # Kubernetes staging deployment"
    echo "  $0 -t k8s -e production -i v1.0.0    # Kubernetes production with specific version"
    echo ""
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            DEPLOYMENT_TYPE="$2"
            shift 2
            ;;
        -e|--env)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -i|--image)
            IMAGE_TAG="$2"
            shift 2
            ;;
        -r|--registry)
            REGISTRY="$2"
            shift 2
            ;;
        -d|--domain)
            DOMAIN="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo "Unknown option $1"
            show_help
            exit 1
            ;;
    esac
done

# Validation functions
check_dependencies() {
    local missing_deps=()
    
    case $DEPLOYMENT_TYPE in
        "local")
            command -v python3 >/dev/null 2>&1 || missing_deps+=("python3")
            command -v pip >/dev/null 2>&1 || missing_deps+=("pip")
            ;;
        "docker")
            command -v docker >/dev/null 2>&1 || missing_deps+=("docker")
            ;;
        "k8s")
            command -v kubectl >/dev/null 2>&1 || missing_deps+=("kubectl")
            command -v helm >/dev/null 2>&1 || missing_deps+=("helm")
            ;;
    esac
    
    if [ ${#missing_deps[@]} -ne 0 ]; then
        echo -e "${RED}❌ Missing dependencies: ${missing_deps[*]}${NC}"
        echo "Please install the required dependencies and try again."
        exit 1
    fi
}

# Local development setup
deploy_local() {
    echo -e "${BLUE}🚀 Setting up local development environment${NC}"
    
    # Create virtual environment
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}📦 Creating Python virtual environment...${NC}"
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    echo -e "${YELLOW}🔧 Activating virtual environment...${NC}"
    source venv/bin/activate
    
    # Install dependencies
    echo -e "${YELLOW}📚 Installing Python dependencies...${NC}"
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
    
    # Download models
    if [ ! -d "models" ]; then
        echo -e "${YELLOW}📥 Downloading translation models...${NC}"
        python scripts/offline_model_downloader.py
    else
        echo -e "${GREEN}✅ Models already downloaded${NC}"
    fi
    
    # Create directories
    mkdir -p uploads outputs temp
    
    # Start the service
    echo -e "${GREEN}🎉 Starting PDF Translation Service locally...${NC}"
    echo -e "${BLUE}📱 Service will be available at: http://localhost:8080${NC}"
    echo -e "${BLUE}📖 API documentation: http://localhost:8080/docs${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop the service${NC}"
    echo ""
    
    python src/api_server.py
}

# Docker deployment
deploy_docker() {
    echo -e "${BLUE}🐳 Deploying with Docker${NC}"
    
    # Build image if it doesn't exist locally
    if ! docker images "${REGISTRY}/pdf-translator:${IMAGE_TAG}" | grep -q pdf-translator; then
        echo -e "${YELLOW}🔨 Building Docker image...${NC}"
        docker build -t "${REGISTRY}/pdf-translator:${IMAGE_TAG}" -f docker/Dockerfile .
    fi
    
    # Create docker-compose override for environment
    cat > docker-compose.override.yml << EOF
version: '3.8'
services:
  pdf-translator:
    image: ${REGISTRY}/pdf-translator:${IMAGE_TAG}
    environment:
      - LOG_LEVEL=${ENVIRONMENT == "production" && "warn" || "info"}
    ports:
      - "8080:8080"
    volumes:
      - ./uploads:/app/uploads
      - ./outputs:/app/outputs
      - ./temp:/app/temp
EOF
    
    # Start services
    echo -e "${YELLOW}🚀 Starting Docker services...${NC}"
    docker-compose up -d
    
    # Wait for service to be ready
    echo -e "${YELLOW}⏳ Waiting for service to be ready...${NC}"
    timeout=60
    while [ $timeout -gt 0 ]; do
        if curl -s http://localhost:8080/health > /dev/null; then
            echo -e "${GREEN}✅ Service is ready!${NC}"
            break
        fi
        sleep 2
        ((timeout -= 2))
    done
    
    if [ $timeout -le 0 ]; then
        echo -e "${RED}❌ Service failed to start within 60 seconds${NC}"
        docker-compose logs
        exit 1
    fi
    
    echo -e "${GREEN}🎉 Docker deployment completed!${NC}"
    echo -e "${BLUE}📱 Service available at: http://localhost:8080${NC}"
    echo -e "${BLUE}📖 API documentation: http://localhost:8080/docs${NC}"
}

# Kubernetes deployment
deploy_k8s() {
    echo -e "${BLUE}☸️  Deploying to Kubernetes (${ENVIRONMENT})${NC}"
    
    # Check if kubectl is connected
    if ! kubectl cluster-info > /dev/null; then
        echo -e "${RED}❌ Unable to connect to Kubernetes cluster${NC}"
        echo "Please check your kubeconfig and try again."
        exit 1
    fi
    
    # Create namespace if it doesn't exist
    if ! kubectl get namespace "${NAMESPACE}" > /dev/null 2>&1; then
        echo -e "${YELLOW}📁 Creating namespace: ${NAMESPACE}${NC}"
        kubectl create namespace "${NAMESPACE}"
    fi
    
    # Choose values file based on environment
    VALUES_FILE="helm/pdf-translation-chart/values.yaml"
    if [ -f "helm/pdf-translation-chart/values-${ENVIRONMENT}.yaml" ]; then
        VALUES_FILE="helm/pdf-translation-chart/values-${ENVIRONMENT}.yaml"
    fi
    
    echo -e "${YELLOW}📋 Using values file: ${VALUES_FILE}${NC}"
    
    # Deploy with Helm
    echo -e "${YELLOW}🚀 Deploying with Helm...${NC}"
    helm upgrade --install "pdf-translator-${ENVIRONMENT}" \
        ./helm/pdf-translation-chart \
        --namespace "${NAMESPACE}" \
        --values "${VALUES_FILE}" \
        --set "image.repository=${REGISTRY}/pdf-translator" \
        --set "image.tag=${IMAGE_TAG}" \
        --set "ingress.hosts[0].host=${DOMAIN}" \
        --set "ingress.tls[0].hosts[0]=${DOMAIN}" \
        --wait \
        --timeout 10m
    
    # Wait for pods to be ready
    echo -e "${YELLOW}⏳ Waiting for pods to be ready...${NC}"
    kubectl wait --for=condition=ready pod \
        -l "app.kubernetes.io/name=pdf-translation-chart" \
        -n "${NAMESPACE}" \
        --timeout=300s
    
    # Get service information
    echo -e "${GREEN}✅ Kubernetes deployment completed!${NC}"
    echo ""
    echo -e "${BLUE}📊 Deployment Information:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Show pod status
    kubectl get pods -n "${NAMESPACE}" -l "app.kubernetes.io/name=pdf-translation-chart"
    echo ""
    
    # Show service endpoints
    if kubectl get ingress -n "${NAMESPACE}" | grep -q pdf-translator; then
        INGRESS_IP=$(kubectl get ingress -n "${NAMESPACE}" -o jsonpath='{.items[0].status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "pending")
        echo -e "${BLUE}🌐 External Access:${NC}"
        if [ "$INGRESS_IP" != "pending" ] && [ -n "$INGRESS_IP" ]; then
            echo -e "   Service: http://${INGRESS_IP}"
            echo -e "   Domain: https://${DOMAIN}"
        else
            echo -e "   ${YELLOW}⏳ External IP pending...${NC}"
            echo -e "   Domain: https://${DOMAIN} (when ready)"
        fi
    else
        # Port forward for local access
        echo -e "${YELLOW}🔗 Setting up port forwarding...${NC}"
        kubectl port-forward "service/pdf-translator-service" 8080:80 -n "${NAMESPACE}" &
        PORT_FORWARD_PID=$!
        echo -e "${BLUE}📱 Local access: http://localhost:8080${NC}"
        echo -e "${YELLOW}💡 Port forward PID: ${PORT_FORWARD_PID}${NC}"
    fi
    
    echo ""
    echo -e "${BLUE}📖 Useful commands:${NC}"
    echo "   View logs: kubectl logs -f deployment/pdf-translator-deployment -n ${NAMESPACE}"
    echo "   Scale up: kubectl scale deployment/pdf-translator-deployment --replicas=5 -n ${NAMESPACE}"
    echo "   Delete: helm uninstall pdf-translator-${ENVIRONMENT} -n ${NAMESPACE}"
}

# Health check function
run_health_check() {
    local url="http://localhost:8080/health"
    
    echo -e "${YELLOW}🏥 Running health check...${NC}"
    
    if curl -s "$url" | jq -e '.status == "healthy"' > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Service is healthy!${NC}"
        return 0
    else
        echo -e "${RED}❌ Service health check failed${NC}"
        return 1
    fi
}

# Main execution
main() {
    echo -e "${PURPLE}╔═══════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║     PDF Translation Service Setup    ║${NC}"
    echo -e "${PURPLE}╚═══════════════════════════════════════╝${NC}"
    echo ""
    
    echo -e "${BLUE}📋 Configuration:${NC}"
    echo "   Deployment Type: $DEPLOYMENT_TYPE"
    echo "   Environment: $ENVIRONMENT"
    echo "   Namespace: $NAMESPACE"
    echo "   Image Tag: $IMAGE_TAG"
    echo "   Registry: $REGISTRY"
    echo "   Domain: $DOMAIN"
    echo ""
    
    # Check dependencies
    check_dependencies
    
    # Deploy based on type
    case $DEPLOYMENT_TYPE in
        "local")
            deploy_local
            ;;
        "docker")
            deploy_docker
            ;;
        "k8s")
            deploy_k8s
            ;;
        *)
            echo -e "${RED}❌ Unknown deployment type: $DEPLOYMENT_TYPE${NC}"
            echo "Supported types: local, docker, k8s"
            exit 1
            ;;
    esac
}

# Trap signals for cleanup
cleanup() {
    echo -e "\n${YELLOW}🧹 Cleaning up...${NC}"
    if [ -n "$PORT_FORWARD_PID" ]; then
        kill $PORT_FORWARD_PID 2>/dev/null || true
    fi
    exit 0
}

trap cleanup INT TERM

# Run main function
main

# Keep script running for local deployment
if [ "$DEPLOYMENT_TYPE" = "local" ]; then
    wait
fi