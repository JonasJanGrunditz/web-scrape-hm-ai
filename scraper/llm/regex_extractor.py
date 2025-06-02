import re

def extract_hm_product_info(markdown_content: str) -> dict:
    """
    Extracts specific product information from H&M product page markdown using regex patterns.
    
    Args:
        markdown_content (str): The markdown content from H&M product page
        
    Returns:
        dict: Extracted product information containing sizes, description, material, and price
    """
    
    # Extract price (format: "XXX,XX kr.")
    price_pattern = r'(\d+,\d{2}\s*kr\.?)'
    price_match = re.search(price_pattern, markdown_content)
    price = price_match.group(1) if price_match else None
    
    # Extract sizes section (from "Välj storlek" to "Storleksguide")
    sizes_pattern = r'Välj storlek\s*(.*?)\s*Storleksguide'
    sizes_match = re.search(sizes_pattern, markdown_content, re.DOTALL)
    sizes_section = sizes_match.group(1).strip() if sizes_match else None
    
    # Clean up the sizes section to get individual sizes
    sizes = []
    if sizes_section:
        # Split by lines and filter out empty lines
        size_lines = [line.strip() for line in sizes_section.split('\n') if line.strip()]
        sizes = size_lines
    
    # Extract description section (from "Beskrivning" to "Material")
    description_pattern = r'Beskrivning\s*(.*?)\s*Material'
    description_match = re.search(description_pattern, markdown_content, re.DOTALL)
    description = description_match.group(1).strip() if description_match else None
    
    # Extract material section (from "Material" to next major section or end)
    # Look for "Material" followed by content until we hit another section
    material_pattern = r'Material\s*(.*?)(?=\n[A-ZÅÄÖ][a-zåäö\s]+(?:\n|$)|$)'
    material_match = re.search(material_pattern, markdown_content, re.DOTALL)
    material = material_match.group(1).strip() if material_match else None
    
    # If the above doesn't work, try a simpler approach for material
    if not material:
        material_pattern_simple = r'Material\s*(.*?)(?=Leverans|Skötselråd|HM\.com|$)'
        material_match_simple = re.search(material_pattern_simple, markdown_content, re.DOTALL)
        material = material_match_simple.group(1).strip() if material_match_simple else None
    
    return {
        'price': price,
        'sizes': sizes,
        'description': description,
        'material': material
    }

def extract_hm_product_info_formatted(markdown_content: str) -> str:
    """
    Extracts and formats product information from H&M product page markdown.
    Returns a formatted string similar to your example.
    
    Args:
        markdown_content (str): The markdown content from H&M product page
        
    Returns:
        str: Formatted product information
    """
    
    # Extract price
    price_pattern = r'(\d+,\d{2}\s*kr\.?)'
    price_match = re.search(price_pattern, markdown_content)
    price = price_match.group(1) if price_match else "Price not found"
    
    # Extract the section from "Välj storlek" to just before "Beskrivning"
    sizes_section_pattern = r'(Välj storlek.*?)(?=Beskrivning)'
    sizes_match = re.search(sizes_section_pattern, markdown_content, re.DOTALL)
    sizes_section = sizes_match.group(1) if sizes_match else ""
    
    # Extract description section from "Beskrivning" to "Material"
    description_pattern = r'(Beskrivning.*?)(?=Material\s*\n)'
    description_match = re.search(description_pattern, markdown_content, re.DOTALL)
    description_section = description_match.group(1) if description_match else ""
    
    # Extract material section - look for "Material" followed by content
    material_pattern = r'(Material\s*\n.*?Komposition\s*\n.*?\d+%.*?)(?=\nYtterligare materialinformation|\nVikten|\nFörklaring|\nSkötselråd|$)'
    material_match = re.search(material_pattern, markdown_content, re.DOTALL)
    material_section = material_match.group(1) if material_match else ""
    
    # Combine all sections
    result = f"{sizes_section}\n{description_section}\n{material_section}".strip()
    
    # Add price at the end
    if price:
        result += f"\nand the price {price}"
    
    return result

