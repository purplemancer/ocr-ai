import difflib
import concurrent.futures

OCR_SUBSTITUTIONS = {
    '0': 'O', 'O': '0',
    '5': 'S', 'S': '5',
    'Z': '2', '2': 'Z',
    'B': '8', '8': 'B',
    'G': '6', '6': 'G',
    'I': '1', '1': 'I'
}

EXPECTED_TYPES = {
    0: int, 1: int, 
    2: str, 3: str, 4: str, 5: str, 6: str, 
    7: int, 8: int, 9: int, 10: int, 
    11: str, 
    12: int, 
    13: 'Z', 
    14: (str, int) 
}

class GSTIN:

    def find_match(file_pre : str, gstin : str):
        # change accordingly
        with open(f'/opt/fast_ocr_sol/ocr_api/gstin/{file_pre}_gstin.txt', 'r') as file:
            gstin_list = file.read().split('\n')

        closet_matches = difflib.get_close_matches(gstin, gstin_list, n=1, cutoff=0.8)

        if closet_matches:
            return closet_matches[0]
        else:
            return False
        
    def validate(gstin:str):

        prefix_lst = [  '01','02','03','04','05','06','07','08','09','10','11','12','13','14','15','16','17',
                        '18','19','20','21','22','23','24','26','27','29','30','31','32','33','34','35','36',
                        '37','38','97']
        gst_lst = [ gstin for _ in range(len(prefix_lst))]
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = list(executor.map(GSTIN.find_match, prefix_lst, gst_lst))
        
        for result in results:
            if result:
                return result
        
        return gstin
    

    def ocr_gstin_corrector(gstin_from_ocr:str):
        """
        Corrects GSTIN strings extracted from OCR output.

        Args:
            gstin_from_ocr (str): The raw GSTIN string extracted from OCR.

        Returns:
            str: The corrected GSTIN string.
        """
        corrected_gstin = list(gstin_from_ocr)

        if len(gstin_from_ocr) == 16 and "VV" in gstin_from_ocr:
            corrected_gstin = list(gstin_from_ocr.replace("VV","W"))

        elif len(gstin_from_ocr) == 14 and "W" in gstin_from_ocr:
            corrected_gstin = list(gstin_from_ocr.replace("W","VV"))
        
        # else:
        #     typesense_corr = retrieve_gst_no_info(gstin_from_ocr,"gst_no")
        #     corrected_gstin = list(typesense_corr[0]) if typesense_corr[0] else corrected_gstin
        
        if len(corrected_gstin)==15:
            for idx, char in enumerate(corrected_gstin):
                expected_type = EXPECTED_TYPES[idx]
                
                if expected_type == int and not char.isdigit():
                    corrected_gstin[idx] = OCR_SUBSTITUTIONS.get(char, char)
                elif expected_type == str and not char.isalpha():
                    corrected_gstin[idx] = OCR_SUBSTITUTIONS.get(char, char)
                elif expected_type == 'Z' and char != 'Z':
                    corrected_gstin[idx] = 'Z'

        return ''.join(corrected_gstin)


if __name__=='__main__':
    # 27AEIPL3129H1ZI
    print(GSTIN.ocr_gstin_corrector("27AE1PL3129H1ZI"))