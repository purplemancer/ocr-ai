from async_legible import *
from pdf2text import *

import asyncio
from io import StringIO
from pdf2text import pdf2text
import json

from time import perf_counter

import csv

import concurrent.futures

import threading
import queue
import cv2

import base64

import qr_decode

class async_invoice:

    def __init__(self, filebin):
        self.ocr_time = 0
        self.ai_time = 0
        self.image_list     = pdf2text.to_image(filebin)
        start_time = perf_counter()
        self.text_list, self.img_l = async_invoice.ocr_images_conc(self.image_list)
        print(self.text_list)
        self.ocr_time += perf_counter() - start_time
        self.client    = async_legible() 
        self.invoice = {
                'Vendor':               '',
                'Vendor GSTIN':         '',
                'Client':               '',
                'Client GSTIN':         '',
                'Invoice Date':         '',
                'Invoice Number':       '',
                'Total Invoice Value':  '',
                'IGST Value':           '',
                'CGST Value':           '',
                'SGST Value':           '',
                'Purchase Order Number':'',
                'ACK Number':           '',
                'ACK Date':             '',
                'IRN':                  '',
                'E-way Bill Number':    '',
                'Currency':             '',
                'Line Items':           []
            }
        self.ocr_response = []

    def get_first_page_sync(self):
        start_time = perf_counter()
        # self.img_l[0].save('rot.png')
        if not isinstance(self.img_l[0], str):
            self.ocr_response = pdf2text.paddle_ocr(self.img_l[0])
            print(self.ocr_response)
            if pdf2text.valid(self.ocr_response, self.img_l[0]):
                ocr_txt = ' '.join(map(str, self.ocr_response[0])) 
                self.ocr_time += perf_counter()-start_time
                start_time = perf_counter()
                result = self.client.inv_frst_pge_sync(ocr_txt)
                self.ai_time += perf_counter()-start_time
                reader = csv.reader(StringIO(result))
                second_row = next(reader)
                if len(second_row) == 1:
                    second_row = next(reader)
                if len(second_row[0]):
                    if second_row[0].lower()[:3]=='ack':
                        second_row = next(reader)
                qr = qr_decode.decodeQR(self.img_l[0])
                print(qr)
                if not qr:
                    print('in here')
                    qr = qr_decode.decodeQR(self.img_l[-1])
                if len(second_row) == 12:
                    self.invoice['Vendor']                  = second_row[4]
                    self.invoice['Vendor GSTIN']            = second_row[5].replace(" ","")
                    self.invoice['Client']                  = second_row[6]
                    self.invoice['Client GSTIN']            = second_row[7].replace(" ", "")
                    self.invoice['Invoice Number']          = second_row[8].replace(' ','')
                    self.invoice['Invoice Date']            = second_row[9]
                    self.invoice['Purchase Order Number']   = second_row[10].replace(' ','')
                    self.invoice['ACK Number']              = second_row[0].replace(' ','')
                    self.invoice['ACK Date']                = second_row[1]
                    self.invoice['IRN']                     = second_row[2].replace(' ','')
                    ewb = second_row[3].replace(' ','').replace('Z','2').replace('O','0').replace('L','1').replace('I','1')
                    if ewb.isnumeric():
                        self.invoice['E-way Bill Number']   = ewb
                    self.invoice['Currency']                = second_row[11].replace(' ','')
                
                elif len(second_row) == 13 or len(second_row) == 14:
                    if second_row[5].isalnum() or second_row[5].replace(' ','') == 'NA':    
                        self.invoice['Vendor']                  = second_row[4]            
                        self.invoice['Vendor GSTIN']            = second_row[5].replace(" ","")
                        
                        if second_row[7].isalnum() or second_row[7].replace(' ','') == 'NA':
                            self.invoice['Client']                  = second_row[6]
                            self.invoice['Client GSTIN']            = second_row[7].replace(" ", "")
                            self.invoice['Invoice Number']          = second_row[8].replace(' ','')
                            self.invoice['Invoice Date']            = second_row[9].replace('/', '-')
                            self.invoice['Purchase Order Number']   = second_row[10].replace(' ','')
                            self.invoice['ACK Number']              = second_row[0].replace(' ','')
                            self.invoice['ACK Date']                = second_row[1].replace('/','-')
                            self.invoice['IRN']                     = second_row[2].replace(' ','')
                            self.invoice['E-way Bill Number']       = second_row[3].replace(' ','')
                            self.invoice['Currency']                = second_row[11].replace(' ','')
                        
                        else:
                            self.invoice['Client']                  = second_row[6]+' '+second_row[7]
                            self.invoice['Client GSTIN']            = second_row[8].replace(" ", "")
                            self.invoice['Invoice Number']          = second_row[9].replace(' ','')
                            self.invoice['Invoice Date']            = second_row[10].replace('/','-')
                            self.invoice['Purchase Order Number']   = second_row[11].replace(' ','')
                            self.invoice['ACK Number']              = second_row[0].replace(' ','')
                            self.invoice['ACK Date']                = second_row[1].replace('/','-')
                            self.invoice['IRN']                     = second_row[2].replace(' ','')
                            self.invoice['E-way Bill Number']       = second_row[3].replace(' ','')
                            self.invoice['Currency']                = second_row[12].replace(' ','')
                            
                    else:
                        self.invoice['Vendor']                  = second_row[4]+' '+second_row[5]            
                        self.invoice['Vendor GSTIN']            = second_row[6].replace(" ","")
                        
                        if second_row[8].isalnum() or second_row[7].replace(' ','') == 'NA':
                            self.invoice['Client']                  = second_row[7]
                            self.invoice['Client GSTIN']            = second_row[8].replace(" ", "")
                            self.invoice['Invoice Number']          = second_row[9].replace(' ','')
                            self.invoice['Invoice Date']            = second_row[10].replace('/','-')
                            self.invoice['Purchase Order Number']   = second_row[11].replace(' ','')
                            self.invoice['ACK Number']              = second_row[0].replace(' ','')
                            self.invoice['ACK Date']                = second_row[1].replace('/','-')
                            self.invoice['IRN']                     = second_row[2].replace(' ','')
                            self.invoice['E-way Bill Number']       = second_row[3].replace(' ','')
                            self.invoice['Currency']                = second_row[12].replace(' ','')
                        
                        else:
                            self.invoice['Client']                  = second_row[7]+' '+second_row[7]
                            self.invoice['Client GSTIN']            = second_row[9].replace(" ", "")
                            self.invoice['Invoice Number']          = second_row[10].replace(' ','')
                            self.invoice['Invoice Date']            = second_row[11].replace('/','-')
                            self.invoice['Purchase Order Number']   = second_row[12].replace(' ','')
                            self.invoice['ACK Number']              = second_row[0].replace(' ','')
                            self.invoice['ACK Date']                = second_row[1].replace('/', '-')
                            self.invoice['IRN']                     = second_row[2].replace(' ','')
                            self.invoice['E-way Bill Number']       = second_row[3].replace(' ','')
                            self.invoice['Currency']                = second_row[13].replace(' ','')
                if qr:
                    qr_dict = dict(qr)
                    self.invoice['Vendor GSTIN']    = qr_dict["SellerGstin"]
                    self.invoice['Client GSTIN']    = qr_dict['BuyerGstin']
                    self.invoice['Invoice Number']  = qr_dict['DocNo']
                    self.invoice['Invoice Date']    = qr_dict['DocDt'].replace('/', '-')
                    self.invoice['IRN']             = qr_dict['Irn']
                    self.invoice['qr']              = qr
                else:
                    self.invoice['qr'] = qr
                return True
            else:
                return False


    async def load_line_items(self):
        start_time = perf_counter()
        line_items = await self.get_line_items()
        (line_items)
        self.ai_time += perf_counter() - start_time
        line_items_csv = StringIO(line_items[0])
        line_items_rdr = csv.reader(line_items_csv)
        if line_items[1]:
            for row in line_items_rdr:
                if (len(row) == 9):
                    if (len(row[0])>0) & (row[0].lower() != 'na') & (row[0].lower()[:4] != "item") & (row[0].lower() != '0') & (row[0].lower()[:5] != 'total') & (row[0].lower()[:5] != 'trade')  & (row[1].replace(' ', '') != '') & (row[1].replace(' ', '').lower()[0] != 'n'):
                        self.invoice["Line Items"].append(async_invoice.line_item_inter(row))
        
        else:
           for row in line_items_rdr:
                if (len(row) == 11):
                    if (len(row[0])>0) & (row[0].lower() != 'na') & (row[0].lower()[:4] != "item") & (row[0].lower() != '0') & (row[0].lower()[:5] != 'total') & (row[0].lower()[:5] != 'trade') & (row[8].replace(' ', '') != '') & (row[8].replace(' ', '').lower()[0] != 'n'):
                        line_item = row
                        self.invoice["Line Items"].append(async_invoice.line_item_intra(row))                

    async def load_totals(self):
        
        if self.det_intera_or_inter():
            await self.load_totals_inter()
        else:
            await self.load_totals_intra()
        
        
        
    async def load_totals_inter(self):
        txt_lst = self.text_list
        page_count = len(txt_lst)
        
        total_invoice_value = 0.0
        igst_value = 0.0
        last_page_index = 1
        
        while (total_invoice_value == 0.0) & (page_count - last_page_index != -1):
            lastpage = txt_lst[page_count-last_page_index]
            start_time = perf_counter()
            totals_page = await self.client.inv_last_pge_inter(lastpage)
            self.ai_time += perf_counter() - start_time
            totals_fle = StringIO(totals_page)
            totals_rdr = csv.reader(totals_fle)
            cmnts = False
            for i, row in enumerate(totals_rdr):
                
                if len(row) == 1: 
                    cmnts = True
                if cmnts:
                    j = i - 1
                else:
                    j = i
                    
                if (j == 1) & (len(row) == 2):
                    total_invoice_value = float(row[-1].replace(' ',''))
                    igst_value = float(row[0].replace(' ',''))
            last_page_index += 1
        self.invoice['Total Invoice Value'] = total_invoice_value
        self.invoice['IGST Value'] = igst_value
        return self.invoice
        
        
    async def load_totals_intra(self):
        txt_lst = self.text_list
        page_count = len(txt_lst)
        total_inv_value = 0.0
        cgst_value = 0.0
        sgst_value = 0.0
        last_page_index = 1
        while (total_inv_value == 0.0) & (page_count-last_page_index != -1):
            totals_page = txt_lst[page_count-last_page_index]
            totals = await self.client.inv_last_pge_intra(totals_page)
            
            totalsFle = StringIO(totals)
            totalsRdr = csv.reader(totalsFle)
            
            cmnts = False
            
            for i, row in enumerate(totalsRdr):

                if cmnts:
                    j = i-1
                else:
                    j = i
                
                if len(row) == 1: 
                    cmnts = True
                if cmnts:
                    j = i - 1
                else:
                    j = i
                    
                if (j == 1) & (len(row) == 3):
                    total_inv_value = (row[0].replace(' ',''))
                    cgst_value = (row[1].replace(' ', ''))
                    sgst_value = (row[2].replace(' ',''))
            last_page_index += 1
        self.invoice['Total Invoice Value'] = total_inv_value
        self.invoice['CGST Value'] = cgst_value
        self.invoice['SGST Value'] = sgst_value

    async def get_line_items(self):
        txt_lst = self.text_list
        if self.det_intera_or_inter():
           coroutines = [self.client.inv_line_items_inter(page) for page in txt_lst]

           line_items = await asyncio.gather(*coroutines)

           return ['\n'.join(line_items), 1]  
        else:
            coroutines = [self.client.inv_line_items_intra(page) for page in txt_lst]

            line_items = await asyncio.gather(*coroutines)

            return ['\n'.join(line_items), 0]
    

    def det_intera_or_inter(self):
        if self.invoice['Client GSTIN'][:2] == self.invoice['Vendor GSTIN'][:2]:
            return 0
        return 1


    def line_item_intra(lineItmRaw):
        form = {
                        "Item Description": lineItmRaw[0],
                        "HSN-SAC Code": lineItmRaw[1].replace(' ',''),
                        "Quantity": lineItmRaw[2].replace(' ', ''),
                        "Rate per Unit": lineItmRaw[5],
                        "CGST Rate":lineItmRaw[6],
                        "CGST Value":lineItmRaw[4],
                        "SGST Rate": lineItmRaw[7],
                        "SGST Value": lineItmRaw[3],
                        "Total Value": lineItmRaw[8],
                        'Item Code': lineItmRaw[10],
                        'UOM': lineItmRaw[9]
                       }        
        return form


    def line_item_inter(lineItmRaw):
        form = {
                        "Item Description": lineItmRaw[0],
                        "HSN-SAC Code": lineItmRaw[1].replace(' ',''),
                        "Quantity": lineItmRaw[2].replace(' ',''),
                        "Rate per Unit": lineItmRaw[4],
                        "IGST Rate":lineItmRaw[5],
                        "IGST Value":lineItmRaw[6],
                        "Total Value": lineItmRaw[7],
                        'Item Code': lineItmRaw[8],
                        "UOM": lineItmRaw[3]
                        }
        return form

    def ocr_images_conc(image_list):
        if not isinstance(image_list[0], str):
            image_results = []
            with concurrent.futures.ThreadPoolExecutor() as executor:
                for image in tqdm(executor.map(pdf2text.rotate_image, image_list), total=len(image_list), desc='Rotating Images'):
                    image_results.append(image)
        else:
            image_results = image_list

        return pdf2text.to_text(image_results), image_results
    
