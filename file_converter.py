import subprocess
import os
import time
import requests
from PIL import Image

def convert_file(input_path, target_format):
    """Convert any file to target format using appropriate tool."""
    try:
        ext = os.path.splitext(input_path)[1].lower().strip('.')
        base = os.path.splitext(input_path)[0]
        output_path = f"{base}.{target_format}"
        
        # Image conversions
        image_formats = ('png', 'jpg', 'jpeg', 'webp', 'bmp', 'tiff', 'tif', 'gif', 'ico', 'heic', 'svg', 'psd', 'eps')
        if ext in image_formats and target_format in image_formats + ('pdf',):
            return convert_image(input_path, output_path, target_format)
        
        # Audio/Video conversions using FFmpeg
        audio_formats = ('mp3', 'ogg', 'opus', 'wav', 'flac', 'wma', 'm4a', 'aac', 'aiff', 'amr')
        video_formats = ('mp4', 'avi', 'wmv', 'mkv', '3gp', '3gpp', 'mpg', 'mpeg', 'webm', 'ts', 'mov', 'flv', 'vob')
        if ext in audio_formats + video_formats or target_format in audio_formats + video_formats:
            return convert_media(input_path, output_path, target_format)
        
        # Document/Presentation conversions using LibreOffice
        office_formats = ('docx', 'doc', 'xlsx', 'xls', 'pptx', 'ppt', 'pptm', 'pps', 'ppsx', 'odt', 'ods', 'odp', 'rtf', 'csv', 'html', 'txt')
        if ext in office_formats and target_format == 'pdf':
            return convert_with_libreoffice(input_path, 'pdf')
        if ext in office_formats and target_format in office_formats:
            return convert_with_libreoffice(input_path, target_format)
        if ext == 'pdf' and target_format in ('docx', 'txt'):
            return convert_pdf_to(input_path, output_path, target_format)
        if ext == 'pdf' and target_format in ('jpg', 'png'):
            return convert_pdf_to_image(input_path, output_path, target_format)
        
        # eBook conversions using Calibre
        ebook_formats = ('epub', 'mobi', 'fb2', 'djvu', 'azw3', 'lrf', 'pdb')
        if ext in ebook_formats or target_format in ebook_formats:
            return convert_ebook(input_path, output_path, target_format)
        
        # Subtitle conversions
        subtitle_formats = ('srt', 'vtt', 'ass', 'ssa', 'sub')
        if ext in subtitle_formats and target_format in subtitle_formats + ('txt',):
            return convert_subtitle(input_path, output_path, target_format)
        
        # Fallback: try LibreOffice
        return convert_with_libreoffice(input_path, target_format)
    except Exception as e:
        print(f"Conversion error: {e}")
        return None

def convert_image(input_path, output_path, target_format):
    """Convert images using Pillow or ImageMagick."""
    try:
        if target_format == 'pdf':
            img = Image.open(input_path).convert("RGB")
            img.save(output_path)
            return output_path
        
        # Try Pillow first
        img = Image.open(input_path)
        if target_format in ('jpg', 'jpeg'):
            img = img.convert("RGB")
        img.save(output_path)
        return output_path
    except Exception:
        # Fallback to ImageMagick
        try:
            cmd = ['convert', input_path, output_path]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return output_path if os.path.exists(output_path) else None
        except Exception:
            return None

def convert_media(input_path, output_path, target_format):
    """Convert audio/video using FFmpeg."""
    try:
        cmd = ['ffmpeg', '-y', '-i', input_path, '-q:a', '2', '-q:v', '2', output_path]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)
        return output_path if os.path.exists(output_path) else None
    except Exception:
        return None

def convert_with_libreoffice(input_path, target_format):
    """Convert documents using LibreOffice."""
    try:
        outdir = os.path.dirname(input_path) or '.'
        cmd = ['libreoffice', '--headless', '--convert-to', target_format, '--outdir', outdir, input_path]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        
        base = os.path.splitext(os.path.basename(input_path))[0]
        output_path = os.path.join(outdir, f"{base}.{target_format}")
        return output_path if os.path.exists(output_path) else None
    except Exception:
        return None

def convert_pdf_to(input_path, output_path, target_format):
    """Convert PDF to Word or Text."""
    try:
        if target_format == 'txt':
            cmd = ['pdftotext', input_path, output_path]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return output_path if os.path.exists(output_path) else None
        elif target_format == 'docx':
            # Use LibreOffice for PDF to DOCX
            outdir = os.path.dirname(input_path) or '.'
            cmd = ['libreoffice', '--headless', '--infilter=writer_pdf_import', '--convert-to', 'docx', '--outdir', outdir, input_path]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
            base = os.path.splitext(os.path.basename(input_path))[0]
            result = os.path.join(outdir, f"{base}.docx")
            return result if os.path.exists(result) else None
    except Exception:
        return None

