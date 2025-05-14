import os
import re

def remove_remaining_colons(notebook_path):
    import nbformat as nbf
    nb = nbf.read(notebook_path, as_version=4)
    for cell in nb.cells:
        if cell.cell_type == "markdown":
            cell.source = cell.source.replace(":::", "").strip()
    nbf.write(nb, notebook_path)


import nbformat as nbf
import argparse

def preprocess_markdown(md_content):
    # Remove ```output blocks
    md_content = re.sub(r"```output\n.*?\n```", "", md_content, flags=re.DOTALL)

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

    # Remove ::: solution blocks and their contents
    md_content = re.sub(r"^:::*\s*solution\s*\n.*?^:::*\s*$", "", md_content, flags=re.MULTILINE | re.DOTALL | re.IGNORECASE)

    # Remove ::: instructor blocks and their contents
    md_content = re.sub(r"^:::*\s*instructor\s*\n.*?^:::*\s*$", "", md_content, flags=re.MULTILINE | re.DOTALL | re.IGNORECASE)

    # Transform ::: callout, challenge, discussion blocks
    pattern = re.compile(
        r"^:::*\s*(callout|challenge|discussion)\s*\n+##\s*(.*?)\n+(.*?)(?=^:::*\s*$)",
        re.MULTILINE | re.DOTALL | re.IGNORECASE
    )
    def repl(match):
        block_type = match.group(1).capitalize()
        heading = match.group(2).strip()
        body = match.group(3).strip()
        result = f"## {block_type}: {heading}\n\n{body}"
        if block_type.lower() == "challenge":
            result += "\n\n<!-- BLANK_CELL_HERE -->"
        return result



    md_content = re.sub(pattern, repl, md_content)

    # Remove orphaned alt text lines
    md_content = re.sub(r'^\{alt=.*?\}\s*$', '', md_content, flags=re.MULTILINE)

    return md_content


def insert_blank_cells_after_markers(notebook_path):
    import nbformat as nbf
    nb = nbf.read(notebook_path, as_version=4)
    new_cells = []
    for cell in nb.cells:
        if cell.cell_type == "markdown" and "<!-- BLANK_CELL_HERE -->" in cell.source:
            parts = cell.source.split("<!-- BLANK_CELL_HERE -->")
            before = parts[0].strip()
            after = parts[1].strip() if len(parts) > 1 else ""
            if before:
                new_cells.append(nbf.v4.new_markdown_cell(before))
            new_cells.append(nbf.v4.new_code_cell(""))
            if after and after != ":::":  # ignore leftover :::
                new_cells.append(nbf.v4.new_markdown_cell(after))
        else:
            new_cells.append(cell)
    nb.cells = new_cells
    nbf.write(nb, notebook_path)


