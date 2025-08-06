from openai import AsyncOpenAI, OpenAI
from os import getenv
import asyncio
import tiktoken

class async_legible:

    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.cost = 0
        self.enc3 = tiktoken.encoding_for_model('gpt-4')
        self.enc4 = tiktoken.encoding_for_model('gpt-4')
        #   creating an instance of an OpenAI object
        self.client = AsyncOpenAI(
            api_key = 'redacted'
            )
        self.client_sync = OpenAI(
            api_key= 'redacted'
        )
    
    def count_tokens(self,enc,message):
        if enc == 3:
            return sum(len(self.enc3.encode(msg['content'])) for msg in message)
        elif enc == 4:
            return sum(len(self.enc4.encode(msg['content'])) for msg in message)
    
    def calc_cost(self, model, input_tokens, output_tokens):
        if model == 3:
            self.cost += (input_tokens/1000000)*0.150+(output_tokens/1000000)*0.600
        elif model == 4:
            self.cost += (input_tokens/1000000)*0.150+(output_tokens/1000000)*0.600

    def inv_frst_pge_sync(self, data: str):
        message = [{'role':'system','content':'Analyse the text, and generate a csv output for the following headers:Ack. Number, Ack. Date, IRN No., E-Way Bill Number, Vendor/Supplier/Seller Name, Vendor/Supplier/Seller GSTIN, Client/Customer/Buyer Name, Client/Customer/Buyer GSTIN, Invoice Number, Invoive Date, Purchase Order Number (PO Number) or Buyer Order Number, Currency'},
                {'role':'system','content':'Step 1: Dont include any comments in final response.'},
                {'role':'system','content':'Rule 1: Dont include commas in any of the header values.'},
                {'role':'system','content':'Rule 2: Make sure there are only 12 field values.'},
                {'role':'system','content':"Rule 3: Output should be in CSV format only."},
                {'role':'system','content':'Rule 4:Date should be in dd-mm-yyyy format.'},
                {'role':'system','content':'Rule 5:If a header value is not present, then populate the field with NA.'},
                {'role':'system','content':'Rule 6: The default currency should be INR.'},
                {'role':'system','content':'Rule 7: Look for the invoice number next to it or in the next 8 strings supplied to you'},
                {'role':'system','content':'Rule 8: do not use order number instead of buyer order number.'},
                {'role':'user','content':f'{data}'}]
        self.frst_pge = self.client_sync.chat.completions.create(
            model = 'gpt-4o-mini',
            messages = message,
            temperature = 0,
            top_p = 0,
            seed = 112233445566778899
        )
        self.input_tokens += self.count_tokens(4, message) 
        frst_page_txt = self.frst_pge.choices[0].message.content
        self.output_tokens += self.count_tokens(4, [{'content':frst_page_txt}])
        frst_page_txt = '\n'.join([line for line in frst_page_txt.splitlines() if line.strip()])
        
        self.calc_cost(4, self.count_tokens(4, message), self.count_tokens(4, [{'content':frst_page_txt}]))

        return frst_page_txt
    
    async def inv_last_pge_inter(self, data:str):
        msgs = [
                {'role':'user','content':f'Given data: {data}'},
                {'role':'system','content':'Step 1: Dont include any comments or formating in the final response'},
                {'role':'system','content':'Analyse the given data, and generate a csv output for the following headers: Total IGST Amount, Total Invoice Value'},

                {'role':'system','content':'Rule 1: header values are float type without commas'},
                {'role':'system','content':'Rule 2: Dont generate any values that are not present in the given data.'},
                {'role':'system','content':'Rule 3: Dont perform any mathamatical operations on the given data.'},
                {'role':'system','content':'Rule 4: Output should be in csv format only.'}
            ]
        self.last_pge = await self.client.chat.completions.create(
            model = 'gpt-4o-mini',
            messages = msgs, 
            top_p = 0,
            temperature = 0,
            seed = 112233445566778899
        )
        self.input_tokens += self.count_tokens(3, msgs)
        response = self.last_pge.choices[0].message.content
        self.output_tokens += self.count_tokens(3, [{'content':response}])
        self.calc_cost(3, self.count_tokens(3, msgs), self.count_tokens(3, [{'content':response}]))
        return response

    async def inv_last_pge_intra(self, data:str):
        msgs = [
                {'role':'user','content':f'Given Text:{data}'},
                {'role':'system','content':'Step 1: Dont include any comments or formating in the final response'},
                {'role':'system','content':'Analyse the given text, and generate a csv output for the following headers: Total Invoice Value, Total CGST, Total SGST'},
               
                {'role':'system','content':'Rule 1: Header values are float type without commas'},
                {'role':'system','content':'Rule 2: Dont generate any value that is not already present in the given data.'},
                {'role':'system','content':'Rule 3: Dont perform any mathamatical operations on the given data.'},
                {'role':'system','content':'Rule 4: Output should be in csv format only.'}

            ]
        self.last_pge = await self.client.chat.completions.create(
            model = 'gpt-4o-mini',
            messages = msgs,
            top_p = 0,
            temperature = 0,
            seed = 112233445566778899
        )
        
        self.input_tokens += self.count_tokens(3, msgs)
        response = self.last_pge.choices[0].message.content
        self.output_tokens += self.count_tokens(3, [{'content':response}])
        self.calc_cost(3, self.count_tokens(3, msgs), self.count_tokens(3, [{'content':response}]))
        return response
 



