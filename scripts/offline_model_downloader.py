#!/usr/bin/env python3
"""
Complete Offline Model Downloader for Hugging Face Models
Downloads all necessary files for Helsinki-NLP/opus-mt-de-en model
Bypasses SSL certificate issues entirely
"""

import os
import sys
import ssl
import urllib.request
import urllib.error
from pathlib import Path
import json
import time

class ModelDownloader:
    def __init__(self):
        self.model_name = "Helsinki-NLP/opus-mt-de-en"
        self.base_url = f"https://huggingface.co/{self.model_name}/resolve/main/"
        self.local_dir = Path("./models") / self.model_name
        
        # Required files for the model
        self.required_files = [
            "config.json",
            "pytorch_model.bin", 
            "source.spm",
            "target.spm",
            "tokenizer_config.json",
            "vocab.json",
            "generation_config.json"  # Sometimes needed
        ]
        
    def create_unverified_context(self):
        """Create SSL context that doesn't verify certificates."""
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        return context
        
    def download_file(self, filename, max_retries=3):
        """Download a single file with retries and SSL bypass."""
        url = self.base_url + filename
        local_path = self.local_dir / filename
        
        if local_path.exists():
            print(f"✅ {filename} already exists, skipping...")
            return True
            
        print(f"📥 Downloading {filename}...")
        
        for attempt in range(max_retries):
            try:
                # Create request with proper headers
                request = urllib.request.Request(url)
                request.add_header('User-Agent', 
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
                request.add_header('Accept', '*/*')
                request.add_header('Connection', 'keep-alive')
                
                # Use unverified SSL context
                context = self.create_unverified_context()
                
                with urllib.request.urlopen(request, context=context, timeout=30) as response:
                    total_size = response.headers.get('Content-Length')
                    if total_size:
                        total_size = int(total_size)
                        print(f"   📊 Size: {total_size / (1024*1024):.1f} MB")
                    
                    with open(local_path, 'wb') as f:
                        downloaded = 0
                        chunk_size = 8192
                        
                        while True:
                            chunk = response.read(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            
                            if total_size:
                                progress = (downloaded / total_size) * 100
                                print(f"\r   ⏳ Progress: {progress:.1f}%", end='', flush=True)
                        
                        print()  # New line after progress
                
                print(f"✅ Downloaded {filename}")
                return True
                
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    print(f"⚠️ {filename} not found (404) - might be optional")
                    return True  # Some files are optional
                else:
                    print(f"❌ HTTP Error {e.code} for {filename}")
                    
            except Exception as e:
                print(f"❌ Attempt {attempt + 1} failed for {filename}: {e}")
                if attempt < max_retries - 1:
                    print(f"🔄 Retrying in 2 seconds...")
                    time.sleep(2)
        
        print(f"❌ Failed to download {filename} after {max_retries} attempts")
        return False
    
    def download_all_files(self):
        """Download all required model files."""
        print(f"📁 Creating model directory: {self.local_dir}")
        self.local_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"🚀 Starting download of {self.model_name}")
        print("🔓 Using SSL bypass for corporate network compatibility")
        print()
        
        success_count = 0
        critical_files = ["config.json", "pytorch_model.bin", "tokenizer_config.json"]
        
        for filename in self.required_files:
            if self.download_file(filename):
                success_count += 1
        
        print(f"\n📊 Download Summary:")
        print(f"   ✅ Successfully downloaded: {success_count}/{len(self.required_files)} files")
        
        # Check if critical files are present
        missing_critical = [f for f in critical_files if not (self.local_dir / f).exists()]
        
        if missing_critical:
            print(f"   ❌ Missing critical files: {missing_critical}")
            return False
        else:
            print(f"   🎉 All critical files downloaded successfully!")
            return True
    
    def create_test_script(self):
        """Create a test script to verify the downloaded model works."""
        test_script = '''#!/usr/bin/env python3
"""Test script for downloaded model"""

import sys
from pathlib import Path

try:
    from transformers import MarianMTModel, MarianTokenizer
    
    model_path = "./models/Helsinki-NLP/opus-mt-de-en"
    
    print("🧪 Testing downloaded model...")
    print(f"📁 Model path: {Path(model_path).absolute()}")
    
    # Load model and tokenizer from local files
    tokenizer = MarianTokenizer.from_pretrained(model_path, local_files_only=True)
    model = MarianMTModel.from_pretrained(model_path, local_files_only=True)
    
    # Test translation
    test_text = "Hallo Welt! Wie geht es dir?"
    print(f"🇩🇪 German: {test_text}")
    
    tokens = tokenizer(test_text, return_tensors="pt", padding=True)
    translated = model.generate(**tokens)
    result = tokenizer.decode(translated[0], skip_special_tokens=True)
    
    print(f"🇺🇸 English: {result}")
    print("✅ Model test successful!")
    
except Exception as e:
    print(f"❌ Model test failed: {e}")
    sys.exit(1)
'''
        
        with open("test_offline_model.py", 'w', encoding='utf-8') as f:
            f.write(test_script)
        
        print("📝 Created test_offline_model.py")

def main():
    print("🔧 Offline Model Downloader for PDF Translation")
    print("="*50)
    
    downloader = ModelDownloader()
    
    if downloader.download_all_files():
        downloader.create_test_script()
        
        print("\n🎉 Setup Complete!")
        print("\n🧪 Next steps:")
        print("1. Test the model: python test_offline_model.py")
        print("2. Use in PDF translator: python pdf_translator.py input.pdf output.pdf --model './models/Helsinki-NLP/opus-mt-de-en'")
        print("\n💡 The model is now fully offline - no internet required!")
        
    else:
        print("\n❌ Download failed!")
        print("\n🔧 Alternative options:")
        print("1. Try downloading from a different network")
        print("2. Ask someone to download and share the model files")
        print("3. Use a VPN to bypass network restrictions")

if __name__ == "__main__":
    main()