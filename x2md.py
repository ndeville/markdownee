from datetime import datetime
import os
ts_db = f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"
ts_time = f"{datetime.now().strftime('%H:%M:%S')}"
print(f"\n---------- {ts_time} starting {os.path.basename(__file__)}")
import time
start_time = time.time()

import re
import argparse

####################
# CONVERT ANY DOCUMENT TO MARKDOWN
# USING MICROSOFT'S MARKITDOWN LIBRARY
# https://github.com/microsoft/markitdown

# IMPORTS

import os

from doc2md import create_markdown_from_file
from url2md import extract_text_from_url

# GLOBALS



import os




def save_to_markdown(text, filename='output.md'):
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f'```\n{text}\n```')

# MAIN
def process_input(input_source):
    try:
        if input_source.startswith('http'):
            print(f"\nExtracting text from URL: {input_source}")
            extracted_text_from_url = extract_text_from_url(input_source)
            
            # Check if the extracted text contains meaningful content
            cleaned_text = extracted_text_from_url.strip()
            if not cleaned_text or cleaned_text.isspace():
                print("\n❌ No meaningful content found in the URL or content is too short. Please check the URL and try again.")
                return
            if len(cleaned_text) < 100:
                print(f"\n❌ Content is too short: {len(cleaned_text)} characters:\n{cleaned_text}\n\nPlease check the URL and try again.\n\n")
                return
                
            # Create timestamp and clean URL for filename
            clean_url = re.sub(r'[^\w]', '_', input_source)[:50]  # Limit length and replace non-word chars
            output_path = f"/Users/nic/txt/{datetime.now().strftime('%Y-%m-%d %H:%M')}_{clean_url}.md"
            
            save_to_markdown(extracted_text_from_url, output_path)
            print(f"\n✅ Markdown file generated: {output_path}\n")
            
            # Open the file in VS Code using the full path with proper escaping
            os.system(f"open -a 'Visual Studio Code' '{output_path}'")
        else:
            markdown_file = create_markdown_from_file(input_source)
            print(f"\n✅ Markdown file generated: {markdown_file}\n")
            
            # Open the file in VS Code using the full path with proper escaping
            os.system(f"open -a 'Visual Studio Code' '{markdown_file}'")
    except Exception as e:
        print(f"Error: {e}")




if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert documents or URLs to Markdown')
    parser.add_argument('input', nargs='?', help='URL or file path to convert')
    args = parser.parse_args()

    if args.input:
        # If input is provided as argument
        process_input(args.input)
    else:
        # If no argument provided, ask for input
        user_input = input("\nEnter URL or file path to convert: ")
        process_input(user_input)

    print('\n\n-------------------------------')
    run_time = round((time.time() - start_time), 3)
    if run_time < 1:
        print(f'\n{os.path.basename(__file__)} finished in {round(run_time*1000)}ms at {datetime.now().strftime("%H:%M:%S")}.\n')
    elif run_time < 60:
        print(f'\n{os.path.basename(__file__)} finished in {round(run_time)}s at {datetime.now().strftime("%H:%M:%S")}.\n')
    elif run_time < 3600:
        print(f'\n{os.path.basename(__file__)} finished in {round(run_time/60)}mns at {datetime.now().strftime("%H:%M:%S")}.\n')
    else:
        print(f'\n{os.path.basename(__file__)} finished in {round(run_time/3600, 2)}hrs at {datetime.now().strftime("%H:%M:%S")}.\n')