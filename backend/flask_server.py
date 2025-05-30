from flask import Flask, request, jsonify
import os
import base64
from io import BytesIO
from PIL import Image
import json
import traceback
from text_content_filteration import detect_content, process_text
from image_filteration import ImageContentFilter
from flask_cors import CORS

app = Flask(__name__)
# Enable CORS for all routes and all origins
CORS(app)

# Initialize the image content filter
image_filter = ImageContentFilter()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'ok',
        'message': 'Python filtration server is running'
    })

@app.route('/filter/text', methods=['POST'])
def filter_text():
    """Text content filtering endpoint"""
    try:
        data = request.json
        if not data or 'text' not in data:
            return jsonify({'error': 'No text provided'}), 400
        
        text = data['text']
        action = data.get('action', 'filter')  # Default action is to filter
        
        # Detect problematic content
        detection_results = detect_content(text)
        
        # Process the text based on detection results
        processed_text = process_text(text, detection_results, action)
        
        return jsonify({
            'original_text': text,
            'processed_text': processed_text,
            'detection_results': detection_results,
            'action': action
        })
    
    except Exception as e:
        print(f"Error in text filtering: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/filter/image', methods=['POST'])
def filter_image():
    """Image content filtering endpoint"""
    try:
        if 'image' not in request.files and 'image_data' not in request.form:
            return jsonify({'error': 'No image provided'}), 400
        
        # Handle file upload
        if 'image' in request.files:
            image_file = request.files['image']
            image = Image.open(image_file)
            
            # Save to a temporary file for processing
            temp_path = 'temp_image.jpg'
            image.save(temp_path)
            
            # Analyze the image
            results = image_filter.analyze_image(image_path=temp_path, show_results=False)
            
            # Clean up the temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
        
        # Handle base64 encoded image
        elif 'image_data' in request.form:
            image_data = request.form['image_data']
            # Remove data URL prefix if present
            if ',' in image_data:
                image_data = image_data.split(',', 1)[1]
            
            # Decode base64 to binary
            binary_data = base64.b64decode(image_data)
            image = Image.open(BytesIO(binary_data))
            
            # Analyze the image
            results = image_filter.analyze_image(image_data=binary_data, show_results=False)
        
        return jsonify(results)
    
    except Exception as e:
        print(f"Error in image filtering: {str(e)}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# Load environment variables from .env file if it exists
if os.path.exists('.env'):
    from dotenv import load_dotenv
    load_dotenv()

# For Render deployment
if __name__ == '__main__':
    port = int(os.environ.get('PORT', os.environ.get('PYTHON_PORT', 5000)))
    app.run(host='0.0.0.0', port=port, debug=False)