"""
250422-2111
script to convert kaltura knowledge base html files to markdown.
First downloaded/cloned https://knowledge.kaltura.com/help using wget (see apps/cli-wget)
Then running this script to convert to a single markdown file to be ingested in AI workflows.
"""

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
skipped_files = 0

list_files_with_errors = []

# List of strings that, if found in a file path, will cause the file to be skipped
blacklist_files = [
    "release-note",
    "new-articles?",
    "on-prem-release",
    "popular-articles?",
    "the-kaltura-player-release-note",
    "updated-articles?",
    "kms-version",
    "version-",
]

def should_skip_file(file_path):
    """Check if the file should be skipped based on blacklist criteria."""
    file_path_lower = file_path.lower()
    return any(blacklisted in file_path_lower for blacklisted in blacklist_files)

def process_kaltura_knowledge_files():
    global count_file, processed_files, count_errors, skipped_files

    # Define source and destination paths
    source_dir = "/Users/nic/dl/kaltura-knowledge/knowledge.kaltura.com"
    output_file = "/Users/nic/Dropbox/Kaltura/ai/kaltura-knowledge-base.md"
    
    # Create a list to store all markdown content
    all_markdown = []
    
    print(f"\nℹ️  Processing HTML files from: {source_dir}\n\n")
    
    # Walk through all files in the source directory in alphabetical order
    for root, _, files in os.walk(source_dir):
        for file in sorted(files):
            if file.endswith('.html'):
                count_file += 1
                html_file_path = os.path.join(root, file)
                relative_path = os.path.relpath(html_file_path, source_dir)
                
                # Skip files that match blacklist criteria
                if should_skip_file(html_file_path):
                    skipped_files += 1
                    print(f"{count_file}/{len(files):,} ⏭️  Skipped blacklisted file #{skipped_files}: {html_file_path}")
                    continue
                
                
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
                    
                    print(f"{count_file}/{len(files):,} ✅ processed file: {html_file_path}")
                    processed_files += 1
                    # if processed_files % 10 == 0:
                    #     print(f"Processed {processed_files} files...")
                        
                except Exception as e:
                    print(f"{count_file}/{len(files):,} ❌ Error processing file: {html_file_path} with error: {e}")
                    list_files_with_errors.append(html_file_path)
                    count_errors += 1
    
    # Write all markdown content to the output file
    with open(output_file, 'w', encoding='utf-8') as f:
        # Add a title and timestamp
        f.write(f"# Kaltura Knowledge Base\n\n")
        f.write(f"_Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}_\n\n")
        f.write("".join(all_markdown))
    
    print(f"\n✅ Processed {processed_files} HTML files")
    print(f"⏭️  Skipped {skipped_files} blacklisted files")

    # Convert .md to .txt
    txt_file = output_file.replace(".md", ".txt")
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write("".join(all_markdown))
    # Delete .md file
    os.remove(output_file)

    # Add some introduction text at the beginning of the file
    introduction = """# Kaltura Knowledge Base

This is a collection of articles from the Kaltura Knowledge Base to be found at https://knowledge.kaltura.com/help. 
Articles are listed in alphabetical order based on the page title, ie not grouped by category.

"""
    with open(txt_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    lines.insert(0, introduction)
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print(f"\n✅ file generated: {txt_file}")
    
    # Open the file in VS Code
    os.system(f"open -a 'Visual Studio Code' '{txt_file}'")

    return True



if __name__ == "__main__":
    success = process_kaltura_knowledge_files()

    for le in list_files_with_errors:
        print(f"❌ {le}")
    print(f"\n\n❌ TO REVIEW ABOVE:{count_errors} HTML files with errors")

    print(f"\nℹ️  {skipped_files} files skipped / blacklisted")

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
