import re
import string
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer, PorterStemmer
from nltk.tokenize import word_tokenize

lemmatizer = WordNetLemmatizer()
stemmer = PorterStemmer()

protected_negation_words = {"no", "not", "nor", "never"}

try:
    stop_words = set(stopwords.words("english")) - protected_negation_words
except LookupError:
    stop_words = {"the", "is", "and", "a", "an", "of", "to", "in", "for", "with", "on"}

def safe_word_tokenize(text):
    try:
        return word_tokenize(text)
    except LookupError:
        return re.findall(r"\b\w+\b", text)

def safe_lemmatize(token):
    token = token.lower()
    try:
        # Try verb first, then noun
        lemma = lemmatizer.lemmatize(token, pos="v")
        if lemma == token:
            lemma = lemmatizer.lemmatize(token, pos="n")
        return lemma
    except LookupError:
        # Fallback to standard Porter Stemmer instead of raw string slicing
        return stemmer.stem(token)

def preprocess_text(text):
    text = text.lower()
    # Remove URLs
    text = re.sub(r"http\S+|www\.\S+", "", text)
    
    # Replace punctuation with spaces to avoid merging concatenated words
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r"\s+", " ", text).strip()

    tokens = safe_word_tokenize(text)
    
    # Filter stopwords while retaining protected negations
    tokens = [
        token for token in tokens 
        if token not in stop_words or token in protected_negation_words
    ]
    
    tokens = [safe_lemmatize(token) for token in tokens]
    return " ".join(tokens)
