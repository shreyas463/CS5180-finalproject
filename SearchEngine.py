import pymongo
import pickle
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from bson.objectid import ObjectId
from collections import defaultdict
import spacy
from spellchecker import SpellChecker

# MongoDB connection
client = pymongo.MongoClient()
db = client['CPP3']
faculty_collection = db['FacultyInfo']
inverted_index_collection = db['InvertedIndex']
embeddings_collection = db['Embeddings']

# File paths
TFIDF_PKL_FILE = "tfidf_vectorizer.pkl"

# Load SpaCy model for lemmatization
nlp = spacy.load("en_core_web_lg")

# Initialize the spell checker
spell = SpellChecker()

# Function to lemmatize query
def lemmatize_query(query):
    doc = nlp(query)
    lemmatized = " ".join(
        [token.lemma_ for token in doc if not token.is_punct and not token.is_stop]
    )
    return lemmatized

# Function to check spelling
def check_spelling(query):
    words = query.split()
    misspelled = spell.unknown(words)
    return {word: spell.correction(word) for word in misspelled}

# Perform TF-IDF search
def searchWithTFIDF(query_sentence, vectorizer):
    query_vector, query_terms = process_query(query_sentence, vectorizer)
    candidate_docs = collect_candidate_documents(query_terms)
    return compute_similarity_scores(query_vector, candidate_docs)

def process_query(query_sentence, vectorizer):
    query_vector = vectorizer.transform([query_sentence]).toarray()
    query_terms = vectorizer.inverse_transform(query_vector)[0]
    return query_vector, query_terms

def collect_candidate_documents(query_terms):
    candidate_docs = defaultdict(float)
    for term in query_terms:
        term_entry = inverted_index_collection.find_one({"term": term})
        if term_entry:
            for doc in term_entry['documents']:
                doc_id = doc['document_id']
                candidate_docs[doc_id] += doc['tfidf_score']
    return candidate_docs

def compute_similarity_scores(query_vector, candidate_docs):
    results = []
    for doc_id, score in candidate_docs.items():
        embedding_entry = embeddings_collection.find_one(
            {"document_id": doc_id})
        if embedding_entry:
            embedding = np.array(embedding_entry["tfidf"])
            similarity = cosine_similarity(
                query_vector, embedding.reshape(1, -1))[0][0]
            results.append(fetch_document_details(doc_id, similarity))
    return sorted(results, key=lambda x: x['similarity'], reverse=True)

def fetch_document_details(doc_id, similarity):
    faculty_details = faculty_collection.find_one({"_id": ObjectId(doc_id)})
    professor_url = faculty_details.get("profile_url", "URL not available")
    summary = faculty_details.get("summary", "Info not available")
    return {
        "document_id": doc_id,
        "similarity": similarity,
        "url": professor_url,
        "summary": summary
    }

# Pagination
def paginate_results(results, page, page_size=5):
    start_idx = page * page_size
    end_idx = start_idx + page_size
    return results[start_idx:end_idx], (len(results) + page_size - 1) // page_size

# console application of the search engine
def search_console():
    vectorizer = load_vectorizer()
    if not vectorizer:
        return

    while True:
        query = input("\nEnter your query or [q] to quit: ").strip()
        if query.lower() == 'q':
            print("Thank you for using the Search System. See you soon!")
            break

        query = process_query_with_spellcheck(query)
        lemmatized_query = lemmatize_query(query)
        results = searchWithTFIDF(lemmatized_query, vectorizer)

        if not results:
            print("\nNo relevant results found for your query.")
            continue

        paginate_and_display_results(results)

def load_vectorizer():
    try:
        with open(TFIDF_PKL_FILE, 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        print(f"Vectorizer file {TFIDF_PKL_FILE} not found.")
        return None

def process_query_with_spellcheck(query):
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
    page = 0
    page_size = 5
    while True:
        paginated_results, total_pages = paginate_results(results, page, page_size)
        display_results_page(paginated_results, page, total_pages)

        action = display_pagination_menu(page, total_pages)
        if action == 'n' and page < total_pages - 1:
            page += 1
        elif action == 'p' and page > 0:
            page -= 1
        elif action == 'r':
            return
        elif action == 'q':
            print("Thank you for using the Search System. See you soon!")
            exit()
        else:
            print("Invalid choice. Try again.")

def display_results_page(paginated_results, page, total_pages):
    print(f"\nSearch Results (Page {page + 1} of {total_pages}):")
    print("=" * 80)
    
    for idx, result in enumerate(paginated_results, start=1):
        name = result.get('name', 'N/A')
        url = result.get('url', 'N/A')
        similarity = result.get('similarity', 0)

        # Format the URL as a clickable link if supported by the terminal
        if url != 'N/A':
            formatted_url = f"\033]8;;{url}\033\\{url}\033]8;;\033\\"
        else:
            formatted_url = url

        print(f"{idx}. Name: {name}")
        print(f"   URL: {formatted_url}")
        print(f"   Similarity: {similarity:.2f}")
        print("-" * 80)

                
def display_pagination_menu(page, total_pages):
    print("\nNavigation Options:")
    if page < total_pages - 1:
        print("  [n] Next Page")
    if page > 0:
        print("  [p] Previous Page")
    print("  [r] Run a New Query")
    print("  [q] Quit")
    return input("\nEnter your choice: ").strip().lower()

if __name__ == "__main__":
    search_console()
