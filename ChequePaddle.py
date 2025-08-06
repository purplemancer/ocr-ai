from pdf2text import *
from typing import IO
import re,threading,typer
from time import perf_counter
from typing import List
from rapidfuzz import fuzz,utils,process
from fastapi.responses import JSONResponse
from conf_parse import api_key
from prompts import cheque_prompt
from llm_gemini_img import GeminiImageProcessor
from db_store import save_file
from datetime import datetime

def find_nth(s, ch, n):
    """Return the index of the nth occurrence of ch in s"""
    start = -1
    for _ in range(n):
        start = s.find(ch, start + 1)
        if start == -1:
            return -1
    return start

def split_micr_code(micr:str):
    idx_c2 = find_nth(micr, 'C', 2) + 1 
    idx_a1 = micr.find('A') + 1 
    idx_c3 = find_nth(micr, 'C', 3) + 1

    part1 = micr[:idx_c2]
    part2 = micr[idx_c2:idx_a1]
    part3 = micr[idx_a1:idx_c3]
    part4 = micr[idx_c3:]

    return [part1.strip(), part2.strip(), part3.strip(), part4.strip()]

class ChequePaddle:

    def __init__(self, filebin : IO, file_name:str):
        self.cheque  = {
            'docIFSC'   : '',
            'docNo'     : '',
            'micrCode'     : '',
            'docScore'  : 0
        }
        self.file = filebin
        self.file_name = file_name
        self.ocr_time = 0

    def validate_file(self,ocr_text:List[str]):
        common_words = [
            "bearer",
            "authorised", 
            "authorisedsignatory",
            "validfor3months",
            "validforthreemonths",
            "pay",
            "payable"
        ]

        stripped_text = [word.replace(" ", "").strip().lower() for word in ocr_text]
        match_count = 0
        threshold = 70

        # check for the 23 digit at the bottom centre
        number_pattern = r'\b\d{19,23}\b'
        for word in ocr_text:
            match = re.search(number_pattern, word)
            if match:
                return True
        for word in common_words:
            result = process.extractOne(word, stripped_text, scorer=fuzz.ratio, processor=utils.default_process)
            if result:
                match_score = result[1]
                print(f"Word: {word}, Best Match: {result[0]}, Score: {match_score}")
                if match_score >= threshold:
                    match_count += 1

        print("Number of matching words:", match_count)

        return match_count >= len(common_words) // 2
    
    def loadCheque(self):
        image = pdf2text.to_image(self.file)[0]
        start_time = perf_counter()
        paddleOutput,image_rescaled    = pdf2text.to_text_with_paddle(image,doc_type="cheque")

        if not self.validate_file(paddleOutput[0]):
            return JSONResponse(status_code=400, content={"status": 400, "message": "Invalid document type. Please upload a valid cheque"})
        
        txt_list        = paddleOutput[0][:-2]
        score_list      = paddleOutput[1]
        self.ocr_time = perf_counter() - start_time
        mircchScore     = 0
        ifscScore   = 0
        accScore    = 0
        docScore    = 0
        tempIFSC    = ''

        txt_list = [re.sub(r'[. ]', '', word) for word in txt_list] 

        # ex: PARMODKUMAR this can match if 0O is included in the ifscPattern
        ifscPattern = re.compile(r'[A-Z]{4}[0][A-Z0-9]{6}$')
        AcNoPattern = re.compile(r'^\d{8,18}(-\d{2,18}){0,3}$')
        # AcNoPattern = re.compile(r'^\d{8,18}$')

        for i, word in enumerate(txt_list):

            if AcNoPattern.search(word):
                self.cheque['docNo'] = AcNoPattern.search(word).group()
                accScore             = score_list[i]
                break

            elif ifscPattern.search(word.upper()):
                word = word.upper()
                tempIFSC  = ifscPattern.search(word).group()
                self.cheque['docIFSC']  = tempIFSC
                ifscScore               = score_list[i]

        # MICR logic
        custom_oem_psm_config = r'--tessdata-dir "./tessdata_fast" --oem 1 --psm 6'
        tess_ocr_data = pytesseract.image_to_string(image_rescaled, lang='e13b', config=custom_oem_psm_config)
        tess_ocr_data_list = tess_ocr_data.split("\n")[::-1]
        
        for word in tess_ocr_data_list:
            if 23 <= len(word) <= 31 and word.count("C") == 3 and word.strip()[-3] == "C":
                typer.secho(word, fg=typer.colors.RED)

                split_micr = split_micr_code(word)

                cheque_section, micr_section, account_section, transaction_id = split_micr

                cheque_no = cheque_section[-7:-1] if len(cheque_section) > 6 else cheque_section
                micr_code = micr_section[-10:-1] if len(micr_section) > 9 else micr_section
                account_code = account_section[-7:-1] if len(account_section) > 6 else account_section

                self.cheque['micrCode'] = f"{cheque_no} {micr_code} {account_code} {transaction_id}"
                break

        docScore                = ((accScore+ifscScore)/2.0)*100
        self.cheque['docScore'] = round(docScore,2)
        
        print("self.cheque before gemini =",self.cheque)
        # checking whether we have all the fields or not
        result  = self.result_validator(self.cheque)
        if not result:
            processor = GeminiImageProcessor(api_key)
            llm_response = processor.process_images([image], cheque_prompt,["docIFSC","docNo","micrCode"])
            llm_response['docScore'] = round(docScore,2)
            file_name_with_timestamp = f"{datetime.now().strftime('%d%m%Y_%H%M%S')}_{self.file_name}"
            threading.Thread(target=save_file,args=(self.file,file_name_with_timestamp)).start()
            self.cheque = llm_response if llm_response is not {} else self.cheque

        self.cheque['docNo'] = self.cheque['docNo'].replace('-','')
        return self.cheque

    def result_validator(self, cheque_data):
        if cheque_data.get("docIFSC") and cheque_data.get("docNo") and cheque_data.get('micrCode'):
            return True
        return False







