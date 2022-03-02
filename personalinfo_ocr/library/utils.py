import re
import os
import json
import time
import requests
import PyPDF2
import cv2
import numpy as np
import pandas as pd

from skimage import io
from typing import Tuple

from django.conf import settings

from personalinfo_ocr.library.modules import _make_value_list
from library.common import remove_file, handle_textfile, chmod


def convert_to_text(text):
    text = re.sub('[-=+,#/\?:^$.@*\"※~&%ㆍ!』\\‘|\(\)\[\]\<\>`\'…》]', '', text).replace(" ", "")
    text = ''.join(text.split())
    return text


def char_error_cnt(target_text, text, return_type='cnt'):
    #     text = text.replace(' ', '')

    docompose_target_text = convert(target_text)
    s_decompose_text = convert(text)

    t_size = len(docompose_target_text)
    if t_size == 0:
        return 0
    len_diff = np.abs(t_size - len(s_decompose_text))
    cer_error_cnt_list = []
    if (t_size - len(s_decompose_text)) > 0:

        for i in range(len_diff + 1):

            sample_text = s_decompose_text
            sample_text += [''] * (len(docompose_target_text) - len(
                s_decompose_text) - i)  # for i in range(len(docompose_target_text) - len(s_decompose_text)-c)]
            #             print(sample_text)
            if i > 0:
                sample_text.insert(0, '')
                sample_text.pop(-1)
            #             print(sample_text,docompose_target_text)
            cer_error_cnt = (np.array(sample_text) == np.array(docompose_target_text)).sum()
            cer_error_cnt_list.append(cer_error_cnt)



    elif (t_size - len(s_decompose_text)) == 0:

        sample_text = s_decompose_text

        cer_error_cnt = (np.array(sample_text) == np.array(docompose_target_text)).sum()

        cer_error_cnt_list.append(cer_error_cnt)

    else:

        for i in range(len_diff + 1):
            sample_text = docompose_target_text
            sample_text += [''] * (len(s_decompose_text) - len(
                docompose_target_text) - i)  # for i in range(len(docompose_target_text) - len(s_decompose_text)-c)]

            if i > 0:
                sample_text.insert(0, '')
                sample_text.pop(-1)

            cer_error_cnt = (np.array(sample_text) == np.array(s_decompose_text)).sum()
            cer_error_cnt_list.append(cer_error_cnt)

    if return_type == 'cnt':
        return np.max(cer_error_cnt_list)

    if return_type == 'per':
        if (t_size - len(s_decompose_text)) < 0:
            return np.max(cer_error_cnt_list) / len(s_decompose_text)
        else:

            return np.max(cer_error_cnt_list) / t_size



def convert(test_keyword):
    split_keyword_list = list(test_keyword)
    # 유니코드 한글 시작 : 44032, 끝 : 55199
    BASE_CODE, CHOSUNG, JUNGSUNG = 44032, 588, 28
    # 초성 리스트. 00 ~ 18
    CHOSUNG_LIST = ['ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ', 'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']
    # 중성 리스트. 00 ~ 20
    JUNGSUNG_LIST = ['ㅏ', 'ㅐ', 'ㅑ', 'ㅒ', 'ㅓ', 'ㅔ', 'ㅕ', 'ㅖ', 'ㅗ', 'ㅘ', 'ㅙ', 'ㅚ', 'ㅛ', 'ㅜ', 'ㅝ', 'ㅞ', 'ㅟ', 'ㅠ', 'ㅡ', 'ㅢ',
                     'ㅣ']
    # 종성 리스트. 00 ~ 27 + 1(1개 없음)
    JONGSUNG_LIST = [' ', 'ㄱ', 'ㄲ', 'ㄳ', 'ㄴ', 'ㄵ', 'ㄶ', 'ㄷ', 'ㄹ', 'ㄺ', 'ㄻ', 'ㄼ', 'ㄽ', 'ㄾ', 'ㄿ', 'ㅀ', 'ㅁ', 'ㅂ', 'ㅄ', 'ㅅ',
                     'ㅆ', 'ㅇ', 'ㅈ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ']

    result = list()
    for keyword in split_keyword_list:
        # 한글 여부 check 후 분리
        if re.match('.*[ㄱ-ㅎㅏ-ㅣ가-힣]+.*', keyword) is not None:

            char_code = ord(keyword) - BASE_CODE

            if char_code >= 0:
                char1 = int(char_code / CHOSUNG)

                result.append(CHOSUNG_LIST[char1])

                #             print('result1',result)
                char2 = int((char_code - (CHOSUNG * char1)) / JUNGSUNG)
                result.append(JUNGSUNG_LIST[char2])
                #             print('result2',result)
                char3 = int((char_code - (CHOSUNG * char1) - (JUNGSUNG * char2)))
                if char3 == 0:
                    continue
                #                 result.append('#')
                else:
                    result.append(JONGSUNG_LIST[char3])
        #             print('result3',result)

        else:
            result.append(keyword)
    return result


