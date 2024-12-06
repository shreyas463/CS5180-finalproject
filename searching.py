import pymongo
import pickle
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
from bson.objectid import ObjectId
import spacy  # For lemmatization
from spellchecker import SpellChecker  # Added for spell checking

# MongoDB connection
client = pymongo.MongoClient()
db = client['CPP3']
faculty_collection = db['faculty_info']
inverted_index_collection = db['inverted_index']
embeddings_collection = db['embeddings']

# File paths
VECTORIZER_FILE = "vectorizer.pkl"

# Load SpaCy model for lemmatization
nlp = spacy.load("en_core_web_lg")

# Initialize the spell checker
spell = SpellChecker()

# Function to lemmatize query


def lemmatize_query(query):
    """
    Lemmatizes the input query using SpaCy.
    """
    doc = nlp(query)
    lemmatized = " ".join(
        [token.lemma_ for token in doc if not token.is_punct and not token.is_stop]
    )
    return lemmatized

# Function to check spelling


def check_spelling(query):
    """
    Checks spelling of the input query and provides suggestions.
    """
    words = query.split()  # Split query into individual words
    misspelled = spell.unknown(words)  # Identify misspelled words
    corrections = {word: spell.correction(
        word) for word in misspelled}  # Suggest corrections
    return corrections

# Perform TF-IDF search


def searchWithTFIDF(query_sentence, vectorizer):
    """
    Performs a TF-IDF-based search for the given query.
    """
    query_vector, query_terms = process_query(query_sentence, vectorizer)
    candidate_docs = collect_candidate_documents(query_terms)
    results = compute_similarity_scores(query_vector, candidate_docs)
    return sorted(results, key=lambda x: x['similarity'], reverse=True)


def process_query(query_sentence, vectorizer):
    """
    Processes the query sentence to create a TF-IDF vector and extract query terms.
    Args:
        query_sentence (str): The input query sentence.
        vectorizer (TfidfVectorizer): The fitted TF-IDF vectorizer.
    Returns:
        query_vector (numpy array): The TF-IDF vector for the query.
        query_terms (list): The list of terms extracted from the query.
    """
    query_vector = vectorizer.transform([query_sentence]).toarray()
    query_terms = vectorizer.inverse_transform(query_vector)[0]
    return query_vector, query_terms


def collect_candidate_documents(query_terms):
    """
    Collects candidate documents and their cumulative TF-IDF scores based on query terms.
    Args:
        query_terms (list): The list of terms extracted from the query.
    Returns:
        candidate_docs (defaultdict): Mapping of document IDs to cumulative scores.
    """
    candidate_docs = defaultdict(float)
    for term in query_terms:
        term_entry = inverted_index_collection.find_one({"term": term})
        if term_entry:
            for doc in term_entry['documents']:
                doc_id = doc['document_id']
                candidate_docs[doc_id] += doc['tfidf_score']
    return candidate_docs


def compute_similarity_scores(query_vector, candidate_docs):
    """
    Computes similarity scores between the query vector and document embeddings.
    Args:
        query_vector (numpy array): The TF-IDF vector for the query.
        candidate_docs (defaultdict): Mapping of document IDs to cumulative scores.
    Returns:
        results (list): List of dictionaries containing document details and similarity scores.
    """
    results = []
    for doc_id, score in candidate_docs.items():
        embedding_entry = embeddings_collection.find_one(
            {"document_id": doc_id})
        if embedding_entry:
            embedding = np.array(embedding_entry["tfidf"])
            similarity = cosine_similarity(
                query_vector, embedding.reshape(1, -1))[0][0]
            results.append(fetch_document_details(doc_id, similarity))
    return results


def fetch_document_details(doc_id, similarity):
    """
    Fetches details for a document from the database.
    Args:
        doc_id (str): The document ID.
        similarity (float): The similarity score for the document.
    Returns:
        dict: A dictionary containing document details and similarity score.
    """
    faculty_details = faculty_collection.find_one({"_id": ObjectId(doc_id)})
    professor_url = faculty_details.get("profile_url", "URL not available")
    summary = faculty_details.get("summary", "Info not available")
    return {
        "document_id": doc_id,
        "similarity": similarity,
        "url": professor_url,
        "summary": summary
    }

# Function to paginate results


