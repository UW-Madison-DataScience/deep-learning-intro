
def preprocess_markdown(md_content):
    # Normalize ::: questions/objectives/keypoints blocks
    header_block_pattern = re.compile(
        r"^:{2,}\s*(questions|objectives|keypoints)\s*\n+(.*?)(?=^:{2,}\s*$)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE
    )
    def header_repl(match):
        heading = match.group(1).capitalize()
        body = match.group(2).strip()
        return f"## {heading}\n\n{body}"
    md_content = re.sub(header_block_pattern, header_repl, md_content)
    # Step 1: Remove ::: solution blocks and their contents
    md_content = re.sub(r"^:::*\s*solution\s*\n.*?^:::*\s*$", "", md_content, flags=re.MULTILINE | re.DOTALL | re.IGNORECASE)

    # Step 2: Transform ::: callout or challenge blocks with headers into markdown headings
    pattern = re.compile(
        r"^:::*\s*(callout|challenge|discussion)\s*\n+##\s*(.*?)\n+(.*?)(?=^:::*\s*$)", 
        re.MULTILINE | re.DOTALL | re.IGNORECASE
    )

    def repl(match):
        block_type = match.group(1).capitalize()
        heading = match.group(2).strip()
        body = match.group(3).strip()
        return f"## {block_type}: {heading}\n\n{body}"

    md_content = re.sub(pattern, repl, md_content)
    return md_content


import os
import re
import nbformat as nbf
import argparse



def postprocess_challenge_and_callout(md_content):
    # Merge ::: callout or ::: challenge blocks with following ## headers
    pattern = re.compile(
        r'^:::\s*(callout|challenge)\s*\n+##\s*(.*?)\n+(.*?)(?=^:::\s*$)', 
        re.MULTILINE | re.DOTALL | re.IGNORECASE
    )
    
    def repl(match):
        block_type = match.group(1).capitalize()
        heading = match.group(2).strip()
        body = match.group(3).strip()
        return f"## {block_type}: {heading}\n\n{body}"

    return re.sub(pattern, repl, md_content)


def md_to_notebook(md_file, notebook_file, base_image_url, excluded_figs=None):
    # Read the Markdown file
    with open(md_file, 'r', encoding='utf-8') as file:
        md_lines = file.readlines()

    # # Preview the first 100 lines of the Markdown file
    # print("Preview of the first 100 lines of the Markdown file:")
    # for i, line in enumerate(md_lines[:100]):
    #     print(f"{i+1}: {line}", end='')
    # print("\n")

    md_content = ''.join(md_lines)

    # Initialize a new notebook
    nb = nbf.v4.new_notebook()
    cells = []

    # Extract the title from the YAML front matter
    title_match = re.search(r'^---\s*title:\s*"(.*?)".*?---', md_content, flags=re.DOTALL | re.MULTILINE)
    if title_match:
        title = title_match.group(1)
        cells.append(nbf.v4.new_markdown_cell(f"# {title}"))

    # Remove the YAML front matter
    md_content = re.sub(r'^---.*?---', '', md_content, flags=re.DOTALL | re.MULTILINE)

    
    # Handle reference-style image definitions like:
    # [penguin]: fig/penguin.png
    ref_image_map = {}
    ref_pattern = re.compile(r'^\[([^\]]+)]\s*:\s*(\S+)', re.MULTILINE)
    for match in ref_pattern.finditer(md_content):
        label, path = match.groups()
        ref_image_map[label] = f"{base_image_url}/{path.strip()}"

    def replace_reference_images(match):
        alt_text = match.group(1)
        label = match.group(2)
        url = ref_image_map.get(label)
        return f"![{alt_text}]({url})" if url else match.group(0)

    md_content = re.sub(r'!\[\]\[([^\]]+)\]', lambda m: f'![{m.group(1)}][{m.group(1)}]', md_content)
    md_content = re.sub(r'!\[([^\]]+)]\[([^\]]+)]', replace_reference_images, md_content)

    # Remove reference definitions from the bottom of the file
    md_content = re.sub(r'^\[([^\]]+)]\s*:\s*\S+.*$', '', md_content, flags=re.MULTILINE)

