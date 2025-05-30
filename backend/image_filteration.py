import os
import io
import base64
import re
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import requests
import matplotlib.pyplot as plt
from google.cloud import vision
import numpy as np
from IPython.display import display, HTML
import logging
import json
import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(_name_)

# Load environment variables
load_dotenv()

class ImageContentFilter:
    def __init__(self):
        """Initialize the content filter with Google Cloud Vision API"""
        # Load Google Cloud credentials from .env
        self.api_key = os.getenv("GOOGLE_CLOUD_API_KEY")
        self.confidence_thresholds = {
            "adult": 0.7,
            "violence": 0.6,
            "racy": 0.7,
            "medical": 0.8,
            "spoof": 0.8,  # Useful for potential deepfakes
            "text_offense": 0.7,
            "hate_symbols": 0.6,  # Lower threshold for hate symbols
            "personal_info": 0.7,
            "deepfake": 0.7,
            "spam": 0.7
        }
        
        # Enhanced blur settings
        self.blur_settings = {
            "unsafe": 30,
            "questionable": 15,
            "potentially_concerning": 8
        }
        
        # Check if API key is available
        if not self.api_key:
            raise ValueError("Google Cloud API key not found in .env file. Please add GOOGLE_CLOUD_API_KEY=your_key_here to your .env file.")

        # Initialize Google Cloud Vision client
        try:
            # First try to use the environment variable
            credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            if credentials_path and os.path.exists(credentials_path):
                self.client = vision.ImageAnnotatorClient.from_service_account_json(credentials_path)
                logger.info(f"Using Google Cloud credentials from environment variable: {credentials_path}")
            else:
                # Fallback to a local path relative to the project
                local_credentials_path = os.path.join(os.path.dirname(_file_), "google_credentials.json")
                if os.path.exists(local_credentials_path):
                    self.client = vision.ImageAnnotatorClient.from_service_account_json(local_credentials_path)
                    logger.info(f"Using Google Cloud credentials from local file: {local_credentials_path}")
                else:
                    # Last resort - try the hardcoded path but with a warning
                    fallback_path = "C:/Users/Antriksh Sharma/Documents/project capstone/my-project-92814-457204-c90e6bf83130.json"
                    if os.path.exists(fallback_path):
                        self.client = vision.ImageAnnotatorClient.from_service_account_json(fallback_path)
                        logger.warning(f"Using fallback Google Cloud credentials: {fallback_path}")
                    else:
                        raise FileNotFoundError(f"No valid Google Cloud credentials found. Please set GOOGLE_APPLICATION_CREDENTIALS environment variable.")
        except Exception as e:
            logger.error(f"Error initializing Google Cloud Vision client: {str(e)}")
            raise
        
        # Offensive terms for text analysis
        self.offensive_terms = [
            "hate", "kill", "attack", "racist", "nazi", "violence", 
            "offensive", "explicit", "suicide", "abuse", "kill", "murder",
            "slur", "profanity", "obscene"
        ]
        
        # NEW: Dictionary of known hate symbols to detect
        self.hate_symbols = {
            "swastika": ["swastika", "nazi symbol"],
            "confederate flag": ["confederate flag", "rebel flag"],
            "white power": ["white power", "white pride"],
            "kkk": ["kkk", "ku klux klan"],
            "ss bolts": ["ss bolts", "nazi ss"],
            "iron cross": ["iron cross"],
            "celtic cross": ["celtic cross"],
            "othala rune": ["othala rune"],
            "sonnenrad": ["black sun", "sonnenrad"],
            "blood drop cross": ["blood drop cross"],
            "fascist symbols": ["fascist", "fascism"]
        }
        
        # NEW: Pattern for detecting personal information
        self.pii_patterns = {
            "credit_card": r"(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|6(?:011|5[0-9]{2})[0-9]{12}|(?:2131|1800|35\d{3})\d{11})",
            "ssn": r"\b(?!000|666|9\d{2})([0-8]\d{2}|7([0-6]\d|7[012]))([-])?(?!00)\d\d\3(?!0000)\d{4}\b",
            "bank_account": r"\b[0-9]{8,17}\b",
            "routing_number": r"\b[0-9]{9}\b",
            "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "phone": r"\b(?:\+\d{1,3}[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}\b"
        }
        
        # NEW: Spam and scam indicators
        self.spam_indicators = [
            "urgent", "act now", "limited time", "congratulations", "won", "lottery", 
            "prize", "free money", "million dollars", "click here", "verify your account",
            "bank transfer", "inheritance", "nigerian prince", "urgently", "warning", 
            "security alert", "suspended", "verify identity", "account locked", 
            "unusual activity", "claim your", "wire transfer", "send money"
        ]
        
        # NEW: Deepfake indicators (labels that might suggest a deepfake)
        self.deepfake_indicators = [
            "artificial", "generated", "synthetic", "manipulated", "fake", "unnatural",
            "distorted", "warped", "ai generated", "computer generated", "gans", 
            "generative", "unreal", "edited", "modified"
        ]
        
        logger.info("Content filter initialized successfully")

    def analyze_image(self, image_path=None, image_url=None, image_data=None, show_results=True, export_comparison=True):
        """
        Analyze an image for content filtering using Google Cloud Vision API
    
        Args:
            image_path (str): Path to the local image file
            image_url (str): URL of an image online
            image_data (bytes): Raw image data
            show_results (bool): Whether to display visual results
            export_comparison (bool): Whether to export side-by-side comparison
        
        Returns:
            dict: Analysis results
        """
        try:
            # Load the image based on the provided input
            if image_path:
                try:
                    with open(image_path, 'rb') as image_file:
                        content = image_file.read()
                    image = vision.Image(content=content)
                    display_image = Image.open(io.BytesIO(content))
                    source = f"Local file: {os.path.basename(image_path)}"
                    source_filename = os.path.basename(image_path)
                except FileNotFoundError:
                    raise ValueError(f"Image file not found: {image_path}")
                except Exception as e:
                    raise ValueError(f"Error opening image file: {str(e)}")
            
            elif image_url:
                try:
                    # Handle data URLs (base64 encoded images)
                    if image_url.startswith('data:image'):
                        try:
                            # Extract the base64 part
                            content_type, data = image_url.split(',', 1)
                            # Decode the base64 data
                            content = base64.b64decode(data)
                            image = vision.Image(content=content)
                            display_image = Image.open(io.BytesIO(content))
                            source = "Data URL image"
                            source_filename = "data_url_image"
                        except Exception as e:
                            logger.error(f"Error processing data URL: {str(e)}")
                            raise ValueError(f"Error processing data URL image: {str(e)}")
                    else:
                        # Regular URL handling
                        headers = {
                            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                        }
                        response = requests.get(image_url, timeout=10, headers=headers)
                        response.raise_for_status()  # Raise exception for bad HTTP responses
                        content = response.content
                        
                        # Check if the content is actually an image
                        content_type = response.headers.get('Content-Type', '')
                        if not content_type.startswith('image/'):
                            logger.warning(f"URL does not point to an image. Content-Type: {content_type}")
                            # Try to proceed anyway, it might still be an image
                        
                        image = vision.Image(content=content)
                        display_image = Image.open(io.BytesIO(content))
                        source = f"URL: {image_url}"
                        # Extract filename from URL for export
                        source_filename = os.path.basename(image_url.split('?')[0])  # Remove query parameters
                        if not source_filename:
                            source_filename = "downloaded_image"
                except requests.exceptions.RequestException as e:
                    logger.error(f"Error downloading image from URL: {str(e)}")
                    raise ValueError(f"Error downloading image from URL: {str(e)}")
                except Exception as e:
                    logger.error(f"Error processing image from URL: {str(e)}")
                    raise ValueError(f"Error processing image from URL: {str(e)}")
            
            else:
                raise ValueError("No image provided. Please provide either image_path, image_url, or image_data.")
        
            # Create a comprehensive feature list
            features = [
                vision.Feature(type_=vision.Feature.Type.SAFE_SEARCH_DETECTION),
                vision.Feature(type_=vision.Feature.Type.LABEL_DETECTION, max_results=20),  # Increased from 10 to 20
                vision.Feature(type_=vision.Feature.Type.TEXT_DETECTION),
                vision.Feature(type_=vision.Feature.Type.OBJECT_LOCALIZATION, max_results=20),  # Increased from 10 to 20
                vision.Feature(type_=vision.Feature.Type.FACE_DETECTION),  # NEW: Added face detection for deepfake analysis
                vision.Feature(type_=vision.Feature.Type.IMAGE_PROPERTIES)  # NEW: Added for image properties analysis
            ]
        
            # Perform image annotation
            request = vision.AnnotateImageRequest(image=image, features=features)
            response = self.client.annotate_image(request=request)
        
            # Check if the API returned an error
            if response.error.message:
                raise ValueError(f"Google Vision API error: {response.error.message}")
        
            # Process the response
            results = self._process_response(response, display_image, source)
        
            # Create processed image
            processed_image = self._create_processed_image(display_image, results)
            
            # Display results if requested
            if show_results:
                self._display_results(results, display_image, processed_image)
            
            # Export side-by-side comparison if requested
            if export_comparison:
                export_path = self._export_side_by_side(display_image, processed_image, results, source_filename)
                results["export_path"] = export_path
        
            return results
        
        except Exception as e:
            logger.exception(f"Error in image analysis: {str(e)}")
            raise
    
    def _create_processed_image(self, image, results):
        """Create a processed image based on the analysis results"""
        processed_image = image.copy()
        
        # Apply visual indicator based on safety score
        if results["overall_safety"] == "unsafe":
            # Apply strong blur for unsafe content
            processed_image = processed_image.filter(ImageFilter.GaussianBlur(radius=self.blur_settings["unsafe"]))
        elif results["overall_safety"] == "questionable":
            # Apply medium blur for questionable content
            processed_image = processed_image.filter(ImageFilter.GaussianBlur(radius=self.blur_settings["questionable"]))
        elif results["overall_safety"] == "potentially_concerning":
            # Apply light blur for minor concerns
            processed_image = processed_image.filter(ImageFilter.GaussianBlur(radius=self.blur_settings["potentially_concerning"]))
    
        # Convert to RGBA if not already (needed for drawing)
        if processed_image.mode != 'RGBA':
            processed_image = processed_image.convert('RGBA')
    
        draw = ImageDraw.Draw(processed_image)
    
        # Draw detected objects with bounding boxes
        for obj in results["detected_objects"]:
            name = obj["name"]
            vertices = obj["bounding_box"]
            x_coords = [v["x"] * image.width for v in vertices]
            y_coords = [v["y"] * image.height for v in vertices]
        
            # Draw rectangle
            is_concerning = any(f"concerning_object:{name}" in flag for flag in results["content_flags"])
            color = (255, 0, 0, 180) if is_concerning else (0, 255, 0, 180)
        
            # Convert to list of tuples for drawing
            xy = list(zip(x_coords, y_coords))
            draw.polygon(xy, outline=color)
        
            # Add label at top of bounding box
            draw.text((min(x_coords), min(y_coords) - 10), name, fill=color)
            
        # NEW: If PII was detected, highlight the areas
        if "personal_info" in results["content_flags"] and "pii_locations" in results.get("detailed_analysis", {}):
            for pii_loc in results["detailed_analysis"]["pii_locations"]:
                vertices = pii_loc["bounding_box"]
                x_coords = [v["x"] * image.width for v in vertices]
                y_coords = [v["y"] * image.height for v in vertices]
                
                # Draw rectangle with red color
                xy = list(zip(x_coords, y_coords))
                draw.polygon(xy, outline=(255, 0, 0, 255), width=3)
                
                # Add "PII DETECTED" label
                draw.text((min(x_coords), min(y_coords) - 15), "PII DETECTED", fill=(255, 0, 0, 255))
                
        # NEW: If hate symbols were detected, highlight them
        if "hate_symbols" in results["content_flags"] and "hate_symbol_locations" in results.get("detailed_analysis", {}):
            for symbol_loc in results["detailed_analysis"]["hate_symbol_locations"]:
                vertices = symbol_loc["bounding_box"]
                x_coords = [v["x"] * image.width for v in vertices]
                y_coords = [v["y"] * image.height for v in vertices]
                
                # Draw rectangle with purple color
                xy = list(zip(x_coords, y_coords))
                draw.polygon(xy, outline=(128, 0, 128, 255), width=3)
                
                # Add "HATE SYMBOL" label
                draw.text((min(x_coords), min(y_coords) - 15), "HATE SYMBOL", fill=(128, 0, 128, 255))
            
        return processed_image
    
    def _export_side_by_side(self, original_image, processed_image, results, source_filename):
        """Export original and processed images side by side"""
        try:
            # Ensure both images have the same mode
            if original_image.mode != processed_image.mode:
                original_image = original_image.convert('RGBA')
                processed_image = processed_image.convert('RGBA')
            
            # Get dimensions
            width, height = original_image.size
            
            # Create a new image with double width
            combined_image = Image.new(original_image.mode, (width * 2, height))
            
            # Paste original image on the left
            combined_image.paste(original_image, (0, 0))
            
            # Paste processed image on the right
            combined_image.paste(processed_image, (width, 0))
            
            # Add a dividing line
            draw = ImageDraw.Draw(combined_image)
            draw.line([(width, 0), (width, height)], fill=(255, 0, 0, 255), width=2)
            
            # Add safety label
            safety_text = results["overall_safety"].upper().replace("_", " ")
            action_text = results["suggested_action"].upper()
            
            # Try to load a font (fallback to default if not available)
            try:
                font = ImageFont.truetype("arial.ttf", 20)
            except IOError:
                font = ImageFont.load_default()
            
            # Add safety info text to the right side
            text_position = (width + 10, 10)
            text_color = (255, 0, 0, 255) if results["overall_safety"] == "unsafe" else (255, 165, 0, 255)
            draw.text(text_position, f"STATUS: {safety_text}", fill=text_color, font=font)
            draw.text((width + 10, 40), f"ACTION: {action_text}", fill=text_color, font=font)
            
            # Generate output filename
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = os.path.splitext(source_filename)[0]
            output_filename = f"{base_name}analyzed{timestamp}.jpg"
            
            # Convert to RGB for JPG export
            if combined_image.mode == 'RGBA':
                combined_image = combined_image.convert('RGB')
                
            # Save the combined image
            combined_image.save(output_filename, 'JPEG', quality=95)
            logger.info(f"Exported side-by-side comparison to {output_filename}")
            
            return output_filename
            
        except Exception as e:
            logger.exception(f"Error exporting side-by-side comparison: {str(e)}")
            return None
        
    def _process_response(self, response, display_image, source):
        """Process the Google Cloud Vision API response"""
        results = {
            "source": source,
            "image_size": f"{display_image.width}x{display_image.height}",
            "safe_search": {},
            "labels": [],
            "text_content": "",
            "detected_objects": [],
            "content_flags": [],
            "overall_safety": "safe",
            "detailed_analysis": {}
        }
    
        # Process Safe Search
        safe_search = response.safe_search_annotation
    
        # Convert likelihood enum to score
        likelihood_scores = {
            vision.Likelihood.UNKNOWN: 0.0,
            vision.Likelihood.VERY_UNLIKELY: 0.1,
            vision.Likelihood.UNLIKELY: 0.3,
            vision.Likelihood.POSSIBLE: 0.5,
            vision.Likelihood.LIKELY: 0.7,
            vision.Likelihood.VERY_LIKELY: 0.9
        }
    
        # Get likelihood name properly
        def get_likelihood_name(likelihood_value):
            for name, value in vision.Likelihood._dict_.items():
                if isinstance(value, int) and value == likelihood_value:
                    return name
            return "UNKNOWN"  # Fallback
    
        # Process each safe search category
        safe_search_results = {
            "adult": {"score": likelihood_scores[safe_search.adult], "likelihood": get_likelihood_name(safe_search.adult)},
            "violence": {"score": likelihood_scores[safe_search.violence], "likelihood": get_likelihood_name(safe_search.violence)},
            "racy": {"score": likelihood_scores[safe_search.racy], "likelihood": get_likelihood_name(safe_search.racy)},
            "medical": {"score": likelihood_scores[safe_search.medical], "likelihood": get_likelihood_name(safe_search.medical)},
            "spoof": {"score": likelihood_scores[safe_search.spoof], "likelihood": get_likelihood_name(safe_search.spoof)}
        }
        results["safe_search"] = safe_search_results
    
        # Flag content based on thresholds
        for category, data in safe_search_results.items():
            if data["score"] >= self.confidence_thresholds.get(category, 0.7):
                results["content_flags"].append(category)
    
        # Process Labels
        labels = []
        for label in response.label_annotations:
            labels.append({
                "description": label.description,
                "score": label.score,
                "topicality": label.topicality
            })
        results["labels"] = labels
    
        # Look for potentially concerning labels
        concerning_keywords = [
            "weapon", "gun", "knife", "blood", "drug", "alcohol", "cigarette", 
            "smoking", "death", "corpse", "nazi", "hate", "explicit", "nude", 
            "naked", "underwear"
        ]
    
        for label in labels:
            if any(keyword in label["description"].lower() for keyword in concerning_keywords) and label["score"] > 0.7:
                results["content_flags"].append(f"concerning_label:{label['description']}")
    
        # Process Text
        if response.text_annotations:
            full_text = response.text_annotations[0].description
            results["text_content"] = full_text
        
            # Check for offensive content in text
            text_lower = full_text.lower()
            offensive_words_found = [word for word in self.offensive_terms if word in text_lower]
        
            if offensive_words_found:
                results["content_flags"].append("offensive_text")
                results["detailed_analysis"]["offensive_text"] = offensive_words_found
                
            # NEW: Check for hate symbols mentioned in text
            hate_symbols_found = []
            for symbol, keywords in self.hate_symbols.items():
                if any(keyword.lower() in text_lower for keyword in keywords):
                    hate_symbols_found.append(symbol)
            
            if hate_symbols_found:
                results["content_flags"].append("hate_symbols")
                results["detailed_analysis"]["hate_symbols_text"] = hate_symbols_found
                
            # NEW: Check for personal information in text
            pii_found = {}
            pii_locations = []
            
            # Process each text annotation (words/phrases with location)
            for text_annot in response.text_annotations[1:]:  # Skip the first one which is the full text
                text_content = text_annot.description
                
                # Check for PII patterns
                for pii_type, pattern in self.pii_patterns.items():
                    if re.search(pattern, text_content):
                        if pii_type not in pii_found:
                            pii_found[pii_type] = []
                        
                        # Don't store the actual PII, just note that it was found
                        pii_found[pii_type].append("PII DETECTED")
                        
                        # Store the bounding box for highlighting
                        vertices = [
                            {"x": vertex.x, "y": vertex.y} 
                            for vertex in text_annot.bounding_poly.vertices
                        ]
                        pii_locations.append({
                            "type": pii_type,
                            "bounding_box": vertices
                        })
            
            if pii_found:
                results["content_flags"].append("personal_info")
                results["detailed_analysis"]["personal_info"] = pii_found
                results["detailed_analysis"]["pii_locations"] = pii_locations
                
            # NEW: Check for spam/scam indicators
            spam_indicators_found = [indicator for indicator in self.spam_indicators 
                                    if indicator.lower() in text_lower]
            
            if len(spam_indicators_found) >= 2:  # If at least 2 indicators are found
                results["content_flags"].append("spam_message")
                results["detailed_analysis"]["spam_indicators"] = spam_indicators_found
    
        # Process Objects
        objects = []
        for obj in response.localized_object_annotations:
            objects.append({
                "name": obj.name,
                "score": obj.score,
                "bounding_box": [
                    {
                        "x": vertex.x,
                        "y": vertex.y
                    } for vertex in obj.bounding_poly.normalized_vertices
                ]
            })
        results["detected_objects"] = objects
    
        # Check for potentially concerning objects
        concerning_objects = ["Weapon", "Gun", "Knife", "Alcohol", "Cigarette", "Drug"]
        for obj in objects:
            if obj["name"] in concerning_objects and obj["score"] > 0.7:
                results["content_flags"].append(f"concerning_object:{obj['name']}")
        
        # NEW: Analyze faces for potential deepfake indicators
        if response.face_annotations:
            faces = response.face_annotations
            face_analysis = []
            
            deepfake_score = 0
            for i, face in enumerate(faces):
                face_data = {
                    "detection_confidence": face.detection_confidence,
                    "joy_likelihood": get_likelihood_name(face.joy_likelihood),
                    "sorrow_likelihood": get_likelihood_name(face.sorrow_likelihood),
                    "anger_likelihood": get_likelihood_name(face.anger_likelihood),
                    "surprise_likelihood": get_likelihood_name(face.surprise_likelihood),
                    "blurred_likelihood": get_likelihood_name(face.blurred_likelihood),
                    "headwear_likelihood": get_likelihood_name(face.headwear_likelihood)
                }
                
                # Check for inconsistencies that might indicate a deepfake
                # High detection confidence but high blur is suspicious
                if face.detection_confidence > 0.8 and likelihood_scores[face.blurred_likelihood] > 0.5:
                    deepfake_score += 0.2
                
                # Extreme emotion likelihood combinations can be suspicious
                if (likelihood_scores[face.joy_likelihood] > 0.7 and 
                    likelihood_scores[face.sorrow_likelihood] > 0.7):
                    deepfake_score += 0.3  # Contradictory emotions
                
                face_analysis.append(face_data)
            
            results["detailed_analysis"]["face_analysis"] = face_analysis
            
            # Check for unusual face attributes that might indicate manipulation
            if deepfake_score > 0.3:
                results["content_flags"].append("potential_deepfake")
                results["detailed_analysis"]["deepfake_score"] = deepfake_score
        
        # NEW: Check image labels for deepfake indicators
        deepfake_indicators_found = []
        for label in labels:
            if any(indicator in label["description"].lower() for indicator in self.deepfake_indicators) and label["score"] > 0.6:
                deepfake_indicators_found.append(label["description"])
        
        if deepfake_indicators_found:
            if "potential_deepfake" not in results["content_flags"]:
                results["content_flags"].append("potential_deepfake")
            results["detailed_analysis"]["deepfake_indicators"] = deepfake_indicators_found
            
        # NEW: Check for image manipulation using image properties
        if response.image_properties_annotation:
            colors = response.image_properties_annotation.dominant_colors.colors
            
            # Analyze color distribution for potential manipulation signs
            if len(colors) > 0:
                # Unusual color patterns can indicate manipulation
                color_scores = [color.score for color in colors]
                color_distribution_score = np.std(color_scores) if len(color_scores) > 1 else 0
                
                if color_distribution_score > 0.4:  # High variance in color distribution
                    if "potential_deepfake" not in results["content_flags"]:
                        results["content_flags"].append("potential_deepfake")
                    if "deepfake_indicators" not in results["detailed_analysis"]:
                        results["detailed_analysis"]["deepfake_indicators"] = []
                    results["detailed_analysis"]["deepfake_indicators"].append("unusual color distribution")
            
        # NEW: Check for hate symbols in objects and labels
        hate_symbol_locations = []
        for obj in objects:
            obj_name_lower = obj["name"].lower()
            for symbol, keywords in self.hate_symbols.items():
                if any(keyword.lower() in obj_name_lower for keyword in keywords):
                    if "hate_symbols" not in results["content_flags"]:
                        results["content_flags"].append("hate_symbols")
                    
                    # Store location for highlighting
                    hate_symbol_locations.append({
                        "symbol": symbol,
                        "bounding_box": obj["bounding_box"]
                    })
        
        if hate_symbol_locations:
            results["detailed_analysis"]["hate_symbol_locations"] = hate_symbol_locations
    
        # Determine overall safety
        if results["content_flags"]:
            # Check severity - Most severe concerns first
            if ("adult" in results["content_flags"] or 
                "violence" in results["content_flags"] or 
                "personal_info" in results["content_flags"]):
                results["overall_safety"] = "unsafe"
            elif ("racy" in results["content_flags"] or 
                 "concerning_object:Weapon" in results["content_flags"] or
                 "hate_symbols" in results["content_flags"] or
                 "potential_deepfake" in results["content_flags"]):
                results["overall_safety"] = "questionable"
            elif len(results["content_flags"]) > 2:  # Multiple minor flags
                results["overall_safety"] = "questionable"
            else:
                results["overall_safety"] = "potentially_concerning"
    
        results["suggested_action"] = self._get_recommended_action(results)
    
        return results
    
    def _get_recommended_action(self, results):
        """Determine recommended action based on analysis"""
        if results["overall_safety"] == "unsafe":
            return "block"
        elif results["overall_safety"] == "questionable":
            return "blur"
        elif results["overall_safety"] == "potentially_concerning":
            return "warn"
        else:
            return "allow"
    
    def _display_results(self, results, original_image, processed_image):
        """Display the results in the notebook with blurring for unsafe content"""
        # Calculate scaled dimensions for display (max height 500)
        max_height = 500
        aspect_ratio = original_image.width / original_image.height
    
        if original_image.height > max_height:
            display_height = max_height
            display_width = int(max_height * aspect_ratio)
        else:
            display_height = original_image.height
            display_width = original_image.width
    
        # Create figure with subplots
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, display_height/80))
    
        # Display original image
        ax1.imshow(original_image)
        ax1.set_title("Original Image")
        ax1.axis('off')
    
        # Display processed image with title based on safety score
        ax2.imshow(processed_image)
        if results["overall_safety"] == "unsafe":
            ax2.set_title("UNSAFE CONTENT DETECTED - BLURRED", color='red', fontweight='bold')
        elif results["overall_safety"] == "questionable":
            ax2.set_title("Questionable Content - Blurred", color='orange')
        elif results["overall_safety"] == "potentially_concerning":
            ax2.set_title("Potentially Concerning - Slightly Blurred", color='darkgoldenrod')
        else:
            ax2.set_title("No Issues Detected", color='green')
        ax2.axis('off')
    
        plt.tight_layout()
        plt.show()
    
        # Display text analysis
        display(HTML("<h3>Image Content Analysis Results</h3>"))
    
        # Create a styled HTML table for results
        css_style = """
        <style>
        .results-table {
            border-collapse: collapse;
            width: 100%;
            margin-bottom: 20px;
        }
        .results-table th, .results-table td {
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }
        .results-table tr:nth-child(even) {
            background-color: #f2f2f2;
        }
        .results-table th {
            padding-top: 12px;
            padding-bottom: 12px;
            background-color: #4CAF50;
            color: white;
        }
        .safe { color: green; font-weight: bold; }
        .questionable { color: orange; font-weight: bold; }
        .unsafe { color: red; font-weight: bold; }
        .flag-item { margin: 5px 0; padding: 3px 8px; border-radius: 3px; display: inline-block; margin-right: 5px; }
        .flag-adult { background-color: #ffcccc; }
        .flag-violence { background-color: #ffaaaa; }
        .flag-racy { background-color: #ffd8b1; }
        .flag-text { background-color: #ffffcc; }
        .flag-object { background-color: #e6ccff; }
        .flag-pii { background-color: #ff6666; }
        .flag-hate { background-color: #9370db; }
        .flag-deepfake { background-color: #ff4500; }
        .flag-spam { background-color: #ffa07a; }
        </style>
        """
    
        # Determine safety class for styling
        safety_class = ""
        if results["overall_safety"] == "safe":
            safety_class = "safe"
        elif results["overall_safety"] in ["potentially_concerning", "questionable"]:
            safety_class = "questionable"
        else:
            safety_class = "unsafe"
    
        # Create HTML content
        html_content = f"""
        <table class="results-table">
            <tr>
                <th colspan="2">Overview</th>
            </tr>
            <tr>
                <td>Source</td>
                <td>{results["source"]}</td>
            </tr>
            <tr>
                <td>Image Size</td>
                <td>{results["image_size"]}</td>
            </tr>
            <tr>
                <td>Overall Safety Rating</td>
                <td class="{safety_class}">{results["overall_safety"].upper().replace("_", " ")}</td>
            </tr>
            <tr>
                <td>Recommended Action</td>
                <td class="{safety_class}">{results["suggested_action"].upper()}</td>
            </tr>
        """
        
        # Add export path if available
        if "export_path" in results:
            html_content += f"""
            <tr>
                <td>Side-by-Side Export</td>
                <td>{results["export_path"]}</td>
            </tr>
            """
            
        html_content += "</table>"
    
        # Safe Search results
        html_content += """
        <table class="results-table">
            <tr>
                <th>Category</th>
                <th>Rating</th>
                <th>Confidence</th>
            </tr>
        """
    
        for category, data in results["safe_search"].items():
            score = data["score"]
            likelihood = data["likelihood"]
        
            # Determine cell color based on score
            cell_class = ""
            if score >= 0.7:
                cell_class = "unsafe"
            elif score >= 0.5:
                cell_class = "questionable"
            else:
                cell_class = "safe"
            
            html_content += f"""
            <tr>
                <td>{category.capitalize()}</td>
                <td class="{cell_class}">{likelihood}</td>
                <td>{score:.2f}</td>
            </tr>
            """
    
        html_content += "</table>"
    
        # Content flags
        if results["content_flags"]:
            html_content += """
            <table class="results-table">
                <tr>
                    <th>Content Flags</th>
                </tr>
                <tr>
                    <td>
            """
        
            for flag in results["content_flags"]:
                flag_class = ""
                if flag == "adult":
                    flag_class = "flag-adult"
                elif flag == "violence":
                    flag_class = "flag-violence"
                elif flag == "racy":
                    flag_class = "flag-racy"
                elif "text" in flag:
                    flag_class = "flag-text"
                elif "object" in flag:
                    flag_class = "flag-object"
                elif flag == "personal_info":
                    flag_class = "flag-pii"
                elif flag == "hate_symbols":
                    flag_class = "flag-hate"
                elif flag == "potential_deepfake":
                    flag_class = "flag-deepfake"
                elif flag == "spam_message":
                    flag_class = "flag-spam"
                
                html_content += f'<span class="flag-item {flag_class}">{flag.replace("_", " ").replace(":", ": ")}</span>'
        
            html_content += """
                    </td>
                </tr>
            </table>
            """
        
        # NEW: Display detailed analysis for special categories
        if results["detailed_analysis"]:
            # Format the detailed analysis into a nice HTML representation
            html_content += """
            <table class="results-table">
                <tr>
                    <th colspan="2">Detailed Analysis</th>
                </tr>
            """
            
            # PII detection
            if "personal_info" in results["detailed_analysis"]:
                html_content += """
                <tr>
                    <td>Personal Information</td>
                    <td>
                        <span class="flag-item flag-pii">PII DETECTED</span> 
                        Personal/financial information found in image
                    </td>
                </tr>
                """
                
            # Hate symbols
            if "hate_symbols_text" in results["detailed_analysis"]:
                symbols = ", ".join(results["detailed_analysis"]["hate_symbols_text"])
                html_content += f"""
                <tr>
                    <td>Hate Symbols</td>
                    <td>
                        <span class="flag-item flag-hate">DETECTED</span> 
                        Potential hate symbols: {symbols}
                    </td>
                </tr>
                """
                
            # Deepfake indicators
            if "deepfake_indicators" in results["detailed_analysis"]:
                indicators = ", ".join(results["detailed_analysis"]["deepfake_indicators"])
                score = results["detailed_analysis"].get("deepfake_score", "N/A")
                html_content += f"""
                <tr>
                    <td>Potential Deepfake</td>
                    <td>
                        <span class="flag-item flag-deepfake">SUSPICIOUS</span> 
                        Score: {score}<br>
                        Indicators: {indicators}
                    </td>
                </tr>
                """
                
            # Spam indicators
            if "spam_indicators" in results["detailed_analysis"]:
                indicators = ", ".join(results["detailed_analysis"]["spam_indicators"])
                html_content += f"""
                <tr>
                    <td>Spam/Scam Content</td>
                    <td>
                        <span class="flag-item flag-spam">SUSPICIOUS</span> 
                        Spam indicators: {indicators}
                    </td>
                </tr>
                """
                
            html_content += "</table>"
    
        # Text content
        if results["text_content"]:
            # Fix: Store the replacement result separately to avoid using \n in f-string
            escaped_text = results["text_content"].replace("\n", "<br>")
            
            html_content += f"""
            <table class="results-table">
            <tr>
                <th>Detected Text</th>
            </tr>
            <tr>
                <td>{escaped_text}</td>
            </tr>
            </table>
            """
    
        # Display the HTML (combine the style and content)
        display(HTML(css_style + html_content))
    
        # Print labels in a compact way
        if results["labels"]:
            print("\nImage Labels:")
            labels_text = ", ".join([f"{label['description']} ({label['score']:.2f})" for label in results["labels"]])
            print(labels_text)


