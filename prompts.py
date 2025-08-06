cheque_prompt = """Please analyze the following cheque image and extract:
        1. IFSC Code
        2. Account Number
        3. Extract the complete 23 or more digit code from the bottom MICR line including 2 digit transaction code.Ignore special characters.

        Provide the response in JSON format with keys "docIFSC", "docNo", and "micrCode".
        If you cannot find either value, use "" for that field."""

ie_prompt = """Please analyze the following Importer-Exporter certificate image and extract:
        1. IEC Number
        2. Date of issue
        
        Provide the response in JSON format with keys "docNo" and "docDate".
        If you cannot find either value, use "" for that field."""

cin_prompt = """Please analyze the following Certification of Incorporation image and extract:
        1. Corporate Identity Number
        2. Organisation Name
        
        Provide the response in JSON format with keys "docNo" and "docName".
        If you cannot find either value, use "" for that field."""

gst_prompt = """Please analyze the following GST Registration certificate image and extract:
        1. Registration Legal Name
        2. Registration Number
        3. Address of Principal Place of Business
        
        Provide the response in JSON format with keys "docName", "docNo" and "docAddress".
        If you cannot find either value, use "" for that field."""

msme_prompt = """Please analyze the following Udyam Registration certificate image and extract:
        1. Registration Name
        2. Registration Number
        3. Activity
        4. Category
        5. Date of Incorporation
        6. Date of Registration
        
        Provide the response in JSON format with keys "docName", "docNo", "docActivity", "docCategory","docDateInc" and "docDateReg".
        If you cannot find either value, use "" for that field."""

pan_prompt = """Please analyze the following PAN image and extract:
        1. Name
        2. PAN Number
        3. Date of Birth
        
        Provide the response in JSON format with keys "docName", "docNo", "docDate".
        If you cannot find either value, use "" for that field."""