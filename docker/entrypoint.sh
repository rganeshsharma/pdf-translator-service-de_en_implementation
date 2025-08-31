#!/bin/bash
# Docker entrypoint for PDF Translation Service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🐳 PDF Translation Service - Docker Container${NC}"
echo "================================================="

# Function to show help
show_help() {
    echo -e "${BLUE}PDF Translation Service - Docker Container${NC}"
    echo ""
    echo "Usage: docker run [docker-options] pdf-translator [command] [args...]"
    echo ""
    echo "Commands:"
    echo "  translate INPUT OUTPUT [OPTIONS]  Translate a PDF file"
    echo "  test                              Test the translation model"
    echo "  bash                              Open interactive shell"
    echo "  --help                            Show this help message"
    echo ""
    echo "Translation Options:"
    echo "  --batch-size SIZE                 Translation batch size (default: 16)"
    echo "  --no-formatting                   Disable formatting preservation"
    echo "  --verbose                         Enable verbose logging"
    echo "  --cache-file FILE                 Use translation cache file"
    echo ""
    echo "Examples:"
    echo "  # Translate a PDF (mount local directories)"
    echo "  docker run -v /path/to/input:/app/input -v /path/to/output:/app/output \\"
    echo "    pdf-translator translate /app/input/document.pdf /app/output/translated.pdf"
    echo ""
    echo "  # Quick translation with current directory"
    echo "  docker run -v \$(pwd):/app/input -v \$(pwd):/app/output \\"
    echo "    pdf-translator translate /app/input/german.pdf /app/output/english.pdf"
    echo ""
    echo "  # Test the model"
    echo "  docker run pdf-translator test"
    echo ""
    echo "  # Interactive mode"
    echo "  docker run -it pdf-translator bash"
}

# Function to test model
test_model() {
    echo -e "${YELLOW}🧪 Testing translation model...${NC}"
    python simple_test.py
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Model test successful!${NC}"
    else
        echo -e "${RED}❌ Model test failed!${NC}"
        exit 1
    fi
}

# Function to translate PDF
translate_pdf() {
    local input_file="$1"
    local output_file="$2"
    shift 2
    local extra_args="$@"
    
    echo -e "${BLUE}📄 Translating PDF...${NC}"
    echo "Input: $input_file"
    echo "Output: $output_file"
    echo "Extra args: $extra_args"
    echo ""
    
    # Check if input file exists
    if [ ! -f "$input_file" ]; then
        echo -e "${RED}❌ Input file not found: $input_file${NC}"
        echo ""
        echo "💡 Make sure to mount your input directory:"
        echo "   docker run -v /path/to/your/files:/app/input ... pdf-translator translate /app/input/your-file.pdf ..."
        exit 1
    fi
    
    # Create output directory if needed
    mkdir -p "$(dirname "$output_file")"
    
    # Run translation
    python pdf_translator.py "$input_file" "$output_file" --offline $extra_args
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ Translation completed successfully!${NC}"
        echo "Output file: $output_file"
        
        # Show file info
        if [ -f "$output_file" ]; then
            echo "File size: $(du -h "$output_file" | cut -f1)"
        fi
    else
        echo -e "${RED}❌ Translation failed!${NC}"
        exit 1
    fi
}

# Function to check directories
check_directories() {
    echo -e "${BLUE}📁 Checking directories...${NC}"
    
    # Check model directory
    if [ -d "$MODEL_PATH" ]; then
        echo -e "${GREEN}✅ Model directory found: $MODEL_PATH${NC}"
        model_files=$(ls -1 "$MODEL_PATH" | wc -l)
        echo "   📊 Model files: $model_files"
    else
        echo -e "${RED}❌ Model directory not found: $MODEL_PATH${NC}"
        exit 1
    fi
    
    # Check input/output directories
    echo "📂 Input directory: /app/input"
    echo "📂 Output directory: /app/output"
    echo "📂 Temp directory: /app/temp"
    
    # List input files if any
    if [ -d "/app/input" ] && [ "$(ls -A /app/input 2>/dev/null)" ]; then
        echo -e "${YELLOW}📋 Files in input directory:${NC}"
        ls -la /app/input
    else
        echo -e "${YELLOW}⚠️  Input directory is empty${NC}"
        echo "   Mount your files with: -v /path/to/files:/app/input"
    fi
    
    echo ""
}

# Main command processing
case "${1}" in
    "translate")
        if [ -z "$2" ] || [ -z "$3" ]; then
            echo -e "${RED}❌ Missing arguments for translate command${NC}"
            echo "Usage: translate INPUT_FILE OUTPUT_FILE [OPTIONS]"
            exit 1
        fi
        check_directories
        test_model
        translate_pdf "$2" "$3" "${@:4}"
        ;;
    "test")
        check_directories
        test_model
        ;;
    "bash"|"sh"|"/bin/bash"|"/bin/sh")
        echo -e "${YELLOW}🐚 Opening interactive shell...${NC}"
        exec /bin/bash
        ;;
    "--help"|"help"|"")
        show_help
        ;;
    *)
        echo -e "${RED}❌ Unknown command: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac