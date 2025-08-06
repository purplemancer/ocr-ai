import difflib
import Levenshtein
import concurrent.futures

class PAN:

    def find_match(file_pre : str, pan : str):
        # need to change for server
        with open(f'/opt/fast_ocr_sol/ocr_api/pan/{file_pre}_pan.txt', 'r') as file:
            pan_list = file.read().split('\n')

        closet_matches = difflib.get_close_matches(pan, pan_list, n=1, cutoff=0.9)

        if closet_matches:
            return closet_matches[0]
        else:
            return None
        
    def validate(pan:str):      

        prefix_lst = ['01','02','03','04','05','06','07','08','09','10','11','12','13','14','15','16','17',
                   '18','19','20','21','22','23','24','26','27','29','30','31','32','33','34','35','36',
                   '37','38','97']
        pan_lst = [pan for _ in range(len(prefix_lst))]
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = list(executor.map(PAN.find_match, prefix_lst, pan_lst))
        
        if results:
            results = list(filter(lambda x: x is not None, results))
            most_similar_pan = min(results,key=lambda s: Levenshtein.distance(pan, s))
        
            if most_similar_pan:
                return most_similar_pan
        return pan
