'''
pdf2text class:
This class has all the functions pertaining conversion of an image or pdf file to text. 
The following functions are included in the class: pdf to image conversion, text extraction and orientation correction.

'''
from pdf2image import convert_from_bytes
from os import remove
import tempfile
import math
import os
import re
import io
from numpy import mean, array
import numpy as np
import subprocess
import cv2
from PIL import Image
from typing import IO
import random
import string
import pytesseract
from skimage.transform import radon, resize,rotate
from pytesseract import Output
import imutils
import magic
import logging
from paddleocr import PaddleOCR
import fitz
from skimage.color import rgb2gray
from skimage.transform import (hough_line, hough_line_peaks)
from scipy.stats import mode
from skimage.filters import threshold_otsu, sobel
import time
import concurrent.futures
from tqdm import tqdm
from OCRService import *
import base64
from io import BytesIO
from deskew import determine_skew
from log_exec_times import log_execution_time
#from conf_parse import PADDLEOCR_URL
from rapidfuzz import process,utils,fuzz

class pdf2text:
    
    '''
    Orientation Detection and Correction Algorithm
    
    Algorithm thresholds the image before using sobel filter to get the edges in the image.
    The edges are then converted to hough lines.
    The mode of the peak of hough line angles is the orientation of the image.
    pytesseract is used to detect a 180 degree offset, and the offset is corrected.

    '''
    @log_execution_time
    def image_odc(img : Image):
        image = np.array(img)
        image = image[:,:,:3]

        image       = rgb2gray(image)
        threshold   = threshold_otsu(image)
        bin_image   = image < threshold

        image_edges = sobel(bin_image)
       
        h, theta, d = hough_line(image_edges)
        _,angles,_  = hough_line_peaks(h, theta, d)
        angle       = np.rad2deg(mode(angles)[0])
        
        if angle < 0:
            angle  = 90 - abs(angle)

        rot_image = img.rotate(angle, resample = Image.Resampling.BICUBIC, expand=True)
        filename = ''.join(random.choices(string.ascii_lowercase+string.digits,k=9))
        rot_image.save(f'{filename}.png')

        image = cv2.imread(f'{filename}.png')
        remove(f'{filename}.png')
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 199, 5)

        osd_data = pytesseract.image_to_osd(gray, output_type=pytesseract.Output.DICT)
        
        if osd_data['rotate'] == 0:
            return rot_image 
        else:
            return rot_image.rotate(-osd_data['rotate'], resample = Image.Resampling.BICUBIC, expand=True)


    '''
    File Binary to Image Conversion

    Firstly, file type is detected.
    If the file is an invoice and PDF type, the function checks for selectable text,
    and returns the text.
    In the case of non selectable text, pdf2image library is used to get a list of Image objects is returned.
    If the file is an image, then a single element Image object list is returned  
    
    '''
    @log_execution_time
    def to_image(file_bytes : IO, isInvoice=False):
        mime = magic.Magic(mime=True)
        fileType = mime.from_buffer(file_bytes).split('/')[-1]

        if (fileType.lower() == 'pdf'):
            if isInvoice:
                text_list = pdf2text.scan_pdf(file_bytes)
                if text_list:
                    return text_list
            
            return convert_from_bytes(file_bytes)
        
        try:
            fileName = ''.join(random.choices(string.ascii_lowercase+string.digits,k=9))
            fileName = fileName+'.'+fileType
            
            with open(fileName,'wb') as image_file:
                image_file.write(file_bytes)
                image_file.close()
            image = cv2.imread(fileName)
            image = Image.fromarray(image)
            remove(fileName)
            return [image]
        
        except Exception as e:
            raise e

    def paddle_ocr(image:Image, lang='en'):
        payload = {'include_scores':True}
        files = []
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        buffered.seek(0)
        files.append(('files', (f'image_1.png', buffered, 'image/png')))
        response = requests.post(url=PADDLEOCR_URL, data=payload,files=files)
        paddle_result = response.json()["image_1.png"]
        return [paddle_result[0],paddle_result[2]]
        # ocr = PaddleOCR(use_gpu=False,lang=lang)
        # results = ocr.ocr(np.array(image), cls=False)[0]
        # txts    = [line[1][0] for line in results]
        # cord    = [line[0] for line in results]
        # return [txts, cord]   
    
    '''
    Tesseract OCR in combination openCV image binarization for params as instances of PIL.Image.Image class
    
    Returns the text contained within the given parameter

    '''
    def to_text(image_list, lang = 'eng'):
        if isinstance(image_list[0], Image.Image):
            results = []
            with concurrent.futures.ThreadPoolExecutor() as executor:
                mod_iamge_list_results = executor.map(pdf2text.image_to_b64, image_list)
                mod_image_list = list(tqdm(mod_iamge_list_results, total=len(image_list), desc="Preprocessing Images")) 

            with concurrent.futures.ThreadPoolExecutor() as executor:
                results_list = executor.map(pdf2text.call_open_ocr, mod_image_list)
                results = list(tqdm(results_list, total=len(mod_image_list), desc='OCR Progress'))
            # print(results)
            return results
        
        elif isinstance(image_list[0], str):
            return image_list
        
        else:
            raise TypeError('to_text() function only accepts string and Image objects.')
    

    '''
    Paddle OCR in combination with various oreintation detection algorithms

    Returns a 2D list of text blocks and respective scores

    '''

    @log_execution_time
    def to_text_with_paddle(image:Image,lang='en',doc_type=""):

        doc_type = doc_type.lower()

        rotation_categories = {"ie", "pan","cheque"}
        odc_categories = {"gst", "msme"}

        image_rescaled = pdf2text.rescale_image(image=image)

        if doc_type in rotation_categories:
            # image.save("before_rotate_scaled.png")
            image_rescaled = pdf2text.align_document(image_rescaled)
            # image_rescaled.save("after_rotate.png")

        elif doc_type in odc_categories:  
            image_array = np.array(image_rescaled)
            
            # Convert to grayscale if image is RGB
            if len(image_array.shape) == 3:
                grayscale = np.mean(image_array, axis=2).astype(np.uint8)
            else:
                grayscale = image_array
                
            angle = determine_skew(grayscale,angle_pm_90=True) 
            
            if int(abs(angle)) not in range(0,6):
                image_rescaled = pdf2text.image_odc(image_rescaled)

        try:
            payload = {'include_scores':True,'convert_coords': True}
            files = []
            buffered = BytesIO()
            image_rescaled.save(buffered, format="PNG")
            buffered.seek(0)
            print(1)
            files.append(('files', (f'image_1.png', buffered, 'image/png')))
            response = requests.post(url=PADDLEOCR_URL, data=payload, files=files)
            print(2)
            print(response)
            paddle_result = response.json()["image_1.png"]
            print(paddle_result)
            processed_result = pdf2text.process_paddle_result(doc_type, paddle_result)
            return processed_result if doc_type != "cheque" else (processed_result,image_rescaled)
        
        except Exception as e:
            error_message = "OCR text extraction failed"
            raise Exception(error_message)
        
        
        
    ##############################################################
    ##################      HELPER FUNCTIONS    ##################
    ##############################################################
    '''
    Convert image to base64 after preprocessing
    '''
    def image_to_b64(image):
        _, image    = cv2.threshold(np.array(image), 145, 255, cv2.THRESH_BINARY)
        _, buffer   = cv2.imencode('.tiff', image)
        image_bytes =buffer.tobytes()
        image_b64   = (base64.b64encode(image_bytes)).decode('utf-8')
        return image_b64
        
    
    '''
    PAAS for open-ocr
    '''
    def call_open_ocr(image_base64):
        open_ocr_caller = OCRService()
        return '\n'.join(line for line in open_ocr_caller.get_ocr_text(image_base64).split('\n') if line.rstrip())

    '''
    Extraction of selectable pdf text using the fitz library.
    
    '''
    def scan_pdf(file_bin : IO):
        
        doc = fitz.open(filetype='pdf', stream=file_bin)
        text_list = []

        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            text = page.get_text()
            if text:
                text_list.append(text)
            else:
                return None
    
        return text_list
   

    '''
    get_rotation() helper function to get the root mean square of an Image array
    
    '''
    def rms_flat(a):
        return np.sqrt(np.mean(np.abs(a)**2))
    

    '''
    rotate_image() helper function to get the orientation of an image

    '''
    @log_execution_time
    def get_rotation(image):
        # Compute the Radon transform for angles from 0 to 180 degrees
        sinogram = radon(image,circle=True)
        # Compute RMS for each projection
        rms_values = np.array([pdf2text.rms_flat(line) for line in sinogram.T])

        # Find the mode of the RMS values
        # Find the angle corresponding to the mode value
        rotation = int(np.argmax(rms_values))

        if rotation < 90:
            return 90 + rotation
        elif 90<=rotation<180:
            return rotation - 90
        return rotation
        

    '''
    rotate_image() helper function to adjust the threshold of binarization.

    '''
    def tess_osd(image : Image):   
        img_arr = np.array(image)
        
        img_arr_gry = cv2.cvtColor(img_arr, cv2.COLOR_BGR2GRAY)

        
        blurred = cv2.GaussianBlur(img_arr_gry, (7, 7), 0)
        
        
        thresh_img_arr    = cv2.adaptiveThreshold(img_arr_gry, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 21, 4)
        
        thresh_img_obj      = Image.fromarray(thresh_img_arr)
        
        try:
            rot_data = pytesseract.image_to_osd(thresh_img_obj, lang='eng', output_type = Output.DICT)
            
        except Exception as e:
            raise e

        return rot_data['rotate']
    '''
    helper function of text_to_paddle() to get the orientation of PAN cards.

    '''
    @log_execution_time
    def rotate_image(image : Image, resize_factor=2):
        image_temp = rgb2gray(image)
        image_resized = resize(image_temp, (image_temp.shape[0]//resize_factor, image_temp.shape[1]//resize_factor), anti_aliasing=True)
        oreintation_angle = pdf2text.get_rotation(image_resized)
        rot_img = image.rotate(-oreintation_angle,fillcolor=255, expand=True)
        

        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as temp_file:
            temp_file_name = temp_file.name
            rot_img.save(temp_file_name)
        
            # Command to run Tesseract with specified parameters
            command = ['tesseract', temp_file_name, 'stdout', '--psm', '0']

            try:
                # Run the subprocess and capture the output
                result = subprocess.run(command, capture_output=True, text=True, check=True)
                # Output is in the standard output; parse the angle from it
                output = result.stdout

                # Extract the angle from the output
                for line in output.splitlines():
                    if 'Rotate' in line:
                        final_orientation = float(line.split(':')[-1].strip())
                        print(oreintation_angle,final_orientation)

                        if final_orientation != 0:
                            image = image.rotate(-oreintation_angle, fillcolor=255, expand=True)
                            image = image.rotate(-final_orientation, fillcolor=255, expand=True)
                            # image.save("after_rotate.png")
                            return image

                        image = image.rotate(-oreintation_angle, fillcolor=255, expand=True)
                        # image.save("after_rotate.png")
                        return image
            
            except subprocess.CalledProcessError as e:
                print(f"Error calling Tesseract: {e}")
                return image
            finally:
                # Remove the temporary file
                os.remove(temp_file_name)

    def make_image_0_degrees(rotated_pil,rotated):

        import tempfile,subprocess,os

        with tempfile.NamedTemporaryFile(suffix='.png', delete=True) as temp_file:
            try:
                temp_file_name = temp_file.name
                # from PIL import ImageOps
                # rotated_pil=ImageOps.autocontrast(rotated_pil)
                rotated_pil.save(temp_file_name)
                rotated_pil.save("midway.png")

                # ocr_result = pytesseract.image_to_osd(rotated_pil)
                # print("pytesseract ods =",ocr_result)

                from tesserocr import PyTessBaseAPI, PSM
                print("here")
                with PyTessBaseAPI(psm=PSM.OSD_ONLY) as api:
                    print("in tesserocr")
                    api.SetImageFile(temp_file_name)

                    os = api.DetectOS()
                    print("Orientation: {orientation}\nOrientation confidence: {oconfidence}\n""Script: {script}\nScript confidence: {sconfidence}".format(**os))

                print("here too")
                # Command to run Tesseract with specified parameters
                command = ['tesseract', temp_file_name, 'stdout', '--psm', '0','--oem', '0' '-c', 'min_characters_to_try=50']
                # Run the subprocess and capture the output
                result = subprocess.run(command, capture_output=True, text=True, check=True)

                output = result.stdout
                print(output)

                import re
                match = re.search(r'Rotate:\s+(\d+)', output)
                if match:
                    angle_to_be_rotated = int(match.group(1))

                if angle_to_be_rotated == 180:
                    final_rotated = rotate(rotated, angle_to_be_rotated, mode='constant', cval=255, preserve_range=True, resize=True)
                    final_rotated_img = Image.fromarray(final_rotated.astype(np.uint8))
                    return final_rotated_img,final_rotated

            except subprocess.CalledProcessError as e:
                print(f"Error calling Tesseract: {e}")

        return rotated_pil,rotated

    @log_execution_time
    def align_document(image: Image.Image) -> Image.Image:
        """
        Align the document by detecting edges and correcting perspective.
        Returns original image if no clear document contour is found.
        
        Args:
            image: Input PIL Image
            
        Returns:
            Aligned PIL Image or original image if alignment fails
        """
        try:
            # Convert PIL Image to numpy array
            image_array = np.array(image)
            
            # Convert to grayscale if image is RGB
            if len(image_array.shape) == 3:
                grayscale = np.mean(image_array, axis=2).astype(np.uint8)
            else:
                grayscale = image_array
                
            start=time.perf_counter()
            angle = determine_skew(grayscale,angle_pm_90=True)
            print("Angle=",angle)
            print(time.perf_counter()-start,"seconds")

            if int(abs(angle)) not in range(0,6):
                print("rotating the image...")
                rotated_array = rotate(image_array, int(angle), mode='constant', cval=255, preserve_range=True,resize=True)

                rotated = rotated_array.astype(np.uint8)
                rotated_pil = Image.fromarray(rotated)
                return rotated_pil

            # NOTE: This is the tesseract logic
            # final_rotated_img,final_rotated = pdf2text.make_image_0_degrees(rotated_pil,rotated)
            # final_rotated_img.save("tess_output.png")

            # if len(final_rotated.shape) == 3:
            #     rotated_pil_final = Image.fromarray(final_rotated_img, 'RGB')
            # else:
            #     rotated_pil_final = Image.fromarray(final_rotated_img, 'L')
            # return rotated_pil_final

            # return original image if rotation is not required
            return image
            
        except Exception as e:
            print("Exception got called")
            return rotated_pil
    
    
    # 'To validate whether the given file is an invoice or not'
    def valid(data, img):
        from async_invoice import async_invoice
                
        found = False

        qi = []
        di = []
        if not found:
            width, height = img.size
            height = height * 0.2
            # print("..................................",height)

            actual_height = 0

            for co, i in enumerate(data[0]):
                # print(i.lower())
                if 'invoice' in i.lower():
                    # print("data...............", i)
                    # print("...........................",data[1][co])
                    actual_height = data[1][co][0][1]
                    break
            # print('act...................', actual_height)
            # print('he................', height)
            if actual_height < height and actual_height != 0:
                found = True
            
        if not found:
            for i in data[0]:
                if 'description' in i.lower() or 'particulars' in i.lower() or 'item' in i.lower():
                    ind = data[0].index(i)
                    di.append(data[1][ind][0])

                if 'qty' in i.lower() or  'quantity' in i.lower() or 'hsn' in i.lower() or 'amount' in i.lower():
                    ind = data[0].index(i)
                    qi.append(data[1][ind][0])

            threshold_x = 1500
            threshold_y = 20  # You mentioned "less than then" which might be a typo, assuming it's less than 0.

            for point1 in qi:  # Accessing the first list
                for point2 in di:  # Accessing the second list
                    diff_x = point1[0] - point2[0]
                    diff_y = abs(point1[1] - point2[1])
                    if diff_x < threshold_x and diff_y < threshold_y:
                        found = True
                        break
        
        return found
    
    def arr(co):
        # Convert coordinates to numpy array of shape (n, 1, 2)
        pts = np.array(co, dtype=np.int32).reshape((-1, 1, 2))
        # Get bounding rectangle
        x, y, w, h = cv2.boundingRect(pts)
        return w

    def Pan_Valid(txt,box):
        data = []
        check_point1 = ''
        check_point2 = ''
        # print(txt)
        for count, i in enumerate(txt):
            if 'income' in i.lower() or 'department' in i.lower():
                check_point1 = box[count]
            elif 'india' in i.lower() or 'govt' in i.lower():
                check_point2 = box[count]
            if check_point2 != '' and check_point1 != '':
                break
        if check_point2 != '' and check_point1 != '':
            check_point1 = pdf2text.arr(check_point1)
            check_point2 = pdf2text.arr(check_point2)
            check_point1 = check_point1 * 100 / (check_point1 * 2.85)
            check_point2 = check_point2 * 100 / (check_point2 * 3.33)
            check = (check_point1 * 2.85) - (check_point2 + check_point1)
            # print(check)
            if 28 < check < 45:
                return True
            else:
                return False
        elif check_point2 == '' or check_point1 == '':
                return False

    @log_execution_time
    def rescale_image(image:Image.Image, max_width=1200, max_height=1800):

        original_width, original_height = image.size

        if original_width > max_width or original_height > max_height:
            # Determine scaling factor based on thresholds
            width_scale = max_width / original_width
            height_scale = max_height / original_height
            scale_factor = min(width_scale, height_scale)

            new_width = int(original_width * scale_factor)
            new_height = int(original_height * scale_factor)

            image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        return image
    
    @log_execution_time
    def process_paddle_result(doc_type, paddle_result):

        if doc_type == "pan" and len(paddle_result[0]) < 34:
            result = process.extractOne("INCOME TAX DEPARTMENT", paddle_result[0], scorer=fuzz.ratio, processor=utils.default_process,score_cutoff=70)
            if not (result and result[2] in range(5)):
                return paddle_result[0][::-1], paddle_result[1][::-1], paddle_result[2][::-1]

        txts, scores, boxes = paddle_result[0], paddle_result[1], paddle_result[2]
        return [txts, scores, boxes]
    