from pdf2text import *
from typing import IO
from datetime import datetime, date
import re
from fuzzywuzzy import fuzz
from time import perf_counter
from fastapi.responses import JSONResponse
from db_store import save_file

class DLPaddle:
    closest_date = date(2021, 7, 2)
    def __init__(self, filebin : IO,file_name:str):
        self.DL  = {
            'Name' : '',
            'DLNO' : '',
            'DOB' : '',
            'IssueDate' : '',
            'ValidUpto' : '',
            'Status' : [],
            'docScore'  : 0
        }
        self.file = filebin
        self.file_name = file_name
        self.ocr_time = 0

    def loadDL(self):
        image = pdf2text.to_image(self.file)
        state_codes = [
        'AP', 'AR', 'AN', 'AS', 'BR', 'CH', 'DD', 'CT', 'DL', 'DD', 'GA', 'GJ', 'HR', 'JK',
        'HP', 'JH', 'KA', 'KL', 'LA', 'LD', 'MH', 'MN', 'ML', 'MZ', 'NL', 'MP', 'OR', 'CG',
        'OD', 'PB', 'RJ', 'SK', 'TN', 'TG', 'TR', 'UP', 'UT', 'WB', 'TS', 'UK', 'PY', 'UA'
        ]
        dummy = ''
        start_time = perf_counter()
        paddleOutput    = pdf2text.to_text_with_paddle(image[0],doc_type="dl")
        txt_list        = paddleOutput[0]
        score_list      = paddleOutput[1]
        self.ocr_time = perf_counter() - start_time
        dates = []
        NameScore = 0
        DLNOScore  = 0
        DOBScore = 0
        IssueDateScore = 0 
        ValidUptoScore = 0
        Scode = ''
        Dscore = []
        
        D_ = L_ = False
        for c , i in enumerate(txt_list):
            D_match = fuzz.partial_ratio('driving', i.lower())
            L_match = fuzz.partial_ratio('licence', i.lower())
            if D_match > 70:
                D_ = True
            if L_match > 70:
                L_ = True
            if D_ and L_:
                # print('Done')
                break
            if c == (len(txt_list) - 1):
                self.DL = JSONResponse(status_code=400, content={"status": "uncool", "message": "Invalid document type. Please upload a valid driving license"})
                return "Please upload a valid DL file"


        # Regular expression pattern for dd-mm-yyyy
        pattern1 = re.compile(r'\d{2}/\d{2}/\d{4}')
        pattern2 = re.compile(r'\d{2}-\d{2}-\d{4}')
        pattern3 = re.compile(r'\d{2}-[a-zA-Z]{3}-\d{4}')
        pattern4 = re.compile(r'\d{2}/\d{2}/\d{6}/\d{2}/\d{4}')
        Name = False
        for i, block  in enumerate(txt_list):
            if block:
                    dummy += block
            if len(block) > 14 and block.replace('-','').replace(' ','')[-10:].isnumeric():
                for s in state_codes:
                    if s in block:
                        Scode = s
                        start_index = block.find(s)
                        T_DL = block[start_index:].upper().replace(' ','').replace('DLNO','').replace(':','').replace('.','').replace('-','').replace('DLNUMBER','')
                        T_DL = T_DL[:5].replace('o','0').replace('O','0') + T_DL[5:]
                        match = re.search(r'\d', T_DL)
                        # print(T_DL)
                        if match:
                            start_index = match.start()
                            # Extract the two characters before the numeric sequence
                            T_DL = T_DL[start_index-2:]
                        try:
                            if Scode not in ('TS', 'TG', 'AP') and (T_DL[4:6] in ('19', '20') or T_DL[5:7] in ('19', '20')):
                                self.DL['DLNO'] = T_DL
                                DLNOScore       = score_list[i]
                            elif Scode in ('TS', 'TG', 'AP', '') and T_DL[5:7] in ('19', '20'):
                                self.DL['DLNO'] = T_DL
                                DLNOScore       = score_list[i]

                                self.DL['Name'] = txt_list[i + 1]
                                NameScore       = score_list[i + 1]
                        except Exception as e:
                            # Handle any other type of exception
                            return f"An unexpected error occurred: {str(e)} "
            elif Name == True:
                if len(block) > 4 and block.replace(' ', '').isalpha():
                    self.DL['Name'] = block.upper()
                    NameScore       = score_list[i]
                    Name = False
            elif pattern4.search(block):
                # block = block.replace(' ','')
                data = pattern4.search(block).group()
                dates.append(data[:10])
                Dscore.append(score_list[i])
                dates.append(data[10:])
                Dscore.append(score_list[i])
            elif pattern1.search(block):
                data = pattern1.search(block).group()
                if data:
                    dates.append(data)
                    Dscore.append(score_list[i])
            elif pattern2.search(block):
                data = pattern2.search(block).group()
                if data:
                    dates.append(data)
                    Dscore.append(score_list[i])
            elif pattern3.search(block):
                data = pattern3.search(block).group()
                formatted_string = datetime.strptime(data, '%d-%b-%Y').strftime('%d-%m-%Y')
                if formatted_string:
                    dates.append(formatted_string)
                    Dscore.append(score_list[i])
            elif 'name' in block.lower() and 'fath' not in block.lower():
                if len(block) > 8:
                    self.DL['Name'] = block.upper().replace('NAME','')
                    NameScore       = score_list[i]
                else:
                    Name = True


    # The driving license sRCNOecond page (back side).               
        try:   
            paddleOutput1    = pdf2text.to_text_with_paddle(image[1],doc_type="dl")
            txt_list1        = paddleOutput1[0]
            score_list1      = paddleOutput1[1]
            # print(txt_list1)
            for i, block in enumerate(txt_list1):
                if block:
                    dummy += block
                if pattern1.search(block):
                    data = pattern1.search(block).group()
                    if data:
                        dates.append(data)
                        Dscore.append(score_list1[i])
                elif pattern2.search(block):
                    data = pattern2.search(block).group()
                    if data:
                        dates.append(data)
                        Dscore.append(score_list1[i])
                elif pattern3.search(block):
                    data = pattern3.search(block).group()
                    formatted_string = datetime.strptime(data, '%d-%b-%Y').strftime('%d-%m-%Y')
                    if formatted_string:
                        dates.append(formatted_string)
                        Dscore.append(score_list1[i]) 
        except:
            pass
        
        try:
            Total = txt_list + txt_list1[:-2]
        except:
            Total = txt_list
        # print(Total) 
        for block in Total: 
              
            if 'LMVNT' in block.replace(' ', '').replace('-', ''):
                self.DL['Status'].append('LMV-NT')
            if 'LMVT' in block.replace(' ', '').replace('-', ''):
                self.DL['Status'].append('LMV-T')
            if 'LMV' in block.replace(' ', '').replace('-', ''):
                self.DL['Status'].append('LMV')
            if 'MCWG' in block.replace(' ', '').replace('-', ''):
                self.DL['Status'].append('MCWG')
            if ('TRANS' in block.replace(' ', '').replace('-', '')) and not('TRANSP' in block.replace(' ', '').replace('-', ''))  :
                self.DL['Status'].append('TRANS')
            if 'HMV' in block.replace(' ', '').replace('-', ''):
                self.DL['Status'].append('HMV')
            if 'HGMV' in block.replace(' ', '').replace('-', ''):
                self.DL['Status'].append('HGMV')
            if 'HPMV' in block.replace(' ', '').replace('-', ''):
                self.DL['Status'].append('HPMV')
            if 'HTV' in block.replace(' ', '').replace('-', ''):
                self.DL['Status'].append('HTV') 
            if 'MCWOG' in block.replace(' ', '').replace('-', ''):
                self.DL['Status'].append('MCWOG') 



        # Arranging dates            
        dates_with_slashes = [date.replace('-', '/') for date in dates]  
        dates = []
        for date_str in dates_with_slashes:
            try:
                date = datetime.strptime(date_str, '%d/%m/%Y').date()
                dates.append(date)
            except Exception as e:
                # Handle any other type of exception
                return f"An unexpected error occurred: {str(e)} "

        # Find the earliest and latest dates
        earliest_date = min(dates)
        latest_date = max(dates)
        # Convert dates back to string format for output
        self.DL['DOB'] = earliest_date.strftime('%d/%m/%Y')
        DOBScore = Dscore[dates.index(earliest_date)]
        self.DL['ValidUpto'] = latest_date.strftime('%d/%m/%Y')
        ValidUptoScore = Dscore[dates.index(latest_date)]
        tempnumber = self.DL['DLNO']

        for dt in dates:

            if str(dt.year) == tempnumber[4:8]:
                self.DL['IssueDate'] = dt.strftime('%d/%m/%Y')
                IssueDateScore = Dscore[dates.index(dt)]
            elif str(dt.year) == tempnumber[5:9]:
                self.DL['IssueDate'] = dt.strftime('%d/%m/%Y')
                IssueDateScore = Dscore[dates.index(dt)]

        if self.DL['IssueDate'] == '':
            if Scode != '' and (Scode not in ('TS', 'TG', 'AP')):
                tempYear = tempnumber[4:8]
                try:
                    if 1900 < int(tempYear) < 2099:
                        self.DL['IssueDate'] = DLPaddle.find_closest_date(dates, int(tempYear))
                        IssueDateScore = Dscore[dates.index(DLPaddle.closest_date)]
                except Exception as e:
                    # Handle any other type of exception
                    pass
            elif Scode != '' and (Scode in ('TS', 'TG', 'AP')):
                tempYear = tempnumber[5:9]
                try:
                    if 1900 < int(tempYear) < 2099:
                        self.DL['IssueDate'] = DLPaddle.find_closest_date(dates, int(tempYear))
                        IssueDateScore = Dscore[dates.index(DLPaddle.closest_date)]
                except Exception as e:
                    # Handle any other type of exception
                    pass
                    
    
        
        dummy  = dummy.lower().replace(' ','').replace(',','').replace('-','').replace('.','').replace('transport','').replace('non','')
        # print(dummy)
        if 'lightmotorvehiclenontransport' in dummy:
            self.DL['Status'].append('LMV-NT')
        if 'lightmotorvehicletransport' in dummy:
            self.DL['Status'].append('LMV-T')
        if 'lightmotorvehicle' in dummy:
            self.DL['Status'].append('LMV')
        if 'motorcyclewithgear' in dummy:
            self.DL['Status'].append('MCWG')
        if 'heavygoodsmotorvehicle' in dummy or 'heavypassengermotorvehicle' in dummy:
            self.DL['Status'].append('TRANS')
        if 'heavymotorvehicle' in dummy:
            self.DL['Status'].append('HMV')
        if 'heavygoodsmotorcar' in dummy:
            self.DL['Status'].append('HGMV')
        if 'heavypassengermotorvehicle' in dummy:
            self.DL['Status'].append('HPMV')
        if 'heavytransportvehicle' in dummy:
            self.DL['Status'].append('HTV')  
              
        if NameScore == 0  and DLNOScore == 0 and DOBScore == 0 and IssueDateScore == 0 and ValidUptoScore == 0:
            self.DL = JSONResponse(status_code=400, content={"status": "uncool", "message": "Invalid document type. Please upload a valid driving license"})
            return self.DL
              
        Score = ((NameScore + DLNOScore + DOBScore + IssueDateScore + ValidUptoScore ) /5) * 100
        self.DL['docScore'] = round(Score,2)
                    
        return self.DL


    def find_closest_date(dates, refyear):
        min_diff = float('inf')
        closest_date = None

        for date_str in dates:
        
            # Extract the year from the datetime object
            year = date_str.year

            # Only consider dates where the year is greater than the reference year
            if year >= refyear:
                # Calculate the difference between the year and the reference year
                diff = year - refyear
                # Update closest date if the current difference is smaller
                if diff < min_diff:
                    min_diff = diff
                    DLPaddle.closest_date = date_str

        return DLPaddle.closest_date.strftime('%d/%m/%Y')
