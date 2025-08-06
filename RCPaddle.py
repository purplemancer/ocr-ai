from pdf2text import *
from typing import IO
from datetime import datetime, date
import re
from time import perf_counter
from rapidfuzz import fuzz,utils,process
from fastapi.responses import JSONResponse
from db_store import save_file

class RCPaddle:
    closest_date = date(2021, 7, 2)
    def __init__(self, filebin : IO,file_name:str):
        self.file = filebin
        self.file_name = file_name
        self.RC  = {
            'Name'          : '',
            'RCNO'          : '',
            'Mfg'           : '',
            'Fuel'          : [],
            'DateOfReg'     : '',
            'ValidUpto'     : '',
            'ChassisNumber' : '',
            'EngineNumber'  : '',
            'VehcileClass'  : '',
            'Score'         : ''
        }
        self.ocr_time = 0
    
    def validate_file(self,ocr_text_lowercase,num_images):
        common_words = ['petrol', 'diesel', 'owner' , 'address', 'cylinder', 'capacity', 'model', 'chassis', 'colour', 'authority']
        dl_words = ['driving','license','union']

        match_count = 0
        capacity_thresh = 80
        gen_thresh = 70

        dl_score = sum(1 for word in dl_words if process.extractOne(word, ocr_text_lowercase, scorer=fuzz.ratio, processor=utils.default_process, score_cutoff=gen_thresh))

        if dl_score == len(dl_words):
            return False

        capacity_matches = process.extract("capacity", ocr_text_lowercase, scorer=fuzz.ratio, processor=utils.default_process, score_cutoff=capacity_thresh, limit=2)

        if len(capacity_matches) == 2:

            cubic_match = process.extractOne("cubic", ocr_text_lowercase, scorer=fuzz.ratio, processor=utils.default_process, score_cutoff=gen_thresh)
            seating_match = process.extractOne("seating", ocr_text_lowercase, scorer=fuzz.ratio, processor=utils.default_process, score_cutoff=gen_thresh)

            capacity_indices = [match[2] for match in capacity_matches]
            cubic_index = cubic_match[2] if cubic_match is not None else 0
            seating_index = seating_match[2] if cubic_match is not None else 0

            if cubic_match and seating_match:
                if (abs(capacity_indices[0]-cubic_index) == 1 and abs(capacity_indices[1]-seating_index) == 1) or (abs(capacity_indices[1]-cubic_index) == 1 and abs(capacity_indices[0]-seating_index) == 1):
                    return True

        for word in common_words:
            result = process.extractOne(word, ocr_text_lowercase, scorer=fuzz.ratio, processor=utils.default_process, score_cutoff=gen_thresh)
            if result:
                match_score = result[1]
                print(f"Word: {word}, Best Match: {result[0]}, Score: {match_score}")
                if match_score >= gen_thresh:
                    match_count += 1

        print("Number of matching words:", match_count)
        rc_validation_threshold = 0.3 if num_images == 1 else 0.5 if num_images == 2 else 0.7
        return match_count / len(common_words) >= rc_validation_threshold

    
    def loadRC(self):
        images = pdf2text.to_image(self.file)
        start_time = perf_counter()
        paddle_output_1    = pdf2text.to_text_with_paddle(images[0], doc_type = "rc")
        print(paddle_output_1[0])
        txt_list        = paddle_output_1[0]
        score_list      = paddle_output_1[1]
        self.ocr_time = perf_counter() - start_time
        try:
            paddle_output_2    = pdf2text.to_text_with_paddle(images[1], doc_type = "rc")
            print(paddle_output_2[0])
            txt_list1        = paddle_output_2[0]
            score_list1      = paddle_output_2[1]
        except:
             paddle_output_2 = []
        
        combined = paddle_output_1[0] + paddle_output_2[0]
        singular_words = [word.lower() for phrase in combined for word in phrase.split()]

        if not self.validate_file(singular_words,len(images)):
            return JSONResponse(status_code=400, content={"status": "uncool", "message": "Invalid document type. Please upload a valid registration certificate"})
        
        state_codes = [
        'AP', 'AR', 'AN', 'AS', 'BR', 'CH', 'DD', 'CT', 'DL', 'DD', 'GA', 'GJ', 'HR', 'JK',
        'HP', 'JH', 'KA', 'KL', 'LA', 'LD', 'MH', 'MN', 'ML', 'MZ', 'NL', 'MP', 'OR', 'CG',
        'OD', 'PB', 'RJ', 'SK', 'TN', 'TG', 'TR', 'UP', 'UT', 'WB', 'TS', 'UK', 'PY', 'UA'
        ]

        months_short = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]


        dummy = ''
        dates = []
        NameScore = 0
        RCNOScore  = 0
        MfgScore = 0
        FuelScore   = 0
        EngineScore = 0
        VehcileClassScore = 0
        ChassisScore = 0
        Scode = ''
        DatesScore = 0
        Dscore = []
        
        pattern1 = re.compile(r'[A-Z]{2}\d{2}[A-Z]{1,2}\d{4}')
        pattern6 = re.compile(r'[A-Z]{4}\d{4}[A-Z]{2}')

        # Date patterns
        pattern2 = re.compile(r'\d{2}/\d{2}/\d{4}')
        pattern3 = re.compile(r'\d{2}-\d{1,2}-\d{4}')
        pattern4 = re.compile(r'\d{2}-[a-zA-Z]{3}-\d{4}')
        pattern5 = re.compile(r'(0?[1-9]|1[0-2])/\d{4}')
        pattern8 = re.compile(r'(0?[1-9]|1[0-2])-\d{4}')
        pattern7 = re.compile(r'[a-zA-Z]{3}-\d{4}')
        Name = False
        Chassis = False
        Engine = False

        try:
            Total = txt_list + txt_list1
            score_list = score_list + score_list1
        except:
            Total = txt_list
            score_list = score_list
        

        for i,block in enumerate(txt_list):
            if block:
                dummy += block

            if pattern1.search(block) and len(block) > 8:
                data = pattern1.search(block).group()
                if data[:2] in state_codes:
                    self.RC['RCNO'] = data
                    RCNOScore = score_list[i]
            elif pattern6.search(block.replace(':','')) and len(block) > 8:
                data = pattern6.search(block).group()
                if data[:2] in state_codes:
                    self.RC['RCNO'] = data
                    RCNOScore = score_list[i]
            elif Name == True:
                    if len(block) > 4 and block.replace(' ', '').replace('.', '').isalpha() and all(keyword not in block.lower() for keyword in ['diesel', 'petrol', 'cng', 'emission']):
                        self.RC['Name'] = block.upper()
                        NameScore       = score_list[i]
                        Name = False
            elif ('name' in block.lower() or 'owner' in block.lower()) and not 'ownership' in block.lower() and not '/' in block:
                        Tn = block.lower().replace('name','').replace('owner','').replace('reg','')
                        if len(Tn) > 4:
                            self.RC['Name'] = Tn.upper()
                            NameScore       = score_list[i]
                        else:
                            Name = True
        # Total
        for i,block in enumerate(Total):
            if block:
                dummy += block

            if pattern2.search(block):
                data = pattern2.search(block).group()
                if data:
                    dates.append(data)
                    Dscore.append(score_list[i])

            if Engine == True:
                if len(block) > 8 and block.isalnum():
                    self.RC['EngineNumber'] = block.upper()
                    EngineScore       = score_list[i]
                    Engine = False

            if Chassis == True:
                if len(block) > 12 and block.isalnum():
                    self.RC['ChassisNumber'] = block.upper()
                    ChassisScore       = score_list[i]
                    Chassis = False

            if pattern3.search(block):
                data = pattern3.search(block).group()
                if data:
                    dates.append(data)
                    Dscore.append(score_list[i])

            elif pattern4.search(block):
                data = pattern4.search(block).group()
                formatted_string = datetime.strptime(data, '%d-%b-%Y').strftime('%d-%m-%Y')
                if formatted_string:
                    dates.append(formatted_string)
                    Dscore.append(score_list[i])
            
            elif pattern5.search(block):
                data = pattern5.search(block).group()
                if data[-4:-2] in ('20', '19'):
                    tmp = Total[i+1].lower()+Total[i-1].lower()+Total[i-2].lower()+Total[i-3].lower()+Total[i-4].lower()+block.lower()
                    if data and ('mfg' in tmp or 'yr' in tmp or 'mth' in tmp or 'month' in tmp or 'manufacture' in tmp):
                        self.RC['Mfg'] = data
                        MfgScore = score_list[i]
            elif pattern8.search(block):
                data = pattern8.search(block).group()
                if '20' in data[-4:-2] or '19' in data[-4:-2]:
                    tmp = Total[i+1].lower()+Total[i-1].lower()+Total[i-2].lower()+Total[i-3].lower()+Total[i-4].lower()+block
                    if data and ('mfg' in tmp or 'yr' in tmp or 'mth' in tmp or 'month' in tmp):
                        self.RC['Mfg'] = data
                        MfgScore = score_list[i]
            try:
                if block[:3].lower() in months_short and block.isalnum():
                    Tb = block[:3] + '-' + block[-4:]
                    data = pattern7.search(Tb).group()
                    formatted_string = datetime.strptime(data, '%b-%Y').strftime('%m-%Y')
                    tmp = Total[i+1].lower()+Total[i-1].lower()+Total[i-2].lower()+Total[i-3].lower()+Total[i-4].lower()+block.lower()
                    if data and ('mfg' in tmp or 'yr' in tmp or 'mth' in tmp or 'month' in tmp):
                        self.RC['Mfg'] = formatted_string
                        MfgScore = score_list[i]
            except:
                pass
            if 'diesel' in block.lower():
                self.RC['Fuel'].append('DIESEL')
                FuelScore = score_list[i]

            if 'petrol' in block.lower():
                self.RC['Fuel'].append('PETROL')
                FuelScore = score_list[i]

            if 'CNG' in block:
                self.RC['Fuel'].append('CNG')
                FuelScore = score_list[i]
            
            if 'LPG' in block:
                self.RC['Fuel'].append('LPG')
                FuelScore = score_list[i]
            
            if 'chassis' in block.lower() or 'CH.NO' in block:  
                Tn = block.lower().replace('chassis','').replace('number','').replace(':','').replace(' ', '').replace('.', '').replace('no', '')
                if Tn.isalnum() and len(Tn) > 12:
                    self.RC['ChassisNumber'] = block.lower().replace('.','').replace(' ','').replace('chassis','').replace('no','').upper()
                    ChassisScore       = score_list[i]
                else:
                    Chassis = True
    
            if 'engine' in block.lower() or 'E.NO' in block:
                Tn = block.lower().replace('engine','').replace('number','').replace(':','').replace(' ', '').replace('.', '').replace('no', '').replace('motor','')
                if Tn.isalnum() and len(Tn) > 8:
                    self.RC['EngineNumber'] = block.lower().replace('engine','').replace('.','').replace(' ','').replace('no','').upper()
                    EngineScore       = score_list[i]
                else:
                    Engine = True

        dummy  = dummy.lower().replace(' ','').replace(',','').replace('-','').replace('.','')

        dates_with_slashes = [date.replace('-', '/') for date in dates]  
        dates = []
        for date_str in dates_with_slashes:
            try:
                date = datetime.strptime(date_str, '%d/%m/%Y').date()
                dates.append(date)
            except Exception as e:
                # Handle any other type of exception
                print(f"An unexpected error occurred: {str(e)} ")
        try:
            earliest_date = min(dates)
        except:
            pass
        # Convert dates back to string format for output
        self.RC['DateOfReg'] = earliest_date.strftime('%d/%m/%Y')
        DatesScore += Dscore[0]

        if len(dates) >= 2:
            # if ('lifetax' in dummy) or ('lifetime' in dummy) or ('life' in dummy):
            self.RC['ValidUpto'] = dates[1].strftime('%d/%m/%Y')
            DatesScore += Dscore[1]
        if 'motorcycle' in dummy:
            self.RC['VehcileClass'] = 'Motor Cycle'
            VehcileClassScore += 1
        if 'motorcar' in dummy:
            self.RC['VehcileClass'] = 'Motor Car'
            VehcileClassScore += 1
        if 'scooter' in dummy:
            self.RC['VehcileClass'] = 'Scooter'
            VehcileClassScore += 1
        if 'goodscarrier' in dummy:
            self.RC['VehcileClass'] = 'Goods Carrier'
            VehcileClassScore += 1
        if 'autorickshaw' in dummy:
            self.RC['VehcileClass'] = 'Auto Rickshaw'
            VehcileClassScore += 1
        if 'goodsautorickshaw' in dummy:
            self.RC['VehcileClass'] = 'Goods Auto Rickshaw'
            VehcileClassScore += 1
        if 'passengercars' in dummy:
            self.RC['VehcileClass'] = 'Passenger Cars'
            VehcileClassScore += 1
        if 'multipurposevehicle' in dummy:
            self.RC['VehcileClass'] = 'Multi Purpose Vehicle'
            VehcileClassScore += 1
        if 'lightcommercialvehicle' in dummy:
            self.RC['VehcileClass'] = 'Light Commercial Vehicle'
            VehcileClassScore += 1
        if 'heavycommercialvehicle' in dummy:
            self.RC['VehcileClass'] = 'Heavy Commercial Vehiclee'
            VehcileClassScore += 1
        if 'threewheeler' in dummy:
            self.RC['VehcileClass'] = 'Three Wheeler'
            VehcileClassScore += 1
        if 'invalidcarriage' in dummy:
            self.RC['VehcileClass'] = 'Invalid Carriage'
            VehcileClassScore += 1
        if 'agriculturaltractor' in dummy:
            self.RC['VehcileClass'] = 'Agricultural Tractor'
            VehcileClassScore += 1
        if 'omnibus' in dummy:
            self.RC['VehcileClass'] = 'Omnibus'
            VehcileClassScore += 1
        if 'heavygoodsvehicle' in dummy:
            self.RC['VehcileClass'] = 'Heavy Goods Vehicle'
            VehcileClassScore += 1
        if 'lightgoodsvehicle' in dummy:
            self.RC['VehcileClass'] = 'Light Goods Vehicle'
            VehcileClassScore += 1

        # print(((NameScore + RCNOScore + MfgScore + FuelScore + EngineScore + VehcileClassScore + ChassisScore + DatesScore)/9)*100)
        self.RC['Score'] = round(((NameScore + RCNOScore + MfgScore + FuelScore + EngineScore + VehcileClassScore + ChassisScore + DatesScore)/9)*100,2)
        
        if NameScore == 0 and RCNOScore == 0 and MfgScore == 0 and FuelScore == 0 and EngineScore == 0 and VehcileClassScore == 0 and ChassisScore == 0 and DatesScore == 0:
            raise TypeError('Ensure correct file type is uploaded.')


        self.RC['Fuel'] = list(set(self.RC['Fuel']))
        return self.RC
