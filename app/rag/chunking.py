from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter


def chunk_markdown(content: str, source: str) -> list[dict]:
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    md_header_splits = markdown_splitter.split_text(content)
    
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    splits = text_splitter.split_documents(md_header_splits)
    
    chunks = []
    for split in splits:
        section = " > ".join([v for k, v in split.metadata.items() if k.startswith("Header")])
        formatted_content = f"[{source} > {section}]\n{split.page_content}" if section else split.page_content
        chunks.append({
            "content": formatted_content,
            "metadata": {
                "source": source,
                "section": section,
                "page": None
            }
        })
    return chunks
