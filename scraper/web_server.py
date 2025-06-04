import os
import asyncio
import threading
from flask import Flask, jsonify, request
from main import main as scraper_main

app = Flask(__name__)

# Store the status of scraping operations
scraping_status = {
    "is_running": False,
    "last_run": None,
    "last_result": None,
    "error": None
}

def run_scraper():
    """Run the scraper in a separate thread"""
    global scraping_status
    try:
        scraping_status["is_running"] = True
        scraping_status["error"] = None
        
        # Run the async main function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(scraper_main())
        
        scraping_status["last_result"] = "Scraping completed successfully"
        scraping_status["last_run"] = "success"
        
    except Exception as e:
        scraping_status["error"] = str(e)
        scraping_status["last_result"] = f"Scraping failed: {str(e)}"
        scraping_status["last_run"] = "error"
    finally:
        scraping_status["is_running"] = False

@app.route('/')
def health_check():
    """Health check endpoint for Cloud Run"""
    return jsonify({
        "status": "healthy",
        "service": "HM Scraper",
        "version": "1.0"
    })

@app.route('/scrape', methods=['POST'])
def trigger_scrape():
    """Endpoint to trigger the scraping process"""
    if scraping_status["is_running"]:
        return jsonify({
            "status": "error",
            "message": "Scraping is already in progress"
        }), 409
    
    # Start scraping in a background thread
    thread = threading.Thread(target=run_scraper)
    thread.daemon = True
    thread.start()
    
    return jsonify({
        "status": "started",
        "message": "Scraping process has been initiated"
    })

@app.route('/status')
def get_status():
    """Get the current status of the scraper"""
    return jsonify(scraping_status)

@app.route('/health')
def health():
    """Health endpoint for Cloud Run health checks"""
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    # Get port from environment variable (Cloud Run sets this)
    port = int(os.environ.get('PORT', 8080))
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=port, debug=False)