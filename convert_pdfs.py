import os
from pypdf import PdfReader
import pytesseract
from pdf2image import convert_from_path

def extract_text_from_image(input_path):
    images = convert_from_path(input_path, 300) # 300 DPI, play with larger values for better quality
    
    text = ''
    for image in images:
        text += pytesseract.image_to_string(image) or ''
    
    return text

def extract_text_from_pdf(input_path, output_path):
    with open(input_path, 'rb') as file:
        pdf = PdfReader(file)
        text = ''
        for page in pdf.pages:
            text += page.extract_text() or ''  # Adding a fallback of empty string if None is returned

        # if text is empty, then we might have a scanned pdf -- try to extract text using OCR
        if not text:
            text = extract_text_from_image(input_path)

        with open(output_path, 'w') as output_file:
            output_file.write(text)

def process_directory(input_directory, output_directory):
    for root, dirs, files in os.walk(input_directory):
        for file in files:
            if file.endswith('.pdf'):
                input_path = os.path.join(root, file)
                # Be careful about replacement here. Consider validating or refining this for edge cases.
                output_path = os.path.join(output_directory, os.path.relpath(input_path, start=input_directory)).replace('.pdf', '.txt')
                output_dir = os.path.dirname(output_path)
                os.makedirs(output_dir, exist_ok=True)
                extract_text_from_pdf(input_path, output_path)
            elif file.endswith('.json'):
                # just copy JSON files to the output directory without any processing
                input_path = os.path.join(root, file)
                output_path = os.path.join(output_directory, os.path.relpath(input_path, start=input_directory))
                output_dir = os.path.dirname(output_path)
                os.makedirs(output_dir, exist_ok=True)
                os.system(f'cp {input_path} {output_path}')

# Example usage
input_directory = './docs'
output_directory = './output'
process_directory(input_directory, output_directory)