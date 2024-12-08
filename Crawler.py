from urllib.request import urlopen
from urllib.error import HTTPError, URLError
from bs4 import BeautifulSoup
import regex as re
from pymongo import MongoClient
import pprint
from urllib.parse import urljoin


class Frontier:
    """
    Manages the list of URLs to be crawled. Handles the queue-like structure
    to fetch and add URLs dynamically during the crawling process.
    """

    def __init__(self, baseurl):
        """
            Initializes the Frontier with a base URL, if provided.
            Maintains a list of URLs to be processed.
            """
        self.frontier = [baseurl] if baseurl is not None else []

    def done(self):
        """
            Checks if the Frontier is empty, indicating that no URLs are left to process.
            Returns:
                bool: True if the frontier is empty, False otherwise.
            """
        return len(self.frontier) == 0

    def nextURL(self):
        """
            Retrieves and removes the next URL from the Frontier.
            Returns:
                str: The next URL to be processed.
            """
        return self.frontier.pop(0)

    def addURL(self, url):
        """
        Adds a new URL to the Frontier for future crawling.
        Args:
            url (str): The URL to be added to the Frontier.
        """

        # Add a new URL to the frontier
        self.frontier.append(url)


class Crawler:
    """
       Implements the web crawler functionality, including fetching web pages,
       storing them in MongoDB, identifying target pages, and extracting relevant data.
       """

    # --- Initialization Methods ---
    def __init__(self, baseurl):
        """
            Initializes the Crawler with a base URL, MongoDB connection, and the Frontier.
            Args:
                baseurl (str): The starting point for the crawler.
            """
        self.frontier = Frontier(baseurl)
        self.visited = set()  # Track visited URLs
        db = self.connectToMongoDB()
        self.crawledPages = db['CrawledPages']  # Reference to the MongoDB collection

    def connectToMongoDB(self):
        """
        Establishes a connection to the MongoDB database.
        Returns:
            MongoClient: A MongoDB database object.
        """
        DB_NAME = "CPP_Biology"
        DB_HOST = "localhost"
        DB_PORT = 27017
        try:
            client = MongoClient(host=DB_HOST, port=DB_PORT)
            db = client[DB_NAME]
            return db
        except:
            print("Database not connected successfully")
        # Remove all existing documents in the collection
        self.crawledPages.delete_many({})

    # --- Utility Methods ---
    def retrievHTML(self, url):
        """
        Fetches the HTML content of the given URL.
        Args:
            url (str): The URL to fetch HTML from.
        Returns:
            str: The HTML content as a string, or None if the fetch fails.
        """
        try:
            response = urlopen(url)
            self.visited.add(url)  # Mark the URL as visited
            return response.read().decode('utf-8', errors='ignore')
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

    def savePage(self, url, html, is_target):
        """
        Saves a web page's URL, HTML content, and target flag to the MongoDB collection.
        Args:
            url (str): The URL of the page.
            html (str): The HTML content of the page.
            is_target (bool): Whether the page is a target page or not.
        """
        entry = {
            'url': url.strip(),
            'isTarget': is_target,
            'html': html,
        }
        self.crawledPages.insert_one(entry)


    def parseForLinks(self, bs):
        """
        Extracts all valid hyperlinks from the page.
        Converts relative links to absolute URLs.
        Args:
            bs (BeautifulSoup): Parsed HTML content.
        Returns:
            list: A list of extracted URLs.
        """
        discovered_links = [item['href'] for item in bs.find_all(
            'a', href=re.compile(r'^(?!#).*$'))]
        for i, item in enumerate(discovered_links):
            if item.startswith('/'):
                discovered_links[i] = "https://www.cpp.edu" + item
            elif item.startswith('http'):
                continue  # Leave full URLs as is
        return discovered_links

    # --- Inspection Methods ---
    def inspect_pages(self):
        """
               Displays all documents stored in the 'pages' MongoDB collection.
               Useful for debugging and verifying stored data.
               """
        for document in self.crawledPages.find():
            pprint.pprint(document)

    # --- Target Identification Methods ---
    def match_target_element(self, bs):
        """
        Checks if a web page contains a specific target element.
        Args:
            bs (BeautifulSoup): Parsed HTML content.
        Returns:
            Tag or None: The matched element if found, otherwise None.
        """
        return bs.find('div', {'class': 'fac-info'})

    def isValidPage(self, page, url):
        """
        Validates the page document retrieved from MongoDB.
        Args:
            page (dict): The MongoDB document of the page.
            url (str): The URL of the page.
        Returns:
            bool: True if the page is valid, False otherwise.
        """
        if not page or 'html' not in page:
            print(f"No HTML content found for target page: {url}")
            return False
        return True

    def processNavigationLinks(self, soup, url):
        """
        Processes the navigation links from the 'fac-nav' section of the page.
        Args:
            soup (BeautifulSoup): The parsed HTML content of the page.
            url (str): The URL of the page.
        """
        fac_nav = soup.find('ul', class_='fac-nav')
        if not fac_nav:
            print(f"'fac-nav' not found for URL: {url}")
            return

        nav_links = self.extractNavigationLinks(fac_nav)
        self.fetchAndStoreNavLinks(nav_links, url)

    def extractNavigationLinks(self, fac_nav):
        """
        Extracts all valid navigation links from the 'fac-nav' section.
        Args:
            fac_nav (Tag): The 'ul' element containing navigation links.
        Returns:
            list: A list of extracted links.
        """
        nav_links = []
        for li in fac_nav.find_all('li'):
            link_tag = li.find('a')
            if link_tag and 'href' in link_tag.attrs:
                href = link_tag['href']
                # Skip specific unwanted links
                if href.strip().lower() != 'index.shtml':
                    nav_links.append(href)
        return nav_links

    def fetchAndStoreNavLinks(self, nav_links, url):
        """
        Fetches and stores HTML content of each navigation link in MongoDB.
        Args:
            nav_links (list): A list of navigation links.
            url (str): The URL of the parent page.
        """
        for link in nav_links:
            full_url = self.constructFullUrl(url, link)
            print(f"Navigation link identified: {full_url}")

            nav_html = self.retrievHTML(full_url)
            if nav_html:
                self.storeNavigationLinkHtml(url, link, nav_html)
            else:
                print(f"Failed to fetch navigation link: {full_url}")

    def constructFullUrl(self, url, link):
        """
        Constructs the full URL for a given navigation link.
        Args:
            url (str): The URL of the parent page.
            link (str): The navigation link.
        Returns:
            str: The full URL of the navigation link.
        """
        tempUrl = None
        if not url.endswith('/'):
            # special case for professor Steve Alas
            if '.' not in url.split('/')[-1]:
                tempUrl = url + '/'
        return urljoin(tempUrl, link) if tempUrl else urljoin(url, link)

    def storeNavigationLinkHtml(self, parent_url, link, nav_html):
        """
        Stores the HTML content of a navigation link in the MongoDB document.
        Args:
            parent_url (str): The URL of the parent page.
            link (str): The navigation link.
            nav_html (str): The HTML content of the navigation link.
        """
        self.crawledPages.update_one(
            {'url': parent_url},
            {'$set': {f'nav_links.{link}': BeautifulSoup(
                nav_html, 'html.parser').prettify()}}
        )
        print(f"Navigation page stored for link: {link}")

    # --- Frontier Management Methods ---
    def resetFrontier(self):
        """
        Resets the Frontier, effectively clearing the queue of URLs.
        """
        self.frontier = Frontier(None)

    # --- Crawling Logic ---
    def crawl(self, num_targets=10):
        """
        Implements the main crawling logic:
        - Fetches pages from the Frontier.
        - Identifies and flags target pages.
        - Stops after finding the specified number of target pages.
        Args:
            num_targets (int): The number of target pages to find before stopping.
        """
        targets_found = 0
        while not self.frontier.done():
            url = self.frontier.nextURL()
            html = self.retrievHTML(url)
            if html is None:
                continue

            bs = BeautifulSoup(html, 'html.parser')
            # Check if the page is a target
            is_target = bool(self.match_target_element(bs))
            
            # Save the page with the determined isTarget flag
            self.savePage(url, bs.prettify(), is_target)

            # Process the target page if applicable
            if is_target:
                self.processNavigationLinks(bs, url.strip())
                targets_found += 1

            if targets_found == num_targets:
                self.resetFrontier()
                print(
                    f"{targets_found} targets found. Frontier cleared. Terminating crawl.")
                break

            for item in self.parseForLinks(bs):
                if item not in self.visited:
                    self.frontier.addURL(item)


if __name__ == '__main__':
    """
    Main execution block of the script.
    Ensures that the script runs only when executed directly, not when imported as a module.
    """

    # Instantiate the Crawler class with the base URL to begin the web crawling process.
    # This URL serves as the starting point for the crawler.
    crawler = Crawler(
        'https://www.cpp.edu/sci/biological-sciences/index.shtml')

    # Initiate the crawling process.
    # The crawler will fetch pages, store them in MongoDB, and identify target pages.
    crawler.crawl()

    # Print a message to indicate that the crawling process is complete.
    print("Crawling Process Done!")