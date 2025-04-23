# 250422-2111

import os
from datetime import datetime
import time

from html2md import html_to_markdown

# Start timing the execution
start_time = time.time()
ts_time = f"{datetime.now().strftime('%H:%M:%S')}"
print(f"\n---------- {ts_time} starting kaltura-knowledge2md.py")

# Counter for files
count_file = 0
processed_files = 0
count_errors = 0

def process_kaltura_knowledge_files():
    global count_file, processed_files, count_errors

    # Define source and destination paths
    source_dir = "/Users/nic/dl/kaltura-knowledge/knowledge.kaltura.com"
    output_file = "/Users/nic/test/kaltura-knowledge.md"
    
    # Create a list to store all markdown content
    all_markdown = []
    

    
    print(f"\nℹ️  Processing HTML files from: {source_dir}\n\n")
    
    # Walk through all files in the source directory
    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.endswith('.html'):
                count_file += 1
                html_file_path = os.path.join(root, file)
                relative_path = os.path.relpath(html_file_path, source_dir)
                print(f"Processing file {count_file} of {len(files):,}: {html_file_path}")
                
                try:
                    # Convert HTML to Markdown
                    markdown_content = html_to_markdown(
                        html_file_path,
                        div_class="hg-article-body",
                        end_marker="Was this article helpful?"
                    )
                    
                    # Add file information and content to the collection
                    file_header = f"\n\n## {relative_path}\n\n"
                    all_markdown.append(file_header + markdown_content)
                    
                    processed_files += 1
                    # if processed_files % 10 == 0:
                    #     print(f"Processed {processed_files} files...")
                        
                except Exception as e:
                    print(f"❌ Error processing {html_file_path}: {e}")
    
    # Write all markdown content to the output file
    with open(output_file, 'w', encoding='utf-8') as f:
        # Add a title and timestamp
        f.write(f"# Kaltura Knowledge Base\n\n")
        f.write(f"_Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n\n")
        f.write("".join(all_markdown))
    
    print(f"\n✅ Processed {processed_files} HTML files")
    print(f"\n✅ Markdown file generated: {output_file}")
    
    # Open the file in VS Code
    os.system(f"open -a 'Visual Studio Code' '{output_file}'")
    return True

if __name__ == "__main__":
    success = process_kaltura_knowledge_files()

    print(f"\n❌ {count_errors} HTML files with errors")
    print(f"\n✅ Total processed {processed_files} HTML files")
    
    # Print execution time
    run_time = time.time() - start_time
    if run_time < 1:
        print(f'\nScript finished in {round(run_time*1000)}ms at {datetime.now().strftime("%H:%M:%S")}.')
    elif run_time < 60:
        print(f'\nScript finished in {round(run_time)}s at {datetime.now().strftime("%H:%M:%S")}.')
    elif run_time < 3600:
        print(f'\nScript finished in {round(run_time/60)}mins at {datetime.now().strftime("%H:%M:%S")}.')
    else:
        print(f'\nScript finished in {round(run_time/3600, 2)}hrs at {datetime.now().strftime("%H:%M:%S")}.')
    
    print("-------------------------------\n")
