from pymongo import MongoClient
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin

# Function to connect to the MongoDB database


def connectDataBase():
    """
       Connects to the MongoDB database using the provided host, port, and database name.
       Ensures the database is accessible before proceeding with data extraction.
       Returns the database object for further operations.
       """
    DB_NAME = 'CPP_Biology'
    DB_HOST = 'localhost'
    DB_PORT = 27017
    try:
        # Establish a connection to MongoDB
        client = MongoClient(host=DB_HOST, port=DB_PORT)
        db = client[DB_NAME]  # Select the database
        return db
    except Exception as e:
        print(f"Database connection failed: {e}")

# Function to process faculty pages and extract structured data


def handle_faculty_pages(pages_collection, faculty_collection):
    """
    Handles all faculty pages marked as target pages in the database.
    Iterates through each target page and processes it to extract structured data.
    Stores the processed data into a separate MongoDB collection for faculty information.
    """
    # Fetch all target pages
    faculty_pages = list(pages_collection.find({"isTarget": True}))
    for member in faculty_pages:
        process_faculty_page(member, pages_collection, faculty_collection)


def process_faculty_page(member, pages_collection, faculty_collection):
    """
    Processes an individual faculty page to extract and structure data.
    Utilizes helper functions to extract specific content such as main body text,
    aside sections, navigation links, and faculty details.
    Combines the extracted data into a comprehensive summary and saves it in the faculty collection.
    """
    # Extract basic page information
    html = member['html']
    url = member['url']
    bs = BeautifulSoup(html, 'html.parser')

    # Extract and process main body content
    main_body_text = extract_main_body(bs, url)

    # Extract and process aside sections
    aside_text = extract_aside_sections(bs, url)

    # Process navigation links
    summary = f"About Me {main_body_text}\n\n{aside_text}".strip()
    summary += process_navigation_links(member, url)

    # Extract faculty details
    faculty_details = extract_faculty_details(bs, url)

    # Combine all extracted information
    summary += f"\n\n{faculty_details['info']}\n"
    print_faculty_details(faculty_details)

    # Prepare and insert data into the faculty collection
    faculty_data = prepare_faculty_data(member, faculty_details, summary, url)
    faculty_collection.insert_one(faculty_data)


def extract_main_body(bs, url):
    """
     Extracts the main descriptive content of a faculty page, identified by the 'blurb' class.
     Provides a concise summary of the primary page information.
     Handles cases where no main body content is available gracefully.
     """
    main_body = bs.find('div', class_='blurb')
    if main_body:
        main_body_text = main_body.get_text(separator='\n', strip=True)
        print(f"Extracted Main Body Text from {url}")
        print(main_body_text)
        return main_body_text
    else:
        print(f"No main body found in {url}")
        return ''


def extract_aside_sections(bs, url):
    """
    Extracts additional information from aside sections on a faculty page.
    Labels sections with their aria-label attributes for better context.
    Consolidates text from multiple aside sections into a single summary.
    """
    aside_text = ''
    asides = bs.select('main aside')
    for aside in asides:
        aria_label = aside.get('aria-label', 'Unknown Section')
        section_text = aside.get_text(separator='\n', strip=True)
        aside_text += f"\n[Section: {aria_label}]\n{section_text}\n"
        print(f"Extracted text from aside section: {aria_label}")
    return aside_text


def process_navigation_links(member, url):
    """
    Processes navigation links available on a faculty page.
    Retrieves and parses the HTML content of linked pages to extract relevant information.
    Appends the extracted content to the overall summary.
    Handles missing or malformed navigation links gracefully.
    """
    summary = ''
    nav_links = member.get('nav_links', {})
    for link_name, link_data in nav_links.items():
        link_html = link_data.get('shtml', '')
        if not link_html.strip():
            print(f"No HTML content found for navigation link: {link_name}")
            continue
        try:
            nav_soup = BeautifulSoup(link_html, 'html.parser')
            nav_body = nav_soup.find('div', class_='blurb')
            if nav_body:
                nav_text = nav_body.get_text(separator='\n', strip=True)
                summary += f"\n\n[Navigation Section: {link_name}]\n{nav_text}"
                print(f"Extracted important text from navigation link: {link_name}")
            else:
                print(f"No important content found in navigation link: {link_name}")
        except Exception as e:
            print(f"Error parsing navigation link {link_name}: {e}")
    return summary