# Example Usage Function
def analyze_image_interactive():
    """Interactive function to analyze images from various sources"""
    try:
        filter = ImageContentFilter()
        
        print("Enhanced Image Content Filter")
        print("=============================================")
        print("Choose an input method:")
        print("1. Local file path")
        print("2. Image URL")
        
        choice = input("Enter your choice (1-2): ")
        
        try:
            if choice == "1":
                path = input("Enter the path to your local image file: ")
                results = filter.analyze_image(image_path=path, export_comparison=True)
                
            elif choice == "2":
                url = input("Enter the image URL: ")
                results = filter.analyze_image(image_url=url, export_comparison=True)
            else:
                print("Invalid choice, please run again.")
                return
            
            # Let user know about the side-by-side export
            img_expo = input("Export the image comparison? (0=no/1=yes): ")
            if img_expo == "1":
                if "export_path" in results:
                    print(f"\nSide-by-side comparison exported to: {results['export_path']}")
            
            # Export results to JSON if desired
            export = input("Export analysis results to JSON file? (y/n): ")
            if export.lower() == 'y':
                output_file = f"content_filter_results_{results['overall_safety']}{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.json"
                with open(output_file, 'w') as f:
                    json.dump(results, f, indent=2)
                print(f"Analysis results exported to {output_file}")
                
        except ValueError as e:
            print(f"Error: {str(e)}")
            logger.error(f"Value error: {str(e)}")
        except Exception as e:
            print(f"Unexpected error analyzing image: {str(e)}")
            logger.exception("Error in analysis")
    
    except Exception as e:
        print(f"Failed to initialize the content filter: {str(e)}")
        logger.exception("Fatal error in content filter")
        
# Run the interactive function
if _name_ == "_main_":
    analyze_image_interactive()