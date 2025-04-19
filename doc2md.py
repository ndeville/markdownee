import os
from markitdown import MarkItDown


# FUNCTIONS
def create_markdown_from_file(file_path):
    """
    Converts the given file to Markdown and saves it as a .md file in the same location.
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    # Create an instance of MarkItDown
    markitdown = MarkItDown()

    # Convert the file to Markdown
    result = markitdown.convert(file_path)
    markdown_content = result.text_content

    # Generate the output .md file path
    file_base, _ = os.path.splitext(file_path)
    markdown_file_path = f"{file_base}.md"

    # Write the Markdown content to the .md file
    with open(markdown_file_path, 'w', encoding='utf-8') as md_file:
        md_file.write(markdown_content)

    return markdown_file_path