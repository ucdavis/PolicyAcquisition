# Run to verify the output of the run_details.json file in the docs directory
import os
from tabulate import tabulate

def find_files(directory, filename="run_details.json"):
    result = []
    for root, dirs, files in os.walk(directory):
        # Check if the specified file is in the current root directory
        contains_file = filename in files
        # Append the result along with the directory path
        result.append((root, contains_file))
    return result

def main():
    # Specify the directory to scan
    base_directory = './output/'

    docs_directory = base_directory + 'docs/'
    content_directory = base_directory + 'content/'
    
    # Get the listing of directories and file existence
    doc_results = find_files(docs_directory)
    content_results = find_files(content_directory)

    # Print results
    print(tabulate(doc_results, headers=["Directory", "Contains File"]))

    print(tabulate(content_results, headers=["Directory", "Contains File"]))
    
if __name__ == "__main__":
    main()