# Replace local image paths with URLs
    def replace_image_path(match):
        alt_text = match.group(1)
        image_path = match.group(2)
        web_image_url = f"{base_image_url}/{os.path.basename(image_path)}"
        return f"![{alt_text}]({web_image_url})"

    md_content = re.sub(r'!\[(.*?)\]\((.*?)\)', replace_image_path, md_content)

    md_content = postprocess_challenge_and_callout(md_content)

    md_content = preprocess_markdown(md_content)

    # Split the content into lines
    lines = md_content.split('\n')

    code_buffer = []
    is_in_code_block = False
    text_buffer = []

    def process_buffer(buffer, cell_type="markdown"):
        if buffer:
            content = '\n'.join(buffer).strip()
            if cell_type == "code":
                cells.append(nbf.v4.new_code_cell(content))
            else:
                cells.append(nbf.v4.new_markdown_cell(content))
            buffer.clear()

    is_in_code_block = False
    is_output_block = False
    is_in_instructor_block = False
    is_in_challenge_block = False
    is_in_solution_block = False

    for line in lines:
        stripped = line.strip()

        # Handle output blocks
        if stripped == '```output':
            is_output_block = True
            continue
        elif stripped == '```' and is_output_block:
            is_output_block = False
            continue
        elif is_output_block:
            continue

        # Handle instructor blocks
        if re.match(r'^:{2,}\s*instructor\s*$', stripped, re.IGNORECASE):
            is_in_instructor_block = True
            continue
        elif re.match(r'^:{2,}\s*$', stripped) and is_in_instructor_block:
            is_in_instructor_block = False
            continue
        elif is_in_instructor_block:
            continue

        # Handle challenge blocks
        if re.match(r'^:{2,}\s*challenge\s*$', stripped, re.IGNORECASE):
            is_in_challenge_block = True
            text_buffer.append(line)  # keep challenge marker
            continue
        elif re.match(r'^:{2,}\s*$', stripped) and is_in_challenge_block and not is_in_solution_block:
            is_in_challenge_block = False
            text_buffer.append(line)  # close challenge block
            continue

        # Handle solution sub-blocks inside challenge
        if is_in_challenge_block:
            if re.match(r'^:{2,}\s*solution\s*$', stripped, re.IGNORECASE):
                is_in_solution_block = True
                continue
            elif re.match(r'^:{2,}\s*$', stripped) and is_in_solution_block:
                is_in_solution_block = False
                continue
            elif is_in_solution_block:
                continue
            else:
                text_buffer.append(line)
            continue  # skip normal processing outside challenge

        # Regular code block processing
        if stripped.startswith('```'):
            is_in_code_block = not is_in_code_block
            if is_in_code_block:
                process_buffer(text_buffer, "markdown")
            else:
                process_buffer(code_buffer, "code")
        elif is_in_code_block:
            code_buffer.append(line)
        else:
            text_buffer.append(line)



    # Process any remaining buffers
    process_buffer(text_buffer, "markdown")

    # Remove empty cells
    cells = [cell for cell in cells if cell['source'].strip()]

    # Add cells to the notebook
    # Final filtering of excluded image references from markdown cells
    if excluded_figs:
        filtered_cells = []
        for cell in cells:
            if cell['cell_type'] == 'markdown':
                source = cell['source']
                if any(img in source for img in excluded_figs):
                    continue
            filtered_cells.append(cell)
        cells = filtered_cells

    nb['cells'] = cells

    # Write the notebook to a file
    with open(notebook_file, 'w', encoding='utf-8') as file:
        nbf.write(nb, file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert Markdown file to Jupyter Notebook")
    parser.add_argument('--exclude-images', nargs='*', default=[], help='List of image filenames to exclude')
    parser.add_argument("input_dir", help="Directory containing the input Markdown file")
    parser.add_argument("output_dir", help="Directory to save the output Jupyter Notebook")
    parser.add_argument("base_image_url", help="Base URL for images")
    parser.add_argument("filename", help="Filename of the input Markdown file (with extension)")

    args = parser.parse_args()
    excluded_figs = args.exclude_images

    # Ensure directories have trailing slashes and exist
    input_path = os.path.join(args.input_dir, args.filename)
    os.makedirs(args.output_dir, exist_ok=True)
    output_path = os.path.join(args.output_dir, os.path.splitext(args.filename)[0] + ".ipynb")

    print(f"Converting {input_path} to {output_path}...")

    md_to_notebook(input_path, output_path, args.base_image_url, excluded_figs=excluded_figs)

#e.g., ...
# python convert_md_to_notebook.py ./episodes ./notebooks https://github.com/user/repo/raw/main/images example.md

