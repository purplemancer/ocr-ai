from pdf2text import *
from typing import IO
from difflib import get_close_matches
import re
from time import perf_counter
from fastapi.responses import JSONResponse
from concurrent.futures import ThreadPoolExecutor
from conf_parse import api_key
from prompts import msme_prompt
from llm_gemini_img import GeminiImageProcessor
from db_store import save_file
from datetime import datetime

class MSMEPaddle:

    def __init__(self, filebin : IO, file_name:str):
        self.filebin = filebin
        self.file_name = file_name
        self.MSMEForm = {
            'docName':'',
            'docNo':'',
            'docType':'',
            'docActivity':'',
            'docCategory':'NA',
            'docDateInc':'',
            'docDateReg':'',
            'docScore':0
        }
        self.ocr_time = 0

    def loadMSME(self):
        images  = pdf2text.to_image(self.filebin)
        if len(images) >= 3:
            images = images[:2]
        text_list = []
        score_list = []
        
        nameScore = 0
        numScore = 0
        activityScore = 0
        catagoryScore = 0
        dateIncScore = 0
        dateRegScore = 0
        docScore = 0
        docTypeScore = 0
        docType = False
        Act = False
        major = False
        start_time = perf_counter()
        # for image in images:
        #     paddle_output = pdf2text.to_text_with_paddle(image,doc_type="msme")
        #     text_list.append(paddle_output[0])
        #     score_list.append(paddle_output[1])

        def process_image(image):
            paddle_output = pdf2text.to_text_with_paddle(image, doc_type="msme")
            return paddle_output[0], paddle_output[1], paddle_output[2]

        text_list = []
        score_list = []
        bbox_list = []

        with ThreadPoolExecutor() as executor:
            results = executor.map(process_image, images)

        for text, score, bbox in results:
            text_list.append(text)
            score_list.append(score)
            bbox_list.append(bbox)

        self.ocr_time = perf_counter() - start_time
        pattern = re.compile(r'\d{2}\d{2}\d{4}')   
        pattern1 = r"UDYAM-[A-Z]{2}-\d{2}-\d{7}"     
        in_social_catagory = False
        in_incorporation = False
        social_catagories = ['GENERAL', 'OBC', 'SC', 'ST', 'UNIDENTIFIED']
        major_activity = ['manufacturing', 'services', 'trading']
        state_codes = ['AP','AR','AS','BR','CG','DH','DL','GA','GJ','HR','HP','JH','KA','KL', 'KR','LD','MP','MH','MN','ML','MZ','NL','OD','PY','PB','RJ','SK','TN','TS','TR','UP','UT','WB']
        UDYAM = False
        count = 0
        
        for c, j in enumerate(text_list[0]):
            match = re.search(pattern1, j)
            if match:
                UDYAM = True
            elif 'udyam' in j.lower():
                count = count + 1
            if UDYAM == True or count > 1:
                break
            if c+1 == len(text_list[0]):
                self.MSMEForm = JSONResponse(status_code=400, content={"status": "uncool", "message": "Invalid document type. Please upload a valid MSME file"})
                return self.MSMEForm

        for i, block in enumerate(text_list[0]):
            # if 'typeofenterprise' in block.lower().replace(' ',''):
            #     check = text_list[0][i+1]
            #     if ('small' in check.lower() or 'micro' in check.lower() or 'medium' in check.lower()) and self.MSMEForm['docType'] == '':
            #         self.MSMEForm['docType'] = text_list[0][i+1]
            #         docTypeScore = float(score_list[0][i+1])
            #     else:
            #         check = text_list[0][i+2]
            #         if ('small' in check or 'micro' in check or 'medium' in check) and self.MSMEForm['docType'] == '':
            #             self.MSMEForm['docType'] = text_list[0][i+1]
            #             docTypeScore = float(score_list[0][i+1])
            if docType == True:
                if ('small' in block.lower() or 'micro' in block.lower() or 'medium' in block.lower()) and self.MSMEForm['docType'] == '' and 'our' not in block.lower() and 'hands' not in block.lower() and 'enterprises' not in block.lower():
                    if 'micro' in block.lower():
                        self.MSMEForm['docType'] = 'MICRO'
                    elif 'small' in block.lower():
                        self.MSMEForm['docType'] = 'SMALL'
                    elif 'medium' in block.lower():
                        self.MSMEForm['docType'] = 'MEDIUM'
                    docTypeScore = float(score_list[0][i])
                    docType = False
            if 'registrationcertificate' in block.lower().replace(' ',''):
                docType = True
            
            if in_social_catagory:
                match = get_close_matches(block.upper(), social_catagories)
                if match:
                    self.MSMEForm['docCategory'] = match[0]
                    catagoryScore = score_list[0][i]
                    in_social_catagory = False
                else:
                    continue
            elif in_incorporation:
                date = pattern.search(block.replace('/',''))
                if date:
                    self.MSMEForm['docDateInc'] = block
                    dateIncScore = score_list[0][i]
                    break
                else:
                    continue
                
            elif 'UDYAM' in block:
                a = block.replace('UDYAM','').replace('-','').replace('.','')
                try:
                    if a.isalnum() and a[:2] in state_codes and a[2:4].isnumeric():
                        self.MSMEForm['docNo'] = block
                        numScore = float(score_list[0][i+1])
                except Exception as e:
                    raise e

            elif 'nameofenterprise' in block.lower().replace(' ',''):
                max_height = bbox_list[0][i][1] + bbox_list[0][i][3]
                min_height = bbox_list[0][i][1]
                name  = ''
                score = 0
                if (bbox_list[0][i-1][1] + bbox_list[0][i-1][3]) > min_height:
                    name += text_list[0][i-1]
                    score += score_list[0][i-1]
                if bbox_list[0][i+1][1] < max_height:
                    name += ' ' + text_list[0][i+1]
                    score += score_list[0][i+1]
                self.MSMEForm['docName'] = name
                nameScore = score

            elif block.lower().replace(' ','') == 'majoractivity':
                if  get_close_matches(text_list[0][i+1].lower(), major_activity):
                    self.MSMEForm['docActivity'] = text_list[0][i+1]
                    activityScore = float(score_list[0][i+1])
                elif get_close_matches(text_list[0][i-1].lower(), major_activity):
                    self.MSMEForm['docActivity'] = text_list[0][i-1]
                    activityScore = float(score_list[0][i-1])

            elif 'category' in block.lower().replace(' ',''):
                in_social_catagory = True

            elif block.lower().replace(' ','').replace('/','').lower() == 'dateofincorporation':
                in_incorporation = True
        if self.MSMEForm['docActivity'] == '':
            Act = True
        for i, block in enumerate(text_list[0]):
            if block.lower().replace(' ','') == 'typeofenterprise':
                major = True
            if self.MSMEForm['docDateReg'] == '' and block.replace(' ','').lower() == 'dateofudyamregistration':
                    self.MSMEForm['docDateReg'] = text_list[0][i+1]
                    dateRegScore = float(score_list[0][i])
            elif Act and major:
                if block.lower().replace(' ','') in major_activity:
                    self.MSMEForm['docActivity'] = text_list[0][i]
                    activityScore = float(score_list[0][i])
                    Act = False



        if self.MSMEForm['docDateReg'] == '' and len(text_list) > 1:
            for i, block in enumerate(text_list[1]):
                if block.replace(' ','').lower() == 'dateofudyamregistration':
                    self.MSMEForm['docDateReg'] = text_list[1][i+1]
                    dateRegScore = float(score_list[1][i])

        if dateRegScore == 0 and dateIncScore == 0 and catagoryScore == 0 and activityScore == 0 and nameScore == 0 and numScore == 0:
            self.MSMEForm = JSONResponse(status_code=400, content={"status": "uncool", "message": "Invalid document type. Please upload a valid MSME file"})
            return self.MSMEForm

        docScore = ((dateRegScore+docTypeScore+dateIncScore+catagoryScore+activityScore+nameScore+numScore)/7.0)*100.0
        self.MSMEForm['docScore'] = round(docScore,2)

        # checking whether we have all the fields or not
        result  = self.result_validator(self.MSMEForm)
        if not result:
            processor = GeminiImageProcessor(api_key)
            llm_response = processor.process_images(images, msme_prompt,["docName","docNo","docActivity","docCategory","docDateInc","docDateReg"])
            llm_response['docScore'] = round(docScore,2)
            file_name_with_timestamp = f"{datetime.now().strftime('%d%m%Y_%H%M%S')}_{self.file_name}"
            save_file(self.filebin,file_name_with_timestamp)
            self.MSMEForm = llm_response if llm_response is not {} else self.MSMEForm

        return self.MSMEForm

    def result_validator(self, MSME_response):
        required_keys = ["docName", "docNo", "docActivity", "docCategory", "docDateInc", "docDateReg"]
        return all(MSME_response.get(key) for key in required_keys)
                


