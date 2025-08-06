from typing import IO
from pdf2text import pdf2text
from async_invoice import async_invoice
import Levenshtein
import re
from datetime import datetime
from paddleocr import PaddleOCR
import pytesseract
import time
from tqdm import tqdm  # For progress bar
from pytesseract import Output
from PIL import Image
import concurrent.futures
from fuzzywuzzy import fuzz


class BoundingBox:

    def __init__(self, invoice : IO):
        self.invoice = invoice
        self.CO = {
                'Vendor':'',
                'Vendor GSTIN':'',
                'Client':'',
                'Client GSTIN':'',
                'Invoice Number':'',
                'Invoice Date':'',
                'IRN':'',
                'Purchase Order Number':'',
                'E-way Bill Number':'',
                'ACK Date':'',
                'ACK Number':'',     
            }
        
    def place(self, txt, cord):
        co = []
        # Pages = async_invoice.Bounding
        keys_of_interest = ["Vendor", "Vendor GSTIN", "Client", "Client GSTIN", "Invoice Number", "Invoice Date", "IRN", "Purchase Order Number", "E-way Bill Number", "ACK Date", "ACK Number"]
        # Extract values
        values = [self.invoice.get(key, "Not Found").lower() for key in keys_of_interest]
        # print(values)
        dates = BoundingBox.format_date(values[5])
        dates1 = BoundingBox.format_date(values[9])
        page0_co = cord
        page0_txt = txt
        # print(page0_txt)
        # print(page0_co)
        txt_list = [x.lower() for x in page0_txt]

        for j, value in enumerate(values):

            for i, data in enumerate(txt_list):

                if (value.replace(' ','') in data.replace(' ','')) and value.replace(' ','') != 'na' and value != '':
                    
                    index = txt_list.index(data)
                    co.append([1,page0_co[index]])
                    break
                elif i == (len(txt_list)-1):
                    co.append("NOT FOUND")

                elif j == 6 and  (value[:10].replace(' ','') in data.replace(' ','')) and (value.replace(' ','') != 'na') and value != '':
                    index = txt_list.index(data)
                    co.append([1,page0_co[index]])
                    break


                elif j == 5 and len(dates) > 1 and dates[0] != '':
                    a = len(co)
                    for dt in dates:
                        if dt in data.replace(' ',''):
                            index = txt_list.index(data)
                            co.append([1,page0_co[index]])
                            break
                    b = len(co)
                    if b > a:
                        break
                    
                       
                elif j == 9 and len(dates1) > 1 and dates1[0] != '':
                    c = len(co)
                    for dt in dates1:
                        if dt in data.replace(' ',''):
                            index = txt_list.index(data)
                            co.append([1,page0_co[index]])
                            break
                    d = len(co)
                    if d > c:
                        break
                    

                

        keys = list(self.CO.keys())
        dates1 = []
        dates = []
        # Loop through the values of co and assign them to the keys of CO
        for i in range(min(len(co), len(keys))):
            self.CO[keys[i]] = co[i]


        return self.CO

    def format_date(date):
        date1 = date2 = date3 = date4 = date5 = date6 = ''
        pattern = re.compile(r'\d{1,2}-[a-z]{3}-\d{2,4}')
        if pattern.search(date):
            date   = pattern.search(date).group()
            date_obj = datetime.strptime(date, '%d-%b-%y')
            date = str(date_obj.strftime('%d-%m-%y'))

        if '/' in date:
            date = date.replace('/','-')
        if date.replace(' ','') != 'na' and date.replace(' ','') != '':
            date1 = date.replace(' ','')
            date2 = date1.replace('-','/')
            input_format = "NA"
            # Identify the input format
            if len(date1) == 10:  # Format like "01-04-2023"
                input_format = "%d-%m-%Y"
            elif len(date1) == 8:  # Format like "01-04-23"
                input_format = "%d-%m-%y"
            if input_format != "NA":
                # Parse the date string into a datetime object
                date_obj = datetime.strptime(date1, input_format)
        
                # Convert to the second desired format: "01-Apr-2024" or "01-Apr-24"
                date3 = date_obj.strftime("%d-%b-%y") if len(date1) == 8 else date_obj.strftime("%d-%b-%Y")
                if date3[0] == '0':
                    date3 = date3[1:]
                date3 = date3.lower()
                if date3[-4:-2] == '20':
                    date4 = date3[: -4] + date3[-2:]
                if date1[0] == '0' and date2[0] == '0':
                    date5 = date1[1:]
                    date6 = date2[1:]
                    date5 = date5.replace('-0', '-')
                    date6 = date6.replace('/0', '/')
                    if date5[-4:-2] == '20' and date6[-4:-2] == '20':
                        date5 = date5[: -4] + date5[-2:]
                        date6 = date6[: -4] + date6[-2:]
            
        return [date1, date2, date3, date4, date5, date6]





    # For line items
    def line_items_co(self, image_list):
        co = []
        data_co = []
        if not isinstance(image_list[0], str):
            with concurrent.futures.ThreadPoolExecutor() as executor:
                for image in tqdm(executor.map(BoundingBox.extract_bounding_boxes, image_list), total=len(image_list), desc='Tesseract ocr coordinates'):
                    data_co.append(image)
        else:
            pass

        # Extracting "Item Description" from all Line Items
        item_descriptions_invoice = [item["Item Description"] for item in self.invoice["Line Items"]]
        # print(item_descriptions_invoice)
        # print(data_co)

        for j, value in enumerate(item_descriptions_invoice):
            for num, page in enumerate(data_co):
                for i, data in enumerate(page[0]):
                    similarity_ratio = fuzz.partial_ratio(data.lower(), value.lower())
                    if similarity_ratio > 70:    
                        index = page[0].index(data)
                        # print("........................",value ,"...............", data,"...........", num, page[1][index])
                        co.append([num, page[1][index]])
                        break
                        
                    elif i == (len(page[0])-1):
                        co.append("NOT FOUND")

        # print(co)
        return co




    def extract_bounding_boxes(image):

        # Get the OCR data with bounding box information
        data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
        # print('........................................')
        # Initialize lists for storing lines and their bounding boxes
        lines = []
        bounding_boxes = []
        current_line = []
        prev_line_num = None

        for i in range(len(data['text'])):
            if data['text'][i].strip():  # Ignore empty text
                line_num = data['line_num'][i]
                
                # If the line number changes, save the previous line's data
                if line_num != prev_line_num and current_line:
                    # Collect text for the current line
                    line_text = " ".join([word['text'] for word in current_line])
                    lines.append(line_text)
                    
                    # Calculate the bounding box for the current line
                    left = min([word['left'] for word in current_line])
                    top = min([word['top'] for word in current_line])
                    right = max([word['left'] + word['width'] for word in current_line])
                    bottom = max([word['top'] + word['height'] for word in current_line])
                    bounding_boxes.append((left, top, right, bottom))
                    
                    # Clear current line data for the next one
                    current_line = []
                
                # Add the word's bounding box to the current line
                current_line.append({
                    'text': data['text'][i],
                    'left': data['left'][i],
                    'top': data['top'][i],
                    'width': data['width'][i],
                    'height': data['height'][i]
                })
                
                prev_line_num = line_num
        
        # Add the last line's data if not empty
        if current_line:
            line_text = " ".join([word['text'] for word in current_line])
            lines.append(line_text)
            
            left = min([word['left'] for word in current_line])
            top = min([word['top'] for word in current_line])
            right = max([word['left'] + word['width'] for word in current_line])
            bottom = max([word['top'] + word['height'] for word in current_line])
            bounding_boxes.append((left, top, right, bottom))

        return [lines, bounding_boxes]


















    # def extract_text_and_coordinates(image, confidence_threshold=60):
   
    #     st = time.time()
    #     # Perform OCR and get positional data
    #     data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
    
    #     # Extract text and coordinates
    #     text_list = []
    #     coordinates_list = []

    #     for i in range(len(data['text'])):
    #         if int(data['conf'][i]) > 0:  # Filter out low-confidence results
    #             text_list.append(data['text'][i])
    #             x = data['left'][i]
    #             y = data['top'][i]
    #             w = data['width'][i]
    #             h = data['height'][i]
    #             coordinates_list.append((x, y, w, h))

    #     et = time.time()

    #     return [text_list, coordinates_list]


  




