
from flask import Flask, render_template, request, jsonify, send_from_directory
import os
from tasks import validate_emails_task

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['RESULTS_FOLDER'] = 'results'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB limit

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    
    if not file.filename.endswith('.txt'):
        return jsonify({'error': 'Only .txt files allowed'}), 400
    
    filename = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filename)
    
    task = validate_emails_task.delay(filename)
    return jsonify({
        'task_id': task.id,
        'filename': file.filename
    })

@app.route('/status/<task_id>')
def task_status(task_id):
    from celery.result import AsyncResult
    task = AsyncResult(task_id)
    
    if task.state == 'FAILURE':
        return jsonify({
            'status': 'failed',
            'error': str(task.result)
        })
    
    return jsonify({
        'status': task.state,
        'progress': task.info.get('percent', 0) if task.info else 0,
        'current': task.info.get('current', 0) if task.info else 0,
        'total': task.info.get('total', 0) if task.info else 0,
    })

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(
        app.config['RESULTS_FOLDER'],
        filename,
        as_attachment=True
    )

if __name__ == '__main__':
    app.run(debug=True)
