import os
import requests
from exa_py import Exa

# Initialize Exa client
exa = Exa("a46db4b2-46a6-4c9d-a9e1-dec776d72573")

def download_ielts_pdfs(topic, save_folder="downloaded_pdfs"):
    print(f"🔍 Searching Exa for PDF links related to: {topic}...\n")
    
    # Create the folder if it doesn't exist
    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    # The Declarative Prompt
    query = f"Here is a complete, official PDF practice test and study guide for {topic}:"
    
    try:
        # Notice we are just using 'search' now, not 'search_and_contents'
        response = exa.search(
            query,
            type="neural",
            num_results=10 # Ask for more results since we are just getting links
        )
        
        # Fake a browser User-Agent so websites don't block our download request
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        download_count = 0

        for result in response.results:
            url = result.url
            
            # Check if it's a PDF link
            if url.lower().endswith(".pdf"):
                print(f"✅ Found PDF Link: {url}")
                
                try:
                    # Clean up the filename so it's safe to save
                    filename = url.split("/")[-1].split("?")[0]
                    if not filename.endswith(".pdf"):
                        filename = f"document_{download_count}.pdf"
                        
                    filepath = os.path.join(save_folder, filename)
                    
                    print(f"⏳ Downloading to {filepath}...")
                    
                    # Stream the download so we don't crash if the PDF is huge
                    pdf_response = requests.get(url, headers=headers, stream=True, timeout=15)
                    pdf_response.raise_for_status() # Check for HTTP errors
                    
                    with open(filepath, 'wb') as f:
                        for chunk in pdf_response.iter_content(chunk_size=8192):
                            f.write(chunk)
                            
                    print("🎉 Download complete!\n")
                    download_count += 1
                    
                except Exception as e:
                    print(f"❌ Failed to download {url}. Error: {e}\n")
            else:
                print(f"⏭️ Skipped non-PDF: {url}")

        print(f"--- Finished! Successfully downloaded {download_count} PDFs. ---")

    except Exception as e:
        print(f"An error occurred with Exa: {e}")

# --- Run the Script ---
if __name__ == "__main__":
    target_topic = "Derivative tests with answers"
    download_ielts_pdfs(target_topic)