def paginate_results(results, page, page_size=5):
    """
    Paginates the search results.
    """
    start_idx = page * page_size
    end_idx = start_idx + page_size
    paginated_results = results[start_idx:end_idx]
    total_pages = (len(results) + page_size - 1) // page_size
    return paginated_results, total_pages

# Main interface


def main_interface():
    """
    Main function for interacting with the search system.
    """
    vectorizer = load_vectorizer()
    if not vectorizer:
        return

    while True:
        choice = display_main_menu()
        if choice == '2':
            print("Thank you for using the Search System. See you soon!")
            break
        elif choice == '1':
            handle_query(vectorizer)
        else:
            print("Invalid choice. Try again.")


def load_vectorizer():
    """
    Loads the vectorizer from the saved file.
    Returns:
        vectorizer (TfidfVectorizer): The loaded TF-IDF vectorizer.
    """
    try:
        with open(VECTORIZER_FILE, 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        print(f"Vectorizer file {VECTORIZER_FILE} not found.")
        return None


def display_main_menu():
    """
    Displays the main menu and gets the user's choice.
    Returns:
        choice (str): The user's menu choice.
    """
    print("\n*****MENU***:")
    print("1. Enter a Query")
    print("2. Exit")
    return input("\nEnter your choice: ").strip()


def handle_query(vectorizer):
    """
    Handles the query process, including spell-checking, lemmatization, and search.
    Args:
        vectorizer (TfidfVectorizer): The loaded TF-IDF vectorizer.
    """
    query = input("\nEnter your query: ").strip().lower()
    if not query:
        print("Query cannot be empty. Please try again.")
        return

    query = process_query_with_spellcheck(query)
    lemmatized_query = lemmatize_query(query)
    results = searchWithTFIDF(lemmatized_query, vectorizer)

    if not results:
        print("\nNo relevant results found for your query.")
        return

    paginate_and_display_results(results)


def process_query_with_spellcheck(query):
    """
    Performs spell-checking on the query and applies corrections if approved by the user.
    Args:
        query (str): The user's input query.
    Returns:
        query (str): The updated query after spell-checking.
    """
    corrections = check_spelling(query)
    if corrections:
        print("\nSpell Check Suggestions:")
        for word, suggestion in corrections.items():
            print(f"Did you mean '{suggestion}'?")
        use_suggestion = input("(y/n): ").strip().lower()
        if use_suggestion == "y":
            for word, suggestion in corrections.items():
                query = query.replace(word, suggestion)
            print(f"Updated Query: {query}")
    return query


def paginate_and_display_results(results):
    """
    Handles the pagination and display of search results.
    Args:
        results (list): The search results.
    """
    page = 0
    page_size = 5
    while True:
        paginated_results, total_pages = paginate_results(
            results, page, page_size)
        display_results_page(paginated_results, page, total_pages)

        action = display_pagination_menu(page, total_pages)
        if action == 'n' and page < total_pages - 1:
            page += 1
        elif action == 'p' and page > 0:
            page -= 1
        elif action == 'r':
            break
        elif action == 'q':
            print("Thank you for using the Search System. See you soon!")
            return
        else:
            print("Invalid choice. Try again.")


def display_results_page(paginated_results, page, total_pages):
    """
    Displays a single page of search results.
    Args:
        paginated_results (list): The results for the current page.
        page (int): The current page number.
        total_pages (int): The total number of pages.
    """
    print(f"\nSearch Results (Page {page + 1} of {total_pages}):")
    print("=" * 80)
    for idx, res in enumerate(paginated_results, start=1):
        print(f"{idx}. Document ID: {res['document_id']}")
        print(f"   Similarity: {res['similarity']:.3f}")
        print(f"   URL: {res['url']}")
        print(f"   Info: {res['summary']}")
        print("-" * 80)


def display_pagination_menu(page, total_pages):
    """
    Displays the pagination menu and gets the user's navigation choice.
    Args:
        page (int): The current page number.
        total_pages (int): The total number of pages.
    Returns:
        action (str): The user's navigation choice.
    """
    print("\nNavigation Options:")
    if page < total_pages - 1:
        print("  [n] Next Page")
    if page > 0:
        print("  [p] Previous Page")
    print("  [r] Run a New Query")
    print("  [q] Quit")
    return input("\nEnter your choice: ").strip().lower()


if __name__ == "__main__":

    """
    Entry point of the script.
    Ensures that the `main_interface` function is executed only when
    the script is run directly and not when imported as a module in another script.
    """
    main_interface()
