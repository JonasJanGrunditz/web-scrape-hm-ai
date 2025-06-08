from google.cloud import storage
import json
import threading
from google.api_core import exceptions

# Thread lock for concurrent access to GCS
_gcs_lock = threading.Lock()

def upload_urls_to_gcs(urls, bucket_name="web-scrape-ai", destination_blob_name="garments/urls.txt", project_id="voii-459718"):
    """Upload a list of URLs to a GCP bucket, appending to existing content."""
    if not urls:
        return
    
    with _gcs_lock:  # Ensure thread-safe access
        storage_client = storage.Client(project=project_id)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        
        try:
            # Try to download existing content
            existing_content = blob.download_as_text()
            existing_urls = set(existing_content.strip().split('\n')) if existing_content.strip() else set()
        except exceptions.NotFound:
            # File doesn't exist yet
            existing_urls = set()
        
        # Add new URLs to existing ones (avoiding duplicates)
        new_urls = set(urls)
        all_urls = existing_urls.union(new_urls)
        
        # Remove empty strings
        all_urls = {url for url in all_urls if url.strip()}
        
        # Upload the combined content
        content = "\n".join(sorted(all_urls))
        blob.upload_from_string(content, content_type="text/plain; charset=utf-8")
        
        print(f"Added {len(new_urls)} new URLs to {bucket_name}/{destination_blob_name}. Total URLs: {len(all_urls)}")





def download_urls_from_gcs(bucket_name="web-scrape-ai", destination_blob_name="garments/urls.txt", project_id="voii-459718"):
    """Download URLs from a GCP bucket."""
    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    content = blob.download_as_text()
    urls = content.splitlines()
    print(f"Downloaded {len(urls)} URLs from {bucket_name}/{destination_blob_name}")
    return urls


def download_processed_garments_from_gcs(bucket_name="web-scrape-ai", destination_blob_name="garments-info/products-info_test.txt", project_id="voii-459718"):
    """Download processed garment data from a GCP bucket."""
    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    content = blob.download_as_text()
    garments = content.splitlines()
    print(f"Downloaded {len(garments)} processed garment items from {bucket_name}/{destination_blob_name}")
    return garments

def download_image_mapping_from_gcs(bucket_name="web-scrape-ai", destination_blob_name="image_mapping1.json", project_id="voii-459718"):
    """Download image mapping dictionary from GCP bucket."""
    try:
        storage_client = storage.Client(project=project_id)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        
        # Download and parse JSON content
        mapping_json = blob.download_as_text()
        mapping_dict = json.loads(mapping_json)
        print(f"Downloaded image mapping with {len(mapping_dict)} entries from {bucket_name}/{destination_blob_name}")
        return mapping_dict
        
    except exceptions.NotFound:
        print(f"Image mapping file not found in {bucket_name}/{destination_blob_name}. Starting with empty mapping.")
        return {}
    except Exception as e:
        print(f"Error downloading image mapping from GCP: {str(e)}")
        return {}

def upload_image_mapping_to_gcs(mapping_dict, bucket_name="web-scrape-ai", destination_blob_name="image_mapping1.json", project_id="voii-459718"):
    """Upload image mapping dictionary as JSON to GCP bucket, merging with existing mappings."""
    if not mapping_dict:
        return True  # Return True for empty mapping (no error)
    
    with _gcs_lock:  # Ensure thread-safe access
        try:
            storage_client = storage.Client(project=project_id)
            bucket = storage_client.bucket(bucket_name)
            blob = bucket.blob(destination_blob_name)
            
            # Download existing mapping
            try:
                existing_mapping_json = blob.download_as_text()
                existing_mapping = json.loads(existing_mapping_json)
            except exceptions.NotFound:
                # File doesn't exist yet
                existing_mapping = {}
            except json.JSONDecodeError:
                print("Warning: Existing mapping file is corrupted. Starting fresh.")
                existing_mapping = {}
            
            # Merge existing and new mappings (new mappings override existing ones for same keys)
            combined_mapping = existing_mapping.copy()
            combined_mapping.update(mapping_dict)
            
            # Convert combined dictionary to JSON string
            mapping_json = json.dumps(combined_mapping, indent=2)
            
            # Upload as JSON content
            blob.upload_from_string(mapping_json, content_type="application/json; charset=utf-8")
            
            new_entries = len(mapping_dict)
            total_entries = len(combined_mapping)
            print(f"Added {new_entries} new image mapping entries to {bucket_name}/{destination_blob_name}. Total entries: {total_entries}")
            return True
         
        except Exception as e:
            print(f"Error uploading image mapping to GCP: {str(e)}")
            return False

def upload_processed_garments_to_gcs(garments, bucket_name="web-scrape-ai", destination_blob_name="garments-info/products-info_test.txt", project_id="voii-459718"):
    """Upload processed garment data to a GCP bucket, appending to existing content."""
    if not garments:
        return
    
    with _gcs_lock:  # Ensure thread-safe access
        storage_client = storage.Client(project=project_id)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        
        try:
            # Try to download existing content
            existing_content = blob.download_as_text()
            existing_garments = existing_content.strip().split('\n') if existing_content.strip() else []
        except exceptions.NotFound:
            # File doesn't exist yet
            existing_garments = []
        
        # Combine existing and new garments
        all_garments = existing_garments + [str(garment) for garment in garments if garment is not None]
        
        # Upload the combined content
        content = "\n".join(all_garments)
        blob.upload_from_string(content, content_type="text/plain; charset=utf-8")
        
        print(f"Added {len(garments)} new garment entries to {bucket_name}/{destination_blob_name}. Total entries: {len(all_garments)}")
