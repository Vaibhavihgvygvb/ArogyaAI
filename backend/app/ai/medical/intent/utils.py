import re


def extract_keywords(query: str) -> list[str]:
    stop_words = {
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "dare", "ought",
        "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
        "what", "when", "where", "who", "whom", "which", "why", "how",
        "this", "that", "these", "those", "it", "its", "i", "me", "my",
        "we", "our", "you", "your", "he", "him", "his", "she", "her",
        "they", "them", "their", "and", "but", "or", "not", "no", "nor",
    }
    words = re.findall(r'\b[a-zA-Z]{2,}\b', query.lower())
    return [w for w in words if w not in stop_words][:20]