def char_error_cnt2(target_text, text, return_type='cnt'):
    #     text = text.replace(' ', '')

    docompose_target_text = convert(target_text)
    s_decompose_text = convert(text)

    t_size = len(docompose_target_text)
    if t_size == 0:
        return 0

    if len(s_decompose_text) < t_size:
        return 0

    len_diff = np.abs(t_size - len(s_decompose_text))
    cer_error_cnt_list = []

    for i in range(len_diff + 1):

        sample_text = docompose_target_text
        sample_text += [''] * (len(s_decompose_text) - len(
            docompose_target_text) - i)  # for i in range(len(docompose_target_text) - len(s_decompose_text)-c)]

        if i > 0:
            sample_text.insert(0, '')
            sample_text.pop(-1)

        cer_error_cnt = (np.array(sample_text) == np.array(s_decompose_text)).sum()

        cer_error_cnt_list.append(cer_error_cnt)

    if return_type == 'cnt':
        return np.max(cer_error_cnt_list)

    if return_type == 'per':
        return np.max(cer_error_cnt_list) / t_size


def load_img(img_path):
    print(img_path)
    img = io.imread(img_path)  # RGB order
    if img.shape[0] == 2: img = img[0]
    if len(img.shape) == 2: img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    if img.shape[2] == 4:   img = img[:, :, :3]
    img = np.array(img)

    return img


def post_request(img_path,end_point='text_detection', add_data={}):
    try:
        myfile = {
            'image': open(img_path, 'rb')
        }

        response = requests.request("POST", verify=False, url=settings.MODEL_API_URL+end_point+'/', files=myfile, data=add_data)

        data = response.text
        if end_point == 'text_detection':
            return True, json.loads(data)['bboxes']
        else:
            return True, json.loads(data)

    except Exception as e:
        print('detection_error', e)
        return False, {}


def merge_predict2(bboxes, result_list, img):
    # # OCR 결과 Dataframe 생성

    bboxes = np.array(bboxes).astype(int)
    bboxes_df = pd.DataFrame(bboxes.reshape(-1, 8), columns=['x1', 'y1', 'x2', 'y2', 'x3', 'y3', 'x4', 'y4'])

    temp = np.array(result_list)
    # print(temp)
    bboxes_df['ocr'] = temp
    #     bboxes_df['per'] = temp[:, 2]
    merge_df = bboxes_df.copy()
    default_df = bboxes_df.copy()
    for i in range(5):
        #         print(merge_df)
        merge_df = merging_area(merge_df, img)
        #         if i == 0:
        #             merge_df = merge_df
        bboxes_df = pd.concat([bboxes_df, merge_df])
    #     bboxes_df = pd.concat([bboxes_df,merge_df])

    bboxes_df['height'] = bboxes_df['y4'] - bboxes_df['y1']
    bboxes_df['width'] = bboxes_df['x2'] - bboxes_df['x1']
    default_df['height'] = default_df['y4'] - default_df['y1']
    default_df['width'] = default_df['x2'] - default_df['x1']

    return bboxes_df, default_df


