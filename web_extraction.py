import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
import regex as re


def url_to_filename(url):
    """
    Convert a URL to a valid filename that preserves structure.
    """
    # Remove protocol and trailing slash
    if url.endswith("/"):
        url = url[:-1]
    
    clean_url = url.replace("https://", "").replace("http://", "").replace("www.", "")
    
    # Use distinct separators:
    # . becomes _DOT_
    # / becomes _SLASH_  
    # - stays as -
    filename = clean_url.replace(".", "_DOT_").replace("/", "_SLASH_")
    
    return filename + ".md"

def filename_to_url(filename):
    """Convert filename back to URL"""
    name = filename.replace('.md', '')
    url_part = name.replace('_DOT_', '.').replace('_SLASH_', '/')
    return f"https://{url_part}"

# name = url_to_filename(top_level_website)
# print(f"Generated filename: {name}")

async def convert_HTML_2_Markdown(website):
    config = CrawlerRunConfig(
        markdown_generator = DefaultMarkdownGenerator(),
        # Core
        verbose=True,            # Detailed logging

        # Content
        excluded_tags = ["small"],           # Remove entire tag blocks
        exclude_social_media_links=True,     # Remove links to known social sites

        # # Page & JS
        # js_code="document.querySelector('.show-more')?.click();",
        # wait_for="css:.loaded-block",
        # page_timeout=30000,

        # # Extraction
        # extraction_strategy=JsonCssExtractionStrategy(schema),

        # # Session
        # session_id="persistent_session",

        # # Media
        # screenshot=True,
        # pdf=True,

        # # Anti-bot
        # simulate_user=True,
        # magic=True,
    )

    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            website, 
            config=config
            )

        save_file = url_to_filename(website)

        with open(save_file, "w", encoding="utf-8") as f:
            f.write(result.markdown)

        print(f"Markdown content saved to {save_file}")


def extract_embeded_links(md, debug=0, save=0):
    """
    Extract embedded links from the markdown file.
    """
    if not md.endswith(".md"):
        raise ValueError("Input must be a markdown file with .md extension")
    
    with open(md, "r", encoding="utf-8") as f:
        content = f.read()

    # File extensions to exclude
    excluded_extensions = [
        # Images
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico',
        # Documents
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        # Media
        '.mp4', '.avi', '.mov', '.mp3', '.wav',
        # Archives
        '.zip', '.rar', '.tar', '.gz'
    ]
    
    forbidden_websites = ["youtube", "vimeo", "twitter", "facebook", "instagram", "linkedin", "tiktok", "flickr", "pinterest", "reddit", "tumblr", "snapchat", "whatsapp", "telegram", "discord", "sociablecider"]
    
    # Find all links
    links = re.findall(r'(?<=\()https?://[^\s\)"]+(?=[\s\)"])', content)
    links = [url.split("#")[0] if "#" in url else url for url in links]
    
    # Filter links
    filtered_links = []
    for url in links:
        # Check for forbidden websites
        is_forbidden = any(forbidden_site in url.lower() for forbidden_site in forbidden_websites)
        if is_forbidden:
            continue
            
        # Check for file extensions
        url_lower = url.lower()
        is_file = any(url_lower.endswith(ext) for ext in excluded_extensions)
        if is_file:
            continue
            
        # Check for common non-page patterns
        if any(pattern in url_lower for pattern in ['/files/', '/images/', '/assets/', '/static/', '/media/', 'itok=']):
            continue
            
        filtered_links.append(url)
    links = filtered_links
    
    # Remove duplicates and sort
    links = [url[:-1] if url.endswith("/") else url for url in links]  # Remove trailing slashes
    links = sorted(set(links))
    print(len(links), "links found after filtering")
    
    if debug:
        print(f"Found {len(links)} links after filtering")
        for url in links:
            print(f"URL: {url}")
    
    if save:
        with open("extracted_links.txt", "w", encoding="utf-8") as f:
            f.writelines(url + "\n" for url in links)

    return links

def main():
    top_level_website = "https://cse.umn.edu/"

    asyncio.run(convert_HTML_2_Markdown(top_level_website))
    embedded_links = extract_embeded_links(url_to_filename(top_level_website), save=1)

main()