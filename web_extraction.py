import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
import regex as re
from pathlib import Path


class WebScraper:
    def __init__(self, 
                 knowledge_directory="knowledge_base",
                 total_url_limit=1000,
                 url_limit_per_website=100,
                 verbose=True):
        """
        Initialize the WebScraper with configuration parameters.
        
        Args:
            knowledge_directory: Directory to save markdown files
            total_url_limit: Maximum total URLs to extract across all websites
            url_limit_per_website: Maximum URLs to extract per website
            verbose: Enable detailed logging
        """
        self.knowledge_directory = Path(knowledge_directory)
        self.total_url_limit = total_url_limit
        self.url_limit_per_website = url_limit_per_website
        self.verbose = verbose
        
        # Create directory if it doesn't exist
        self.knowledge_directory.mkdir(exist_ok=True)
        
        # Default websites to scrape
        self.top_level_websites = [
            "https://cse.umn.edu/", 
            "https://ote.umn.edu/", 
            "https://onestop.umn.edu/"
        ]
        
        # Filter configurations
        self.excluded_extensions = [
            # Images
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico',
            # Documents
            '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
            # Media
            '.mp4', '.avi', '.mov', '.mp3', '.wav',
            # Archives
            '.zip', '.rar', '.tar', '.gz'
        ]
        
        self.forbidden_websites = [
            "youtube", "vimeo", "twitter", "facebook", "instagram", 
            "linkedin", "tiktok", "flickr", "pinterest", "reddit", 
            "tumblr", "snapchat", "whatsapp", "telegram", "discord", 
            "sociablecider"
        ]
        
        self.static_patterns = [
            '/files/', '/images/', '/assets/', '/static/', '/media/', 'itok='
        ]

    def url_to_filename(self, url):
        """
        Convert a URL to a valid filename that preserves structure.
        """
        # Remove protocol and trailing slash
        if url.endswith("/"):
            url = url[:-1]
        
        clean_url = url.replace("https://", "").replace("http://", "").replace("www.", "")
        
        # Use distinct separators:
        # / becomes _SLASH_  
        # - stays as -
        filename = clean_url.replace("/", "_SLASH_")
        
        return filename + ".md"

    def filename_to_url(self, filename):
        """Convert filename back to URL"""
        name = filename.replace('.md', '')
        url_part = name.replace('_SLASH_', '/')
        return f"https://{url_part}"

    async def convert_HTML_2_Markdown(self, website):
        """
        Scrape a website and convert it to markdown format.
        
        Args:
            website: URL of the website to scrape
            
        Returns:
            Path to the saved markdown file or None if failed
        """
        config = CrawlerRunConfig(
            markdown_generator = DefaultMarkdownGenerator(),
            # Core
            verbose=self.verbose,            # Detailed logging

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

                save_file = self.url_to_filename(website)
                filepath = self.knowledge_directory / save_file
                
                if result.success:
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(result.markdown)

                    if self.verbose:
                        print(f"✓ Markdown content saved to {filepath}")
                    return filepath
                else:
                    raise Exception(f"Failed to scrape {website}: !result.success, {result.error_message}")  
            except Exception as e:
                print(f"✗ Error occurred while scraping {website}. Error: {e}")
                return None

    def filter_links(self, links):
        """Filter out unwanted links based on configured criteria."""
        filtered_links = []
        for url in links:
            # Check for forbidden websites
            is_forbidden = any(forbidden_site in url.lower() for forbidden_site in self.forbidden_websites)
            if is_forbidden:
                continue
                
            # Check for file extensions
            url_lower = url.lower()
            is_file = any(url_lower.endswith(ext) for ext in self.excluded_extensions)
            if is_file:
                continue
                
            # Check for common non-page patterns
            if any(pattern in url_lower for pattern in self.static_patterns):
                continue
                
            filtered_links.append(url)
        return filtered_links

    def extract_embeded_links(self, md, debug=0, save=0, limit=None):
        """
        Extract embedded links from the markdown file.
        
        Args:
            md: Path to markdown file (string or Path object)
            debug: Print debug information if 1
            save: Save links to file if 1
            limit: Maximum number of links to return
            
        Returns:
            List of filtered and cleaned URLs
        """
        # Handle both string paths and Path objects
        filepath = Path(md) if isinstance(md, str) else md
        
        # Check file extension using Path object
        if filepath.suffix != ".md":
            raise ValueError("Input must be a markdown file with .md extension")
        
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        if content is None or content.strip() == "":
            return []

        # Find all links
        links = re.findall(r'(?<=\()https?://[^\s\)"]+(?=[\s\)"])', content)
        if self.verbose:
            print(f"Found {len(links)} links in the markdown file")

        # edit the links
        links = [url.split("#")[0] if "#" in url else url for url in links]
        links = [url[:-1] if url.endswith("/") else url for url in links]  # Remove trailing slashes

        # filtering out unwanted links
        links = self.filter_links(links)
        links = [url[:-1] if url.endswith("/") else url for url in links]  # Remove trailing slashes again after filtering

        # Remove duplicates and sort
        links = sorted(set(links))

        if limit is not None:
            links = links[:limit] # TODO: maybe use llm to rank the links base on relevance

        if debug:
            for url in links:
                print(f"URL: {url}")
        
        if save:
            with open("extracted_links.txt", "w", encoding="utf-8") as f:
                for url in links:
                    line = f"{url} --> {self.url_to_filename(url)}\n"
                    f.write(line)  # Use write() instead of writelines()

        return links

    async def scrape_website_and_extract_links(self, website, extract_limit=None):
        """
        Scrape a website and extract its embedded links.
        
        Args:
            website: URL of the website to scrape
            extract_limit: Maximum number of links to extract (uses instance limit if None)
            
        Returns:
            List of extracted links
        """
        # First scrape the website
        markdown_file = await self.convert_HTML_2_Markdown(website)
        
        if markdown_file is None:
            return []
        
        # Then extract links from the markdown
        limit = extract_limit or self.url_limit_per_website
        links = self.extract_embeded_links(
            markdown_file, 
            debug=0,
            save=1,
            limit=limit
        )
        
        if self.verbose:
            print(f"✓ {len(links)} links found after filtering")
        
        return links

    async def scrape_all_websites(self):
        """Scrape all configured top-level websites."""
        all_links = []
        
        for website in self.top_level_websites:
            if self.verbose:
                print(f"\n🌐 Scraping: {website}")
            
            links = await self.scrape_website_and_extract_links(website)
            all_links.extend(links)
            
            if len(all_links) >= self.total_url_limit:
                if self.verbose:
                    print(f"Reached total URL limit ({self.total_url_limit})")
                break
        
        # Remove duplicates across all websites
        unique_links = sorted(set(all_links))
        
        if self.verbose:
            print(f"\n✅ Total unique links found: {len(unique_links)}")
        
        return unique_links


async def main():
    """Example usage of the WebScraper class."""
    # Create scraper instance
    scraper = WebScraper(
        knowledge_directory="knowledge_base",
        url_limit_per_website=100,
        verbose=True
    )
    
    # Option 1: Scrape single website
    website = scraper.top_level_websites[0]  # Use first website from the list
    print(f"🌐 Scraping single website: {website}")
    
    links = await scraper.scrape_website_and_extract_links(website)
    print(f"✅ Found {len(links)} links from {website}")
    
    # Option 2: Scrape all configured websites (uncomment to use)
    # print("\n🌐 Scraping all configured websites...")
    # all_links = await scraper.scrape_all_websites()


if __name__ == "__main__":
    asyncio.run(main())



# prune = PruningContentFilter(threshold=0.5, threshold_type="fixed", min_word_threshold=50)
# md_gen = DefaultMarkdownGenerator(content_filter=prune)

# cfg = CrawlerRunConfig(markdown_generator=md_gen, exclude_external_links=True,
#                        excluded_tags=["nav", "footer", "header"], word_count_threshold=20)

# async with AsyncWebCrawler() as crawler:
#     result = await crawler.arun(url="https://cse.umn.edu", config=cfg)
#     print(result.markdown_raw[:200])
#     print(result.markdown_fit[:200])