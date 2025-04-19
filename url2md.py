from bs4 import BeautifulSoup

def extract_text_from_url(url):
    import subprocess
    import tempfile
    
    # Create a temporary file to store the curl output
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        temp_path = temp_file.name
    
    # Use curl to fetch the URL content
    try:
        curl_command = ["curl", "-s", url]
        html_content = subprocess.check_output(curl_command, universal_newlines=True)
        
        # Parse the HTML content with BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script and style elements
        for script_or_style in soup(['script', 'style']):
            script_or_style.decompose()
        
        # Extract and clean the text
        text = soup.get_text(separator='\n')
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return '\n\n'.join(lines)
    
    except subprocess.CalledProcessError as e:
        raise Exception(f"Failed to fetch URL with curl: {e}")