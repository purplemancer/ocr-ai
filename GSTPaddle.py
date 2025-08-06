from typing import IO
from pdf2text import *
from gstin import *
import re
from time import perf_counter
from rapidfuzz import fuzz,process,utils
from typing import List
from fastapi.responses import JSONResponse
from conf_parse import api_key
from prompts import gst_prompt
from llm_gemini_img import GeminiImageProcessor
from db_store import save_file
from datetime import datetime


class GSTPaddle:

    def __init__(self, filebin:IO,file_name:str):
        self.filebin = filebin
        self.file_name = file_name
        self.GST_form = {
            'docName':'',
            'docNo':'',
            'docAddress':'',
            'docScore':''
        }
        self.ocr_time = 0

    def validate_file(self,ocr_text:List[str]):
        common_words = [
            "registrationcertificate",
            "registrationnumber",
            "dateofliability",
            "dateofvalidity",
            "governmentofindia",
            "formgstreg"
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
    
    def loadGST(self):
        images = pdf2text.to_image(self.filebin)
        start_time = perf_counter()
        paddle_output = pdf2text.to_text_with_paddle(images[0].convert('RGB'),doc_type="gst")
        if not self.validate_file(paddle_output[0]):
            return JSONResponse(status_code=400, content={"status": "uncool", "message": "Invalid document type. Please upload a valid GST file"})
        txt_list = paddle_output[0]
        score_list = paddle_output[1]
        self.ocr_time = perf_counter() - start_time
        in_address_block = False
        pattern = re.compile(r'\d{6}')

        nameScore = 0
        numScore = 0
        addScore = 0
        docScore = 0

        for i, block in enumerate(txt_list):

            if 'legalname' in block.lower().replace(' ',''):
                if len(txt_list[i+1]) < 3:
                    self.GST_form['docName'] = txt_list[i+2]
                    nameScore = float(score_list[i+2])
                else:
                    self.GST_form['docName'] = txt_list[i+1]
                    nameScore = float(score_list[i+1])
                
            if 'registrationnumber' in block.lower().replace(' ',''):
                match = re.search(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[12]{1}[Z]{1}[A-Z0-9]{1}", block)
                if match:
                    self.GST_form['docNo'] = match.group()
                else:
                    # self.GST_form['docNo'] = GSTIN.validate(block[-15:])
                    self.GST_form['docNo'] = GSTIN.ocr_gstin_corrector(block[-15:])
                    numScore = float(score_list[i])

            if in_address_block:
                if block.lower().replace(' ','') == 'business':
                    continue 
                self.GST_form['docAddress'] += block.replace('\n','')
                if pattern.search(block) or 'date' in block.lower().replace(' ',''):
                    break

            if in_address_block:
                addScore += float(score_list[i+1])

            elif 'addressofprincipalplaceof' in block.lower().replace(' ',''):
                in_address_block = True
                addScore += float(score_list[i+1])
        
        addScore = addScore/3

        # if addScore == 0 and numScore == 0 and nameScore == 0:
        #     raise TypeError('Ensure correct file type.')

        docScore = round(((nameScore+numScore+addScore)/3.0)*100.0,2)
        self.GST_form['docScore'] = docScore

        # checking whether we have all the fields or not
        result  = self.result_validator(self.GST_form)
        if not result:
            processor = GeminiImageProcessor(api_key)
            llm_response = processor.process_images([images[0]], gst_prompt,["docName","docNo","docAddress"])
            llm_response['docScore'] = round(docScore,2)
            file_name_with_timestamp = f"{datetime.now().strftime('%d%m%Y_%H%M%S')}_{self.file_name}"
            save_file(self.filebin,file_name_with_timestamp)
            self.GST_form = llm_response if llm_response is not {} else self.GST_form

        return self.GST_form

    def result_validator(self, GST_data):
        required_keys = ["docName", "docNo", "docAddress"]
        gst_pattern = r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[0-9]{1}[Z]{1}[A-Z0-9]{1}"
        gstin = self.GST_form["docNo"]
        return all(GST_data.get(key) for key in required_keys) and re.fullmatch(gst_pattern,gstin)
