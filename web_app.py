"""
Веб-интерфейс для PDF Translator - ИСПРАВЛЕННАЯ ВЕРСИЯ
"""

from flask import Flask, request, render_template, send_file, jsonify
from pathlib import Path
import tempfile
import os

from config import TranslatorConfig
from extractor import PDFExtractor
from translator import TextTranslator
from reconstructor import PDFReconstructor
from utils import get_logger

app = Flask(__name__)
logger = get_logger(__name__)

# Настройка
UPLOAD_FOLDER = Path(tempfile.gettempdir()) / 'pdf_translator'
UPLOAD_FOLDER.mkdir(exist_ok=True)
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

@app.route('/')
def index():
    """Главная страница."""
    return render_template('index.html')

@app.route('/translate', methods=['POST'])
def translate_pdf():
    """Перевод PDF файла."""
    try:
        # Получаем параметры
        if 'pdf_file' not in request.files:
            return jsonify({'error': 'Файл не загружен'}), 400
        
        pdf_file = request.files['pdf_file']
        target_lang = request.form.get('target_lang', 'ru')
        source_lang = request.form.get('source_lang', 'auto')
        side_by_side = request.form.get('side_by_side', 'true') == 'true'
        model = request.form.get('model', 'gpt-4.1-mini')
        
        if pdf_file.filename == '':
            return jsonify({'error': 'Файл не выбран'}), 400
        
        # Сохраняем входной файл
        input_path = UPLOAD_FOLDER / f'input_{pdf_file.filename}'
        pdf_file.save(str(input_path))
        
        logger.info(f"Начинаем перевод: {pdf_file.filename}")
        logger.info(f"  Язык: {source_lang} → {target_lang}")
        logger.info(f"  Side-by-side: {side_by_side}")
        
        # Создаем конфигурацию
        config = TranslatorConfig(
            source_language=source_lang,
            target_language=target_lang,
            translation_model=model
        )
        
        # Шаг 1: Извлечение
        logger.info("Шаг 1/3: Извлечение контента...")
        with PDFExtractor(str(input_path)) as extractor:
            extracted_data = extractor.extract_all()
        
        pages = extracted_data['pages']
        text_blocks = extracted_data['text_blocks']
        images = extracted_data['images']
        metadata = extracted_data['metadata']
        
        logger.info(f"  Извлечено: {len(pages)} стр, {len(text_blocks)} блоков текста")
        
        # Шаг 2: Перевод
        logger.info("Шаг 2/3: Перевод текста...")
        translator = TextTranslator(config)
        translated_blocks = translator.translate_text_blocks(
            text_blocks, source_lang, target_lang
        )
        logger.info(f"  Переведено: {len(translated_blocks)} блоков")
        
        # Шаг 3: Создание выходного PDF
        logger.info("Шаг 3/3: Создание PDF...")
        reconstructor = PDFReconstructor(config)
        
        output_filename = f'translated_{pdf_file.filename}'
        output_path = UPLOAD_FOLDER / output_filename
        
        if side_by_side:
            # Side-by-side режим: оригинал | перевод
            logger.info("  Режим: Side-by-side (оригинал | перевод)")
            reconstructor.create_side_by_side_pdf(
                original_pdf_path=str(input_path),
                pages=pages,
                text_blocks=translated_blocks,
                images=images,
                output_path=str(output_path),
                page_range=None
            )
        else:
            # Translation-only режим: только перевод (overlay)
            logger.info("  Режим: Translation-only (только перевод)")
            reconstructor.create_translation_only_pdf(
                original_pdf_path=str(input_path),
                pages=pages,
                text_blocks=translated_blocks,
                images=images,
                output_path=str(output_path)
            )
        
        logger.info(f"✓ Готово! Файл: {output_filename}")
        
        # Отправляем файл
        return send_file(
            str(output_path),
            as_attachment=True,
            download_name=output_filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        logger.error(f"Ошибка перевода: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
    
    # Примечание: временные файлы можно удалять вручную
    # или настроить автоочистку через cron job


@app.route('/info', methods=['POST'])
def get_pdf_info():
    """Получить информацию о PDF."""
    try:
        if 'pdf_file' not in request.files:
            return jsonify({'error': 'Файл не загружен'}), 400
        
        pdf_file = request.files['pdf_file']
        input_path = UPLOAD_FOLDER / f'info_{pdf_file.filename}'
        pdf_file.save(str(input_path))
        
        with PDFExtractor(str(input_path)) as extractor:
            stats = extractor.get_statistics()
            metadata = extractor.get_metadata()
        
        # Очистка
        if input_path.exists():
            input_path.unlink()
        
        return jsonify({
            'statistics': stats,
            'metadata': metadata
        })
        
    except Exception as e:
        logger.error(f"Ошибка получения информации: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    # Проверка API ключа
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  ВНИМАНИЕ: OPENAI_API_KEY не установлен!")
        print("Установите переменную окружения:")
        print("  export OPENAI_API_KEY='your-key'")
        exit(1)
    
    print("="*60)
    print("PDF Translator - Веб-интерфейс")
    print("="*60)
    print(f"Загрузки сохраняются в: {UPLOAD_FOLDER}")
    print(f"Максимальный размер файла: 50MB")
    print("")
    print("Запуск сервера на http://0.0.0.0:5000")
    print("="*60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)
