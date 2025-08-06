from PIL import Image
import jwt
import cv2
import numpy as np
from qreader import QReader
import json
def decodeQR(image : Image): 
 
    try:
        image = cv2.cvtColor(np.array(image), cv2.COLOR_BGR2GRAY)
        
        reader = QReader()
        data = reader.detect_and_decode(image=image)
        with open('einvoice_2022_public.pem', 'r') as public_key_file:
            public_key = public_key_file.read()
        for qr in data:
            try:
                decoded_token = jwt.decode(qr.encode('ascii'), public_key, algorithms=['RS256'])
                return json.loads(str(decoded_token['data']))
            except Exception as e:
                continue

    except Exception as e:
        print(e)
        try:
            with open('einvoice_2023_public.pem', 'r') as public_key_file:
                public_key = public_key_file.read()
            for qr in data:
                try:
                    decoded_token = jwt.decode(qr.encode('ascii'), public_key, algorithms=['RS256'])
                    return json.loads(str(decoded_token['data']))  
                except Exception as e:
                    continue
        except Exception as e:
            return False
        
    return False



