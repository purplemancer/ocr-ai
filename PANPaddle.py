import re
from typing import IO
from pan import *
from pdf2text import *
from time import perf_counter
from fastapi.responses import JSONResponse
from conf_parse import api_key
from prompts import pan_prompt
from llm_gemini_img import GeminiImageProcessor
from db_store import save_file
from datetime import datetime

class PANPaddle:

    def __init__(self, file_bin:IO,file_name:str):
        self.file_bin = file_bin
        self.ocr_time = 0   
        self.file_name = file_name

    def get_pan_number(self):
        images      = pdf2text.to_image(self.file_bin)
        start_time = perf_counter()
        paddle_output = pdf2text.to_text_with_paddle(images[0].convert('RGB'), doc_type="pan")
        self.ocr_time = perf_counter() - start_time
        txt_list    = paddle_output[0]
        print(txt_list)
        score_list  = paddle_output[1]
        boxes       = paddle_output[2]
        pattern = re.compile(r'[A-Z]{5}[0-9]{4}[A-Z]')
        date_pattern = re.compile(r'\d{2}\/\d{2}\/\d{4}')
        alnums = []
        check = pdf2text.Pan_Valid(txt_list,boxes)
        if check == False:
            return JSONResponse(status_code=400, content={"status": "uncool", "message": "Invalid document type. Please upload a valid PAN file"})
        gov_index = 0
        date_index = 0

        panNumber = ''
        docDate = ''
        docName = ''

        isPersonal  = False
        isBusiness  = False
        isName      = False
        isFirm      = False

        nameScore   = 0
        dateScore   = 0
        numScore    = 0
        docScore    = 0

        for i, alnu in enumerate(txt_list):
            if 'name' in alnu.lower() and len(txt_list) > 34 and docName == '':
                if txt_list[i+1].isupper():
                    docName = txt_list[i+1]
                    nameScore = float(score_list[i+1])
            if 'govt' in alnu.lower():
                gov_index = i

            elif len(alnu) == 10 and alnu.isalnum():
                alnu = alnu[:5].replace('1','I')+alnu[5:]
                alnu = alnu[:5].replace('5','S')+alnu[5:]
                alnu = alnu[:5].replace('0','O')+alnu[5:]
                alnu = alnu[:5]+alnu[5:9].replace('I','1')+alnu[9]
                alnu = alnu[:5]+alnu[5:9].replace('S','5')+alnu[9]
                alnu = alnu[:5]+alnu[5:9].replace('O','0')+alnu[9]
                alnu = alnu[:9]+alnu[9].replace('1','I')
                alnu = alnu[:9]+alnu[9].replace('5','S')
                alnu = alnu[:9]+alnu[9].replace('0','O')
                alnums.append(alnu)
                if pattern.search(alnu):
                    panNumber   = pattern.search(alnu).group()
                    numScore    = float(score_list[i])

                if panNumber[3].upper() == 'P':
                    isPersonal = True
                elif panNumber[3].upper() == 'C':
                    isBusiness = True
                elif panNumber[3].upper() == 'F':
                    isFirm = True

            elif (len(alnu) == 9) and alnu.isalnum():
                alnu+='I'
                if pattern.search(alnu):
                    panNumber = pattern.search(alnu)
                    numScore = float(score_list[i])

            elif ('name' in alnu.lower()) and not('father' in alnu.lower()) and (isPersonal or isFirm) and len(txt_list) < 34 and docName == '':
                docName = txt_list[i+1]
                nameScore = float(score_list[i+1])
                isName = True
            
            elif (len(alnu) == 10) and date_pattern.search(alnu):
                date_index = i
                docDate = date_pattern.search(alnu).group()
                dateScore = float(score_list[i])
                
        if (isBusiness or (isPersonal and not(isName))) and len(txt_list) < 34:
            if isPersonal:
                ind = gov_index+1
                ref = boxes[ind][0] + boxes[ind][2] + (boxes[ind][2]/len(txt_list[ind])) 
                # docName = ' '.join(txt_list[gov_index+1:date_index-1])
                for data in txt_list[gov_index+1:date_index-1]:
                    s_ind = txt_list.index(data)
                    if boxes[s_ind][0] < ref and data.upper():
                        docName = docName + ' ' + data

                nameScore = float(score_list[gov_index+1])
                count = 1
                
                for score in score_list[gov_index+2:date_index-1]:
                    nameScore = nameScore+float(score)
                    count += 1
                
                nameScore = nameScore/count    
            else:
                docName = ' '.join(txt_list[gov_index+1:date_index])
                nameScore = float(score_list[gov_index+1])
                count = 1

                for score in score_list[gov_index+2:date_index]:
                    nameScore = nameScore+float(score)
                    count += 1
                
                nameScore = nameScore/count
        if len(docName) > 25: 
            name = docName.split(' ')

            # Create a list of tuples: (name_part, corresponding_box_x_value)
            box_mapping = [(i, boxes[c][0]) for c, j in enumerate(txt_list) for i in name if i in j]

            # Sort the box_mapping by x value (boxes[c][0])
            sorted_mapping = sorted(box_mapping, key=lambda x: x[1])

            # Reconstruct the doc in sorted order based on x values
            docName = ' '.join([part for part, _ in sorted_mapping])
            
        if len(docName) > 30 and (docName.isupper() == False):
            for i, txt in enumerate(txt_list):
                if 'father' in txt.lower():
                    if txt_list[i-1].isupper():
                        docName = txt_list[i-1]
                    elif txt_list[i-2].isupper():
                        docName = txt_list[i-2]
        if len(docName) > 15:
            docName = docName.upper().replace('INCOME TAX DEPARTMENT','')
            docName = docName.replace('INCOME','')
            docName = docName.replace('TAX','')
            docName = docName.replace('DEPARTMENT','').strip()

        
        if nameScore == 0 and numScore == 0 and dateScore == 0:
            return JSONResponse(status_code=400, content={"status": "uncool", "message": "Invalid document type. Please upload a valid PAN file"})

        docScore = ((nameScore+numScore+dateScore)/3.0)*100.0
        response = {'docName': docName, 'docNo': panNumber,'docDate':docDate, 'docScore':round(docScore,2)}

         # checking whether we have all the fields or not
        result  = self.result_validator(response)
        if not result:
            processor = GeminiImageProcessor(api_key)
            llm_response = processor.process_images(images, pan_prompt,["docName","docNo","docDate"])
            llm_response['docScore'] = round(docScore,2)
            file_name_with_timestamp = f"{datetime.now().strftime('%d%m%Y_%H%M%S')}_{self.file_name}"
            save_file(self.file_bin,file_name_with_timestamp)
            return llm_response if llm_response is not {} else response

        return response

    def result_validator(self, PAN_response):
        required_keys = ["docName", "docNo", "docDate"]
        return all(PAN_response.get(key) for key in required_keys)
    