def merging_area(temp, img):
    temp['left_min_x_p'] = [np.min([x1, x4]) for x1, x4 in temp[['x1', 'x4']].values.tolist()]
    temp['right_max_x_p'] = [np.min([x2, x3]) for x2, x3 in temp[['x2', 'x3']].values.tolist()]
    temp['top_min_y_p'] = [np.min([y1, y2]) for y1, y2 in temp[['y1', 'y2']].values.tolist()]
    temp['bottom_max_y_p'] = [np.max([y4, y3]) for y4, y3 in temp[['y4', 'y3']].values.tolist()]

    ## 오른쪽변 높이 추출
    temp['right_height'] = temp['y3'] - temp['y2']

    temp = temp.sort_values(['y1', 'x1'])
    temp['unique_no'] = temp.index

    for idx, row in temp.iterrows():
        merge_target = temp[(row['right_max_x_p'] <= temp.left_min_x_p)]
        #     print(row)
        merge_target = merge_target[(row['top_min_y_p'] - row['right_height'] / 2) <= merge_target.top_min_y_p]

        merge_target = merge_target[(row['bottom_max_y_p'] + row['right_height'] / 2) >= merge_target.bottom_max_y_p]

        inner_df = merge_target.copy()

        merge_target = merge_target[(row['right_max_x_p'] + row['right_height']) >= merge_target.left_min_x_p]

        #         if len(inner_df.ocr) ==1:
        #             merge_target = pd.concat([merge_target,inner_df])

        if merge_target.shape[0] != 0:

            temp.loc[merge_target.index, 'unique_no'] = row['unique_no']

            temp = temp.sort_index()

        else:

            temp.loc[idx, 'x2'], temp.loc[idx, 'x3'] = row['x2'] + row['right_height'] / 2, row['x3'] + row[
                'right_height'] / 2

    ### 병합된 좌표 추출
    p1 = temp.sort_values(['unique_no', 'left_min_x_p']).groupby('unique_no')[['x1', 'y1', 'x4', 'y4']].head(1).values
    p2 = temp.sort_values(['unique_no', 'left_min_x_p']).groupby('unique_no')[['x2', 'y2', 'x3', 'y3']].tail(1).values
    ocr_df = pd.DataFrame(np.concatenate((p1, p2), axis=1), columns=['x1', 'y1', 'x4', 'y4', 'x2', 'y2', 'x3', 'y3'])

    ### ocr 병합
    ocr_df['ocr'] = temp.sort_values(['unique_no', 'left_min_x_p']).groupby('unique_no').ocr.apply(
        lambda x: ' '.join(x)).values
    ocr_df = ocr_df[['x1', 'y1', 'x2', 'y2', 'x3', 'y3', 'x4', 'y4', 'ocr']]
    ### 정렬

    return ocr_df


def ocr_to_merge(ocr_data, img)->Tuple[pd.DataFrame, pd.DataFrame, np.array]:
    result_list = {'bboxes': [], 'ocr': []}

    for i in ocr_data.get('data', []):
        # if float(i['per']) >= 0.5:
        pts = i['vertices']
        result_list['bboxes'].append([pts['x1'], pts['y1'], pts['x2'], pts['y2'], pts['x3'], pts['y3'], pts['x4'], pts['y4']])
        result_list['ocr'].append(i['ocr'])
    t = time.time()

    result_list, def_df = merge_predict2(result_list['bboxes'], result_list['ocr'], img)

    print('merging time:', time.time() - t)
    results = [result_list, def_df, img]

    return results

