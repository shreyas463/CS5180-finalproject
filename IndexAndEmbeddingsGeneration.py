import pickle
from pymongo import MongoClient
from sklearn.feature_extraction.text import TfidfVectorizer
from collections import defaultdict

# MongoDB connection setup
client = MongoClient('mongodb://localhost:27017/')
db = client['CPP_Biology']
faculty_collection = db['FacultyInfo']
inverted_index_collection = db['InvertedIndex']
embeddings_collection = db['Embeddings']

# File path for saving the trained TF-IDF vectorizer
TFIDF_PKL_FILE = "tfidf_vectorizer.pkl"


def generate_index_and_store_embeddings():
    """
    Generates and stores an inverted index and TF-IDF embeddings in MongoDB.
    """
    documents, doc_ids = fetch_documents()
    vectorizer, tfidf_matrix, terms = create_tfidf_matrix(documents)
    save_vectorizer(vectorizer)
    inverted_index = build_inverted_index(tfidf_matrix, terms, doc_ids)
    store_inverted_index(inverted_index)
    store_document_embeddings(tfidf_matrix, doc_ids)


def fetch_documents():
    """
    Fetches documents and their IDs from the MongoDB collection.
    Returns:
        documents (list): List of document texts.
        doc_ids (list): List of document IDs.
    """
    documents = []
    doc_ids = []
    # Adjust to use the `faculty_info` field
    for doc in faculty_collection.find({}, {"faculty_info": 1, "_id": 1}):
        text = doc.get('faculty_info')  # Use the `faculty_info` field for text
        if text:  # Skip documents with missing or empty `faculty_info`
            documents.append(text)
            doc_ids.append(str(doc['_id']))
    return documents, doc_ids


def create_tfidf_matrix(documents):
    """
    Creates a TF-IDF matrix for the documents.
    Args:
        documents (list): List of document texts.
    Returns:
        vectorizer (TfidfVectorizer): Fitted TF-IDF vectorizer.
        tfidf_matrix (sparse matrix): TF-IDF matrix for the documents.
        terms (list): List of terms from the TF-IDF model.
    """
    vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 3))
    tfidf_matrix = vectorizer.fit_transform(documents)
    terms = vectorizer.get_feature_names_out()
    return vectorizer, tfidf_matrix, terms


def save_vectorizer(vectorizer):
    """
    Saves the TF-IDF vectorizer to a file for reuse.
    Args:
        vectorizer (TfidfVectorizer): Fitted TF-IDF vectorizer.
    """
    print("Saving vectorizer...")
    with open(TFIDF_PKL_FILE, 'wb') as f:
        pickle.dump(vectorizer, f)
    print(f"Vectorizer saved to {TFIDF_PKL_FILE}.")


def build_inverted_index(tfidf_matrix, terms, doc_ids):
    """
    Builds an inverted index from the TF-IDF matrix.
    Args:
        tfidf_matrix (sparse matrix): TF-IDF matrix for the documents.
        terms (list): List of terms from the TF-IDF model.
        doc_ids (list): List of document IDs.
    Returns:
        inverted_index (defaultdict): Inverted index mapping terms to documents and scores.
    """
    inverted_index = defaultdict(list)
    for term_idx, term in enumerate(terms):
        for doc_idx in range(tfidf_matrix.shape[0]):
            score = tfidf_matrix[doc_idx, term_idx]
            if score > 0:
                inverted_index[term].append(
                    {"document_id": doc_ids[doc_idx], "tfidf_score": score}
                )
    return inverted_index


def store_inverted_index(inverted_index):
    """
    Stores the inverted index in MongoDB.
    Args:
        inverted_index (defaultdict): Inverted index mapping terms to documents and scores.
    """
    inverted_index_collection.delete_many({})
    for term, docs in inverted_index.items():
        inverted_index_collection.insert_one({"term": term, "documents": docs})
    print("Inverted index has been stored in MongoDB.")


def store_document_embeddings(tfidf_matrix, doc_ids):
    """
    Stores document embeddings (TF-IDF vectors) in MongoDB.
    Args:
        tfidf_matrix (sparse matrix): TF-IDF matrix for the documents.
        doc_ids (list): List of document IDs.
    """
    document_vectors = tfidf_matrix.toarray()
    embeddings_collection.delete_many({})
    for doc_idx, doc_id in enumerate(doc_ids):
        embeddings_collection.insert_one({
            "document_id": doc_id,
            "tfidf": document_vectors[doc_idx].tolist()
        })
    print("Document TF-IDF embeddings have been stored in MongoDB.")


def main():
    """
    The main function that orchestrates the execution of the script.
    It calls the `generate_index_and_store_embeddings` function
    to create an inverted index and store TF-IDF embeddings in MongoDB.
    """
    generate_index_and_store_embeddings()


if __name__ == "__main__":
    """
    Entry point of the script.
    Ensures that the `main` function is executed only when the script is run directly,
    and not when it is imported as a module in another script.
    """
    main()
