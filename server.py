from flask import Flask, request, render_template_string, send_file, jsonify
from werkzeug.utils import secure_filename
import os
import fitz  # PyMuPDF
import json
import base64
from pathlib import Path
from deep_translator import GoogleTranslator
import re
import zipfile
from io import BytesIO
import threading
import uuid

app = Flask(__name__)

# Конфигурация
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB максимум
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['ALLOWED_EXTENSIONS'] = {'pdf'}

# Создаем необходимые папки
Path(app.config['UPLOAD_FOLDER']).mkdir(exist_ok=True)
Path(app.config['OUTPUT_FOLDER']).mkdir(exist_ok=True)

# Хранилище задач
tasks = {}

class PDFTranslator:
    def __init__(self, terminology_dict=None, source_lang='en', target_lang='ru'):
        self.terminology = terminology_dict or {}
        self.source_lang = source_lang
        self.target_lang = target_lang
        self.translator = GoogleTranslator(source=source_lang, target=target_lang)
        self.images_data = []
        self.content_blocks = []
        
    def load_terminology_from_dict(self, term_dict):
        """Загрузка терминов из словаря"""
        self.terminology = term_dict
        
    def protect_terminology(self, text):
        protected_text = text
        term_map = {}
        sorted_terms = sorted(self.terminology.keys(), key=len, reverse=True)
        
        for idx, term in enumerate(sorted_terms):
            if term.lower() in protected_text.lower():
                placeholder = f"__TERM{idx}__"
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                protected_text = pattern.sub(placeholder, protected_text)
                term_map[placeholder] = self.terminology[term]
        
        return protected_text, term_map
    
    def restore_terminology(self, text, term_map):
        restored_text = text
        for placeholder, translation in term_map.items():
            restored_text = restored_text.replace(placeholder, translation)
        return restored_text
    
    def translate_text(self, text):
        if not text.strip():
            return text
        
        try:
            protected_text, term_map = self.protect_terminology(text)
            translated = self.translator.translate(protected_text)
            final_text = self.restore_terminology(translated, term_map)
            return final_text
        except Exception as e:
            print(f"Ошибка перевода: {e}")
            return text
    
    def extract_images(self, pdf_document, output_folder):
        Path(output_folder).mkdir(parents=True, exist_ok=True)
        image_counter = 0
        
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            image_list = page.get_images()
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                try:
                    base_image = pdf_document.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    img_rect = page.get_image_bbox(img)
                    
                    image_filename = f"image_{image_counter:04d}.{image_ext}"
                    image_path = os.path.join(output_folder, image_filename)
                    
                    with open(image_path, "wb") as img_file:
                        img_file.write(image_bytes)
                    
                    image_base64 = base64.b64encode(image_bytes).decode()
                    
                    self.images_data.append({
                        'id': image_counter,
                        'filename': image_filename,
                        'page': page_num,
                        'position': img_rect,
                        'ext': image_ext,
                        'base64': image_base64
                    })
                    
                    image_counter += 1
                except Exception as e:
                    print(f"Ошибка извлечения изображения: {e}")
        
        return self.images_data
    
    def extract_text_blocks(self, pdf_document):
        for page_num in range(len(pdf_document)):
            page = pdf_document[page_num]
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if block['type'] == 0:
                    block_text = ""
                    font_size = 12
                    
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            block_text += span["text"]
                            font_size = span["size"]
                        block_text += "\n"
                    
                    if block_text.strip():
                        self.content_blocks.append({
                            'type': 'text',
                            'page': page_num,
                            'bbox': block['bbox'],
                            'original': block_text.strip(),
                            'translated': None,
                            'font_size': font_size
                        })
        
        return self.content_blocks
    
    def translate_blocks(self, progress_callback=None):
        total = len(self.content_blocks)
        for idx, block in enumerate(self.content_blocks):
            if block['type'] == 'text':
                block['translated'] = self.translate_text(block['original'])
                if progress_callback:
                    progress_callback(idx + 1, total)
    
    def merge_content(self):
        merged = []
        
        for block in self.content_blocks:
            merged.append({
                'type': 'text',
                'page': block['page'],
                'y_position': block['bbox'][1],
                'content': block
            })
        
        for img in self.images_data:
            merged.append({
                'type': 'image',
                'page': img['page'],
                'y_position': img['position'][1] if img['position'] else 0,
                'content': img
            })
        
        merged.sort(key=lambda x: (x['page'], x['y_position']))
        return merged
    
    def generate_html(self, merged_content, output_path, original_filename):
        html = f"""<!DOCTYPE html>
<html lang="{self.target_lang}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Перевод: {original_filename}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            background-color: #f0f0f0;
            padding: 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            padding-bottom: 30px;
            border-bottom: 3px solid #333;
            margin-bottom: 30px;
        }}
        .header h1 {{ color: #333; font-size: 28px; margin-bottom: 10px; }}
        .header .meta {{ color: #666; font-size: 14px; }}
        .page-break {{
            page-break-after: always;
            border-top: 2px dashed #ccc;
            margin: 40px 0;
            padding-top: 20px;
        }}
        .page-number {{ color: #999; font-size: 12px; text-align: center; margin-bottom: 20px; }}
        .text-block {{ margin-bottom: 20px; text-align: justify; }}
        .image-container {{ margin: 30px 0; text-align: center; }}
        .image-container img {{
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .image-caption {{ font-size: 12px; color: #666; margin-top: 8px; font-style: italic; }}
        .translation-toggle {{
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 4px;
            padding: 15px;
            margin-bottom: 20px;
        }}
        .toggle-btn {{
            background-color: #007bff;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            margin-bottom: 10px;
        }}
        .toggle-btn:hover {{ background-color: #0056b3; }}
        .original-text {{
            display: none;
            background-color: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 10px;
            margin-top: 10px;
            font-style: italic;
        }}
        .terminology-info {{
            background-color: #e7f3ff;
            border-left: 4px solid #2196F3;
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 4px;
        }}
        .terminology-info h3 {{ color: #1976D2; margin-bottom: 10px; font-size: 16px; }}
    </style>
    <script>
        function toggleOriginal(id) {{
            const elem = document.getElementById('original-' + id);
            const btn = document.getElementById('btn-' + id);
            if (elem.style.display === 'none') {{
                elem.style.display = 'block';
                btn.textContent = 'Скрыть оригинал';
            }} else {{
                elem.style.display = 'none';
                btn.textContent = 'Показать оригинал';
            }}
        }}
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Перевод документа</h1>
            <div class="meta">
                Исходный файл: {original_filename}<br>
                Направление перевода: {self.source_lang.upper()} → {self.target_lang.upper()}<br>
                Текстовых блоков: {len([x for x in merged_content if x['type'] == 'text'])}<br>
                Изображений: {len([x for x in merged_content if x['type'] == 'image'])}
            </div>
        </div>
"""
        
        if self.terminology:
            html += f"""
        <div class="terminology-info">
            <h3>📚 Используемая терминология</h3>
            Документ переведен с учетом специализированного словаря терминов.<br>
            <small>Количество терминов: {len(self.terminology)}</small>
        </div>
"""
        
        current_page = -1
        block_id = 0
        
        for item in merged_content:
            if item['page'] != current_page:
                if current_page != -1:
                    html += '<div class="page-break"></div>\n'
                current_page = item['page']
                html += f'<div class="page-number">Страница {current_page + 1}</div>\n'
            
            if item['type'] == 'text':
                content = item['content']
                html += f"""
        <div class="translation-toggle">
            <button class="toggle-btn" id="btn-{block_id}" onclick="toggleOriginal({block_id})">Показать оригинал</button>
            <div class="text-block">
                {content['translated'].replace(chr(10), '<br>')}
            </div>
            <div class="original-text" id="original-{block_id}">
                <strong>Оригинал:</strong><br>
                {content['original'].replace(chr(10), '<br>')}
            </div>
        </div>
"""
                block_id += 1
            
            elif item['type'] == 'image':
                img = item['content']
                html += f"""
        <div class="image-container">
            <img src="data:image/{img['ext']};base64,{img['base64']}" 
                 alt="Изображение со страницы {img['page'] + 1}">
            <div class="image-caption">Рисунок {img['id'] + 1} (Страница {img['page'] + 1})</div>
        </div>
"""
        
        html += """
    </div>
</body>
</html>"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def process_pdf_task(task_id, pdf_path, terminology, source_lang, target_lang):
    """Фоновая задача обработки PDF"""
    try:
        tasks[task_id]['status'] = 'processing'
        tasks[task_id]['progress'] = 0
        
        translator = PDFTranslator(terminology, source_lang, target_lang)
        pdf_document = fitz.open(pdf_path)
        
        tasks[task_id]['total_pages'] = len(pdf_document)
        
        # Извлечение изображений
        tasks[task_id]['stage'] = 'Извлечение изображений'
        output_folder = os.path.join(app.config['OUTPUT_FOLDER'], task_id)
        Path(output_folder).mkdir(parents=True, exist_ok=True)
        images_folder = os.path.join(output_folder, "images")
        translator.extract_images(pdf_document, images_folder)
        
        # Извлечение текста
        tasks[task_id]['stage'] = 'Извлечение текста'
        translator.extract_text_blocks(pdf_document)
        
        # Перевод
        tasks[task_id]['stage'] = 'Перевод'
        def progress_callback(current, total):
            tasks[task_id]['progress'] = int((current / total) * 100)
        
        translator.translate_blocks(progress_callback)
        
        # Генерация HTML
        tasks[task_id]['stage'] = 'Генерация HTML'
        merged_content = translator.merge_content()
        html_path = os.path.join(output_folder, "translated_document.html")
        translator.generate_html(merged_content, html_path, os.path.basename(pdf_path))
        
        pdf_document.close()
        
        # Создание ZIP архива
        tasks[task_id]['stage'] = 'Создание архива'
        zip_path = os.path.join(output_folder, "result.zip")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            zipf.write(html_path, "translated_document.html")
            for img_data in translator.images_data:
                img_path = os.path.join(images_folder, img_data['filename'])
                zipf.write(img_path, f"images/{img_data['filename']}")
        
        tasks[task_id]['status'] = 'completed'
        tasks[task_id]['result_path'] = zip_path
        tasks[task_id]['html_path'] = html_path
        tasks[task_id]['progress'] = 100
        
    except Exception as e:
        tasks[task_id]['status'] = 'error'
        tasks[task_id]['error'] = str(e)

# HTML шаблон для веб-интерфейса
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF Переводчик</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            padding: 40px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 10px;
            font-size: 32px;
        }
        .subtitle {
            text-align: center;
            color: #666;
            margin-bottom: 30px;
            font-size: 14px;
        }
        .upload-area {
            border: 3px dashed #667eea;
            border-radius: 10px;
            padding: 40px;
            text-align: center;
            margin-bottom: 20px;
            cursor: pointer;
            transition: all 0.3s;
        }
        .upload-area:hover { background-color: #f8f9ff; border-color: #764ba2; }
        .upload-area.dragover { background-color: #e8ebff; }
        input[type="file"] { display: none; }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 600;
        }
        select, textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        select:focus, textarea:focus {
            outline: none;
            border-color: #667eea;
        }
        textarea {
            resize: vertical;
            min-height: 150px;
            font-family: monospace;
        }
        button {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        button:hover { transform: translateY(-2px); }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        .progress-container {
            display: none;
            margin-top: 20px;
        }
        .progress-bar {
            width: 100%;
            height: 30px;
            background-color: #f0f0f0;
            border-radius: 15px;
            overflow: hidden;
            margin-top: 10px;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
        }
        .status {
            text-align: center;
            margin-top: 10px;
            color: #666;
        }
        .result {
            display: none;
            margin-top: 20px;
            padding: 20px;
            background-color: #e8f5e9;
            border-radius: 8px;
            text-align: center;
        }
        .result a {
            display: inline-block;
            margin: 10px;
            padding: 12px 24px;
            background-color: #4caf50;
            color: white;
            text-decoration: none;
            border-radius: 6px;
            transition: background-color 0.3s;
        }
        .result a:hover { background-color: #45a049; }
        .error {
            display: none;
            margin-top: 20px;
            padding: 20px;
            background-color: #ffebee;
            border-radius: 8px;
            color: #c62828;
            text-align: center;
        }
        .info-box {
            background-color: #e3f2fd;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #2196F3;
        }
        .info-box h3 {
            color: #1976D2;
            margin-bottom: 8px;
            font-size: 16px;
        }
        .info-box p {
            color: #666;
            font-size: 14px;
            line-height: 1.6;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>📄 PDF Переводчик</h1>
        <p class="subtitle">Загрузите PDF документ для перевода с сохранением структуры и изображений</p>
        
        <div class="info-box">
            <h3>ℹ️ Инструкция</h3>
            <p>1. Загрузите PDF файл (до 50 МБ)<br>
            2. Выберите языки перевода<br>
            3. При необходимости добавьте словарь терминов в формате JSON<br>
            4. Нажмите "Перевести" и дождитесь завершения</p>
        </div>
        
        <form id="uploadForm">
            <div class="upload-area" id="uploadArea">
                <p style="font-size: 48px; margin-bottom: 10px;">📁</p>
                <p style="color: #667eea; font-weight: 600;">Нажмите или перетащите PDF файл сюда</p>
                <p style="color: #999; font-size: 12px; margin-top: 10px;">Максимальный размер: 50 МБ</p>
                <input type="file" id="pdfFile" name="pdf" accept=".pdf" required>
            </div>
            
            <div class="form-group">
                <label for="sourceLang">Исходный язык:</label>
                <select id="sourceLang" name="source_lang" required>
                    <option value="en">Английский</option>
                    <option value="de">Немецкий</option>
                    <option value="fr">Французский</option>
                    <option value="es">Испанский</option>
                    <option value="it">Итальянский</option>
                    <option value="zh-CN">Китайский</option>
                    <option value="ja">Японский</option>
                </select>
            </div>
            
            <div class="form-group">
                <label for="targetLang">Целевой язык:</label>
                <select id="targetLang" name="target_lang" required>
                    <option value="ru">Русский</option>
                    <option value="en">Английский</option>
                    <option value="de">Немецкий</option>
                    <option value="fr">Французский</option>
                    <option value="es">Испанский</option>
                </select>
            </div>
            
            <div class="form-group">
                <label for="terminology">Словарь терминов (JSON, опционально):</label>
                <textarea id="terminology" name="terminology" placeholder='{"term1": "перевод1", "term2": "перевод2"}'></textarea>
            </div>
            
            <button type="submit" id="submitBtn">🚀 Перевести документ</button>
        </form>
        
        <div class="progress-container" id="progressContainer">
            <h3 style="text-align: center; color: #333; margin-bottom: 10px;">Обработка...</h3>
            <div class="progress-bar">
                <div class="progress-fill" id="progressFill">0%</div>
            </div>
            <div class="status" id="statusText">Инициализация...</div>
        </div>
        
        <div class="result" id="result">
            <h3 style="color: #2e7d32; margin-bottom: 15px;">✅ Перевод завершен!</h3>
            <a href="#" id="downloadZip">📦 Скачать архив (HTML + изображения)</a>
            <a href="#" id="viewHtml" target="_blank">👁️ Просмотреть результат</a>
        </div>
        
        <div class="error" id="error">
            <h3 style="margin-bottom: 10px;">❌ Ошибка</h3>
            <p id="errorText"></p>
        </div>
    </div>
    
    <script>
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('pdfFile');
        const form = document.getElementById('uploadForm');
        const progressContainer = document.getElementById('progressContainer');
        const progressFill = document.getElementById('progressFill');
        const statusText = document.getElementById('statusText');
        const result = document.getElementById('result');
        const error = document.getElementById('error');
        const submitBtn = document.getElementById('submitBtn');
        
        // Drag & Drop
        uploadArea.addEventListener('click', () => fileInput.click());
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            if (e.dataTransfer.files.length) {
                fileInput.files = e.dataTransfer.files;
                uploadArea.querySelector('p').textContent = '✓ ' + e.dataTransfer.files[0].name;
            }
        });
        
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length) {
                uploadArea.querySelector('p').textContent = '✓ ' + e.target.files[0].name;
            }
        });
        
        // Отправка формы
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const formData = new FormData(form);
            
            submitBtn.disabled = true;
            progressContainer.style.display = 'block';
            result.style.display = 'none';
            error.style.display = 'none';
            
            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const data = await response.json();
                
                if (data.success) {
                    const taskId = data.task_id;
                    checkProgress(taskId);
                } else {
                    throw new Error(data.error);
                }
            } catch (err) {
                error.style.display = 'block';
                error.querySelector('#errorText').textContent = err.message;
                progressContainer.style.display = 'none';
                submitBtn.disabled = false;
            }
        });
        
        // Проверка прогресса
        async function checkProgress(taskId) {
            const interval = setInterval(async () => {
                try {
                    const response = await fetch(`/progress/${taskId}`);
                    const data = await response.json();
                    
                    progressFill.style.width = data.progress + '%';
                    progressFill.textContent = data.progress + '%';
                    statusText.textContent = data.stage || data.status;
                    
                    if (data.status === 'completed') {
                        clearInterval(interval);
                        progressContainer.style.display = 'none';
                        result.style.display = 'block';
                        document.getElementById('downloadZip').href = `/download/${taskId}`;
                        document.getElementById('viewHtml').href = `/view/${taskId}`;
                        submitBtn.disabled = false;
                    } else if (data.status === 'error') {
                        clearInterval(interval);
                        error.style.display = 'block';
                        error.querySelector('#errorText').textContent = data.error;
                        progressContainer.style.display = 'none';
                        submitBtn.disabled = false;
                    }
                } catch (err) {
                    clearInterval(interval);
                    error.style.display = 'block';
                    error.querySelector('#errorText').textContent = 'Ошибка получения статуса';
                    progressContainer.style.display = 'none';
                    submitBtn.disabled = false;
                }
            }, 1000);
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/upload', methods=['POST'])
def upload():
    if 'pdf' not in request.files:
        return jsonify({'success': False, 'error': 'Файл не найден'})
    
    file = request.files['pdf']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Файл не выбран'})
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Неверный формат файла'})
    
    # Сохраняем файл
    filename = secure_filename(file.filename)
    task_id = str(uuid.uuid4())
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{task_id}_{filename}")
    file.save(upload_path)
    
    # Получаем параметры
    source_lang = request.form.get('source_lang', 'en')
    target_lang = request.form.get('target_lang', 'ru')
    
    # Парсим терминологию
    terminology = {}
    terminology_text = request.form.get('terminology', '').strip()
    if terminology_text:
        try:
            terminology = json.loads(terminology_text)
        except json.JSONDecodeError:
            return jsonify({'success': False, 'error': 'Неверный формат JSON для терминологии'})
    
    # Создаем задачу
    tasks[task_id] = {
        'status': 'pending',
        'progress': 0,
        'stage': 'Инициализация',
        'filename': filename
    }
    
    # Запускаем обработку в фоновом потоке
    thread = threading.Thread(
        target=process_pdf_task,
        args=(task_id, upload_path, terminology, source_lang, target_lang)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({'success': True, 'task_id': task_id})

@app.route('/progress/<task_id>')
def progress(task_id):
    if task_id not in tasks:
        return jsonify({'status': 'not_found', 'error': 'Задача не найдена'})
    
    return jsonify(tasks[task_id])

@app.route('/download/<task_id>')
def download(task_id):
    if task_id not in tasks:
        return "Задача не найдена", 404
    
    task = tasks[task_id]
    
    if task['status'] != 'completed':
        return "Задача еще не завершена", 400
    
    return send_file(
        task['result_path'],
        as_attachment=True,
        download_name='translated_document.zip',
        mimetype='application/zip'
    )

@app.route('/view/<task_id>')
def view(task_id):
    if task_id not in tasks:
        return "Задача не найдена", 404
    
    task = tasks[task_id]
    
    if task['status'] != 'completed':
        return "Задача еще не завершена", 400
    
    with open(task['html_path'], 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    return html_content

@app.route('/api/translate', methods=['POST'])
def api_translate():
    """API endpoint для программного доступа"""
    if 'pdf' not in request.files:
        return jsonify({'error': 'PDF file is required'}), 400
    
    file = request.files['pdf']
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file format'}), 400
    
    filename = secure_filename(file.filename)
    task_id = str(uuid.uuid4())
    upload_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{task_id}_{filename}")
    file.save(upload_path)
    
    source_lang = request.form.get('source_lang', 'en')
    target_lang = request.form.get('target_lang', 'ru')
    
    terminology = {}
    if 'terminology' in request.files:
        term_file = request.files['terminology']
        terminology = json.load(term_file)
    elif 'terminology_json' in request.form:
        try:
            terminology = json.loads(request.form.get('terminology_json'))
        except:
            pass
    
    tasks[task_id] = {
        'status': 'pending',
        'progress': 0,
        'stage': 'Initialization',
        'filename': filename
    }
    
    thread = threading.Thread(
        target=process_pdf_task,
        args=(task_id, upload_path, terminology, source_lang, target_lang)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'task_id': task_id,
        'status_url': f'/api/status/{task_id}',
        'download_url': f'/download/{task_id}'
    })

@app.route('/api/status/<task_id>')
def api_status(task_id):
    """API endpoint для проверки статуса"""
    if task_id not in tasks:
        return jsonify({'error': 'Task not found'}), 404
    
    return jsonify(tasks[task_id])

if __name__ == '__main__':
    print("\n" + "="*70)
    print(" "*20 + "PDF ПЕРЕВОДЧИК - СЕРВЕР")
    print("="*70)
    print("\n📡 Сервер запущен!")
    print(f"🌐 Веб-интерфейс: http://localhost:5000")
    print(f"🔌 API endpoint: http://localhost:5000/api/translate")
    print("\n💡 Для доступа из сети используйте:")
    print("   python server.py --host 0.0.0.0 --port 5000")
    print("\n" + "="*70 + "\n")
    
    import sys
    host = '127.0.0.1'
    port = 5000
    
    if '--host' in sys.argv:
        host = sys.argv[sys.argv.index('--host') + 1]
    if '--port' in sys.argv:
        port = int(sys.argv[sys.argv.index('--port') + 1])
    
    app.run(host=host, port=port, debug=True, threaded=True)