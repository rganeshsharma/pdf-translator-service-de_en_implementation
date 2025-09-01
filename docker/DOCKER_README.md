# PDF Translation Service - Docker Edition 🐳📄

[![Docker Pulls](https://img.shields.io/docker/pulls/rganeshsharma2489/pdf-translator-service-de_en_docker_deploy)](https://hub.docker.com/repository/docker/rganeshsharma2489/pdf-translator-service-de_en_docker_deploy)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

A standalone Docker container for translating German PDF documents to English while preserving original layout and formatting. **Completely offline** - no internet required after initial setup!

## 🚀 Quick Start (Ready-to-Use Image)

Download the image from DockerHub:

```bash
# Pull the pre-built image
docker pull rganeshsharma2489/pdf-translator-service-de_en_docker_deploy:1.0.0

# Create directories for your files
mkdir -p input output

# Put your German PDF in the input directory
cp your-german-document.pdf input/

# Translate it!
docker run -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output \
  rganeshsharma2489/pdf-translator-service-de_en_docker_deploy:1.0.0 \
  translate /app/input/your-german-document.pdf /app/output/english-document.pdf
```

**That's it!** Check the `output` directory for your translated PDF.

## 🏗️ Customize the Image and Tag

### Prerequisites

**Docker installed** (version 20.10+) 

## Quick Start
```bash
# Pull the image
docker pull rganeshsharma2489/pdf-translator-service-de_en_docker_deploy:1.0.0

# Tag your Image for example 
docker tag rganeshsharma2489/pdf-translator-service-de_en_docker_deploy:1.0.0 pdf-translator:latest

# Create directories
mkdir -p input output

# Add your German PDF to input/ directory
cp your-german-document.pdf input/

# Translate it!
docker run -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output \
  pdf-translator:latest \
  translate /app/input/your-german-document.pdf /app/output/english-document.pdf

```

## 📖 Usage Examples

### Basic Translation

```bash
# Create directories
mkdir -p input output

# Translate a PDF
docker run -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output \
  pdf-translator:latest \
  translate /app/input/contract.pdf /app/output/contract-english.pdf
```

### Advanced Options

```bash
# Fast translation (no formatting preservation)
docker run -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output \
  pdf-translator:latest \
  translate /app/input/document.pdf /app/output/translated.pdf --no-formatting

# Verbose output with custom batch size
docker run -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output \
  pdf-translator:latest \
  translate /app/input/document.pdf /app/output/translated.pdf \
  --batch-size 32 --verbose

# Use translation cache for faster repeated translations
mkdir -p cache
docker run \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  -v $(pwd)/cache:/app/cache \
  pdf-translator:latest \
  translate /app/input/document.pdf /app/output/translated.pdf \
  --cache-file /app/cache/translations.json
```

### Batch Processing

```bash
# Translate all PDFs in a directory
for pdf in input/*.pdf; do
    filename=$(basename "$pdf" .pdf)
    echo "Translating: $filename"
    
    docker run -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output \
      pdf-translator:latest \
      translate "/app/input/$filename.pdf" "/app/output/$filename-english.pdf"
done
```

### Interactive Mode

```bash
# Open a shell inside the container
docker run -it --rm \
  -v $(pwd)/input:/app/input \
  -v $(pwd)/output:/app/output \
  pdf-translator:latest bash

# Inside the container, you can run:
python de_en-translator_v2.py /app/input/test.pdf /app/output/test-en.pdf --model "./models/Helsinki-NLP/opus-mt-de-en"
```

## 🔧 Docker Compose (Persistent Service)

Create a `docker-compose.yml`:

```yaml
version: '3.8'

services:
  pdf-translator:
    image: pdf-translator:latest
    container_name: pdf-translator-service
    volumes:
      - ./input:/app/input
      - ./output:/app/output
      - ./cache:/app/cache
    command: tail -f /dev/null  # Keep running
    restart: unless-stopped
```

Use it:

```bash
# Start the service
docker-compose up -d

# Translate files
docker exec pdf-translator-service \
  python de_en-translator_v2.py /app/input/document.pdf /app/output/document-en.pdf --model "./models/Helsinki-NLP/opus-mt-de-en"

# Stop the service
docker-compose down
```

## 📊 What's Inside the Container

- **Python 3.11** with all required dependencies
- **Translation Model**: Helsinki-NLP/opus-mt-de-en (~284MB)
- **PDF Processing**: PyMuPDF for layout preservation
- **Fonts**: Liberation and DejaVu fonts for better compatibility
- **Security**: Runs as non-root user
- **Size**: ~2-3GB total (includes model files)

## 🏥 Testing and Troubleshooting

### Test the Container

```bash
# Quick model test
docker run --rm pdf-translator:latest test

# Check available commands
docker run --rm pdf-translator:latest --help

# Check model files
docker run --rm pdf-translator:latest bash -c "ls -la /app/models/Helsinki-NLP/opus-mt-de-en/"
```

### Common Issues

**1. "Input file not found"**
```bash
# Check your file path and mount points
ls input/your-file.pdf  # File should exist locally
```

**2. Permission denied**
```bash
# Fix file permissions
chmod 644 input/*.pdf
chmod 755 input output
```

**3. Container runs out of memory**
```bash
# Use smaller batch size
docker run -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output \
  pdf-translator:latest \
  translate /app/input/large.pdf /app/output/large-en.pdf --batch-size 8
```

## 📈 Performance Benchmarks

| Document Size | Processing Time | Memory Usage | Container Size |
|---------------|----------------|--------------|----------------|
| 1-5 pages | 10-30 seconds | 1.5GB | 2.8GB |
| 6-20 pages | 30-120 seconds | 2GB | 2.8GB |
| 21-50 pages | 2-5 minutes | 2.5GB | 2.8GB |
| 50+ pages | 5+ minutes | 3GB+ | 2.8GB |

**Optimization Tips:**
- Use `--no-formatting` for 2x faster processing
- Enable caching with `--cache-file` for repeated translations
- Use smaller `--batch-size` for large documents


## 🔐 Security Features

- **Non-root execution**: Container runs as unprivileged user
- **Read-only root filesystem**: Application files are immutable
- **No network access**: Complete offline operation
- **Minimal attack surface**: Only essential dependencies
- **Volume isolation**: Only mounted directories accessible

## ✨ Key Advantages of Docker Approach

- **📦 Self-contained**: Models and dependencies included
- **🔄 Reproducible**: Same environment everywhere
- **🚀 Easy deployment**: Single `docker run` command
- **💻 Cross-platform**: Works on Windows, Mac, Linux
- **🔒 Secure**: Isolated from host system
- **📱 Portable**: Easy to share and distribute

## 🆚 Comparison with Other Approaches

| Approach | Setup Complexity | Distribution | Isolation | Resource Usage |
|----------|------------------|--------------|-----------|----------------|
| **Docker** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Python Local | ⭐⭐ | ⭐ | ⭐ | ⭐⭐⭐⭐⭐ |
| Kubernetes | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ |

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch
3. Test with Docker: `./docker-build.sh -t`
4. Submit a pull request

## 📞 Support

- **GitHub Issues**: [Report bugs](https://github.com/pdf-translator-service-de_en_docker_deploy/issues) - **Docker Hub**: [View image](https://hub.docker.com/repository/docker/rganeshsharma2489/pdf-translator-service-de_en_docker_deplo)
- **Documentation**: [Full docs](./DOCKER_README.md)

---
 
**🐳 Containerized for your convenience!**

*Translate German PDFs to English with a single Docker command - no setup hassles, no dependency conflicts, just results.*

**Built with ❤️ by the Ganesh Sharma**

*Making document translation accessible, fast, and reliable for everyone.*