def extract_specific_hm_sections(markdown_content: str) -> str:
    """
    Extracts the exact sections you specified from H&M markdown content.
    This function extracts from "Välj storlek" through the Material composition.
    Handles both "Beskrivning" and "Beskrivning och passform" formats.
    """
    
    # Find the start of "Välj storlek" section
    start_pattern = r'Välj storlek'
    start_match = re.search(start_pattern, markdown_content)
    
    if not start_match:
        return "Could not find 'Välj storlek' section"
    
    # Extract content from "Välj storlek" onwards
    content_from_start = markdown_content[start_match.start():]
    
    # Find the end point - we want to stop after Material composition but before "Ytterligare materialinformation"
    # Try multiple patterns to handle different product formats
    end_patterns = [
        # Pattern 1: Stop right before "Ytterligare materialinformation" 
        r'(.*?Komposition.*?)(?=\s*###?\s*Ytterligare materialinformation)',
        # Pattern 2: Stop at "Ytterligare materialinformation" (no ###)
        r'(.*?Komposition.*?)(?=\s*Ytterligare materialinformation)',
        # Pattern 3: Get material composition and stop at next major section
        r'(.*?Komposition.*?(?:\n\s*[\*\-].*?)*?)(?=\s*###?\s*[A-ZÅÄÖ])',
        # Pattern 4: Fallback - stop at any major section after Material
        r'(.*?Material.*?Komposition.*?)(?=\s*###?\s*[A-ZÅÄÖ])',
    ]
    
    extracted_content = None
    
    for pattern in end_patterns:
        match = re.search(pattern, content_from_start, re.DOTALL)
        if match:
            extracted_content = match.group(1)
            break
    
    # If no pattern worked, try a simpler approach
    if not extracted_content:
        # Find Material section and extract a reasonable amount after it
        material_match = re.search(r'Material', content_from_start)
        if material_match:
            # Look for composition section and include it
            composition_match = re.search(r'Komposition.*?(?:\n\s*[\*\-].*?)*', content_from_start[material_match.start():], re.DOTALL)
            if composition_match:
                extracted_content = content_from_start[:material_match.start() + composition_match.end()]
            else:
                extracted_content = content_from_start[:material_match.start() + 200]  # Fallback
        else:
            extracted_content = content_from_start
    
    # Clean up the content - remove unwanted sections
    if extracted_content:
        # Remove sections we don't want (but keep sizes, description, and material)
        unwanted_sections = [
            r'Hitta i butik.*?(?=Beskrivning|Material|$)',
            r'Kolla tillgänglighet.*?(?=Beskrivning|Material|$)',
            r'###?\s*Hitta i butik.*?(?=###?|Beskrivning|Material|$)',
            r'###?\s*Kolla tillgänglighet.*?(?=###?|Beskrivning|Material|$)',
            r'###?\s*Recensioner.*?(?=###?|Beskrivning|Material|$)',
            r'###?\s*Upplevd storlek.*?(?=###?|Beskrivning|Material|$)',
            r'###?\s*Längd.*?(?=###?|Beskrivning|Material|$)',
        ]
        
        for unwanted_pattern in unwanted_sections:
            extracted_content = re.sub(unwanted_pattern, '', extracted_content, flags=re.DOTALL)
    
    # Clean up the extracted content
    if extracted_content:
        extracted_content = extracted_content.strip()
        
        # Remove extra whitespace and clean up formatting
        lines = extracted_content.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line and line not in ['###', '##']:  # Only keep non-empty lines and filter out standalone headers
                cleaned_lines.append(line)
        
        extracted_content = '\n'.join(cleaned_lines)
    
    # Extract price separately
    price_pattern = r'(\d+,\d{2}\s*kr\.?)'
    price_match = re.search(price_pattern, markdown_content)
    price = price_match.group(1) if price_match else None
    
    # Add price to the result
    if price and extracted_content:
        extracted_content += f"\nand the price {price}"
    
    return extracted_content or "Could not extract content"