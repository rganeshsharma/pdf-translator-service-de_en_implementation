#!/bin/bash
# Docker build and push script for PDF Translation Service

set -e

# Configuration
DOCKER_USERNAME="your-dockerhub-username"  # Change this to your DockerHub username
IMAGE_NAME="pdf-translator"
VERSION="1.0.0"
LATEST_TAG="latest"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🐳 Docker Build Script for PDF Translation Service${NC}"
echo "=================================================="

# Function to show help
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -u, --username USER    DockerHub username (default: $DOCKER_USERNAME)"
    echo "  -v, --version VERSION  Image version (default: $VERSION)"
    echo "  -p, --push             Push to DockerHub after build"
    echo "  -t, --test             Run tests after build"
    echo "  --no-cache             Build without cache"
    echo "  -h, --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Build locally only"
    echo "  $0 -u myusername -v 2.0.0 -p        # Build and push with custom version"
    echo "  $0 --test                            # Build and test"
    echo "  $0 -p --no-cache                     # Clean build and push"
}

# Parse command line arguments
PUSH=false
TEST=false
NO_CACHE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--username)
            DOCKER_USERNAME="$2"
            shift 2
            ;;
        -v|--version)
            VERSION="$2"
            shift 2
            ;;
        -p|--push)
            PUSH=true
            shift
            ;;
        -t|--test)
            TEST=true
            shift
            ;;
        --no-cache)
            NO_CACHE="--no-cache"
            shift
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

# Validate prerequisites
echo -e "${YELLOW}🔍 Checking prerequisites...${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker is not installed${NC}"
    exit 1
fi

# Check if we're in the right directory
if [ ! -f "de_en-translator_v2.py" ] || [ ! -d "models" ]; then
    echo -e "${RED}❌ Missing required files. Make sure you're in the pdf-translator directory${NC}"
    echo "Required files:"
    echo "  - de_en-translator_v2.py"
    echo "  - models/ directory with Helsinki-NLP/opus-mt-de-en/"
    echo "  - requirements.txt"
    exit 1
fi

# Check model files
model_dir="models/Helsinki-NLP/opus-mt-de-en"
if [ ! -d "$model_dir" ]; then
    echo -e "${RED}❌ Model directory not found: $model_dir${NC}"
    echo "Please run: python offline_model_downloader.py"
    exit 1
fi

# Check critical model files
critical_files=("config.json" "pytorch_model.bin" "tokenizer_config.json")
for file in "${critical_files[@]}"; do
    if [ ! -f "$model_dir/$file" ]; then
        echo -e "${RED}❌ Missing model file: $model_dir/$file${NC}"
        exit 1
    fi
done

echo -e "${GREEN}✅ Prerequisites check passed${NC}"

# Build configuration
FULL_IMAGE_NAME="$DOCKER_USERNAME/$IMAGE_NAME"
IMAGE_TAG_VERSION="$FULL_IMAGE_NAME:$VERSION"
IMAGE_TAG_LATEST="$FULL_IMAGE_NAME:$LATEST_TAG"

echo ""
echo -e "${BLUE}🔧 Build Configuration:${NC}"
echo "  Docker Username: $DOCKER_USERNAME"
echo "  Image Name: $IMAGE_NAME"
echo "  Version: $VERSION"
echo "  Full Image: $IMAGE_TAG_VERSION"
echo "  Latest Tag: $IMAGE_TAG_LATEST"
echo "  Push to Registry: $PUSH"
echo "  Run Tests: $TEST"
echo ""

# Calculate model size
model_size=$(du -sh "$model_dir" | cut -f1)
echo -e "${YELLOW}📊 Model directory size: $model_size${NC}"
echo ""

# Build the Docker image
echo -e "${YELLOW}🔨 Building Docker image...${NC}"
build_start_time=$(date +%s)

docker build $NO_CACHE \
    -t "$IMAGE_TAG_VERSION" \
    -t "$IMAGE_TAG_LATEST" \
    --label "version=$VERSION" \
    --label "build-date=$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
    --label "description=PDF Translation Service - German to English" \
    .

build_end_time=$(date +%s)
build_duration=$((build_end_time - build_start_time))

echo -e "${GREEN}✅ Docker image built successfully!${NC}"
echo "   Build time: ${build_duration}s"

# Show image information
echo ""
echo -e "${BLUE}📋 Image Information:${NC}"
docker images "$FULL_IMAGE_NAME" --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

# Test the image if requested
if [ "$TEST" = true ]; then
    echo ""
    echo -e "${YELLOW}🧪 Testing the built image...${NC}"
    
    # Test model loading
    echo "Testing model loading..."
    if docker run --rm "$IMAGE_TAG_VERSION" test; then
        echo -e "${GREEN}✅ Model test passed${NC}"
    else
        echo -e "${RED}❌ Model test failed${NC}"
        exit 1
    fi
    
    # Test help command
    echo "Testing help command..."
    docker run --rm "$IMAGE_TAG_VERSION" --help > /dev/null
    echo -e "${GREEN}✅ Help command test passed${NC}"
fi

# Push to DockerHub if requested
if [ "$PUSH" = true ]; then
    echo ""
    echo -e "${YELLOW}📤 Pushing to DockerHub...${NC}"
    
    # Check if logged in to Docker
    if ! docker info | grep -q "Username:"; then
        echo -e "${YELLOW}🔐 Please log in to DockerHub:${NC}"
        docker login
    fi
    
    # Push both tags
    echo "Pushing version tag: $IMAGE_TAG_VERSION"
    docker push "$IMAGE_TAG_VERSION"
    
    echo "Pushing latest tag: $IMAGE_TAG_LATEST"
    docker push "$IMAGE_TAG_LATEST"
    
    echo -e "${GREEN}✅ Successfully pushed to DockerHub!${NC}"
    echo ""
    echo -e "${BLUE}🌐 Your image is now available at:${NC}"
    echo "   docker pull $IMAGE_TAG_VERSION"
    echo "   docker pull $IMAGE_TAG_LATEST"
fi

# Final instructions
echo ""
echo -e "${GREEN}🎉 Build completed successfully!${NC}"
echo ""
echo -e "${BLUE}📖 Usage Instructions:${NC}"
echo ""
echo "1. Test the image:"
echo "   docker run --rm $IMAGE_TAG_LATEST test"
echo ""
echo "2. Translate a PDF:"
echo "   docker run -v \$(pwd):/app/input -v \$(pwd):/app/output \\"
echo "     $IMAGE_TAG_LATEST translate /app/input/german.pdf /app/output/english.pdf"
echo ""
echo "3. Interactive mode:"
echo "   docker run -it --rm $IMAGE_TAG_LATEST bash"
echo ""

if [ "$PUSH" = true ]; then
    echo -e "${BLUE}🌍 Share your image:${NC}"
    echo "   Others can now use: docker run $IMAGE_TAG_LATEST"
fi

echo ""
echo -e "${YELLOW}💡 Pro tip: Add this to your README.md for easy distribution!${NC}"