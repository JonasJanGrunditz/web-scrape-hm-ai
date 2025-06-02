from google.cloud import storage

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