def extract_faculty_details(bs, url):
    """
    Extracts specific details about a faculty member, including name, title, email, phone number, and address.
    Gathers details from the 'fac-info' section and ensures that all missing data is handled with default values.
    Constructs a descriptive faculty info string for inclusion in the summary.
    """
    fac_info = bs.find('div', class_='fac-info')
    if not fac_info:
        return {
            'name': 'Not Available',
            'email': 'Not Available',
            'phone': 'Not Available',
            'image_url': 'default_image.jpg',
            'address': 'Not Available',
            'info': ''
        }

    title_dept = fac_info.find('span', class_='title-dept').get_text(strip=True) if fac_info.find('span', class_='title-dept') else "Not Available"
    name = fac_info.h1.get_text(strip=True) if fac_info.h1 else "Not Available"
    email = fac_info.find('a', {'href': re.compile(r'mailto:')}).get_text(strip=True) if fac_info.find('a', {'href': re.compile(r'mailto:')}) else "Not Available"
    phone = fac_info.find('p', class_='phoneicon').get_text(strip=True) if fac_info.find('p', class_='phoneicon') else "Not Available"
    image_url = extract_image_url(fac_info, url)
    address = extract_address(fac_info)

    faculty_info = f"{name}. {title_dept}. Email: {email}. Phone number: {phone}. Address: {address}."
    
    return {
        'name': name,
        'email': email,
        'phone': phone,
        'image_url': image_url,
        'address': address,
        'info': faculty_info
    }



def extract_image_url(fac_info, url):
    """
    Extracts the URL of the faculty member's profile image from the 'fac-info' section.
    Converts relative image URLs into absolute URLs for consistent accessibility.
    Provides a default image URL if no valid image is found.
    """
    image_tag = fac_info.find('img')
    if image_tag and 'src' in image_tag.attrs:
        image_url = image_tag['src']
        if not image_url.startswith('http'):
            url = ensure_trailing_slash(url)
            image_url = urljoin(url, image_url)
        return image_url
    return "default_image.jpg"


def extract_address(fac_info):
    """
    Extracts the office location or address of the faculty member.
    Retrieves the text from the 'locationicon' class within the 'fac-info' section.
    Handles cases where the address is unavailable gracefully.
    """
    location_tag = fac_info.find('p', class_='locationicon')
    if location_tag and location_tag.find('a'):
        return location_tag.find('a').get_text(strip=True)
    return "Not Available"


def print_faculty_details(details):
    """
    Outputs the extracted faculty details to the console for verification.
    Useful for debugging and ensuring that the extracted data is accurate and complete.
    """
    print(f"Faculty Name: {details['name']}")
    print(f"Faculty Email: {details['email']}")
    print(f"Faculty Contact Number: {details['phone']}")
    print(f"Faculty Image URL: {details['image_url']}")
    print(f"Faculty Info: {details['info']}")
    print()


def prepare_faculty_data(member, details, summary, url):
    """
    Prepares a structured dictionary of all extracted faculty data for insertion into MongoDB.
    Combines the summary, contact details, and other metadata into a single cohesive format.
    Ensures compatibility with the schema of the faculty_info collection.
    """
    return {
        'faculty_name': details['name'],
        'faculty_email': details['email'],
        'contact_number': details['phone'],
        'profile_image': details['image_url'],
        'office_location': details['address'],
        'profile_url': url,
        'reference_id': member['_id'],
        'faculty_info': summary,
        'summary': details['info']
    }

# Function to ensure the URL ends with a trailing slash


def ensure_trailing_slash(url):
    """
       Validates and adjusts the base URL to ensure it ends with a trailing slash.
       Prevents issues with relative URL parsing by appending a slash to directories.
       """
    if not url.endswith('/'):
        # Check if the last segment of the URL is not a file
        if '.' not in url.split('/')[-1]:
            url += '/'
    return url


if __name__ == '__main__':
    """
    Main execution block of the script.
    Ensures that the script runs only when executed directly, not when imported as a module.
    """

    # Connect to the MongoDB database.
    # Establishes a connection to the specified database and retrieves the database object.
    db = connectDataBase()

    # Retrieve the 'pages' collection from the database.
    # This collection stores the HTML content and metadata of crawled web pages.
    pages_collection = db['CrawledPages']

    # Retrieve the 'FacultyInfo' collection from the database.
    # This collection is used to store structured data about faculty members extracted from web pages.
    faculty_collection = db['FacultyInfo']

    # Process and extract data from faculty pages marked as targets.
    # The extracted data is structured and saved into the 'FacultyInfo' collection.
    handle_faculty_pages(pages_collection, faculty_collection)

    # Print a message indicating that the parsing process is complete.
    # This message confirms that all target pages have been processed successfully.
    print("Parsing of Faculty Pages completed!")
