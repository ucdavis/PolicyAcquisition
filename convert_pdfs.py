import os
from pypdf import PdfReader

def extract_text_from_pdf(input_path, output_path):
    with open(input_path, 'rb') as file:
        pdf = PdfReader(file)
        text = ''
        for page in pdf.pages:
            text += page.extract_text() or ''  # Adding a fallback of empty string if None is returned
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

# Example usage
input_directory = './docs'
output_directory = './output'
process_directory(input_directory, output_directory)