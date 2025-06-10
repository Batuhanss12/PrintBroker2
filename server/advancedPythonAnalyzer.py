#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
import os
from pathlib import Path
import re

# Try to import optional libraries
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import magic
    HAS_MAGIC = True
except ImportError:
    HAS_MAGIC = False

class AdvancedDesignAnalyzer:
    def __init__(self):
        self.mm_per_inch = 25.4
        self.pts_per_inch = 72
        self.pts_to_mm = self.mm_per_inch / self.pts_per_inch

    def analyze_file(self, file_path, file_name, mime_type):
        """Ana dosya analiz fonksiyonu"""
        try:
            if not os.path.exists(file_path):
                return self.create_error_result(f"Dosya bulunamadı: {file_path}")

            print(f"🔍 Python analizi başlatıldı: {file_name}", file=sys.stderr)

            # MIME type belirleme
            if not mime_type:
                if HAS_MAGIC:
                    mime_type = magic.from_file(file_path, mime=True)
                else:
                    # Dosya uzantısından MIME type belirle
                    ext = Path(file_path).suffix.lower()
                    mime_map = {
                        '.pdf': 'application/pdf',
                        '.svg': 'image/svg+xml',
                        '.eps': 'application/postscript',
                        '.ai': 'application/postscript',
                        '.jpg': 'image/jpeg',
                        '.jpeg': 'image/jpeg',
                        '.png': 'image/png',
                        '.bmp': 'image/bmp',
                        '.tiff': 'image/tiff'
                    }
                    mime_type = mime_map.get(ext, 'application/octet-stream')

            # Dosya türüne göre analiz
            if mime_type == 'application/pdf':
                return self.analyze_pdf_advanced(file_path, file_name)
            elif mime_type == 'image/svg+xml':
                return self.analyze_svg_advanced(file_path, file_name)
            elif mime_type in ['image/jpeg', 'image/png', 'image/bmp', 'image/tiff']:
                return self.analyze_image_advanced(file_path, file_name)
            elif 'postscript' in mime_type or mime_type == 'application/eps':
                return self.analyze_eps_advanced(file_path, file_name)
            else:
                return self.analyze_by_extension(file_path, file_name)

        except Exception as e:
            print(f"❌ Python analiz hatası: {str(e)}", file=sys.stderr)
            return self.create_error_result(f"Analiz hatası: {str(e)}")

    def analyze_pdf_advanced(self, file_path, file_name):
        """Gelişmiş PDF analizi"""
        try:
            if not HAS_PYMUPDF:
                return self.analyze_pdf_basic(file_path, file_name)

            doc = fitz.open(file_path)
            page = doc[0]  # İlk sayfa

            # Sayfa boyutlarını al
            rect = page.rect
            width_pts = rect.width
            height_pts = rect.height

            # Points'i mm'ye çevir
            original_width_mm = round(width_pts * self.pts_to_mm)
            original_height_mm = round(height_pts * self.pts_to_mm)

            # Otomatik ölçekle
            try:
                original_width_mm = float(original_width_mm) if isinstance(original_width_mm, str) else original_width_mm
                original_height_mm = float(original_height_mm) if isinstance(original_height_mm, str) else original_height_mm
                width_mm, height_mm = self.scale_oversized_design(original_width_mm, original_height_mm)
            except (ValueError, TypeError) as e:
                print(f"Dimension scaling error: {e}", file=sys.stderr)
                width_mm, height_mm = 50, 30  # fallback dimensions

            # İçerik analizi
            try:
                text_blocks = page.get_text("blocks")
                image_list = page.get_images()
                has_text = len(text_blocks) > 0
                has_images = len(image_list) > 0
            except:
                has_text = False
                has_images = False

            # Tasarım kategorisi belirleme
            category = self.determine_category(width_mm, height_mm, file_name, has_text, has_images)

            # Sayfa sayısı
            page_count = len(doc)
            doc.close()

            # Rotate önerisi
            should_rotate = self.should_rotate(width_mm, height_mm, category)

            return {
                "success": True,
                "dimensions": {
                    "widthMM": width_mm,
                    "heightMM": height_mm,
                    "category": category,
                    "confidence": 0.95,
                    "description": f"PDF analizi: {width_mm}x{height_mm}mm {category}",
                    "shouldRotate": should_rotate
                },
                "detectedDesigns": 1,
                "pageCount": page_count,
                "hasText": len(text_blocks) > 0,
                "hasImages": len(image_list) > 0,
                "processingNotes": [
                    "PDF boyutları PyMuPDF ile tespit edildi",
                    f"Orijinal boyut: {original_width_mm}x{original_height_mm}mm",
                    f"Ölçeklenmiş boyut: {width_mm}x{height_mm}mm" if (width_mm != original_width_mm or height_mm != original_height_mm) else f"Boyut: {width_mm}x{height_mm}mm",
                    f"Kategori: {category}",
                    f"Metin blok sayısı: {len(text_blocks)}",
                    f"Görsel sayısı: {len(image_list)}",
                    f"Sayfa sayısı: {page_count}"
                ]
            }

        except Exception as e:
            print(f"PDF analiz hatası: {str(e)}", file=sys.stderr)
            return self.analyze_pdf_basic(file_path, file_name)

    def analyze_pdf_basic(self, file_path, file_name):
        """Temel PDF analizi - kütüphane bağımsız"""
        try:
            # PDF dosyasını binary olarak oku ve MediaBox ara
            with open(file_path, 'rb') as f:
                content = f.read().decode('latin1', errors='ignore')

            # MediaBox pattern'i ara
            import re
            mediabox_pattern = r'/MediaBox\s*\[\s*(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s+(\d+\.?\d*)\s*\]'
            match = re.search(mediabox_pattern, content)

            if match:
                x1, y1, x2, y2 = map(float, match.groups())
                width_pts = x2 - x1
                height_pts = y2 - y1
            else:
                # Varsayılan A4 boyutları
                width_pts = 595
                height_pts = 842

            # Points'i mm'ye çevir
            width_mm = round(width_pts * self.pts_to_mm)
            height_mm = round(height_pts * self.pts_to_mm)

            category = self.determine_category(width_mm, height_mm, file_name)
            should_rotate = self.should_rotate(width_mm, height_mm, category)

            return {
                "success": True,
                "dimensions": {
                    "widthMM": width_mm,
                    "heightMM": height_mm,
                    "category": category,
                    "confidence": 0.7,
                    "description": f"Temel PDF analizi: {width_mm}x{height_mm}mm {category}",
                    "shouldRotate": should_rotate
                },
                "detectedDesigns": 1,
                "processingNotes": [
                    "Temel PDF boyut analizi yapıldı",
                    f"MediaBox: {width_pts}x{height_pts}pts",
                    f"Boyutlar: {width_mm}x{height_mm}mm",
                    f"Kategori: {category}"
                ]
            }

        except Exception as e:
            print(f"Temel PDF analiz hatası: {str(e)}", file=sys.stderr)
            return self.create_fallback_result(file_name)

    def analyze_svg_advanced(self, file_path, file_name):
        """Gelişmiş SVG analizi"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()

            # SVG boyutlarını parse et
            width_mm, height_mm = self.parse_svg_dimensions(svg_content)

            # İçerik analizi
            has_text = '<text' in svg_content or '<tspan' in svg_content
            has_images = '<image' in svg_content
            has_paths = '<path' in svg_content
            has_shapes = any(tag in svg_content for tag in ['<rect', '<circle', '<ellipse', '<polygon'])

            category = self.determine_category(width_mm, height_mm, file_name, has_text, has_images)
            should_rotate = self.should_rotate(width_mm, height_mm, category)

            return {
                "success": True,
                "dimensions": {
                    "widthMM": width_mm,
                    "heightMM": height_mm,
                    "category": category,
                    "confidence": 0.9,
                    "description": f"SVG analizi: {width_mm}x{height_mm}mm {category}",
                    "shouldRotate": should_rotate
                },
                "detectedDesigns": 1,
                "isVector": True,
                "hasText": has_text,
                "hasImages": has_images,
                "hasPaths": has_paths,
                "hasShapes": has_shapes,
                "processingNotes": [
                    "SVG dosyası analiz edildi",
                    f"Boyutlar: {width_mm}x{height_mm}mm",
                    f"Kategori: {category}",
                    f"Metin içeriği: {'Var' if has_text else 'Yok'}",
                    f"Görsel içeriği: {'Var' if has_images else 'Yok'}",
                    f"Vektör yollar: {'Var' if has_paths else 'Yok'}"
                ]
            }

        except Exception as e:
            print(f"SVG analiz hatası: {str(e)}", file=sys.stderr)
            return self.create_fallback_result(file_name)

    def analyze_image_advanced(self, file_path, file_name):
        """Gelişmiş görsel analizi"""
        try:
            # PIL ile görsel analizi
            with Image.open(file_path) as img:
                width_px, height_px = img.size
                dpi = img.info.get('dpi', (300, 300))
                if isinstance(dpi, tuple):
                    dpi_x, dpi_y = dpi
                else:
                    dpi_x = dpi_y = dpi

                # Pixel'den mm'ye çevir
                width_mm = round((width_px / dpi_x) * self.mm_per_inch)
                height_mm = round((height_px / dpi_y) * self.mm_per_inch)

                # OpenCV ile içerik analizi
                import cv2
                import numpy as np
                cv_img = cv2.imread(file_path)
                if cv_img is not None:
                    # Renk analizi
                    mean_color = np.mean(cv_img, axis=(0, 1))
                    is_grayscale = np.allclose(mean_color[0], mean_color[1]) and np.allclose(mean_color[1], mean_color[2])

                    # Kenar tespiti
                    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
                    edges = cv2.Canny(gray, 50, 150)
                    edge_density = np.sum(edges > 0) / edges.size

                    complexity = "basit" if edge_density < 0.1 else "orta" if edge_density < 0.3 else "karmaşık"
                else:
                    is_grayscale = False
                    complexity = "bilinmiyor"

                category = self.determine_category(width_mm, height_mm, file_name)
                should_rotate = self.should_rotate(width_mm, height_mm, category)

                return {
                    "success": True,
                    "dimensions": {
                        "widthMM": width_mm,
                        "heightMM": height_mm,
                        "category": category,
                        "confidence": 0.85,
                        "description": f"Görsel analizi: {width_mm}x{height_mm}mm {category}",
                        "shouldRotate": should_rotate
                    },
                    "detectedDesigns": 1,
                    "imageProperties": {
                        "widthPx": width_px,
                        "heightPx": height_px,
                        "dpi": dpi_x,
                        "isGrayscale": is_grayscale,
                        "complexity": complexity
                    },
                    "processingNotes": [
                        "Görsel dosyası analiz edildi",
                        f"Piksel boyutu: {width_px}x{height_px}px",
                        f"DPI: {dpi_x}",
                        f"Fiziksel boyut: {width_mm}x{height_mm}mm",
                        f"Renk: {'Gri tonlama' if is_grayscale else 'Renkli'}",
                        f"Karmaşıklık: {complexity}"
                    ]
                }

        except Exception as e:
            print(f"Görsel analiz hatası: {str(e)}", file=sys.stderr)
            return self.create_fallback_result(file_name)

    def analyze_eps_advanced(self, file_path, file_name):
        """Gelişmiş EPS analizi"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read().decode('latin1', errors='ignore')

            # BoundingBox arama
            bbox_match = re.search(r'%%BoundingBox:\s*(\d+)\s+(\d+)\s+(\d+)\s+(\d+)', content)

            if bbox_match:
                x1, y1, x2, y2 = map(int, bbox_match.groups())
                width_pts = x2 - x1
                height_pts = y2 - y1
            else:
                # Varsayılan boyutlar
                width_pts = 595  # A4 genişlik
                height_pts = 842  # A4 yükseklik

            width_mm = round(width_pts * self.pts_to_mm)
            height_mm = round(height_pts * self.pts_to_mm)

            category = self.determine_category(width_mm, height_mm, file_name)
            should_rotate = self.should_rotate(width_mm, height_mm, category)

            return {
                "success": True,
                "dimensions": {
                    "widthMM": width_mm,
                    "heightMM": height_mm,
                    "category": category,
                    "confidence": 0.8,
                    "description": f"EPS analizi: {width_mm}x{height_mm}mm {category}",
                    "shouldRotate": should_rotate
                },
                "detectedDesigns": 1,
                "isVector": True,
                "processingNotes": [
                    "EPS dosyası analiz edildi",
                    f"BoundingBox: {width_pts}x{height_pts}pts",
                    f"Fiziksel boyut: {width_mm}x{height_mm}mm",
                    f"Kategori: {category}"
                ]
            }

        except Exception as e:
            print(f"EPS analiz hatası: {str(e)}", file=sys.stderr)
            return self.create_fallback_result(file_name)

    def parse_svg_dimensions(self, svg_content):
        """SVG boyutlarını parse et"""
        # width ve height attributeleri
        width_match = re.search(r'width=["\']([^"\']+)["\']', svg_content)
        height_match = re.search(r'height=["\']([^"\']+)["\']', svg_content)

        width_mm = height_mm = 0

        if width_match and height_match:
            width_mm = self.parse_svg_unit(width_match.group(1))
            height_mm = self.parse_svg_unit(height_match.group(1))

        # ViewBox'tan boyut hesapla
        if width_mm == 0 or height_mm == 0:
            viewbox_match = re.search(r'viewBox=["\']([^"\']+)["\']', svg_content)
            if viewbox_match:
                values = viewbox_match.group(1).split()
                if len(values) >= 4:
                    # SVG units genellikle px, 96 DPI varsayımı
                    width_mm = round(float(values[2]) * self.mm_per_inch / 96)
                    height_mm = round(float(values[3]) * self.mm_per_inch / 96)

        # Varsayılan boyutlar
        if width_mm == 0: width_mm = 100
        if height_mm == 0: height_mm = 80

        return width_mm, height_mm

    def parse_svg_unit(self, value_str):
        """SVG birim değerini mm'ye çevir"""
        if not value_str:
            return 0

        # Sayı ve birim ayrıştır
        match = re.match(r'^(\d+\.?\d*)(mm|cm|px|in|pt)?$', value_str.strip())
        if not match:
            return 0

        value = float(match.group(1))
        unit = match.group(2) or 'px'

        # mm'ye çevir
        if unit == 'mm':
            return round(value)
        elif unit == 'cm':
            return round(value * 10)
        elif unit == 'in':
            return round(value * self.mm_per_inch)
        elif unit == 'pt':
            return round(value * self.pts_to_mm)
        elif unit == 'px':
            return round(value * self.mm_per_inch / 96)  # 96 DPI varsayımı
        else:
            return round(value)

    def determine_category(self, width_mm, height_mm, file_name, has_text=False, has_images=False):
        """Tasarım kategorisini belirle"""
        name = file_name.lower()

        # Maksimum baskı alanı kontrolü (33x48cm = 330x480mm)
        max_sheet_width = 300  # Kesim payları ile birlikte güvenli alan
        max_sheet_height = 450

        # Büyük tasarımlar için otomatik ölçekleme
        if width_mm > max_sheet_width or height_mm > max_sheet_height:
            return 'oversized_design'

        # Dosya adından kategori
        if any(word in name for word in ['logo', 'marka', 'brand']):
            return 'logo'
        elif any(word in name for word in ['kartvizit', 'business', 'card']):
            return 'business_card'
        elif any(word in name for word in ['etiket', 'label', 'sticker']):
            return 'label'
        elif any(word in name for word in ['poster', 'afiş', 'banner']):
            return 'poster'

        # Boyutlara göre kategori
        if 80 <= width_mm <= 90 and 50 <= height_mm <= 60:
            return 'business_card'
        elif width_mm <= 100 and height_mm <= 100:
            return 'label'
        elif width_mm > 200 or height_mm > 200:
            return 'poster'
        elif max(width_mm, height_mm) / min(width_mm, height_mm) > 3:
            return 'banner'
        else:
            return 'label'

    def scale_oversized_design(self, width_mm, height_mm):
        """Büyük tasarımları otomatik ölçekle"""
        max_width = 300  # Güvenli baskı alanı genişliği
        max_height = 450  # Güvenli baskı alanı yüksekliği

        if width_mm <= max_width and height_mm <= max_height:
            return width_mm, height_mm

        # Ölçekleme faktörü hesapla
        scale_factor = min(max_width / width_mm, max_height / height_mm)

        scaled_width = round(width_mm * scale_factor)
        scaled_height = round(height_mm * scale_factor)

        return scaled_width, scaled_height

    def should_rotate(self, width_mm, height_mm, category):
        """Rotate önerisi"""
        aspect_ratio = width_mm / height_mm

        # Dikey tasarımlar için döndürme önerisi
        if category in ['business_card', 'label'] and aspect_ratio < 1:
            return True
        elif category == 'banner' and aspect_ratio < 2:
            return True
        else:
            return False

    def analyze_by_extension(self, file_path, file_name):
        """Dosya uzantısına göre analiz"""
        ext = Path(file_name).suffix.lower()

        if ext in ['.ai', '.eps']:
            return self.analyze_eps_advanced(file_path, file_name)
        elif ext == '.svg':
            return self.analyze_svg_advanced(file_path, file_name)
        elif ext in ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']:
            return self.analyze_image_advanced(file_path, file_name)
        else:
            return self.create_fallback_result(file_name)

    def create_fallback_result(self, file_name):
        """Varsayılan sonuç oluştur"""
        name = file_name.lower()

        # Akıllı varsayılan boyutlar
        if 'logo' in name:
            width_mm, height_mm, category = 100, 80, 'logo'
        elif 'kartvizit' in name or 'business' in name:
            width_mm, height_mm, category = 85, 55, 'business_card'
        elif 'etiket' in name or 'label' in name:
            width_mm, height_mm, category = 60, 40, 'label'
        else:
            width_mm, height_mm, category = 80, 60, 'label'

        return {
            "success": True,
            "dimensions": {
                "widthMM": width_mm,
                "heightMM": height_mm,
                "category": category,
                "confidence": 0.6,
                "description": f"Varsayılan analiz: {width_mm}x{height_mm}mm {category}",
                "shouldRotate": False
            },
            "detectedDesigns": 1,
            "processingNotes": [
                "Dosya uzantısından varsayılan boyutlar atandı",
                f"Boyutlar: {width_mm}x{height_mm}mm",
                f"Kategori: {category}"
            ]
        }

    def create_error_result(self, error_message):
        """Hata sonucu oluştur"""
        return {
            "success": False,
            "error": error_message,
            "dimensions": {
                "widthMM": 50,
                "heightMM": 30,
                "category": "unknown",
                "confidence": 0.1,
                "description": "Analiz başarısız"
            },
            "detectedDesigns": 0,
            "processingNotes": [f"Hata: {error_message}"]
        }

def main():
    if len(sys.argv) != 4:
        print(json.dumps({"error": "Kullanım: python analyzer.py <file_path> <file_name> <mime_type>"}))
        sys.exit(1)

    file_path = sys.argv[1]
    file_name = sys.argv[2]
    mime_type = sys.argv[3]

    analyzer = AdvancedDesignAnalyzer()
    result = analyzer.analyze_file(file_path, file_name, mime_type)

    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()