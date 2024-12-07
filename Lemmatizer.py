import spacy
from pymongo import MongoClient
from bs4 import BeautifulSoup
import re

# Load spaCy model
nlp = spacy.load("en_core_web_lg")

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['CPP_Biology']  
faculty_collection = db['FacultyInfo'] 


def normalize_phone_number(phone_number):
    """
    Normalize phone numbers by removing hyphens, parentheses, and extra spaces.
    """
    # Remove all non-digit characters except for whitespace
    return re.sub(r'[^0-9]', '', phone_number)


def lemmatize_text(fac):
    """
    Lemmatize text using spaCy and clean it, but exclude phone numbers.
    """
    # Allow letters, numbers, whitespace, '@', and '.'; remove other characters
    text = re.sub(r'[^a-zA-Z0-9\s@.]', '', fac)

    # Use regex to find phone numbers (e.g., formats like 123-456-7890 or (123) 456-7890)
    phone_number_pattern = r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    phone_numbers = re.findall(phone_number_pattern, text)

    # Normalize phone numbers to remove formatting
    normalized_phone_numbers = [normalize_phone_number(num) for num in phone_numbers]

    # Remove phone numbers temporarily from the text
    for number in phone_numbers:
        text = text.replace(number, "")

    # Lemmatize the remaining text
    doc = nlp(text)
    lemmatized_text = " ".join(
        [token.lemma_ for token in doc if not token.is_stop])

    # Reinsert the normalized phone numbers at the end of the lemmatized text
    lemmatized_text += " " + " ".join(normalized_phone_numbers)

    return lemmatized_text


def process_faculty_data():
    """
    Fetch data, lemmatize, and update MongoDB.
    """
    for doc in faculty_collection.find():
        raw_text = doc.get("faculty_info", "")
        if raw_text:
            # Perform lemmatization
            lemmatized_text = lemmatize_text(raw_text)

            # Update faculty_info with lemmatized text
            faculty_collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"faculty_info": lemmatized_text, "lem_data": lemmatized_text}}
            )
            print(f"Lemmatized text updated for document ID: {doc['_id']}")
        else:
            print(f"No raw text found for document ID: {doc['_id']}")


if __name__ == "__main__":
    process_faculty_data()