def cleansing_valtext(title_form, val_append_dic):

    if val_append_dic['name'].replace(' ', '') != '' or val_append_dic['personNum'].replace(' ', '') != '':
        try:
            val_append_dic['name'] = \
            re.sub('[-=+,#/\?:^.@*\"※~ㆍ!』‘|\(\)\[\]`\'…》\”\“\’·]', ',', val_append_dic['name']).split(',')[0]
            val_append_dic['name'] = re.sub('(ㄱ-ㅎㅏ-ㅣ)+', '', val_append_dic['name'])
            val_append_dic['name'] = re.sub('[^A-Za-z가-힣]', '', val_append_dic['name'])
            val_append_dic['personNum'] = re.sub('[^0-9]', ' ', val_append_dic['personNum'])
            val_append_dic['personNum'] = ' '.join(val_append_dic['personNum'].split())
        except:
            pass
        # if title_form == '가족관계증명서':
        #     try:
        #         val_append_dic['name'] = re.sub('[-=+,#/\?:^.@*\"※~ㆍ!』‘|\(\)\[\]`\'…》\”\“\’·]', ',', val_append_dic['name']).split(',')[0]
        #         val_append_dic['name'] = re.sub('(ㄱ-ㅎㅏ-ㅣ)+','',val_append_dic['name'])
        #         val_append_dic['name'] = re.sub('[^A-Za-z가-힣]', '', val_append_dic['name'])
        #         val_append_dic['personNum'] = re.sub('[^0-9]', ' ', val_append_dic['personNum'])
        #         val_append_dic['personNum'] = ' '.join(val_append_dic['personNum'].split())
        #     except:
        #         pass
        # elif title_form == '주민등록증':
        #     try:
        #         val_append_dic['name'] = re.sub('[-=+,#/\?:^.@*\"※~ㆍ!』‘|\(\)\[\]`\'…》\”\“\’·]', ',', val_append_dic['name']).split(',')[0]
        #         val_append_dic['name'] = re.sub('(ㄱ-ㅎㅏ-ㅣ)+', '', val_append_dic['name'])
        #         val_append_dic['name'] = re.sub('[^A-Za-z가-힣]', '', val_append_dic['name'])
        #         val_append_dic['personNum'] = re.sub('[^0-9]', ' ', val_append_dic['personNum'])
        #         val_append_dic['personNum'] = ' '.join(val_append_dic['personNum'].split())
        #     except:
        #         pass

    return val_append_dic


def search_value(test_info, form_info, test_df, form_sh):

    value_dic = []
    # pred_val_box_list = []
    title_form = form_info[0]['keyword']
    for idx,form in enumerate(form_info):

        if idx > 0: ###문서제목(index=0) 패스

            val_append_dic = _make_value_list(form, test_info, form_sh, test_df)

            if val_append_dic is not None:

                val_append_dic = cleansing_valtext(title_form, val_append_dic)
                value_dic.append(val_append_dic)
    return value_dic


def execute_ocr(img_paths):

    def _merging_pages(ocr_data:Tuple)->Tuple[pd.DataFrame, pd.DataFrame, list]:
        merging_ocr_df, ori_ocr_df, img_list = pd.DataFrame(), pd.DataFrame(), []
        for t_merging_ocr_df, t_ori_ocr_df, img in ocr_data:
            merging_ocr_df = merging_ocr_df.append(t_merging_ocr_df)
            ori_ocr_df = ori_ocr_df.append(t_ori_ocr_df)
            img_list.append(img)
        return [merging_ocr_df, ori_ocr_df, img_list]

    result_ocr_data = []
    for img_path in img_paths:
        test_img = load_img(img_path)

        test_sh = [test_img.shape[0], test_img.shape[1]]

        version, run_type = 'v3', 'demo'
        is_ok, ocr_data = post_request(img_path, end_point='ocr',
                                       add_data={"bboxes": 'true', "version": version,
                                                 "run_type": run_type})

        ocr_data = ocr_to_merge(ocr_data, test_img)

        ocr_data[1]['img_shape_x'] = test_sh[1]
        ocr_data[1]['img_shape_y'] = test_sh[0]
        result_ocr_data.append(ocr_data)
    result_ocr_data = _merging_pages(result_ocr_data)
    join_text = convert_to_text(''.join(result_ocr_data[1]['ocr'])) if len(result_ocr_data[1]) > 1 else ''

    if join_text == '':
        return False, result_ocr_data, join_text
    else:
        return True, result_ocr_data, join_text


