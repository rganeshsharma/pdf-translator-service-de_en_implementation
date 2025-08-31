# PDF Translation Service - Docker Edition 🐳

A standalone Docker container for translating German PDF documents to English while preserving layout and formatting. The container includes all models and dependencies for completely offline operation.

## 🚀 Quick Start

### Pull and Run (Recommended)

```bash
# Pull the image from DockerHub
docker pull your-dockerhub-username/pdf-translator:latest

# Translate a PDF file
docker run -v $(pwd):/app/input -v $(pwd):/app/output \
  your-dockerhub-username/pdf-translator:latest \
  translate /app/input/german-document.pdf /app/output/english-document.pdf
```

### Test the Container

```bash
# Test that the translation model works
docker run --rm your-dockerhub-username/pdf-translator:latest test
```

## 📋 Features

- **🔄 Offline Translation**: Complete German-to-English translation with no internet required
- **🎨 Layout Preservation**: Maintains original PDF formatting, fonts, and positioning  
- **🐳 Self-Contained**: All models and dependencies included in the image
- **🔒 Secure**: Runs as non-root user with minimal permissions
- **📁 Volume Support**: Easy file mounting for input/output
- **🚀 Fast**: Pre-loaded models for instant translation

## 🛠️ Building from Source

### Prerequisites

1. **Docker installed** (version 20.10+)
2. **Model files downloaded** in your local directory:
   ```
   pdf-translator/
   ├── de_en-translator_v2.py
   ├── models/
   │   └── Helsinki-NLP/
   │       └── opus-mt-de-en/
   │           ├── config.json
   │           ├── pytorch_model.bin
   │           ├── tokenizer_config.json
   │           └── ... (other model files)
   ├── requirements.txt
   └── Dockerfile
   ```

### Download Models (If Not Already Done)

```bash
# Download the translation models offline
python offline_model_downloader.py
```

### Build the Image

```bash
# Make the build script executable
chmod +x docker-build.sh

# Build locally
./docker-build.sh

# Build and push to DockerHub
./docker-build.sh -u your-dockerhub-username -v 1.0.0 -p

# Build with testing
./docker-build.sh -t

# Clean build without cache
./docker-build.sh --no-cache
```

## 📖 Usage Examples

### Basic Translation

```bash
# Translate a single PDF file
docker run -v $(pwd):/app/input -v $(pwd):/app/output \
  pdf-translator:latest \
  translate /app/input/contract.pdf /app/output/contract-english.pdf
```

### Advanced Options

```bash
# Translation with custom batch size and verbose output
docker run -v $(pwd):/app/input -v $(pwd):/app/output \
  pdf-translator:latest \
  translate /app/input/document.pdf /app/output/translated.pdf \
  --batch-size 32 --verbose

# Disable formatting preservation (faster)
docker run -v $(pwd):/app/input -v $(pwd):/app/output \
  pdf-translator:latest \
  translate /app/input/document.pdf /app/output/translated.pdf \
  --no-formatting
```

### Using Translation Cache

```bash
# Create a cache directory
mkdir -p cache

# Use translation cache to speed up repeated translations
docker run \
  -v $(pwd):/app/input \
  -v $(pwd):/app/output \
  -v $(pwd)/cache:/app/cache \
  pdf-translator:latest \
  translate /app/input/document.pdf /app/output/translated.pdf \
  --cache-file /app/cache/translations.json
```

### Interactive Mode

```bash
# Open a shell inside the container
docker run -it --rm \
  -v $(pwd):/app/input \
  -v $(pwd):/app/output \
  pdf-translator:latest bash

# Inside the container, you can run:
python pdf_translator.py /app/input/test.pdf /app/output/test-en.pdf --offline
```

### Batch Processing Multiple Files

```bash
# Create a script for batch processing
cat > batch-translate.sh << 'EOF'
#!/bin/bash
INPUT_DIR="$1"
OUTPUT_DIR="$2"

for pdf in "$INPUT_DIR"/*.pdf; do
    filename=$(basename "$pdf" .pdf)
    echo "Translating: $filename.pdf"
    
    docker run -v "$INPUT_DIR":/app/input -v "$OUTPUT_DIR":/app/output \
      pdf-translator:latest \
      translate "/app/input/$filename.pdf" "/app/output/$filename-english.pdf"
done
EOF

chmod +x batch-translate.sh

# Use it
./batch-translate.sh /path/to/german/pdfs /path/to/english/pdfs
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_PATH` | `/app/models/Helsinki-NLP/opus-mt-de-en` | Path to translation model |
| `PYTHONPATH` | `/app` | Python module search path |
| `OFFLINE_MODE` | `true` | Force offline mode |

