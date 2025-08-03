import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
import regex as re
from pathlib import Path
import json
import os
from datetime import datetime


class WebScraper:
    def __init__(self, 
                 knowledge_directory="knowledge_base",
                 scraped_urls_file="scraped_urls.json",
                 links_queue_file="links_queue.json",
                 top_level_websites=["https://cse.umn.edu/", "https://ote.umn.edu/", "https://onestop.umn.edu/"],
                 total_url_limit=1000,
                 url_limit_per_website=100,
                 verbose=True,
                 ):
        """
        Initialize the WebScraper with configuration parameters.
        
        Args:
            knowledge_directory: Directory to save markdown files
            total_url_limit: Maximum total URLs to extract across all websites
            url_limit_per_website: Maximum URLs to extract per website
            verbose: Enable detailed logging
            top_level_websites: List of initial websites to scrape
            scraped_urls_file: File to persist scraped URLs
            links_queue_file: File to persist pending URLs queue
        """
        # important file paths for persistence
        self.knowledge_directory = Path(knowledge_directory)
        self.knowledge_directory.mkdir(exist_ok=True)
        self.scraped_urls_file = Path(scraped_urls_file)
        # file structure
        # {
        #     "scraped_urls": [
        #         "https://cse.umn.edu",
        #         "https://cse.umn.edu/college",
        #         "https://cse.umn.edu/college/academic-advising",
        #         "https://ote.umn.edu",
        #         "https://onestop.umn.edu/academics"
        #     ],
        #     "count": 5,
        #     "last_updated": "2025-08-03T14:30:45.123456",
        #     "scraper_config": {
        #         "url_limit_per_website": 100,
        #         "total_url_limit": 1000
        #     }
        # }
        self.links_queue_file = Path(links_queue_file)
        # file structure
        # {
        #     "pending_urls": [
        #         "https://cse.umn.edu/college/alumni-awards-and-honors",
        #         "https://cse.umn.edu/college/distinguished-leadership-award",
        #         "https://ote.umn.edu/programs",
        #         "https://onestop.umn.edu/registration",
        #         "https://cse.umn.edu/college/student-services"
        #     ],
        #     "count": 5,
        #     "last_updated": "2025-08-03T14:30:45.123456"
        # }

        # In-memory sets for fast lookups
        self.scraped_urls = set()           # URLs we've already scraped
        self.pending_urls = set()           # URLs we plan to scrape
        
        # Load existing data
        self._load_scraped_urls()
        self._load_pending_urls()

        # Default websites to scrape
        self.top_level_websites = top_level_websites

        # Configuration limits
        self.total_url_limit = total_url_limit
        self.url_limit_per_website = url_limit_per_website
        self.num_websites_scraped = 0 # TODO: update this number on change on self.scraped_urls

        # debugging purposes
        self.verbose = verbose
        
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

    def _load_scraped_urls(self):
        """Load previously scraped URLs from disk."""
        if self.scraped_urls_file.exists():
            try:
                with open(self.scraped_urls_file, 'r') as f:
                    data = json.load(f)
                    self.scraped_urls = set(data.get('scraped_urls', []))
                    if self.verbose:
                        print(f"✓ Loaded {len(self.scraped_urls)} previously scraped URLs")
            except Exception as e:
                print(f"⚠ Error loading scraped URLs: {e}")
                self.scraped_urls = set()

    def _save_scraped_urls(self):
        """Save scraped URLs to disk with metadata."""
        data = {
            'scraped_urls': list(self.scraped_urls),
            'count': len(self.scraped_urls),
            'last_updated': datetime.now().isoformat(),
            'scraper_config': {
                'url_limit_per_website': self.url_limit_per_website,
                'total_url_limit': self.total_url_limit
            }
        }
        
        with open(self.scraped_urls_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _load_pending_urls(self):
        """Load URLs that are queued for scraping."""
        if self.links_queue_file.exists():
            try:
                with open(self.links_queue_file, 'r') as f:
                    data = json.load(f)
                    self.pending_urls = set(data.get('pending_urls', []))
                    if self.verbose:
                        print(f"✓ Loaded {len(self.pending_urls)} pending URLs")
            except Exception as e:
                print(f"⚠ Error loading pending URLs: {e}")
                self.pending_urls = set()

    def _save_pending_urls(self):
        """Save pending URLs to disk."""
        data = {
            'pending_urls': list(self.pending_urls),
            'count': len(self.pending_urls),
            'last_updated': datetime.now().isoformat()
        }
        
        with open(self.links_queue_file, 'w') as f:
            json.dump(data, f, indent=2)

    def _update_persistence_file(self):
        self._save_scraped_urls()
        self._save_pending_urls()

    def add_urls_to_queue(self, urls):
        """Add new URLs to the scraping queue (if not already scraped)."""
        new_urls = set(urls) - self.scraped_urls - self.pending_urls
        
        if new_urls:
            self.pending_urls.update(new_urls)
            self._save_pending_urls()  # Persist immediately
            
            if self.verbose:
                print(f"✓ Added {len(new_urls)} new URLs to queue")
        
        return new_urls

    def mark_url_as_scraped(self, url):
        """Mark a URL as successfully scraped."""
        self.scraped_urls.add(url)
        self.pending_urls.discard(url)  # Remove from pending if present

        self.num_websites_scraped = len(self.scraped_urls)  # Update count

        # Save periodically (not on every URL to avoid I/O overhead)
        if len(self.scraped_urls) % 10 == 0:  # Save every 10 URLs
            self._save_scraped_urls()

    def is_url_scraped(self, url):
        """Fast O(1) check if URL has been scraped."""
        return url in self.scraped_urls

    def is_url_pending_scraped(self, url):
        """Check if URL is in the pending queue."""
        return url in self.pending_urls

    def get_next_urls_to_scrape(self, batch_size=10):
        """Get next batch of URLs to scrape."""
        batch = list(self.pending_urls)[:batch_size]
        return batch

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

    async def convert_HTML_2_Markdown(self, website, save=0):
        """
        Scrape a website and convert it to markdown format.
        
        Args:
            website: URL of the website to scrape
            
        Returns:
            Path to the saved markdown file or None if failed
        """
        # TODO: update the class variable on success
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

                
                if result.success:
                    save_file = self.url_to_filename(website)
                    filepath = self.knowledge_directory / save_file
                    if save == 1:
                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(result.markdown)

                    if self.verbose:
                        print(f"✓ Markdown content saved to {filepath}")
                    return filepath, result.markdown
                else:
                    raise Exception(f"Failed to scrape {website}: !result.success, {result.error_message}")  
            except Exception as e:
                print(f"✗ Error occurred while scraping {website}. Error: {e}")
                return None, None

    def filter_links(self, links):
        """Filter out unwanted links based on configured criteria."""
        filtered_links = []
        links = list(set(links) - self.scraped_urls - self.pending_urls)

        limit = min(self.total_url_limit - self.num_websites_scraped, self.url_limit_per_website)
        count = 0
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

            count += 1
            if count >= limit:
                break
        return filtered_links

    def extract_embedded_links(self, md="", debug=0):
        """
        Extract embedded links from the markdown file.
        
        Args:
            md: Path to markdown file (string or Path object)
            debug: Print debug information if 1
            limit: Maximum number of links to return
            
        Returns:
            List of filtered and cleaned URLs
        """
        # # Handle both string paths and Path objects
        # filepath = Path(fp) if isinstance(fp, str) else fp
        
        # # Check file extension using Path object
        # if filepath.suffix != ".md":
        #     raise ValueError("Input must be a markdown file with .md extension")
        
        # with open(filepath, "r", encoding="utf-8") as f:
        #     content = f.read()
        
        if md is None or md.strip() == "":
            return []

        # Find all links
        links = re.findall(r'(?<=\()https?://[^\s\)"]+(?=[\s\)"])', md)
        if self.verbose:
            print(f"Found {len(links)} links in the markdown file")

        # edit the links
        links = [url.split("#")[0] if "#" in url else url for url in links]
        links = [url[:-1] if url.endswith("/") else url for url in links]  # Remove trailing slashes

        # filtering out unwanted links
        links = self.filter_links(links)
        # links = [url[:-1] if url.endswith("/") else url for url in links]  # Remove trailing slashes again after filtering

        # Remove duplicates (no need to sort for performance)
        # links = sorted(links)
        links = list(set(links))

        

        if debug:
            for url in links:
                print(f"URL: {url}")
        
        # Don't save to file by default anymore - use sets for tracking
        # if save:
        #     with open("extracted_links.txt", "w", encoding="utf-8") as f:
        #         for url in links:
        #             line = f"{url} --> {self.url_to_filename(url)}\n"
        #             f.write(line)  # Use write() instead of writelines()

        return links

    async def scrape_website_and_extract_links(self, website, save=0):
        """
        Scrape a website and extract its embedded links.
        
        Args:
            website: URL of the website to scrape
            extract_limit: Maximum number of links to extract (uses instance limit if None)
            
        Returns:
            List of new URLs found (not previously scraped)
        """
        if self.num_websites_scraped >= self.total_url_limit:
            if self.verbose:
                print(f"🛑 Reached total URL limit ({self.total_url_limit})")
            
            self.pending_urls = set()  
            self._update_persistence_file()
            return []
        
        # Check if already scraped
        if self.is_url_scraped(website):
            if self.verbose:
                print(f"⏭ Skipping {website} (already scraped)")
            return []
        # elif self.is_url_pending_scraped(website):
        #     if self.verbose:
        #         print(f"⏭ Skipping {website} (already in pending queue)")
        #     return []

        # First scrape the website
        filepath, markdown = await self.convert_HTML_2_Markdown(website, save=save)

        # TODO: convert the markdown into vectors here
        # TODO: store the vectors embedding into a db here

        if markdown is None:
            return []
        
        # Then extract links from the markdown
        links = self.extract_embedded_links(
            md=markdown,
            debug=0,
        )
        
        # Mark this URL as scraped
        self.mark_url_as_scraped(website)
        
        # Add new links to queue
        new_links = self.add_urls_to_queue(links)
        
        if self.verbose:
            print(f"✓ Scraped {website}: found {len(links)} links, {len(new_links)} new")
        
        if len(self.pending_urls) == 0:
            self._update_persistence_file()

        return list(new_links)

    async def scrape_all_websites(self):
        """Scrape all configured top-level websites."""
        all_links = []
        
        for website in self.top_level_websites:
            if self.verbose:
                print(f"\n🌐 Scraping: {website}")
            
            links = await self.scrape_website_and_extract_links(website)
            all_links.extend(links)
            
            if len(self.scraped_urls) >= self.total_url_limit:
                if self.verbose:
                    print(f"Reached total URL limit ({self.total_url_limit})")
                break
        
        # Remove duplicates across all websites
        unique_links = list(set(all_links))
        
        if self.verbose:
            print(f"\n✅ Total unique new links found: {len(unique_links)}")
            print(f"📊 Total scraped URLs: {len(self.scraped_urls)}")
            print(f"📊 Pending URLs in queue: {len(self.pending_urls)}")
        
        return unique_links

    async def scrape_recursively(self, max_depth=3, batch_size=10):
        """
        Scrape recursively using the queue system.
        
        Args:
            max_depth: Maximum depth levels to scrape
            batch_size: Number of URLs to process in each batch
            
        Returns:
            Summary statistics
        """
        if self.verbose:
            print(f"🚀 Starting recursive scraping (max_depth={max_depth}, batch_size={batch_size})")
        
        # Start with top-level websites if nothing in queue
        if not self.pending_urls:
            self.add_urls_to_queue(self.top_level_websites)
        
        for depth in range(max_depth):
            if self.verbose:
                print(f"\n🔄 Starting depth {depth + 1}/{max_depth}")
            
            # Get next batch of URLs to scrape
            batch = self.get_next_urls_to_scrape(batch_size)
            
            if not batch:
                if self.verbose:
                    print("✅ No more URLs to scrape")
                break
            
            if self.verbose:
                print(f"📦 Processing batch of {len(batch)} URLs")
            
            # Process batch
            for url in batch:
                try:
                    # Check total limit
                    if len(self.scraped_urls) >= self.total_url_limit:
                        if self.verbose:
                            print(f"🛑 Reached total URL limit ({self.total_url_limit})")
                        break
                        
                    await self.scrape_website_and_extract_links(url)
                except Exception as e:
                    print(f"❌ Error scraping {url}: {e}")
                    # Still mark as scraped to avoid retrying
                    self.mark_url_as_scraped(url)
            
            if self.verbose:
                print(f"📊 Status: {len(self.scraped_urls)} scraped, {len(self.pending_urls)} pending")
            
            # Break if we hit the limit
            if len(self.scraped_urls) >= self.total_url_limit:
                break
        
        # Final save
        self._save_scraped_urls()
        self._save_pending_urls()
        
        summary = {
            'total_scraped': len(self.scraped_urls),
            'pending_urls': len(self.pending_urls),
            'max_depth_reached': depth + 1
        }
        
        if self.verbose:
            print(f"\n🎉 Recursive scraping complete!")
            print(f"📊 Final stats: {summary}")
        
        return summary


async def main():
    """Example usage of the WebScraper class."""
    top_level_websites=["https://cse.umn.edu/", "https://ote.umn.edu/", "https://onestop.umn.edu/"]

    dev_testing_website = top_level_websites[0]
    
    # Create scraper instance
    scraper = WebScraper(
        # for persistence
        knowledge_directory="knowledge_base",
        scraped_urls_file="scraped_urls.json",
        links_queue_file="links_queue.json",

        # limits argument
        url_limit_per_website=50,  # Reduced for faster testing
        total_url_limit=200,       # Reduced for faster testing
        verbose=True,

        # website(s) to scrape
        top_level_websites=dev_testing_website
    )
    
    print(f"📊 Initial state:")
    print(f"   - Previously scraped URLs: {len(scraper.scraped_urls)}")
    print(f"   - Pending URLs in queue: {len(scraper.pending_urls)}")
    
    # Option 1: Scrape single website
    website = dev_testing_website
    print(f"\n🌐 Scraping single website: {website}")
    
    links = await scraper.scrape_website_and_extract_links(website, save=1)
    print(f"✅ Found {len(links)} new links from {website}")
    scraper._update_persistence_file()  # Save state after single scrape
    
    # Option 2: Recursive scraping (uncomment to use)
    # print(f"\n🔄 Starting recursive scraping...")
    # summary = await scraper.scrape_recursively(max_depth=2, batch_size=5)
    
    # Option 3: Scrape all configured websites (alternative approach)
    # print("\n🌐 Scraping all configured websites...")
    # all_links = await scraper.scrape_all_websites()


if __name__ == "__main__":
    asyncio.run(main())


