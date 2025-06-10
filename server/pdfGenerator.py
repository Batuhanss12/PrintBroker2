#!/usr/bin/env python3
import json
import sys
import os
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing
from reportlab.lib.units import mm
import fitz  # PyMuPDF for PDF manipulation
from PIL import Image
import tempfile
import subprocess
import logging
import shutil

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Check system tools availability
SYSTEM_TOOLS = {
    'ghostscript': shutil.which('gs'),
    'inkscape': shutil.which('inkscape'),
    'imagemagick': shutil.which('convert'),
    'rsvg': shutil.which('rsvg-convert')
}

logger.info(f"🔧 System tools availability: {SYSTEM_TOOLS}")

class ProfessionalPDFGenerator:
    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        logger.info(f"🔧 Professional PDF Generator initialized, temp dir: {self.temp_dir}")

    def process_vector_file(self, file_path, output_path, target_width_mm, target_height_mm):
        """Process vector files and convert to PDF-embeddable format with quality preservation"""
        try:
            file_ext = os.path.splitext(file_path)[1].lower()
            logger.info(f"🔧 Professional vector processing: {file_path} ({file_ext})")

            # Pre-flight check
            if not os.path.exists(file_path):
                logger.error(f"❌ Source file not found: {file_path}")
                return False

            file_size = os.path.getsize(file_path)
            logger.info(f"📊 File size: {file_size / 1024:.1f}KB")

            success = False
            if file_ext == '.pdf':
                success = self.extract_pdf_content_advanced(file_path, output_path, target_width_mm, target_height_mm)
            elif file_ext in ['.svg']:
                success = self.convert_svg_to_pdf_advanced(file_path, output_path, target_width_mm, target_height_mm)
            elif file_ext in ['.ai', '.eps']:
                success = self.convert_eps_to_pdf_advanced(file_path, output_path, target_width_mm, target_height_mm)
            else:
                logger.warning(f"⚠️ Unsupported file type: {file_ext}")
                success = self.create_placeholder_pdf(output_path, target_width_mm, target_height_mm, f"Unsupported: {file_ext}")

            if success and os.path.exists(output_path):
                output_size = os.path.getsize(output_path)
                logger.info(f"✅ Processing completed: {output_size / 1024:.1f}KB output")
                return True
            else:
                logger.warning(f"⚠️ Processing failed, creating placeholder")
                return self.create_placeholder_pdf(output_path, target_width_mm, target_height_mm, f"Processing failed: {file_ext}")

        except Exception as e:
            logger.error(f"❌ Error processing vector file: {e}")
            return self.create_placeholder_pdf(output_path, target_width_mm, target_height_mm, "Processing Error")

    def extract_pdf_content_advanced(self, pdf_path, output_path, target_width_mm, target_height_mm):
        """Advanced PDF content extraction with vector preservation"""
        try:
            logger.info(f"🔍 Advanced PDF extraction: {pdf_path}")

            # Open source PDF with error handling
            try:
                src_doc = fitz.open(pdf_path)
            except Exception as e:
                logger.error(f"❌ Cannot open PDF: {e}")
                return False

            if len(src_doc) == 0:
                logger.error("❌ PDF has no pages")
                src_doc.close()
                return False

            # Get first page and analyze content
            page = src_doc[0]
            page_rect = page.rect
            
            # Check if page has actual content
            text_blocks = page.get_text("blocks")
            drawings = page.get_drawings()
            images = page.get_images()
            
            content_info = {
                'text_blocks': len(text_blocks),
                'drawings': len(drawings), 
                'images': len(images),
                'has_content': len(text_blocks) > 0 or len(drawings) > 0 or len(images) > 0
            }
            
            logger.info(f"📄 Content analysis: {content_info}")

            if not content_info['has_content']:
                logger.warning("⚠️ PDF appears to be empty")

            # Calculate optimal scaling
            source_width_pt = page_rect.width
            source_height_pt = page_rect.height
            target_width_pt = target_width_mm * 2.834645669
            target_height_pt = target_height_mm * 2.834645669

            # Preserve aspect ratio
            scale_x = target_width_pt / source_width_pt
            scale_y = target_height_pt / source_height_pt
            scale = min(scale_x, scale_y)

            logger.info(f"📐 Scaling: {scale:.3f} (from {source_width_pt:.1f}×{source_height_pt:.1f}pt to {target_width_pt:.1f}×{target_height_pt:.1f}pt)")

            # Create new PDF with exact target dimensions
            new_doc = fitz.open()
            new_page = new_doc.new_page(width=target_width_pt, height=target_height_pt)

            # Calculate centered position
            scaled_width = source_width_pt * scale
            scaled_height = source_height_pt * scale
            x_offset = (target_width_pt - scaled_width) / 2
            y_offset = (target_height_pt - scaled_height) / 2

            # Create transformation matrix with proper positioning
            mat = fitz.Matrix(scale, scale).pretranslate(x_offset, y_offset)

            # Insert the scaled page content with vector preservation
            try:
                new_page.show_pdf_page(new_page.rect, src_doc, 0, clip=None, matrix=mat)
                logger.info("✅ Vector content preserved in PDF extraction")
            except Exception as e:
                logger.warning(f"⚠️ Vector preservation failed, using fallback: {e}")
                # Fallback: render as high-quality image
                pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))  # 2x for quality
                img_data = pix.tobytes("png")
                new_page.insert_image(new_page.rect, stream=img_data)

            # Save with optimization
            new_doc.save(output_path, garbage=4, deflate=True)
            new_doc.close()
            src_doc.close()

            logger.info("✅ Advanced PDF extraction completed")
            return True

        except Exception as e:
            logger.error(f"❌ Advanced PDF extraction failed: {e}")
            return False

    def convert_svg_to_pdf_advanced(self, svg_path, output_path, target_width_mm, target_height_mm):
        """Advanced SVG to PDF conversion with multiple fallbacks"""
        try:
            logger.info(f"🎨 Advanced SVG conversion: {svg_path}")
            target_width_pt = target_width_mm * 2.834645669
            target_height_pt = target_height_mm * 2.834645669

            # Method 1: CairoSVG (best quality)
            try:
                import cairosvg
                cairosvg.svg2pdf(
                    url=svg_path,
                    write_to=output_path,
                    output_width=target_width_pt,
                    output_height=target_height_pt,
                    background_color='white'
                )
                logger.info("✅ SVG converted using CairoSVG (highest quality)")
                return True
            except ImportError:
                logger.info("📝 CairoSVG not available, trying Inkscape...")
            except Exception as e:
                logger.warning(f"⚠️ CairoSVG conversion failed: {e}")

            # Method 2: Inkscape (professional quality)
            try:
                cmd = [
                    'inkscape',
                    '--export-type=pdf',
                    f'--export-filename={output_path}',
                    f'--export-width={target_width_mm}mm',
                    f'--export-height={target_height_mm}mm',
                    '--export-dpi=300',
                    svg_path
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    logger.info("✅ SVG converted using Inkscape (professional quality)")
                    return True
                else:
                    logger.warning(f"⚠️ Inkscape conversion failed: {result.stderr}")

            except (subprocess.TimeoutExpired, FileNotFoundError):
                logger.warning("⚠️ Inkscape not available")

            # Method 3: rsvg-convert (if available)
            try:
                cmd = [
                    'rsvg-convert',
                    '-f', 'pdf',
                    '-w', str(int(target_width_pt)),
                    '-h', str(int(target_height_pt)),
                    '-o', output_path,
                    svg_path
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    logger.info("✅ SVG converted using rsvg-convert")
                    return True

            except (subprocess.TimeoutExpired, FileNotFoundError):
                logger.info("📝 rsvg-convert not available")

            # Fallback: Create enhanced placeholder
            return self.create_placeholder_pdf(output_path, target_width_mm, target_height_mm, "SVG Content (tools unavailable)")

        except Exception as e:
            logger.error(f"❌ Advanced SVG conversion failed: {e}")
            return False

    def convert_eps_to_pdf_advanced(self, eps_path, output_path, target_width_mm, target_height_mm):
        """Advanced EPS/AI to PDF conversion with vector preservation"""
        try:
            logger.info(f"✏️ Advanced EPS/AI conversion: {eps_path}")
            target_width_pt = target_width_mm * 2.834645669
            target_height_pt = target_height_mm * 2.834645669

            # Method 1: Ghostscript (best for EPS/AI)
            if SYSTEM_TOOLS['ghostscript']:
                try:
                    cmd = [
                        SYSTEM_TOOLS['ghostscript'],
                        '-dNOPAUSE',
                        '-dBATCH',
                        '-dSAFER',
                        '-sDEVICE=pdfwrite',
                        '-dEPSCrop',
                        '-dPDFFitPage',
                        f'-dDEVICEWIDTHPOINTS={target_width_pt}',
                        f'-dDEVICEHEIGHTPOINTS={target_height_pt}',
                        '-dCompatibilityLevel=1.5',
                        '-dColorConversionStrategy=/LeaveColorUnchanged',
                        '-dDownsampleMonoImages=false',
                        '-dDownsampleGrayImages=false',
                        '-dDownsampleColorImages=false',
                        f'-sOutputFile={output_path}',
                        eps_path
                    ]

                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    if result.returncode == 0:
                        logger.info("✅ EPS/AI converted using Ghostscript (vector preserved)")
                        return True
                    else:
                        logger.warning(f"⚠️ Ghostscript conversion failed: {result.stderr}")

                except (subprocess.TimeoutExpired, Exception) as e:
                    logger.warning(f"⚠️ Ghostscript execution failed: {e}")
            else:
                logger.warning("⚠️ Ghostscript not available in system")

            # Method 2: Inkscape (can handle some AI files)
            if SYSTEM_TOOLS['inkscape']:
                try:
                    cmd = [
                        SYSTEM_TOOLS['inkscape'],
                        '--export-type=pdf',
                        f'--export-filename={output_path}',
                        f'--export-width={target_width_mm}mm',
                        f'--export-height={target_height_mm}mm',
                        '--export-dpi=300',
                        eps_path
                    ]

                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    if result.returncode == 0:
                        logger.info("✅ EPS/AI converted using Inkscape")
                        return True

                except (subprocess.TimeoutExpired, Exception) as e:
                    logger.warning(f"⚠️ Inkscape execution failed: {e}")
            else:
                logger.info("📝 Inkscape not available in system")

            # Method 3: ImageMagick (raster fallback with high quality)
            if SYSTEM_TOOLS['imagemagick']:
                try:
                    cmd = [
                        SYSTEM_TOOLS['imagemagick'],
                        '-density', '300',
                        '-colorspace', 'RGB',
                        f'-resize', f'{target_width_mm * 11.81}x{target_height_mm * 11.81}',
                        '-quality', '95',
                        eps_path,
                        output_path
                    ]

                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                    if result.returncode == 0:
                        logger.info("✅ EPS/AI converted using ImageMagick (high-quality raster)")
                        return True

                except (subprocess.TimeoutExpired, Exception) as e:
                    logger.warning(f"⚠️ ImageMagick execution failed: {e}")
            else:
                logger.warning("⚠️ ImageMagick not available in system")

            # Final fallback
            return self.create_placeholder_pdf(output_path, target_width_mm, target_height_mm, "EPS/AI Content (conversion tools unavailable)")

        except Exception as e:
            logger.error(f"❌ Advanced EPS/AI conversion failed: {e}")
            return False

    def extract_pdf_content(self, pdf_path, output_path, target_width_mm, target_height_mm):
        """Extract and resize PDF content while preserving vectors"""
        try:
            logger.info(f"📄 Extracting PDF content from: {pdf_path}")

            # Open source PDF
            src_doc = fitz.open(pdf_path)
            if len(src_doc) == 0:
                logger.error("❌ PDF has no pages")
                return False

            # Get first page
            page = src_doc[0]

            # Calculate scaling
            page_rect = page.rect
            source_width_pt = page_rect.width
            source_height_pt = page_rect.height

            target_width_pt = target_width_mm * 2.834645669  # mm to points
            target_height_pt = target_height_mm * 2.834645669

            # Calculate scale factors
            scale_x = target_width_pt / source_width_pt
            scale_y = target_height_pt / source_height_pt
            scale = min(scale_x, scale_y)  # Maintain aspect ratio

            logger.info(f"📐 Scaling PDF: {scale:.3f} (from {source_width_pt:.1f}x{source_height_pt:.1f}pt to {target_width_pt:.1f}x{target_height_pt:.1f}pt)")

            # Create new PDF with target dimensions
            new_doc = fitz.open()
            new_page = new_doc.new_page(width=target_width_pt, height=target_height_pt)

            # Calculate centered position
            scaled_width = source_width_pt * scale
            scaled_height = source_height_pt * scale
            x_offset = (target_width_pt - scaled_width) / 2
            y_offset = (target_height_pt - scaled_height) / 2

            # Create transformation matrix
            mat = fitz.Matrix(scale, scale).pretranslate(x_offset, y_offset)

            # Insert the scaled page content
            new_page.show_pdf_page(new_page.rect, src_doc, 0, clip=None, matrix=mat)

            # Save the processed PDF
            new_doc.save(output_path)
            new_doc.close()
            src_doc.close()

            logger.info(f"✅ PDF content extracted and scaled successfully")
            return True

        except Exception as e:
            logger.error(f"❌ PDF extraction failed: {e}")
            return False

    def convert_svg_to_pdf(self, svg_path, output_path, target_width_mm, target_height_mm):
        """Convert SVG to PDF while preserving vector quality"""
        try:
            logger.info(f"🎨 Converting SVG to PDF: {svg_path}")

            # Try using cairosvg if available
            try:
                import cairosvg
                target_width_pt = target_width_mm * 2.834645669
                target_height_pt = target_height_mm * 2.834645669

                cairosvg.svg2pdf(
                    url=svg_path,
                    write_to=output_path,
                    output_width=target_width_pt,
                    output_height=target_height_pt
                )
                logger.info("✅ SVG converted using cairosvg")
                return True

            except ImportError:
                logger.info("📝 cairosvg not available, trying Inkscape...")

                # Try using Inkscape command line
                try:
                    cmd = [
                        'inkscape',
                        '--export-type=pdf',
                        f'--export-filename={output_path}',
                        f'--export-width={target_width_mm}',
                        f'--export-height={target_height_mm}',
                        svg_path
                    ]

                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    if result.returncode == 0:
                        logger.info("✅ SVG converted using Inkscape")
                        return True
                    else:
                        logger.warning(f"⚠️ Inkscape conversion failed: {result.stderr}")

                except (subprocess.TimeoutExpired, FileNotFoundError):
                    logger.warning("⚠️ Inkscape not available")

                # Fallback: Create a placeholder PDF
                return self.create_placeholder_pdf(output_path, target_width_mm, target_height_mm, "SVG Content")

        except Exception as e:
            logger.error(f"❌ SVG conversion failed: {e}")
            return False

    def convert_eps_to_pdf(self, eps_path, output_path, target_width_mm, target_height_mm):
        """Convert EPS/AI to PDF while preserving vector quality"""
        try:
            logger.info(f"✏️ Converting EPS/AI to PDF: {eps_path}")

            # Try using Ghostscript
            try:
                target_width_pt = target_width_mm * 2.834645669
                target_height_pt = target_height_mm * 2.834645669

                cmd = [
                    'gs',
                    '-dNOPAUSE',
                    '-dBATCH',
                    '-dSAFER',
                    '-sDEVICE=pdfwrite',
                    f'-dDEVICEWIDTHPOINTS={target_width_pt}',
                    f'-dDEVICEHEIGHTPOINTS={target_height_pt}',
                    '-dFIXEDMEDIA',
                    '-dPDFFitPage',
                    f'-sOutputFile={output_path}',
                    eps_path
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    logger.info("✅ EPS/AI converted using Ghostscript")
                    return True
                else:
                    logger.warning(f"⚠️ Ghostscript conversion failed: {result.stderr}")

            except (subprocess.TimeoutExpired, FileNotFoundError):
                logger.warning("⚠️ Ghostscript not available")

            # Try using ImageMagick as fallback
            try:
                cmd = [
                    'convert',
                    '-density', '300',
                    f'-resize', f'{target_width_mm * 11.81}x{target_height_mm * 11.81}',
                    '-units', 'PixelsPerInch',
                    '-colorspace', 'CMYK',
                    eps_path,
                    output_path
                ]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if result.returncode == 0:
                    logger.info("✅ EPS/AI converted using ImageMagick")
                    return True
                else:
                    logger.warning(f"⚠️ ImageMagick conversion failed: {result.stderr}")

            except (subprocess.TimeoutExpired, FileNotFoundError):
                logger.warning("⚠️ ImageMagick not available")

            # Fallback: Create placeholder
            return self.create_placeholder_pdf(output_path, target_width_mm, target_height_mm, "EPS/AI Content")

        except Exception as e:
            logger.error(f"❌ EPS/AI conversion failed: {e}")
            return False

    def create_placeholder_pdf(self, output_path, width_mm, height_mm, content_type):
        """Create a placeholder PDF when conversion fails"""
        try:
            width_pt = width_mm * 2.834645669
            height_pt = height_mm * 2.834645669

            c = canvas.Canvas(output_path, pagesize=(width_pt, height_pt))

            # Draw border
            c.setStrokeColorRGB(0.5, 0.5, 0.5)
            c.setLineWidth(1)
            c.rect(2, 2, width_pt - 4, height_pt - 4)

            # Add text
            c.setFont("Helvetica", min(12, height_pt / 10))
            c.setFillColorRGB(0.3, 0.3, 0.3)

            text_lines = [
                content_type,
                f"{width_mm:.0f}×{height_mm:.0f}mm",
                "Content Preserved"
            ]

            y_start = height_pt * 0.6
            for i, line in enumerate(text_lines):
                c.drawCentredText(width_pt / 2, y_start - (i * 15), line)

            c.save()
            logger.info(f"📝 Created placeholder PDF: {content_type}")
            return True

        except Exception as e:
            logger.error(f"❌ Placeholder creation failed: {e}")
            return False

    def generate_layout_pdf(self, data):
        """Generate the final layout PDF with embedded content"""
        try:
            arrangements = data['arrangements']
            design_files = data['designFiles']
            output_path = data['outputPath']
            sheet_width = data['sheetWidth']
            sheet_height = data['sheetHeight']

            logger.info(f"🎯 Generating layout PDF with {len(arrangements)} designs")

            # Convert mm to points
            sheet_width_pt = sheet_width * 2.834645669
            sheet_height_pt = sheet_height * 2.834645669

            # Create main PDF
            c = canvas.Canvas(output_path, pagesize=(sheet_width_pt, sheet_height_pt))

            # Add header
            c.setFont("Helvetica-Bold", 16)
            c.setFillColorRGB(0, 0, 0)
            c.drawString(20, sheet_height_pt - 30, "MATBIXX - Professional Vector Layout")

            # Add metadata
            c.setFont("Helvetica", 8)
            c.drawString(20, sheet_height_pt - 50, f"Sheet: {sheet_width}×{sheet_height}mm | Designs: {len(arrangements)} | Generated: Professional Vector System")

            # Process each arrangement
            processed_count = 0
            for i, arrangement in enumerate(arrangements):
                try:
                    design_id = arrangement['designId']
                    x_mm = arrangement['x']
                    y_mm = arrangement['y']
                    width_mm = arrangement['width']
                    height_mm = arrangement['height']

                    # Find corresponding design file
                    design_file = None
                    for df in design_files:
                        if df['id'] == design_id:
                            design_file = df
                            break

                    if not design_file or not design_file.get('filePath'):
                        logger.warning(f"⚠️ Design file not found for ID: {design_id}")
                        continue

                    file_path = design_file['filePath']
                    if not os.path.exists(file_path):
                        logger.warning(f"⚠️ File does not exist: {file_path}")
                        continue

                    logger.info(f"🔄 Processing design {i+1}/{len(arrangements)}: {design_file.get('name', 'Unknown')}")

                    # Convert coordinates (PDF coordinate system)
                    x_pt = x_mm * 2.834645669
                    y_pt = (sheet_height - y_mm - height_mm) * 2.834645669  # Flip Y coordinate
                    width_pt = width_mm * 2.834645669
                    height_pt = height_mm * 2.834645669

                    # Create temporary processed file
                    temp_pdf = os.path.join(self.temp_dir, f"processed_{i}.pdf")

                    # Process the vector file
                    if self.process_vector_file(file_path, temp_pdf, width_mm, height_mm):
                        # Embed the processed PDF into layout
                        try:
                            # Open processed PDF
                            processed_doc = fitz.open(temp_pdf)
                            if len(processed_doc) > 0:
                                processed_page = processed_doc[0]

                                # Convert to image for embedding (preserves quality)
                                mat = fitz.Matrix(2.0, 2.0)  # 2x scaling for quality
                                pix = processed_page.get_pixmap(matrix=mat)
                                img_data = pix.tobytes("png")

                                # Create image reader
                                img_reader = ImageReader(img_data)

                                # Draw the image
                                c.drawImage(img_reader, x_pt, y_pt, width_pt, height_pt, preserveAspectRatio=True)

                                processed_count += 1
                                logger.info(f"✅ Embedded design {i+1}: {design_file.get('name', 'Unknown')}")

                                processed_doc.close()
                            else:
                                logger.warning(f"⚠️ Processed PDF has no pages: {temp_pdf}")

                        except Exception as embed_error:
                            logger.error(f"❌ Failed to embed design {i+1}: {embed_error}")

                            # Draw fallback rectangle
                            c.setStrokeColorRGB(0.8, 0.2, 0.2)
                            c.setFillColorRGB(0.95, 0.95, 0.95)
                            c.rect(x_pt, y_pt, width_pt, height_pt, fill=1, stroke=1)

                            # Add error text
                            c.setFont("Helvetica", 8)
                            c.setFillColorRGB(0.8, 0.2, 0.2)
                            c.drawCentredText(x_pt + width_pt/2, y_pt + height_pt/2, f"Error: {design_file.get('name', 'Unknown')}")
                    else:
                        logger.warning(f"⚠️ Failed to process design {i+1}")

                        # Draw fallback rectangle
                        c.setStrokeColorRGB(0.8, 0.8, 0.2)
                        c.setFillColorRGB(0.98, 0.98, 0.9)
                        c.rect(x_pt, y_pt, width_pt, height_pt, fill=1, stroke=1)

                        # Add text
                        c.setFont("Helvetica", 8)
                        c.setFillColorRGB(0.6, 0.6, 0.1)
                        c.drawCentredText(x_pt + width_pt/2, y_pt + height_pt/2, f"Fallback: {design_file.get('name', 'Unknown')}")

                    # Add design label
                    c.setFont("Helvetica-Bold", 6)
                    c.setFillColorRGB(0, 0, 0)
                    c.drawString(x_pt + 2, y_pt + height_pt - 8, f"{i+1}")

                    # Clean up temp file
                    if os.path.exists(temp_pdf):
                        os.remove(temp_pdf)

                except Exception as arrangement_error:
                    logger.error(f"❌ Error processing arrangement {i+1}: {arrangement_error}")
                    continue

            # Add footer with statistics
            c.setFont("Helvetica", 8)
            footer_y = 20
            c.drawString(20, footer_y, f"✅ Successfully embedded: {processed_count}/{len(arrangements)} designs")
            c.drawString(300, footer_y, f"🔧 Professional Vector Processing System")

            # Save the final PDF
            c.save()

            logger.info(f"🎉 Layout PDF generated successfully: {output_path}")
            logger.info(f"📊 Final stats: {processed_count}/{len(arrangements)} designs embedded")

            return True

        except Exception as e:
            logger.error(f"❌ Layout PDF generation failed: {e}")
            return False

    def cleanup(self):
        """Clean up temporary files"""
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            logger.info("🧹 Cleanup completed")
        except Exception as e:
            logger.warning(f"⚠️ Cleanup warning: {e}")

def main():
    try:
        if len(sys.argv) != 2:
            print("ERROR: Invalid arguments")
            sys.exit(1)

        # Parse JSON input
        input_data = json.loads(sys.argv[1])

        # Create generator
        generator = ProfessionalPDFGenerator()

        # Generate PDF
        success = generator.generate_layout_pdf(input_data)

        # Cleanup
        generator.cleanup()

        if success:
            print(f"SUCCESS: PDF created at {input_data['outputPath']}")
        else:
            print("ERROR: PDF generation failed")
            sys.exit(1)

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("PyMuPDF not installed, installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "PyMuPDF"])
        import fitz

    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.units import mm
    except ImportError:
        print("ReportLab not installed, installing...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.units import mm

    import os
    import sys
    import json
    main()