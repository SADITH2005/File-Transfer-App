from flask import Flask, request, redirect, url_for, send_from_directory, render_template_string
import os
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta
import threading
import qrcode
import socket
import time

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp3', 'mp4', 'pdf', 'docx', 'txt'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Function to get file icon based on extension
def get_file_icon(filename):
    extension = filename.split('.')[-1].lower() if '.' in filename else ''
    if extension in ['jpg', 'jpeg', 'png', 'gif']:
        return 'fa-image'
    elif extension in ['mp3', 'wav']:
        return 'fa-music'
    elif extension in ['mp4', 'avi', 'mov']:
        return 'fa-video'
    elif extension in ['pdf']:
        return 'fa-file-pdf'
    elif extension in ['docx', 'doc', 'txt']:
        return 'fa-file-alt'
    else:
        return 'fa-file'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def cleanup_old_files():
    while True:
        now = datetime.now()
        for filename in os.listdir(UPLOAD_FOLDER):
            path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.isfile(path):
                created_time = datetime.fromtimestamp(os.path.getmtime(path))
                if now - created_time > timedelta(hours=1):
                    os.remove(path)
        time.sleep(600)  # Every 10 minutes

@app.route('/')
def index():
    files = os.listdir(app.config['UPLOAD_FOLDER'])
    files.sort(key=lambda x: os.path.getmtime(os.path.join(app.config['UPLOAD_FOLDER'], x)), reverse=True)
    file_count = len(files)
    
    # Generate file list HTML
    if file_count == 0:
        file_list_html = '''
        <div class="empty-state">
            <div class="empty-icon"><i class="fas fa-folder-open"></i></div>
            <p>No files uploaded yet. Upload your first file!</p>
        </div>
        '''
    else:
        file_items = []
        for file in files:
            icon_class = get_file_icon(file)
            display_name = file[15:] if len(file) > 15 and file[14] == '_' else file
            file_items.append(f'''
            <div class="file-item">
                <div class="file-info">
                    <div class="file-icon"><i class="fas {icon_class}"></i></div>
                    <div class="file-name">{display_name}</div>
                </div>
                <div class="file-actions">
                    <a href="/download/{file}" class="action-btn download-btn" title="Download">
                        <i class="fas fa-download"></i>
                    </a>
                    <a href="/delete/{file}" class="action-btn delete-btn" title="Delete" onclick="return confirm('Are you sure you want to delete this file?')">
                        <i class="fas fa-trash-alt"></i>
                    </a>
                </div>
            </div>
            ''')
        file_list_html = ''.join(file_items)

    # Entire HTML template with placeholders already filled
    html = f'''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fast File Transfer</title>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #f6f9fc, #eef2f7);
            color: #212529;
            line-height: 1.6;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }}
        
        .container {{
            width: 90%;
            max-width: 800px;
            margin: 2rem auto;
            flex: 1;
        }}
        
        header {{
            text-align: center;
            margin-bottom: 2rem;
            animation: fadeIn 0.8s ease;
        }}
        
        h1 {{
            font-size: 2.2rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            color: #4361ee;
        }}
        
        .subtitle {{
            font-size: 1rem;
            color: #6c757d;
            margin-bottom: 1.5rem;
        }}
        
        .card {{
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            padding: 2rem;
            margin-bottom: 2rem;
            animation: slideUp 0.5s ease;
        }}
        
        .upload-form {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 1.5rem;
            margin-bottom: 1.5rem;
        }}
        
        .file-input-container {{
            position: relative;
            width: 100%;
        }}
        
        .file-input {{
            width: 100%;
            padding: 0.8rem;
            border: 2px dashed #ced4da;
            border-radius: 12px;
            background: #f8f9fa;
            cursor: pointer;
            transition: all 0.3s ease;
            text-align: center;
        }}
        
        .file-input:hover {{
            border-color: #4361ee;
            background: #f0f4f8;
        }}
        
        .upload-btn {{
            display: inline-block;
            background: #4361ee;
            color: white;
            border: none;
            padding: 0.8rem 2rem;
            border-radius: 12px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .upload-btn:hover {{
            background: #3f37c9;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(67, 97, 238, 0.3);
        }}
        
        .files-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid #e9ecef;
        }}
        
        .files-title {{
            font-size: 1.25rem;
            font-weight: 600;
            color: #212529;
        }}
        
        .file-count {{
            background: #4361ee;
            color: white;
            padding: 0.2rem 0.5rem;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
        }}
        
        .file-list {{
            display: flex;
            flex-direction: column;
            gap: 0.8rem;
        }}
        
        .file-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 12px;
            transition: all 0.3s ease;
            border-left: 4px solid #4361ee;
        }}
        
        .file-item:hover {{
            background: white;
            box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);
            transform: translateX(4px);
        }}
        
        .file-info {{
            display: flex;
            align-items: center;
            gap: 0.8rem;
        }}
        
        .file-icon {{
            font-size: 1.5rem;
            color: #4361ee;
        }}
        
        .file-name {{
            font-weight: 500;
            word-break: break-all;
        }}
        
        .file-actions {{
            display: flex;
            gap: 0.5rem;
        }}
        
        .action-btn {{
            display: flex;
            align-items: center;
            justify-content: center;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            border: none;
            cursor: pointer;
            transition: all 0.3s ease;
            text-decoration: none;
        }}
        
        .download-btn {{
            background: #4cc9f0;
            color: white;
        }}
        
        .download-btn:hover {{
            background: #3da5f5;
            transform: translateY(-2px);
        }}
        
        .delete-btn {{
            background: #f72585;
            color: white;
        }}
        
        .delete-btn:hover {{
            background: #e5174d;
            transform: translateY(-2px);
        }}
        
        .empty-state {{
            text-align: center;
            padding: 2rem;
            color: #6c757d;
        }}
        
        .empty-icon {{
            font-size: 3rem;
            margin-bottom: 1rem;
            color: #ced4da;
        }}
        
        footer {{
            text-align: center;
            padding: 1.5rem;
            margin-top: auto;
            background: white;
            box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
        }}
        
        .footer-text {{
            color: #6c757d;
            font-size: 0.9rem;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}
        
        @keyframes slideUp {{
            from {{ transform: translateY(20px); opacity: 0; }}
            to {{ transform: translateY(0); opacity: 1; }}
        }}
        
        @media (max-width: 768px) {{
            .container {{
                width: 95%;
                margin: 1rem auto;
            }}
            
            .card {{
                padding: 1.5rem;
            }}
            
            h1 {{
                font-size: 1.8rem;
            }}
            
            .file-item {{
                flex-direction: column;
                align-items: flex-start;
                gap: 0.8rem;
            }}
            
            .file-actions {{
                align-self: flex-end;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Fast File Transfer</h1>
            <p class="subtitle">Easily transfer files between your devices</p>
        </header>
        
        <div class="card">
            <form class="upload-form" action="/upload" method="post" enctype="multipart/form-data">
                <div class="file-input-container">
                    <input type="file" name="file" id="file" class="file-input" required>
                </div>
                <button type="submit" class="upload-btn">
                    <i class="fas fa-cloud-upload-alt"></i> Upload File
                </button>
            </form>
        </div>
        
        <div class="card">
            <div class="files-header">
                <div class="files-title">Recent Files</div>
                <div class="file-count">{file_count}</div>
            </div>
            
            <div class="file-list">
                {file_list_html}
            </div>
        </div>
    </div>
    
    <footer>
        <p class="footer-text">Developed by Sadith Rashmika</p>
    </footer>
</body>
</html>
    '''
    
    return html

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return 'No file part', 400
    file = request.files['file']
    if file.filename == '':
        return 'No selected file', 400
    if file and allowed_file(file.filename):
        filename = secure_filename(datetime.now().strftime("%Y%m%d_%H%M%S_") + file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        return redirect(url_for('index'))
    return 'File type not allowed', 400

@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/delete/<filename>')
def delete_file(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    return redirect(url_for('index'))

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    finally:
        s.close()

if __name__ == '__main__':
    threading.Thread(target=cleanup_old_files, daemon=True).start()

    ip = get_local_ip()
    url = f"http://{ip}:5000"
    qr = qrcode.make(url)
    qr.save("qr_code.png")
    print(f"🚀 Fast File Transfer running at: {url}")
    print(f"📱 Scan the QR code (qr_code.png) with your device camera to connect")
    app.run(debug=True, host='0.0.0.0', port=5000)