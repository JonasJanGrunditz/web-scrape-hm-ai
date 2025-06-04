from google.cloud import storage
import json
def upload_urls_to_gcs(urls, bucket_name="web-scrape-ai", destination_blob_name="garments/urls.txt", project_id="voii-459718"):
    """Upload a list of URLs to a GCP bucket."""
    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    content = "\n".join(urls)
    blob.upload_from_string(content, content_type="text/plain; charset=utf-8")
    print(f"Uploaded {len(urls)} URLs to {bucket_name}/{destination_blob_name}")





def download_urls_from_gcs(bucket_name="web-scrape-ai", destination_blob_name="garments/urls.txt", project_id="voii-459718"):
    """Download URLs from a GCP bucket."""
    storage_client = storage.Client(project=project_id)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    content = blob.download_as_text()
    urls = content.splitlines()
    print(f"Downloaded {len(urls)} URLs from {bucket_name}/{destination_blob_name}")
    return urls


def download_processed_garments_from_gcs(bucket_name="web-scrape-ai", destination_blob_name="garments-info/products-info.txt", project_id="voii-459718"):
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
     