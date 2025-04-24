import os
from bs4 import BeautifulSoup
import html2text

def html_to_markdown(html_file_path, div_class=None, blacklist=None, end_marker=None):
    # Default blacklist strings
    if blacklist is None:
        blacklist = [
            "Last Modified",
            "Last modified",
            "Last Updated",
            "Last updated",
            "Created:",
            "Modified:",
            "Updated:",
            "Date:",
            "Time:",
            "Posted:",
            "Published:",
            "Expand/Collapse"
        ]
    
    # Check if file exists
    if not os.path.exists(html_file_path):
        raise FileNotFoundError(f"HTML file not found: {html_file_path}")
    
    # Read the HTML file
    with open(html_file_path, 'r', encoding='utf-8') as file:
        html_content = file.read()
    
    # Parse HTML with BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # If div_class is specified, find and extract that div
    if div_class:
        article_div = soup.find('div', class_=div_class)
        if not article_div:
            raise ValueError(f"Could not find div with class '{div_class}'")
        content_to_convert = str(article_div)
    else:
        # If no div_class specified, convert entire page
        content_to_convert = str(soup)
    
    # Convert the content to markdown
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.body_width = 0  # Disable text wrapping
    
    # Convert the content to markdown
    markdown_content = h.handle(content_to_convert)
    
    # Filter out blacklisted lines
    lines = markdown_content.split('\n')
    filtered_lines = [
        line for line in lines 
        if not any(line.strip().startswith(blacklisted) for blacklisted in blacklist)
    ]
    
    # If end_marker is specified, truncate content at that point
    if end_marker:
        content = '\n'.join(filtered_lines)
        end_index = content.find(end_marker)
        if end_index != -1:
            content = content[:end_index]
        return content.strip()
    
    return '\n'.join(filtered_lines).strip()

if __name__ == "__main__":
    # Example usage
    try:
        # Convert specific div with default blacklist and end marker
        markdown = html_to_markdown(
            "/Users/nic/dl/kaltura-knowledge/knowledge.kaltura.com/version-169---feb-3-2019.html",
            div_class="hg-article-body",
            end_marker="Was this article helpful?"
        )
        print(markdown)
        
        # Convert with custom blacklist and end marker
        # custom_blacklist = ["Custom string", "Another string"]
        # markdown = html_to_markdown(
        #     "path/to/file.html",
        #     div_class="hg-article-body",
        #     blacklist=custom_blacklist,
        #     end_marker="Custom end marker"
        # )
        # print(markdown)
    except Exception as e:
        print(f"Error: {e}")
