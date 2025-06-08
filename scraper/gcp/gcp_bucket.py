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

def upload_image_mapping_to_gcs(mapping_dict, bucket_name="web-scrape-ai", destination_blob_name="image_mapping1.json", project_id="voii-459718"):
    """Upload image mapping dictionary as JSON to GCP bucket."""
    try:
        from google.cloud import storage
        storage_client = storage.Client(project=project_id)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(destination_blob_name)
        
        # Convert dictionary to JSON string
        mapping_json = json.dumps(mapping_dict, indent=2)
        
        # Upload as JSON content
        blob.upload_from_string(mapping_json, content_type="application/json; charset=utf-8")
        print(f"Uploaded image mapping with {len(mapping_dict)} entries to {bucket_name}/{destination_blob_name}")
     
    except Exception as e:
        print(f"Error uploading image mapping to GCP: {str(e)}")
     