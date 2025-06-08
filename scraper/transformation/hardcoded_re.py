import html
import re
from typing import List, Optional

def extract_urls_from_markdown(text: str) -> List[str]:
    """
    Extract all H&M image URLs from markdown image syntax like:
    [![Alt text](https://image.hm.com/assets/hm/path/image.jpg)](https://example.com/page.html)
    Returns a list of all found H&M image URLs without query parameters.
    """
    pattern = r'\[!\[.*?\]\((https://image\.hm\.com/assets/[^\)]+)\)\]'
    url = re.findall(pattern, text)[0]
    # Remove query parameters from each URL
    clean_urls = url.split("?")[0] 
   
    return clean_urls

def extract_product_id(text: str) -> Optional[str]:
    """
    Extract product ID from H&M URLs like:
    https://www2.hm.com/sv_se/productpage.1259175004.html
    Returns the numeric product ID (e.g., '1259175004')
    """
    pattern = r'productpage\.(\d+)\.html'
    match = re.search(pattern, text)
    return match.group(1) if match else None

def between_size_and_material(text: str) -> Optional[str]:
    """
    returns everything that sits between the headings
    "Välj storlek"  …  "Ytterligare materialinformation"
    """

    # 1) normalise the text for pattern matching --------------------------
    txt_normalized = html.unescape(text)          # turns &nbsp; → '\xa0' etc.
    txt_normalized = txt_normalized.replace('\xa0', ' ')     # non-breaking space → space
    txt_normalized = txt_normalized.lower()                  # ignore case completely

    # 2) regex: be generous with white-space inside the headings ------------
    pattern = (
        r"välj\s+storlek"               # start
        r"\s*(.*?)\s*"                  # everything in between
        r"(?:ytterligare\s+materialinformation"  # end option 1
        r"|förklaring\s+av\s+materialen"         # end option 2
        r"|skötselråd)"                           # end option 3  ← NEW
    )

    # 3) Find the match in normalized text to get positions
    m = re.search(pattern, txt_normalized, flags=re.DOTALL)
    
    if m:
        # Get the original text preserving formatting
        original_text = html.unescape(text).replace('\xa0', ' ')
        
        # Find the same pattern in original text (case-insensitive)
        original_pattern = (
            r"välj\s+storlek"
            r"\s*(.*?)\s*"
            r"(?:ytterligare\s+materialinformation"
            r"|förklaring\s+av\s+materialen"
            r"|skötselråd)"
        )
        
        original_match = re.search(original_pattern, original_text, flags=re.DOTALL | re.IGNORECASE)
        
        if original_match:
            text = "välj storlek " + original_match.group(1).strip()
        else:
            text = "välj storlek " + m.group(1).strip()
    else:
        text = None
    
    
    return text


def extract_price_info(text):
    """
    Extract price information between 'Inte sparat i favoriter' and '## Färg:' sections.
    
    Returns:
        tuple: (discounted_price, original_price, discount_percentage)
        - If two prices: first is discounted, second is original
        - If one price: it's the original price, discounted_price is None
        - discount_percentage is "no discount" if only one price, otherwise percentage as string
    """
    # Pattern to find content between the two sections
    pattern = r'Inte sparat i favoriter\s*(.*?)\s*(?:##\s*)?Färg:'
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    
    if not match:
        return None, None, "no discount"
    
    content = match.group(1).strip()
    
    # Pattern to extract prices in Swedish format (XXX,XX kr)
    price_pattern = r'(\d+,\d{2})\s*kr'
    prices = re.findall(price_pattern, content)
    
    if len(prices) == 0:
        return None, None, "no discount"
    elif len(prices) == 1:
        # Only one price - it's the original price
        original_price = float(prices[0].replace(',', '.'))
        return None, original_price, "no discount"
    elif len(prices) >= 2:
        # Two or more prices - first is discounted, second is original
        discounted_price = float(prices[0].replace(',', '.'))
        original_price = float(prices[1].replace(',', '.'))
        
        # Calculate discount percentage
        discount_percentage = round(((original_price - discounted_price) / original_price) * 100)
        
        return discounted_price, original_price, f"{discount_percentage}%"
    
    return None, None, "no discount"


def count_most_frequent_word(text):
    """
    Count occurrences of specific words in a string and return the most frequent one.
    
    Args:
        text (str): The input string to analyze
        
    Returns:
        tuple: (most_frequent_word, count) or (None, 0) if no words found
    """
    # Define the words to search for
    target_words = ["DAM", "HERR", "BARN", "HOME", "BEAUTY"]
    
    # Convert text to uppercase for case-insensitive matching
    text_upper = text.upper()
    
    # Count occurrences of each word
    word_counts = {}
    for word in target_words:
        count = text_upper.count(word)
        word_counts[word] = count
    
    # Find the word with maximum count
    if not word_counts or all(count == 0 for count in word_counts.values()):
        return None, 0
    
    most_frequent_word = max(word_counts, key=word_counts.get)
    max_count = word_counts[most_frequent_word]
    
    return most_frequent_word