def md_to_notebook(md_file, notebook_file, base_image_url, excluded_figs=None):
    with open(md_file, 'r', encoding='utf-8') as file:
        md_lines = file.readlines()

    md_content = ''.join(md_lines)

    nb = nbf.v4.new_notebook()
    cells = []

    title_match = re.search(r'^---\s*title:\s*"(.*?)".*?---', md_content, flags=re.DOTALL | re.MULTILINE)
    if title_match:
        title = title_match.group(1)
        cells.append(nbf.v4.new_markdown_cell(f"# {title}"))

    md_content = re.sub(r'^---.*?---', '', md_content, flags=re.DOTALL | re.MULTILINE)

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

    md_content = re.sub(r'!\[\]\[([^\]]+)]', lambda m: f'![{m.group(1)}][{m.group(1)}]', md_content)
    md_content = re.sub(r'!\[([^\]]+)]\[([^\]]+)]', replace_reference_images, md_content)

    md_content = re.sub(r'^\[([^\]]+)]\s*:\s*\S+.*$', '', md_content, flags=re.MULTILINE)

    def replace_image_path(match):
        alt_text = match.group(1)
        image_path = match.group(2)
        web_image_url = f"{base_image_url}/{os.path.basename(image_path)}"
        return f"![{alt_text}]({web_image_url})"

    md_content = re.sub(r'!\[(.*?)\]\((.*?)\)', replace_image_path, md_content)

    md_content = preprocess_markdown(md_content)

    lines = md_content.split('\n')

    code_buffer = []
    text_buffer = []
    is_in_code_block = False

    def process_buffer(buffer, cell_type="markdown"):
        if buffer:
            content = '\n'.join(buffer).strip()
            if content:
                if cell_type == "code":
                    cells.append(nbf.v4.new_code_cell(content))
                else:
                    cells.append(nbf.v4.new_markdown_cell(content))
            buffer.clear()

    for i in range(len(lines)):
        line = lines[i]
        stripped = line.strip()

        if stripped.startswith('```'):
            is_in_code_block = not is_in_code_block
            if is_in_code_block:
                process_buffer(text_buffer, "markdown")
            else:
                process_buffer(code_buffer, "code")
            continue

        if is_in_code_block:
            code_buffer.append(line)
            continue

        # Skip excluded image lines and immediate alt text line
        if excluded_figs:
            image_match = re.match(r'!\[.*?\]\(.*?(/|\\)([^/\\]+)\)', line)
            if image_match and image_match.group(2) in excluded_figs:
                # Also skip next line if it's an alt tag
                if i + 1 < len(lines) and re.match(r'^\{alt=.*?\}\s*$', lines[i + 1]):
                    lines[i + 1] = ''
                continue

        
        if stripped == '<!-- BLANK_CELL_HERE -->':
            if i + 1 < len(lines) and lines[i + 1].strip() == ':::':
                i += 1  # skip :::
            process_buffer(text_buffer, "markdown")
            cells.append(nbf.v4.new_code_cell(""))  # blank code cell
            continue

        if stripped == '<!-- BLANK_CELL_HERE -->':
            if i + 1 < len(lines) and lines[i + 1].strip() == ':::':
                i += 1  # skip :::
            process_buffer(text_buffer, "markdown")
            cells.append(nbf.v4.new_code_cell(""))  # blank code cell
            continue

        text_buffer.append(line)

    process_buffer(text_buffer, "markdown")

    nb['cells'] = cells

    with open(notebook_file, 'w', encoding='utf-8') as file:
        nbf.write(nb, file)
    insert_blank_cells_after_markers(notebook_file)
    remove_remaining_colons(notebook_file)
    remove_remaining_colons(notebook_file)
    remove_remaining_colons(notebook_file)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--exclude-images', nargs='*', default=[], help='List of image filenames to exclude')
    parser.add_argument("input_dir")
    parser.add_argument("output_dir")
    parser.add_argument("base_image_url")
    parser.add_argument("filename")
    args = parser.parse_args()

    input_path = os.path.join(args.input_dir, args.filename)
    output_path = os.path.join(args.output_dir, os.path.splitext(args.filename)[0] + ".ipynb")
    os.makedirs(args.output_dir, exist_ok=True)

    md_to_notebook(input_path, output_path, args.base_image_url, excluded_figs=args.exclude_images)



def insert_blank_cells_after_markers(notebook_path):
    import nbformat as nbf
    nb = nbf.read(notebook_path, as_version=4)
    new_cells = []
    for cell in nb.cells:
        if cell.cell_type == "markdown" and "<!-- BLANK_CELL_HERE -->" in cell.source:
            parts = cell.source.split("<!-- BLANK_CELL_HERE -->")
            before = parts[0].strip()
            after = parts[1].strip() if len(parts) > 1 else ""
            if before:
                new_cells.append(nbf.v4.new_markdown_cell(before))
            new_cells.append(nbf.v4.new_code_cell(""))
            if after and after != ":::":  # ignore leftover ::: completely
                new_cells.append(nbf.v4.new_markdown_cell(after))
        else:
            new_cells.append(cell)
    nb.cells = new_cells
    nbf.write(nb, notebook_path)



def remove_remaining_colons(notebook_path):
    import nbformat as nbf
    nb = nbf.read(notebook_path, as_version=4)
    for cell in nb.cells:
        if cell.cell_type == "markdown":
            cell.source = cell.source.replace(":::", "").strip()
    nbf.write(nb, notebook_path)
