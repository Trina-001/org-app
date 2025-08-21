# app/main.py
import os
import threading
from flask import Flask, render_template, request, jsonify
from pathlib import Path
import subprocess
import sys

app = Flask(__name__)

# Add current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Global variables to track process status
process_status = {
    "organize": {"running": False, "message": "Ready", "output": ""},
    "transfer": {"running": False, "message": "Ready", "output": ""}
}

def run_organize(folder_path):
    """Run the organize process in a separate thread"""
    try:
        process_status["organize"]["running"] = True
        process_status["organize"]["message"] = "Organizing files..."
        
        # Import and run merge.py
        import merge
        result = merge.main_web(folder_path)
        
        if result == 0:
            process_status["organize"]["message"] = "Organization completed successfully!"
        else:
            process_status["organize"]["message"] = "Organization completed with errors!"
            
    except Exception as e:
        process_status["organize"]["message"] = f"Error during organization: {str(e)}"
    finally:
        process_status["organize"]["running"] = False

def run_transfer(folder_path):
    """Run the transfer process in a separate thread"""
    try:
        process_status["transfer"]["running"] = True
        process_status["transfer"]["message"] = "Transferring files..."
        
        # Import and run transfer.py
        import transfer
        result = transfer.organize_webp_folders(folder_path)
        
        if result:
            process_status["transfer"]["message"] = "Transfer completed successfully!"
        else:
            process_status["transfer"]["message"] = "Transfer completed with errors!"
            
    except Exception as e:
        process_status["transfer"]["message"] = f"Error during transfer: {str(e)}"
    finally:
        process_status["transfer"]["running"] = False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/organize', methods=['POST'])
def organize():
    if process_status["organize"]["running"]:
        return jsonify({"status": "error", "message": "Organization already in progress"})
    
    folder_path = request.form.get('folder_path')
    if not folder_path or not os.path.exists(folder_path):
        return jsonify({"status": "error", "message": "Invalid folder path"})
    
    # Start organization in a separate thread
    thread = threading.Thread(target=run_organize, args=(folder_path,))
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "success", "message": "Organization started"})

@app.route('/transfer', methods=['POST'])
def transfer():
    if process_status["transfer"]["running"]:
        return jsonify({"status": "error", "message": "Transfer already in progress"})
    
    folder_path = request.form.get('folder_path')
    if not folder_path or not os.path.exists(folder_path):
        return jsonify({"status": "error", "message": "Invalid folder path"})
    
    # Start transfer in a separate thread
    thread = threading.Thread(target=run_transfer, args=(folder_path,))
    thread.daemon = True
    thread.start()
    
    return jsonify({"status": "success", "message": "Transfer started"})

@app.route('/status')
def status():
    return jsonify(process_status)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)