### Volume Mounts

| Mount Point | Purpose | Example |
|-------------|---------|---------|
| `/app/input` | Input PDF files | `-v $(pwd):/app/input` |
| `/app/output` | Output translated files | `-v $(pwd):/app/output` |
| `/app/cache` | Translation cache (optional) | `-v $(pwd)/cache:/app/cache` |

## 🏥 Health Checks

The container includes built-in health checks:

```bash
# Check container health
docker ps --format "table {{.Names}}\t{{.Status}}"

# Manual health check
docker exec <container-id> python simple_test.py
```

## 🚨 Troubleshooting

### Common Issues

**1. "Input file not found" Error**
```bash
# Make sure your file path is correct relative to the mount
ls $(pwd)/your-file.pdf  # Check file exists locally

# Correct mount path
docker run -v $(pwd):/app/input -v $(pwd):/app/output \
  pdf-translator:latest \
  translate /app/input/your-file.pdf /app/output/translated.pdf
```

**2. Permission Denied Errors**
```bash
# Fix file permissions
chmod 644 your-input.pdf
chmod 755 $(pwd)  # Directory permissions

# Run with user mapping (Linux only)
docker run --user $(id -u):$(id -g) \
  -v $(pwd):/app/input -v $(pwd):/app/output \
  pdf-translator:latest translate /app/input/file.pdf /app/output/file-en.pdf
```

**3. Container Won't Start**
```bash
# Check container logs
docker run pdf-translator:latest test

# Debug with interactive mode
docker run -it --rm pdf-translator:latest bash
```

**4. Out of Memory Issues**
```bash
# Increase Docker memory limit or use smaller batch size
docker run -v $(pwd):/app/input -v $(pwd):/app/output \
  pdf-translator:latest \
  translate /app/input/large.pdf /app/output/large-en.pdf \
  --batch-size 8
```

### Debug Commands

```bash
# Check model files
docker run --rm pdf-translator:latest bash -c "ls -la /app/models/Helsinki-NLP/opus-mt-de-en/"

# Check Python dependencies
docker run --rm pdf-translator:latest pip list

# Test model loading
docker run --rm pdf-translator:latest python -c "
from transformers import MarianMTModel, MarianTokenizer
model = MarianMTModel.from_pretrained('/app/models/Helsinki-NLP/opus-mt-de-en', local_files_only=True)
print('Model loaded successfully!')
"
```

## 📊 Performance Benchmarks

| Document Size | Processing Time | Memory Usage |
|---------------|----------------|--------------|
| 1-5 pages | 10-30 seconds | 1.5GB |
| 6-20 pages | 30-120 seconds | 2GB |
| 21-50 pages | 2-5 minutes | 2.5GB |
| 50+ pages | 5+ minutes | 3GB+ |

**Optimization Tips:**
- Use `--batch-size 8` for large documents to reduce memory usage
- Use `--no-formatting` for faster processing when layout isn't critical
- Enable caching with `--cache-file` for repeated translations

## 🐳 Docker Commands Reference

### Image Management

```bash
# List images
docker images pdf-translator

# Remove old images
docker rmi pdf-translator:old-version

# Check image size
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

# Inspect image details
docker inspect pdf-translator:latest
```

### Container Management

```bash
# Run in background (daemon mode)
docker run -d --name pdf-translator-service \
  -v $(pwd):/app/input -v $(pwd):/app/output \
  pdf-translator:latest tail -f /dev/null

# Execute commands in running container
docker exec pdf-translator-service \
  python pdf_translator.py /app/input/test.pdf /app/output/test-en.pdf --offline

# Stop and remove container
docker stop pdf-translator-service
docker rm pdf-translator-service
```

### Maintenance

```bash
# Clean up unused containers and images
docker system prune

# Remove all stopped containers
docker container prune

# Remove unused images
docker image prune
```

## 🔐 Security Considerations

- **Non-root execution**: Container runs as unprivileged user `pdfuser`
- **Read-only root filesystem**: Application files are immutable
- **Minimal attack surface**: Only necessary dependencies included
- **No network access required**: Completely offline operation
- **Volume isolation**: Only mounted directories are accessible

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with Docker: `./docker-build.sh -t`
5. Submit a pull request

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/pdf-translation-service/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/pdf-translation-service/discussions)
- **Docker Hub**: [pdf-translator](https://hub.docker.com/r/yourusername/pdf-translator)

---

**Built with ❤️ by Ganesh Sharma for offline PDF translation**