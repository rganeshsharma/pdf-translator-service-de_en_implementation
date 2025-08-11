#!/usr/bin/env python3
"""
Local German-English PDF Translator with Layout Preservation
Translates PDF documents offline while maintaining original formatting.
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import json
import re

try:
    import pymupdf  # PyMuPDF
    from transformers import MarianMTModel, MarianTokenizer
    import torch
except ImportError as e:
    print(f"Missing required dependencies: {e}")
    print("Please run: pip install PyMuPDF transformers torch sentencepiece")
    sys.exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PDFTranslator:
    """German to English PDF translator with layout preservation."""
    
    def __init__(self, model_name: str = "Helsinki-NLP/opus-mt-de-en"):
        """Initialize the translator with MarianMT model."""
        self.model_name = model_name
        self.tokenizer: Optional[MarianTokenizer] = None
        self.model: Optional[MarianMTModel] = None
        self.translation_cache = {}
        self.force_offline = False
        
        # Text processing settings
        self.max_seq_length = 512
        self.min_text_length = 2
        self.font_substitution_map = {
            # Common German fonts to English equivalents
            'Times-Roman': 'Times-Roman',
            'Helvetica': 'Helvetica', 
            'Arial': 'Arial',
            'Courier': 'Courier'
        }
        
    def load_model(self):
        """Load the MarianMT translation model with offline support."""
        try:
            logger.info(f"Loading translation model: {self.model_name}")
            
            # Check if it's a local path or offline mode is forced
            if os.path.exists(self.model_name) or self.force_offline:
                model_path = self.model_name if os.path.exists(self.model_name) else f"./models/{self.model_name}"
                if os.path.exists(model_path):
                    logger.info(f"Loading from local path: {model_path}")
                    self.tokenizer = MarianTokenizer.from_pretrained(model_path, local_files_only=True)
                    self.model = MarianMTModel.from_pretrained(model_path, local_files_only=True)
                    logger.info("Translation model loaded from local files")
                    return
                else:
                    raise FileNotFoundError(f"Local model not found at {model_path}")
            
            # Try online download
            try:
                self.tokenizer = MarianTokenizer.from_pretrained(self.model_name)
                self.model = MarianMTModel.from_pretrained(self.model_name)
                logger.info("Translation model loaded from Hugging Face Hub")
                return
            except Exception as online_error:
                logger.warning(f"Online download failed: {online_error}")
                
                # Check if model exists in default local location
                local_model_path = f"./models/{self.model_name}"
                if os.path.exists(local_model_path):
                    logger.info(f"Trying local backup at: {local_model_path}")
                    self.tokenizer = MarianTokenizer.from_pretrained(local_model_path, local_files_only=True)
                    self.model = MarianMTModel.from_pretrained(local_model_path, local_files_only=True)
                    logger.info("Translation model loaded from local backup")
                    return
                else:
                    raise online_error
                    
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            logger.error("\n🔧 SOLUTION:")
            logger.error("1. Run: python offline_model_downloader.py")
            logger.error("2. Then: python pdf_translator.py input.pdf output.pdf --model './models/Helsinki-NLP/opus-mt-de-en'")
            logger.error("3. Or fix your SSL certificates")
            raise
    
    def translate_text(self, text: str) -> str:
        """Translate German text to English with caching."""
        if not text or len(text.strip()) < self.min_text_length:
            return text
            
        # Clean and normalize text for better translation
        text = re.sub(r'\s+', ' ', text.strip())  # Normalize whitespace
        
        # Check cache first
        text_key = text.strip()
        if text_key in self.translation_cache:
            return self.translation_cache[text_key]
        
        try:
            # Tokenize and translate
            tokens = self.tokenizer(text, return_tensors="pt", padding=True, truncation=True, 
                                  max_length=self.max_seq_length)
            
            with torch.no_grad():
                translated = self.model.generate(**tokens, max_length=self.max_seq_length)
            
            result = self.tokenizer.decode(translated[0], skip_special_tokens=True)
            
            # Cache the result
            self.translation_cache[text_key] = result
            return result
            
        except Exception as e:
            logger.warning(f"Translation failed for text '{text[:50]}...': {e}")
            return text  # Return original on failure
    
    def translate_batch(self, texts: List[str], batch_size: int = 16) -> List[str]:
        """Translate multiple texts efficiently in batches."""
        if not texts:
            return []
        
        results = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            
            # Filter out empty/short texts and normalize
            valid_texts = []
            for j, text in enumerate(batch):
                if text and len(text.strip()) >= self.min_text_length:
                    # Clean and normalize text
                    cleaned_text = re.sub(r'\s+', ' ', text.strip())
                    valid_texts.append((j, cleaned_text))
            
            if not valid_texts:
                results.extend(batch)
                continue
            
            try:
                # Prepare batch for translation
                texts_to_translate = [text for _, text in valid_texts]
                tokens = self.tokenizer(texts_to_translate, return_tensors="pt", 
                                      padding=True, truncation=True, 
                                      max_length=self.max_seq_length)
                
                with torch.no_grad():
                    translated = self.model.generate(**tokens, max_length=self.max_seq_length)
                
                # Decode results
                translated_texts = [self.tokenizer.decode(t, skip_special_tokens=True) 
                                  for t in translated]
                
                # Map back to original positions
                batch_results = list(batch)
                for (orig_idx, cleaned_text), translation in zip(valid_texts, translated_texts):
                    batch_results[orig_idx] = translation
                    # Cache individual results using original text
                    original_text = batch[orig_idx].strip()
                    self.translation_cache[original_text] = translation
                
                results.extend(batch_results)
                
            except Exception as e:
                logger.warning(f"Batch translation failed: {e}")
                results.extend(batch)  # Return originals on failure
        
        return results
    
    def extract_text_with_layout(self, pdf_path: str) -> List[Dict]:
        """Extract text with detailed layout and positioning information."""
        try:
            doc = pymupdf.open(pdf_path)
            pages_data = []
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                
                # Extract text with detailed formatting
                blocks = page.get_text("dict", flags=11)["blocks"]
                
                page_data = {
                    'page_number': page_num,
                    'page_size': (page.rect.width, page.rect.height),
                    'text_elements': []
                }
                
                for block in blocks:
                    if 'lines' in block:  # Text block
                        for line in block['lines']:
                            for span in line['spans']:
                                if span['text'].strip():  # Skip empty text
                                    element = {
                                        'text': span['text'],
                                        'bbox': span['bbox'],  # (x0, y0, x1, y1)
                                        'font': span['font'],
                                        'size': span['size'],
                                        'color': span.get('color', 0),
                                        'flags': span.get('flags', 0),  # Bold, italic, etc.
                                        'ascender': span.get('ascender', 0.8),
                                        'descender': span.get('descender', -0.2)
                                    }
                                    page_data['text_elements'].append(element)
                
                pages_data.append(page_data)
                logger.info(f"Extracted {len(page_data['text_elements'])} text elements from page {page_num + 1}")
            
            doc.close()
            return pages_data
            
        except Exception as e:
            logger.error(f"Failed to extract text from {pdf_path}: {e}")
            raise
    
    def calculate_text_fit(self, original_text: str, translated_text: str, 
                          bbox: Tuple[float, float, float, float], font_size: float) -> Dict:
        """Calculate if translated text fits in original space and adjust if needed."""
        x0, y0, x1, y1 = bbox
        available_width = x1 - x0
        available_height = y1 - y0
        
        # Rough character width estimation (varies by font)
        avg_char_width = font_size * 0.6  # Approximation for most fonts
        
        original_width = len(original_text) * avg_char_width
        translated_width = len(translated_text) * avg_char_width
        
        scale_factor = 1.0
        adjusted_font_size = font_size
        
        # If translated text is wider, adjust font size
        if translated_width > available_width and available_width > 0:
            scale_factor = available_width / translated_width
            adjusted_font_size = font_size * scale_factor
            
            # Don't make font too small
            min_font_size = max(6, font_size * 0.7)
            if adjusted_font_size < min_font_size:
                adjusted_font_size = min_font_size
                scale_factor = adjusted_font_size / font_size
        
        return {
            'fits': translated_width <= available_width,
            'scale_factor': scale_factor,
            'adjusted_font_size': adjusted_font_size,
            'original_width': original_width,
            'translated_width': translated_width,
            'available_width': available_width
        }
    
    def get_suitable_font(self, original_font: str, target_language: str = "en") -> str:
        """Get suitable font for target language, with fallbacks."""
        if original_font in self.font_substitution_map:
            return self.font_substitution_map[original_font]
        
        # Common fallbacks for different font types
        if 'times' in original_font.lower() or 'serif' in original_font.lower():
            return 'Times-Roman'
        elif 'helvetica' in original_font.lower() or 'arial' in original_font.lower():
            return 'Helvetica'
        elif 'courier' in original_font.lower() or 'mono' in original_font.lower():
            return 'Courier'
        else:
            return 'Helvetica'  # Universal fallback
    
    def translate_pdf(self, input_path: str, output_path: str, 
                     batch_size: int = 16, preserve_formatting: bool = True) -> bool:
        """Translate PDF from German to English while preserving layout."""
        try:
            # Load translation model if not already loaded
            if self.model is None:
                self.load_model()
            
            # Extract text with layout information
            logger.info(f"Extracting text from {input_path}")
            pages_data = self.extract_text_with_layout(input_path)
            
            # Collect all texts for batch translation
            all_texts = []
            text_to_element_map = {}
            
            for page_data in pages_data:
                for element in page_data['text_elements']:
                    text = element['text'].strip()
                    if text and len(text) >= self.min_text_length:
                        all_texts.append(text)
                        if text not in text_to_element_map:
                            text_to_element_map[text] = []
                        text_to_element_map[text].append(element)
            
            # Translate all texts in batches
            logger.info(f"Translating {len(all_texts)} text segments")
            if all_texts:
                translated_texts = self.translate_batch(all_texts, batch_size)
                
                # Create translation mapping
                translation_map = {}
                for original, translated in zip(all_texts, translated_texts):
                    translation_map[original] = translated
            else:
                translation_map = {}
            
            # Create new PDF with translated text
            logger.info(f"Creating translated PDF: {output_path}")
            return self.create_translated_pdf(input_path, output_path, pages_data, 
                                            translation_map, preserve_formatting)
            
        except Exception as e:
            logger.error(f"PDF translation failed: {e}")
            return False
    
    def create_translated_pdf(self, input_path: str, output_path: str, 
                            pages_data: List[Dict], translation_map: Dict[str, str],
                            preserve_formatting: bool = True) -> bool:
        """Create new PDF with translated text using coordinate-based replacement."""
        try:
            # Open original PDF
            doc = pymupdf.open(input_path)
            
            for page_idx, page_data in enumerate(pages_data):
                page = doc[page_idx]
                
                # Process each text element
                redactions = []  # Store areas to redact (remove original text)
                replacements = []  # Store new text to insert
                
                for element in page_data['text_elements']:
                    original_text = element['text'].strip()
                    
                    if original_text in translation_map:
                        translated_text = translation_map[original_text]
                        
                        if original_text != translated_text:  # Only replace if different
                            bbox = element['bbox']
                            
                            # Calculate text fitting
                            fit_info = self.calculate_text_fit(original_text, translated_text, 
                                                             bbox, element['size'])
                            
                            # Add redaction for original text
                            redactions.append(pymupdf.Rect(bbox))
                            
                            # Prepare replacement text
                            font_name = self.get_suitable_font(element['font'])
                            font_size = fit_info['adjusted_font_size'] if preserve_formatting else element['size']
                            
                            replacements.append({
                                'text': translated_text,
                                'point': (bbox[0], bbox[1] + font_size * 0.8),  # Adjust for baseline
                                'font': font_name,
                                'font_size': font_size,
                                'color': element['color']
                            })
                
                # Apply redactions (remove original text)
                for rect in redactions:
                    page.add_redact_annot(rect)
                
                if redactions:
                    page.apply_redactions()
                
                # Insert translated text
                for replacement in replacements:
                    try:
                        # Set text color
                        color_val = replacement['color']
                        if color_val != 0:  # If not black
                            r = ((color_val >> 16) & 255) / 255
                            g = ((color_val >> 8) & 255) / 255
                            b = (color_val & 255) / 255
                        else:
                            r, g, b = 0, 0, 0  # Black
                        
                        # Insert text at calculated position
                        result = page.insert_text(
                            replacement['point'],
                            replacement['text'],
                            fontname=replacement['font'],
                            fontsize=replacement['font_size'],
                            color=(r, g, b)
                        )
                        
                        if result < 0:
                            logger.warning(f"Failed to insert text: {replacement['text'][:30]}...")
                            
                    except Exception as e:
                        logger.warning(f"Failed to insert replacement text: {e}")
                
                logger.info(f"Processed page {page_idx + 1}: {len(replacements)} replacements made")
            
            # Save the translated PDF
            doc.save(output_path)
            doc.close()
            
            logger.info(f"Translation completed successfully: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create translated PDF: {e}")
            return False
    
    def save_translation_cache(self, cache_file: str):
        """Save translation cache to file for reuse."""
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.translation_cache, f, ensure_ascii=False, indent=2)
            logger.info(f"Translation cache saved: {cache_file}")
        except Exception as e:
            logger.warning(f"Failed to save cache: {e}")
    
    def load_translation_cache(self, cache_file: str):
        """Load translation cache from file."""
        try:
            cache_path = Path(cache_file)
            if cache_path.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    self.translation_cache = json.load(f)
                logger.info(f"Translation cache loaded: {len(self.translation_cache)} entries")
        except Exception as e:
            logger.warning(f"Failed to load cache: {e}")

def main():
    """Main function with command-line interface."""
    parser = argparse.ArgumentParser(description="Translate German PDF to English with layout preservation")
    parser.add_argument("input_pdf", help="Input German PDF file")
    parser.add_argument("output_pdf", help="Output English PDF file")
    parser.add_argument("--model", default="Helsinki-NLP/opus-mt-de-en", 
                       help="Translation model path or name (default: Helsinki-NLP/opus-mt-de-en)")
    parser.add_argument("--offline", action="store_true",
                       help="Force offline mode - use local model only")
    parser.add_argument("--batch-size", type=int, default=16, 
                       help="Translation batch size (default: 16)")
    parser.add_argument("--cache-file", help="Translation cache file (optional)")
    parser.add_argument("--no-formatting", action="store_true", 
                       help="Disable formatting preservation (faster)")
    parser.add_argument("--verbose", "-v", action="store_true", 
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Validate input file
    input_path = Path(args.input_pdf)
    if not input_path.exists():
        print(f"Error: Input file not found: {args.input_pdf}")
        return 1
    
    # Create output directory if needed
    output_path = Path(args.output_pdf)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Initialize translator
    translator = PDFTranslator(args.model)
    
    # Force offline mode if requested
    if args.offline:
        translator.force_offline = True
    
    # Load translation cache if specified
    if args.cache_file:
        translator.load_translation_cache(args.cache_file)
    
    try:
        # Perform translation
        success = translator.translate_pdf(
            str(input_path), 
            str(output_path),
            batch_size=args.batch_size,
            preserve_formatting=not args.no_formatting
        )
        
        # Save translation cache if specified
        if args.cache_file:
            translator.save_translation_cache(args.cache_file)
        
        if success:
            print(f"Translation completed successfully: {output_path}")
            return 0
        else:
            print("Translation failed. Check logs for details.")
            return 1
            
    except KeyboardInterrupt:
        print("\nTranslation cancelled by user.")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())