def merging_ocr_data(form_info=[], pdf_result_list=[], img_result_list=[]):

    def _make_merge_dic(form, result_list, merge_dic):
        merge_dic_cp = merge_dic.copy()
        for idx, info in enumerate(result_list):
            if form['keyword'] == info['relation']:
                merge_dic_cp['relation'] = info['relation']
                if len(info['name']) > 0:
                    merge_dic_cp['name'] = info['name']
                if len(info['personNum']) > 0:
                    merge_dic_cp['personNum'] = info['personNum']

        return merge_dic_cp

    def _replace_val(merge_dic,merge_img_dic,dic_key):
        if len(merge_dic[dic_key]) == 0:
            merge_dic[dic_key] = merge_img_dic[dic_key]
        return merge_dic[dic_key]

    merge_dic_list = []
    for idx, form in enumerate(form_info):
        if idx > 0:
            merge_dic = {'relation': '', 'name': '', 'personNum': ''}
            if len(pdf_result_list) > 0:
                merge_dic = _make_merge_dic(form, pdf_result_list, merge_dic)

            if len(img_result_list) > 0:
                merge_img_dic = _make_merge_dic(form, img_result_list, merge_dic)
                merge_dic['relation'] = _replace_val(merge_dic, merge_img_dic, 'relation')
                merge_dic['name'] = _replace_val(merge_dic, merge_img_dic, 'name')
                merge_dic['personNum'] = _replace_val(merge_dic, merge_img_dic, 'personNum')

            if len(merge_dic['name']) > 0 or len(merge_dic['personNum']) > 0:
                merge_dic_list.append(merge_dic)
    return merge_dic_list

def resultprocess_extractor(request,path_list=['','',''],file_list:list=[],result_data:list=['',[]]):

    folder_path, txt_path, pdf_extract_path = path_list
    name_form, result_list = result_data
    method = request.method
    result_dic = {'doc_name': name_form, 'data': result_list}

    if method == "POST":
        # chmod(folder_path)
        remove_file(method=method, folder_path = folder_path, file_list=file_list, pdf_extract_path=pdf_extract_path)
        handle_textfile(method, txt_path, result_data=result_dic)

    elif method == "GET":
        result_dic = handle_textfile(method, txt_path, result_data=result_dic)
        remove_file(method=method, folder_path=folder_path, txt_path = txt_path, file_list=file_list)

    return result_dic

def extract_pdf_pages(pdf_file_path, pdf_out_file_path, page_list_to_extract,file_list):
    with open(pdf_file_path, 'rb') as src_pdf_file:
        pdf_reader = PyPDF2.PdfFileReader(src_pdf_file)
        pdf_writer = PyPDF2.PdfFileWriter()
        # PDF 첫 번째 페이지를 추출하려면 정수 1이 아닌 0을 전달해야 한다.
        # for page_number in range(page_list_to_extract):
        pdf_writer.addPage(pdf_reader.getPage(page_list_to_extract))

        if len(file_list) > 0:
            for file in file_list:
                os.remove(file)
        # Source PDF 파일의 스트림을 끊기 전에 output PDF 파일을 write해야 한다.
        with open(pdf_out_file_path, 'wb') as out_file:
            pdf_writer.write(out_file)


def get_pdf_num_of_pages(pdf_file_path):
    with open(pdf_file_path, 'rb') as src_pdf_file:
        pdf_reader = PyPDF2.PdfFileReader(src_pdf_file)
        num_of_pages = pdf_reader.numPages
    return num_of_pages