#   this method works best for tax invoices when line item extraction is a priority
    async def inv_line_items_inter(self, dataString : str):
        msgs = [
                {'role':'user', 'content':f'Given data:{dataString}'},
                {'role':'system','content':'Step 1: Dont include any comments in the final response.'},
                {'role':'system', 'content':'Step 2: Find line-items from the given data, and generate a csv output for the following headers: Item Description(without commas), HSN-SAC, Quantity or QTY, Unit of Measurment(UOM), Rate per Unit/Rate, IGST rate, IGST value, Total Amount, Item Code.'},
                {'role':'system', 'content':"Step 3: Remove commas from all values and represent as float."},
                {'role':'user', 'content':'Rule 1: Ensure there are exactly 9 values per row. Reprocess if there are more or less elements'},
                {'role':'user', 'content':'Rule 2: If a header value is absent, then populate with NA.'},
                {'role':'user', 'content':'Rule 3: Generated output should only contain information from the given data. Dont generate explanations.'},
                {'role':'user', 'content':'Rule 4: The generated output must be in CSV format only.'}
                ]
        self.line_items = await self.client.chat.completions.create(
            model='gpt-4o-mini',
            messages = msgs,
            temperature = 0,
            top_p = 0,
            seed = 998877665544332211
        )
        self.input_tokens += self.count_tokens(3, msgs)
        inter_txt = self.line_items.choices[0].message.content
        self.output_tokens += self.count_tokens(3, [{'content':inter_txt}])
        self.calc_cost(3, self.count_tokens(3, msgs), self.count_tokens(3, [{'content':inter_txt}]))
        return '\n'.join([line for line in inter_txt.splitlines() if line.strip()])
    

    async def inv_line_items_intra(self, datastring : str):
        msgs = [
                {'role':'user', 'content':f'Given data:{datastring}'},
                {'role':'system','content':'Step 1: Dont include any comments in the final response.'},
                {'role':'system', 'content':'Find line-items from the given data, and generate values without performing any mathematical operations for the following headers: Item Description, HSN Code, Quantity/Qty., CGST Value, SGST Value, Rate(without commas), CGST Rate, SGST Rate, Total Amount, Unit of Measurment(UOM), Item code.'},
                {'role':'user', 'content':'''Step 2:If SGST and CGST rate = 5 then make each 2.5, otherwise,
                                                      If SGST and CGST rate = 12 then make each 6, otherwise,
                                                      If SGST and CGST rate = 18 then make each 9'''},
                {'role':'user', 'content':"Step 3: Remove all commas from all header values and keep all periods."},
                {'role':'user', 'content':'Rule 1: Ensure there are exactly 11 values per row. Reprocess if there are more or less elements'},
                {'role':'user', 'content':'Rule 2: If a header value is absent then populate with NA'},
                {'role':'user', 'content':"Rule 3: Generated output should only contain information from the given data. Don't generate explanations."},
                {'role':'user', 'content':'Rule 4: Output must be in csv format.'}
                ]
        self.line_items = await self.client.chat.completions.create(
            model='gpt-4o-mini',
            messages = msgs,
            temperature = 0,
            top_p = 0,
            seed = 998877665544332211
        )
        self.input_tokens += self.count_tokens(3, msgs)
        intra_txt = self.line_items.choices[0].message.content
        self.output_tokens += self.count_tokens(3, [{'content':intra_txt}])
        self.calc_cost(3, self.count_tokens(3, msgs), self.count_tokens(3, [{'content':intra_txt}]))
        return '\n'.join([line for line in intra_txt.splitlines() if line.strip()])
    
