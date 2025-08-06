from fastapi import APIRouter, UploadFile, HTTPException, Request
from fastapi.responses import JSONResponse

from async_invoice import *
from BoundingBox import *

from ocr_logging import *

from PANPaddle import *
from ChequePaddle import *
from MSMEPaddle import *
from CINPaddle import *
from GSTPaddle import *
from IECPaddle import *
from DLPaddle import *
from RCPaddle import *
from datetime import datetime

router = APIRouter()

@router.post('/collaboract/v1', tags=['ocr'])
async def collaboractv0_0(file:UploadFile, query:str, request:Request):
    try:
        filebin = await file.read()     # Read the file content
        file_name = file.filename
        ip_address  = str(request.client.host)
        start_time  = datetime.now()
        end_time    = 0
        duration    = 0
        method_meth = query
        api_url     = request.url.path
        status_code = 0
        response_body       = ''
        input_token_count   = 0
        output_token_count  = 0
        ai_cost     = 0
        ocr_time    = 0
        ai_time     = 0
        file_bin    = filebin

        

        if query == 'invoice':
            invoice = async_invoice(filebin)
            if invoice.get_first_page_sync():
                coroutine_1 = invoice.load_line_items()
                coroutine_2 = invoice.load_totals()
                await asyncio.gather(coroutine_1, coroutine_2)
                # coordinates = BoundingBox(invoice.invoice)
                # invoice.invoice['Co-ordinates'] = coordinates.place(invoice.ocr_response[0], invoice.ocr_response[1])
                # print(async_invoice.img_l)
                # invoice.invoice['Co-ordinates']['Line Items'] = coordinates.line_items_co(async_invoice.img_l)
                status_code = 200
                response_body = invoice.invoice
                input_token_count = invoice.client.input_tokens
                output_token_count = invoice.client.output_tokens
                ai_cost = invoice.client.cost
                ocr_time = invoice.ocr_time
                ai_time = invoice.ai_time
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                log_response(ip_address, start_time, end_time,
                            duration, method_meth, api_url,
                            status_code, str(response_body), input_token_count,
                            output_token_count, ai_cost, ocr_time,
                            ai_time, file_bin)
                return JSONResponse(status_code=200, content={'response':invoice.invoice, 'status':'cool'})
            else:
                status_code = 400
                response_body = invoice.invoice
                input_token_count = invoice.client.input_tokens
                output_token_count = invoice.client.output_tokens
                ai_cost = invoice.client.cost
                ocr_time = invoice.ocr_time
                # print(response_body, input_token_count, output_token_count, ai_cost, ocr_time)
                ai_time = invoice.ai_time
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                log_response(ip_address, start_time, end_time,
                            duration, method_meth, api_url,
                            status_code, str(response_body), input_token_count,
                            output_token_count, ai_cost, ocr_time,
                            ai_time, file_bin)
                return JSONResponse(status_code=status_code, content={'response':'Upload a valid invoice file', 'status':'uncool'})
        
        elif query == 'pan':
            pan = PANPaddle(filebin,file_name)
            details = pan.get_pan_number()
            status_code =200
            ocr_time = pan.ocr_time
            if isinstance(details, JSONResponse):
                status_code = details.status_code
                result = json.loads(details.body.decode("utf-8"))
            else:
                result = details
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            log_response(ip_address, start_time, end_time,
                            duration, method_meth, api_url,
                            status_code, json.dumps(result), input_token_count,
                            output_token_count, ai_cost, ocr_time,
                            ai_time, file_bin)

            content = {'response':result, 'status': "cool"} if status_code == 200 else result
            return JSONResponse(status_code=status_code, content=content )
        
        elif query == 'gst':
            gst = GSTPaddle(filebin,file_name)
            gst_response = gst.loadGST()
            status_code = 200     
            print(gst_response)

            if isinstance(gst_response, JSONResponse):
                status_code = gst_response.status_code
                result = json.loads(gst_response.body.decode("utf-8"))
            else:
                result = gst.GST_form
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            log_response(ip_address, start_time, end_time,
                            duration, method_meth, api_url,
                            status_code, json.dumps(result), input_token_count,
                            output_token_count, ai_cost, ocr_time,
                            ai_time, file_bin)
            content = {'response':result, 'status': "cool" } if status_code == 200 else result
            
            return JSONResponse(status_code=status_code, content=content )
            
        elif query == 'msme':
            msme = MSMEPaddle(filebin,file_name)
            ms_response = msme.loadMSME()
            status_code = 200
            if isinstance(ms_response, JSONResponse):
                status_code = ms_response.status_code
                result = json.loads(ms_response.body.decode("utf-8"))
            else:
                result = ms_response    
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            log_response(ip_address, start_time, end_time,
                            duration, method_meth, api_url,
                            status_code, json.dumps(result), input_token_count,
                            output_token_count, ai_cost, ocr_time,
                            ai_time, file_bin)
            content = {'response':result, 'status': "cool"} if status_code == 200 else result
            return JSONResponse(status_code=status_code, content=content )
        
        elif query == 'ie':
            iec = IECPaddle(filebin,file_name)
            iec_response = iec.loadIE()
            status_code = 200     

            if isinstance(iec_response, JSONResponse):
                status_code = iec_response.status_code
                result = json.loads(iec_response.body.decode("utf-8"))
            else:
                result = iec.IE_data

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            log_response(ip_address, start_time, end_time,
                            duration, method_meth, api_url,
                            status_code, json.dumps(result), input_token_count,
                            output_token_count, ai_cost, ocr_time,
                            ai_time, file_bin)
            content = {'response':result, 'status': "cool"} if status_code == 200 else result
            
            return JSONResponse(status_code=status_code, content=content )
        
        elif query == 'cheque':
            cheque = ChequePaddle(filebin,file_name)
            cheque_response = cheque.loadCheque()
            status_code = 200     

            if isinstance(cheque_response, JSONResponse):
                status_code = cheque_response.status_code
                result = json.loads(cheque_response.body.decode("utf-8"))
            else:
                result = cheque.cheque

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            log_response(ip_address, start_time, end_time,
                            duration, method_meth, api_url,
                            status_code, json.dumps(result), input_token_count,
                            output_token_count, ai_cost, ocr_time,
                            ai_time, file_bin)
            content = {'response':result, 'status': "cool"} if status_code == 200 else result
            
            return JSONResponse(status_code=status_code, content=content )

        elif query == 'cin':
            cin = CINPaddle(filebin,file_name)
            response = cin.loadCIN()
            status_code = 200
            if isinstance(response, JSONResponse):
                status_code = response.status_code
                result = json.loads(response.body.decode("utf-8"))
            else:
                result = response
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            log_response(ip_address, start_time, end_time,
                            duration, method_meth, api_url,
                            status_code, json.dumps(result), input_token_count,
                            output_token_count, ai_cost, ocr_time,
                            ai_time, file_bin)
            content = {'response':result, 'status': "cool"} if status_code == 200 else result
            return JSONResponse(status_code=status_code, content=content )
        
        elif query == "dl":
            dl = DLPaddle(filebin,file_name)
            response = dl.loadDL()
            status_code = 200
            if isinstance(response, JSONResponse):
                status_code = response.status_code
                result = json.loads(response.body.decode("utf-8"))
            else:
                result = response
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            log_response(ip_address, start_time, end_time,
                            duration, method_meth, api_url,
                            status_code, json.dumps(result), input_token_count,
                            output_token_count, ai_cost, ocr_time,
                            ai_time, file_bin)
            content = {'response':result, 'status': "cool"} if status_code == 200 else result
            return JSONResponse(status_code=status_code, content=content )

        elif query == 'rc':
            rc = RCPaddle(filebin,file_name)
            rc_response = rc.loadRC()
            status_code = 200     

            if isinstance(rc_response, JSONResponse):
                status_code = rc_response.status_code
                result = json.loads(rc_response.body.decode("utf-8"))
            else:
                result = rc.RC

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            log_response(ip_address, start_time, end_time,
                            duration, method_meth, api_url,
                            status_code, json.dumps(result), input_token_count,
                            output_token_count, ai_cost, ocr_time,
                            ai_time, file_bin)
            content = {'response':result, 'status': "cool"} if status_code == 200 else result

            return JSONResponse(status_code=status_code, content=content )

        else:
            status_code = 400
            response_body = 'Invalid query.'
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            log_response(ip_address, start_time, end_time,
                            duration, method_meth, api_url,
                            status_code, str(response_body), input_token_count,
                            output_token_count, ai_cost, ocr_time,
                            ai_time, file_bin)

            return JSONResponse(status_code=200, content={'response':'Invalid query. Check query and try again.', 'status': "uncool"})
           
    except Exception as e:
        status_code = 500
        response_body = e
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        log_response(ip_address, start_time, end_time,
                            duration, method_meth, api_url,
                            status_code, str(response_body), input_token_count,
                            output_token_count, ai_cost, ocr_time,
                            ai_time, file_bin)

        return JSONResponse(status_code=status_code, content={'status_message':f'{str(e)}','status':"uncool"})

