import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
import regex as re

knowledge_directory = "knowledge_base"
all_top_level_websites = ["https://cse.umn.edu/", "https://ote.umn.edu/", "https://onestop.umn.edu/"]
total_url_extraction_limit = 1000
url_extraction_limit_per_website = 100

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
    # filename = clean_url.replace(".", "_DOT_").replace("/", "_SLASH_")
    filename = clean_url.replace("/", "_SLASH_")
    
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
        excluded_tags = ["small", "header", "footer"],           # Remove entire tag blocks
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
        try:
            result = await crawler.arun(
                website, 
                config=config
                )
            # print("Raw Markdown length:", len(result.markdown.raw_markdown))
            # print("Fit Markdown length:", len(result.markdown.fit_markdown))

            save_file = url_to_filename(website)
            
            if result.success:
                with open(save_file, "w", encoding="utf-8") as f:
                    f.write(result.markdown)

                print(f"Markdown content saved to {save_file}")
            else:
                raise Exception(f"Failed to scrape {website}: !result.success, {result.error_message}")  
        except Exception as e:
            print(f"Error occurred while scraping {website}. Error: {e}")
            return

def filter_links(links):
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

    forbidden_websites = ["youtube", "vimeo", "twitter", "facebook", "instagram", "linkedin", "tiktok", "flickr", "pinterest", "reddit", "tumblr", "snapchat", "whatsapp", "telegram", "discord", "sociablecider"] # filter out social media cause atm, our goal is to provide orientation information to incoming freshman

    static_items = ['/files/', '/images/', '/assets/', '/static/', '/media/', 'itok=']

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
        if any(pattern in url_lower for pattern in static_items):
            continue
            
        filtered_links.append(url)
    return filtered_links

def extract_embeded_links(md, debug=0, save=0, limit=None):
    """
    Extract embedded links from the markdown file.
    """
    if not md.endswith(".md"):
        raise ValueError("Input must be a markdown file with .md extension")
    
    with open(md, "r", encoding="utf-8") as f:
        content = f.read()
    
    if content is None or content.strip() == "":
        return []

    # Find all links
    links = re.findall(r'(?<=\()https?://[^\s\)"]+(?=[\s\)"])', content)
    print(f"Found {len(links)} links in the markdown file")

    # edit the links
    links = [url.split("#")[0] if "#" in url else url for url in links]
    links = [url[:-1] if url.endswith("/") else url for url in links]  # Remove trailing slashes

    # filtering out unwanted links
    links = filter_links(links)
    links = [url[:-1] if url.endswith("/") else url for url in links]  # Remove trailing slashes
    # print(f"Found {len(links)} links after filtering")

    # Remove duplicates and sort
    links = sorted(set(links))
    # print(f"Found {len(links)} unique links after removing duplicates")

    if limit is not None:
        links = links[:limit] # TODO: maybe use llm to rank the links base on relevance
        # print(f"Limiting to {limit} links, total links after limit: {len(links)}")

    if debug:
        # print(f"Found {len(links)} links after filtering")
        for url in links:
            print(f"URL: {url}")
    
    if save:
        with open("extracted_links.txt", "w", encoding="utf-8") as f:
            for url in links:
                line = f"{url} --> {url_to_filename(url)}\n"
                f.writelines(line)

    return links

def main():
    top_level_website = all_top_level_websites[0] # For now, just use the first one

    asyncio.run(convert_HTML_2_Markdown(top_level_website))
    embedded_links = extract_embeded_links(url_to_filename(top_level_website), save=1, limit=url_extraction_limit_per_website)
    print(len(embedded_links), "links found after filtering")

main()



# prune = PruningContentFilter(threshold=0.5, threshold_type="fixed", min_word_threshold=50)
# md_gen = DefaultMarkdownGenerator(content_filter=prune)

# cfg = CrawlerRunConfig(markdown_generator=md_gen, exclude_external_links=True,
#                        excluded_tags=["nav", "footer", "header"], word_count_threshold=20)

# async with AsyncWebCrawler() as crawler:
#     result = await crawler.arun(url="https://cse.umn.edu", config=cfg)
#     print(result.markdown_raw[:200])
#     print(result.markdown_fit[:200])