from typing import IO
from pdf2text import *
import re
from time import perf_counter
from rapidfuzz import fuzz,process,utils
from typing import List
from fastapi.responses import JSONResponse
from conf_parse import api_key
from prompts import ie_prompt
from llm_gemini_img import GeminiImageProcessor
from db_store import save_file
from datetime import datetime
import threading

class IECPaddle:

    def __init__(self, file:IO, file_name:str):
        self.filebin = file
        self.file_name = file_name
        self.IE_data = {'docNo':'','docDate':'','docScore':0}
        self.ocr_time = 0 

    def validate_file(self,ocr_text:List[str]):
        common_words = [
            "ministryofcommerceandindustry",
            "governmentofindia",
            "certificateofimporterexportercode",
            "dateofissue",
            "iecnumber"
        ]

        stripped_text = [word.replace(" ", "").strip().lower() for word in ocr_text]
        match_count = 0
        threshold = 70

        for word in common_words:
            result = process.extractOne(word, stripped_text, scorer=fuzz.ratio, processor=utils.default_process)
            if result:
                match_score = result[1]
                print(f"Word: {word}, Best Match: {result[0]}, Score: {match_score}")
                if match_score >= threshold:
                    match_count += 1

        print("Number of matching words:", match_count)

        return match_count >= len(common_words) // 2
       
    def loadIE(self):
        image = pdf2text.to_image(self.filebin)[0]
        width, height = image.size
        max_width,max_height=786,1568
        if width > max_width or height > max_height:
            scale_factor = round(min(max_width / width, max_height / height),2)
            new_size = (int(width * scale_factor), int(height * scale_factor))
            image = image.resize(new_size, Image.Resampling.LANCZOS)

        start_time = perf_counter()
        paddle_output = pdf2text.to_text_with_paddle(image.convert('RGB'), doc_type="ie")

        if not self.validate_file(paddle_output[0]):
            return JSONResponse(status_code=400, content={"status": "uncool", "message": "Invalid document type. Please upload a valid IE file"})
        
        txt_list = paddle_output[0]
        score_list = paddle_output[1]
        self.ocr_time = perf_counter() - start_time
        datePattern = re.compile(r'^(0[1-9]|[12][0-9]|3[01])(0[1-9]|1[0-2])(194[7-9]|19[5-9][0-9]|20[0-5][0-9]|2060)$')
        iec_pattern = r'[0-9]{10}|[A-Z]{5}\d{4}[A-Z]'
        numScore = 0
        dateScore = 0
        found_doc_no=False

        for i,block in enumerate(txt_list):
            if re.search(iec_pattern,block):
                if not found_doc_no:
                    self.IE_data['docNo'] = re.search(iec_pattern, block).group()
                    numScore = score_list[i]
                    found_doc_no=True

            cleaned_block = re.sub(r'[. /]', '', block)

            # Search for the date pattern
            match = datePattern.search(cleaned_block)

            if match:
                date = match.group()
            # Ensure that the date string is in the expected format
            # TODO: Fix hardcoded date format resolution
                if len(date) == 8:
                    self.IE_data['docDate'] = f"{date[:2]}/{date[2:4]}/{date[4:]}"
                    dateScore = float(score_list[i])
                    break
        # if numScore == 0 and dateScore == 0:
        #     raise TypeError('Ensure correct file type is uploaded.')
            
        docScore = ((numScore+dateScore)/2.0)*100.0
        self.IE_data['docScore'] = round(docScore,2)

        # checking whether we have all the fields or not
        result  = self.result_validator(self.IE_data)
        if not result:
            processor = GeminiImageProcessor(api_key)
            llm_response = processor.process_images([image], ie_prompt,["docNo","docDate"])
            llm_response['docScore'] = round(docScore,2)
            file_name_with_timestamp = f"{datetime.now().strftime('%d%m%Y_%H%M%S')}_{self.file_name}"
            threading.Thread(target=save_file,args=(self.filebin,file_name_with_timestamp)).start()
            self.IE_data = llm_response if llm_response is not {} else self.IE_data

        return self.IE_data

    def result_validator(self, IE_data):
        if IE_data.get("docNo") and IE_data.get("docDate"):
            return True
        return False