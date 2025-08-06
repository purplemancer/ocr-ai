from pdf2text import *
from typing import IO
import re
from time import perf_counter
from fuzzywuzzy import fuzz
from fastapi.responses import JSONResponse
from conf_parse import api_key
from prompts import cin_prompt
from llm_gemini_img import GeminiImageProcessor
from db_store import save_file
from datetime import datetime

class CINPaddle:
    def __init__(self , filebin:IO,file_name: str):
        self.filebin = filebin
        self.file_name = file_name
        self.INC = {
            'docNo' : '',
            'docName' : '',
            'docScore':0
        }
        self.ocr_time = 0 

    def loadCIN(self):
        image = pdf2text.to_image(self.filebin)[0]
        start_time = perf_counter()
        paddle_output = pdf2text.to_text_with_paddle(image.convert('RGB'),doc_type="cin")
        self.ocr_time = perf_counter()-start_time
        txt_list = paddle_output[0]
        score_list = paddle_output[1]
        pattern = re.compile(r'\w{1}\d{5}\w{2}\d{4}\w{3}\d{6}')
        numScore = 0
        nameScore = 0
        docScore = 0
        CIN = False
        for c, j in enumerate(txt_list):
            match_percentage = fuzz.ratio('certificateofincorporation', j.lower().replace(' ',''))
            if match_percentage >= 80:
                CIN = True
            if pattern.search(j):
                num = pattern.search(j).group()
                if not num.isnumeric():
                    CIN = True
            if CIN == True:
                break
            if c+1 == len(txt_list):
                self.INC = JSONResponse(status_code=400, content={"status": "uncool", "message": "Invalid document type. Please upload a valid CIN file"})
                return self.INC
        
        for i, block in enumerate(txt_list):
            if pattern.search(block):
                num = pattern.search(block).group()
                if not num.isnumeric():
                    self.INC['docNo'] = num
                    numScore = float(score_list[i])

            elif 'mailingaddressasper' in block.lower().replace(' ',''):
                self.INC['docName'] = txt_list[i+1]
                nameScore = float(score_list[i])
                break
        
        if nameScore == 0 and numScore == 0:
            self.INC = JSONResponse(status_code=400, content={"status": "uncool", "message": "Invalid document type. Please upload a valid CIN file"})
            return self.INC

        docScore = ((nameScore+numScore)/2)*100
        self.INC['docScore'] = round(docScore,2)

        # checking whether we have all the fields or not
        result  = self.result_validator(self.INC)
        if not result:
            processor = GeminiImageProcessor(api_key)
            llm_response = processor.process_images([image], cin_prompt,["docNo","docName"])
            llm_response['docScore'] = round(docScore,2)
            file_name_with_timestamp = f"{datetime.now().strftime('%d%m%Y_%H%M%S')}_{self.file_name}"
            save_file(self.filebin,file_name_with_timestamp)
            self.INC = llm_response if llm_response is not {} else self.INC

        return self.INC

    def result_validator(self, INC_data):
        if INC_data.get("docNo") and INC_data.get("docName"):
            return True
        return False



