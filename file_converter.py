import subprocess
import os
from PIL import Image

def convert_pptx_to_pdf(pptx_path, output_path):
    try:
        # Run LibreOffice headlessly
        cmd = ['libreoffice', '--headless', '--convert-to', 'pdf', '--outdir', '.', pptx_path]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Determine the expected filename from LibreOffice
        generated_pdf = os.path.splitext(os.path.basename(pptx_path))[0] + ".pdf"
        
        # If the output path is different from what LibreOffice generated, rename it
        if os.path.basename(output_path) != generated_pdf and os.path.exists(generated_pdf):
            os.rename(generated_pdf, output_path)
        elif not os.path.exists(output_path) and os.path.exists(generated_pdf):
             os.rename(generated_pdf, output_path)
             
        return output_path if os.path.exists(output_path) else None
    except Exception:
        return None

def convert_excel_to_pdf(excel_path, output_path):
    try:
        cmd = ['libreoffice', '--headless', '--convert-to', 'pdf', '--outdir', '.', excel_path]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        generated_pdf = os.path.splitext(os.path.basename(excel_path))[0] + ".pdf"
        
        if os.path.basename(output_path) != generated_pdf and os.path.exists(generated_pdf):
            os.rename(generated_pdf, output_path)
        elif not os.path.exists(output_path) and os.path.exists(generated_pdf):
             os.rename(generated_pdf, output_path)
             
        return output_path if os.path.exists(output_path) else None
    except Exception:
        return None

def images_to_pdf(image_paths, output_path):
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
