#!/usr/bin/env python3
"""
DeepStack Collector Web Interface
A local Flask web server that provides a user-friendly interface for the DeepStack Collector tool.
"""

import os
import json
import subprocess
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import threading
import time

app = Flask(__name__, template_folder='.')
CORS(app)

# Global storage for analysis jobs (in production, use Redis or database)
analysis_jobs = {}

class AnalysisJob:
    def __init__(self, job_id, urls, job_type='single'):
        self.job_id = job_id
        self.urls = urls
        self.job_type = job_type
        self.status = 'pending'  # pending, running, completed, error
        self.progress = 0
        self.result = None
        self.error = None
        self.created_at = datetime.utcnow()
        self.started_at = None
        self.completed_at = None
        
    def to_dict(self):
        return {
            'job_id': self.job_id,
            'urls': self.urls,
            'job_type': self.job_type,
            'status': self.status,
            'progress': self.progress,
            'result': self.result,
            'error': self.error,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

def run_deepstack_analysis(job):
    """Run the deepstack collector in a separate thread"""
    try:
        job.status = 'running'
        job.started_at = datetime.utcnow()
        job.progress = 10
        
        # Ensure we're in the correct directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_dir)
        
        # Activate virtual environment and run the collector
        venv_python = os.path.join(script_dir, 'venv', 'bin', 'python')
        if not os.path.exists(venv_python):
            venv_python = 'python3'  # Fallback if venv not found
        
        collector_script = os.path.join(script_dir, 'src', 'deepstack_collector.py')
        
        if job.job_type == 'single' and len(job.urls) == 1:
            # Single URL mode
            cmd = [venv_python, collector_script, '-u', job.urls[0]]
            job.progress = 50
            
            # Run the command
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                # Find the output file
                parsed_url = urlparse(job.urls[0])
                domain = parsed_url.netloc.replace('www.', '').replace(':', '_')
                output_file = os.path.join(script_dir, 'output', f'deepstack_output-{domain}.json')
                
                if os.path.exists(output_file):
                    with open(output_file, 'r') as f:
                        job.result = json.load(f)
                else:
                    job.error = "Output file not found"
                    job.status = 'error'
                    return
            else:
                job.error = f"Script failed: {result.stderr}"
                job.status = 'error'
                return
        else:
            # Batch mode - create temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp_file:
                for url in job.urls:
                    temp_file.write(url + '\n')
                temp_file_path = temp_file.name
            
            try:
                # Copy temp file to urls_to_analyze.txt
                urls_file = os.path.join(script_dir, 'urls_to_analyze.txt')
                with open(temp_file_path, 'r') as src, open(urls_file, 'w') as dst:
                    dst.write(src.read())
                
                job.progress = 30
                
                # Run in batch mode
                cmd = [venv_python, collector_script]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                
                job.progress = 80
                
                if result.returncode == 0:
                    # Find the output file
                    output_file = os.path.join(script_dir, 'output', 'deepstack_output.json')
                    
                    if os.path.exists(output_file):
                        with open(output_file, 'r') as f:
                            job.result = json.load(f)
                    else:
                        job.error = "Output file not found"
                        job.status = 'error'
                        return
                else:
                    job.error = f"Script failed: {result.stderr}"
                    job.status = 'error'
                    return
            finally:
                # Clean up temporary files
                try:
                    os.unlink(temp_file_path)
                    if os.path.exists(urls_file):
                        os.unlink(urls_file)
                except:
                    pass  # Ignore cleanup errors
        
        job.progress = 100
        job.status = 'completed'
        job.completed_at = datetime.utcnow()
        
    except subprocess.TimeoutExpired:
        job.error = "Analysis timed out"
        job.status = 'error'
    except Exception as e:
        job.error = str(e)
        job.status = 'error'
    finally:
        if job.status != 'completed':
            job.completed_at = datetime.utcnow()

@app.route('/')
def index():
    """Serve the main HTML interface"""
    return send_from_directory('.', 'index.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

@app.route('/api/analyze', methods=['POST'])
def analyze():
    """Start a new analysis job"""
    try:
        data = request.json
        urls = []
        job_type = 'single'
        
        if 'url' in data and data['url']:
            # Single URL
            url = data['url'].strip()
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            urls = [url]
            job_type = 'single'
            
        elif 'urls' in data and data['urls']:
            # Multiple URLs
            url_text = data['urls'].strip()
            urls = [url.strip() for url in url_text.split('\n') if url.strip() and not url.strip().startswith('#')]
            # Add https:// to URLs that don't have a protocol
            urls = [url if url.startswith(('http://', 'https://')) else 'https://' + url for url in urls]
            job_type = 'batch'
            
        elif 'file_content' in data and data['file_content']:
            # File upload content
            file_content = data['file_content'].strip()
            urls = [url.strip() for url in file_content.split('\n') if url.strip() and not url.strip().startswith('#')]
            # Add https:// to URLs that don't have a protocol
            urls = [url if url.startswith(('http://', 'https://')) else 'https://' + url for url in urls]
            job_type = 'batch'
        
        if not urls:
            return jsonify({'error': 'No valid URLs provided'}), 400
        
        # Create new job
        job_id = str(uuid.uuid4())
        job = AnalysisJob(job_id, urls, job_type)
        analysis_jobs[job_id] = job
        
        # Start analysis in background thread
        thread = threading.Thread(target=run_deepstack_analysis, args=(job,))
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'job_id': job_id,
            'status': 'started',
            'urls_count': len(urls),
            'job_type': job_type
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/status/<job_id>')
def get_status(job_id):
    """Get the status of an analysis job"""
    if job_id not in analysis_jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = analysis_jobs[job_id]
    return jsonify(job.to_dict())

@app.route('/api/result/<job_id>')
def get_result(job_id):
    """Get the result of a completed analysis job"""
    if job_id not in analysis_jobs:
        return jsonify({'error': 'Job not found'}), 404
    
    job = analysis_jobs[job_id]
    
    if job.status != 'completed':
        return jsonify({'error': 'Job not completed yet'}), 400
    
    if not job.result:
        return jsonify({'error': 'No result available'}), 404
    
    return jsonify(job.result)

@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()})

if __name__ == '__main__':
    # Ensure output directory exists
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)
    
    print("🚀 Starting DeepStack Collector Web Interface...")
    print("📊 Open your browser to: http://localhost:5000")
    print("⚠️  Make sure you've activated the virtual environment and installed requirements!")
    print("💡 To stop the server, press Ctrl+C")
    
    # Run Flask app
    app.run(host='127.0.0.1', port=5000, debug=True, threaded=True)