def convert_pdf_to_image(input_path, output_path, target_format):
    """Convert first page of PDF to image."""
    try:
        cmd = ['pdftoppm', '-f', '1', '-l', '1', f'-{target_format}', input_path, output_path.replace(f'.{target_format}', '')]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # pdftoppm adds page number
        expected = output_path.replace(f'.{target_format}', f'-1.{target_format}')
        if os.path.exists(expected):
            os.rename(expected, output_path)
            return output_path
        # Try without page number
        return output_path if os.path.exists(output_path) else None
    except Exception:
        return None

def convert_ebook(input_path, output_path, target_format):
    """Convert eBooks using Calibre's ebook-convert."""
    try:
        cmd = ['ebook-convert', input_path, output_path]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=180)
        return output_path if os.path.exists(output_path) else None
    except Exception:
        return None

def convert_subtitle(input_path, output_path, target_format):
    """Convert subtitles (basic SRT/VTT conversion)."""
    try:
        if target_format == 'txt':
            # Extract text only
            with open(input_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            # Remove timestamps and numbers
            import re
            lines = content.split('\n')
            text_lines = []
            for line in lines:
                line = line.strip()
                if not line: continue
                if line.isdigit(): continue
                if re.match(r'\d{2}:\d{2}', line): continue
                if '-->' in line: continue
                text_lines.append(line)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(text_lines))
            return output_path
        
        # Use ffmpeg for subtitle conversion
        cmd = ['ffmpeg', '-y', '-i', input_path, output_path]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_path if os.path.exists(output_path) else None
    except Exception:
        return None

def images_to_pdf(image_paths, output_path):
    """Merge multiple images into a single PDF."""
    try:
        images = []
        for p in image_paths:
            if os.path.exists(p):
                img = Image.open(p).convert("RGB")
                images.append(img)
        
        if images:
            images[0].save(output_path, save_all=True, append_images=images[1:])
            return output_path
        return None
    except Exception:
        return None

def compress_pdf(input_path, output_path):
    """Compress PDF using Ghostscript."""
    try:
        cmd = [
            'gs', '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4',
            '-dPDFSETTINGS=/ebook', '-dNOPAUSE', '-dQUIET', '-dBATCH',
            f'-sOutputFile={output_path}', input_path
        ]
        subprocess.run(cmd, check=True, timeout=60)
        if os.path.exists(output_path):
            # Only use compressed if smaller
            if os.path.getsize(output_path) < os.path.getsize(input_path):
                return output_path
        return input_path
    except Exception:
        return input_path

def protect_pdf(input_path, password):
    """Protect PDF with password using qpdf."""
    try:
        output_path = f"protected_{os.path.basename(input_path)}"
        cmd = ['qpdf', '--encrypt', password, password, '256', '--', input_path, output_path]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_path if os.path.exists(output_path) else None
    except Exception:
        return None

def ocr_image(input_path):
    """Extract text from image using Tesseract OCR."""
    try:
        cmd = ['tesseract', input_path, 'stdout', '-l', 'ara+eng']
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return result.stdout if result.returncode == 0 else None
    except Exception:
        return None

def url_to_pdf(url, output_path):
    """Convert URL to PDF using wkhtmltopdf or chromium."""
    try:
        # Try wkhtmltopdf first
        cmd = ['wkhtmltopdf', '--quiet', '--no-stop-slow-scripts', '--javascript-delay', '3000', url, output_path]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
        return output_path if os.path.exists(output_path) else None
    except Exception:
        try:
            # Fallback to chromium
            cmd = ['chromium-browser', '--headless', '--disable-gpu', '--no-sandbox', f'--print-to-pdf={output_path}', url]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
            return output_path if os.path.exists(output_path) else None
        except Exception:
            return None

def shorten_url(url):
    """Shorten URL using free API."""
    try:
        # Try TinyURL
        response = requests.get(f"https://tinyurl.com/api-create.php?url={url}", timeout=10)
        if response.status_code == 200 and response.text.startswith("http"):
            return response.text
        return None
    except Exception:
        try:
            # Fallback: is.gd
            response = requests.get(f"https://is.gd/create.php?format=simple&url={url}", timeout=10)
            if response.status_code == 200:
                return response.text
            return None
        except Exception:
            return None
