import html
import re
def extract_urls_from_markdown(text: str) -> list[str]:
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

def extract_product_id(text: str) -> str | None:
    """
    Extract product ID from H&M URLs like:
    https://www2.hm.com/sv_se/productpage.1259175004.html
    Returns the numeric product ID (e.g., '1259175004')
    """
    pattern = r'productpage\.(\d+)\.html'
    match = re.search(pattern, text)
    return match.group(1) if match else None

def between_size_and_material(text: str) -> str | None:
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