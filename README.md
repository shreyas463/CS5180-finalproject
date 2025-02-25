# CPP Biology Faculty Search Engine

## Overview
This project implements a specialized search engine for the Cal Poly Pomona Biology Department's faculty. It crawls faculty web pages, processes the information, and provides a sophisticated search interface to help users find relevant faculty members based on their research interests, expertise, and other attributes.

## Features
- Web crawling of faculty pages with intelligent target identification
- Structured data extraction of faculty profiles
- Advanced text processing with lemmatization
- TF-IDF based search with cosine similarity ranking
- Spell checking for search queries
- Paginated search results with clickable URLs
- MongoDB-based data persistence

## System Architecture
The system consists of five main components:

1. **Web Crawler** (`Crawler.py`)
   - Crawls the Biology department website
   - Identifies and extracts faculty pages
   - Stores raw HTML content in MongoDB

2. **Faculty Parser** (`facultyParser.py`)
   - Extracts structured information from faculty pages
   - Processes main content and navigation sections
   - Stores parsed data in MongoDB

3. **Text Processor** (`Lemmatizer.py`)
   - Implements text normalization using spaCy
   - Preserves important information like phone numbers
   - Enhances search accuracy through lemmatization

4. **Index Generator** (`IndexAndEmbeddingsGeneration.py`)
   - Creates TF-IDF vectors for faculty documents
   - Builds inverted index for efficient searching
   - Generates and stores document embeddings

5. **Search Engine** (`SearchEngine.py`)
   - Provides interactive search interface
   - Implements spell checking and query processing
   - Ranks results using cosine similarity

## Prerequisites
- Python 3.x
- MongoDB
- Required Python packages:
  ```
  beautifulsoup4
  pymongo
  regex
  pyspellchecker
  spacy
  scikit-learn
  numpy
  ```
- spaCy's English language model:
  ```
  python -m spacy download en_core_web_lg
  ```

## Installation

1. Clone the repository:
   ```bash
   git clone [repository-url]
   cd CS5180-finalproject
   ```

2. Install required packages:
   ```bash
   pip install beautifulsoup4 pymongo regex pyspellchecker spacy scikit-learn numpy
   ```

3. Download spaCy's English language model:
   ```bash
   python -m spacy download en_core_web_lg
   ```

4. Ensure MongoDB is running locally on the default port (27017)

## Usage

Run the components in the following order:

1. Start the web crawler:
   ```bash
   python Crawler.py
   ```

2. Parse faculty information:
   ```bash
   python facultyParser.py
   ```

3. Process text with lemmatization:
   ```bash
   python Lemmatizer.py
   ```

4. Generate search indices:
   ```bash
   python IndexAndEmbeddingsGeneration.py
   ```

5. Start the search engine:
   ```bash
   python SearchEngine.py
   ```

## Search Interface Features
- Natural language queries
- Spell check suggestions
- Paginated results (5 results per page)
- Navigation options:
  - Next/Previous page
  - Run new query
  - Quit

## Data Storage
The system uses MongoDB with the following collections:
- `CrawledPages`: Raw HTML content
- `FacultyInfo`: Structured faculty data
- `InvertedIndex`: Search index data
- `Embeddings`: TF-IDF vectors

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## Contributors
- [Your Name]
- [Other Contributors]

## Acknowledgments
- Cal Poly Pomona Biology Department
- CS5180 Information Retrieval Course
