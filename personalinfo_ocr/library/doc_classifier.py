import json

import pandas as pd

from library.common import db_execute,return_response
from personalinfo_ocr.querys import select_personinfo_form_query
from personalinfo_ocr.library.parser import html_parser
from personalinfo_ocr.library.extract_pdf import pdf_extract
from .utils import char_error_cnt2, char_error_cnt, convert_to_text, search_value, execute_ocr, cleansing_valtext

KEYWWORD_EXTRA_PER_THRESHOLD = 0.8


def doc_clf(check_doc,form_list):
    num_form, form_name, form_sh = int(0), '미분류',[]  # num_doc of template image
    max_same_rate = 0
    if len(check_doc) > 0:
        for form in form_list:
            same_rate = char_error_cnt2(form[1], check_doc, return_type='per')
            if same_rate >= 0.8:
                if same_rate > max_same_rate:
                    max_same_rate = same_rate
                    form_name,num_form,form_sh = form[1],int(form[0]),list(form[2])

    return num_form, form_name, form_sh


def search_key(tag_info, form_info, type):

    new_tag_df = pd.DataFrame()

    if type == 'pdf':
        tag_df = pd.DataFrame(tag_info, columns=['x1','y1','x3','y3','ocr'])
        # print(tag_df)
        tag_df = tag_df.sort_values(by=['y1'], ascending=True)
        new_tag_df = pd.DataFrame(columns=tag_df.columns)

        for idx in tag_df.index:
            # print(tag_df)

            same_y1 = tag_df[(tag_df['y1'] >= tag_df['y1'][idx]-2) & (tag_df['y1'] <= tag_df['y1'][idx]+2)]
            # print(same_y1)
            same_y1 = same_y1.sort_values(by=['x1'], ascending=True)
            # ''.join(re.findall(r'\d{6}[-]\d{7}', join_txt))
            new_tag_df = pd.concat([new_tag_df,same_y1])
            # print(new_tag_df)
            new_tag_df = new_tag_df.drop_duplicates(keep='first',ignore_index=True)

    elif type == 'img':
        new_tag_df = tag_info

    test_info = []
    absent_count, key_count =0,0
    for i, info in enumerate(form_info):
        if i > 0:
            key = info['keyword']
            form_key = convert_to_text(key)
            if type == 'pdf':

                for ids, row in new_tag_df.iterrows():

                    test_key = convert_to_text(row['ocr'])

                    acc_per = char_error_cnt(form_key, test_key, return_type='per')

                    if acc_per > 0.9 and new_tag_df['ocr'][ids+3]:

                        name_num = {}
                        key_count += 1
                        name_num['relation'] = form_key
                        name_num['name'] = new_tag_df['ocr'][ids+1]
                        name_num['personNum'] = new_tag_df['ocr'][ids+3]
                        name_num = cleansing_valtext('', name_num)
                        if len(new_tag_df['ocr'][ids+1]) == 0 or new_tag_df['ocr'][ids+3] == 0:
                            absent_count += 1
                        test_info.append(name_num)
                        break


            elif type == 'img':
                # name_num = []
                for ids, row in new_tag_df.iterrows():
                    test_key = convert_to_text(row['ocr'])
                    acc_per = char_error_cnt(form_key, test_key, return_type='per')

                    if acc_per > 0.7:
                        name_num = [form_key,row.tolist()]

                        if name_num not in test_info:
                            test_info.append(name_num)
                        break
                # if name_num not in test_info and len(name_num) > 0:
                #     test_info.append(name_num)
    if type == 'pdf':
        per_attend = (key_count - absent_count) / key_count
    else:
        per_attend = None

    return test_info, per_attend


def ocr_keyword_extraction(form_num, ocr_df, form_sh):
    if form_num == 0 or len(ocr_df) == 0:
        img_result_list, per_absent = [], 0
        return img_result_list, per_absent

    query = select_personinfo_form_query(table='info', cols='*', where_col="num_doc")
    rows = db_execute(query, params={'num_doc': int(form_num)})
    form_info = [{'cr_keyword': json.loads(row['key_area']), 'cr_value': json.loads(row['val_areas']),
                  'keyword': row['txt_area']} for row in rows]

    test_df = ocr_df[1][['x1', 'y1', 'x3', 'y3', 'ocr', 'img_shape_x', 'img_shape_y']]
    test_info, per_pred_key = search_key(test_df, form_info, 'img')

    value_dic = search_value(test_info, form_info, test_df, form_sh)

    img_result_list = []
    for val in value_dic:
        if val not in img_result_list:
            img_result_list.append(val)
    return img_result_list, per_pred_key, form_info


def pdf_based_document_classifier(full_file_path, pdf_extract_path, form_list):
    html, join_text = pdf_extract(full_file_path, pdf_extract_path)
    num_form, name_form, sh_form = doc_clf(join_text, form_list)

    if name_form == '가족관계증명서':
        query = select_personinfo_form_query(table='info', cols='*', where_col="num_doc")
        doc_area_infos = db_execute(query, {'num_doc': int(num_form)})
        form_info = [{'cr_keyword': json.loads(row['key_area']), 'cr_value': json.loads(row['val_areas']),
                      'keyword': row['txt_area']} for idx, row in enumerate(doc_area_infos)]
        tag_info = html_parser(html)
        pdf_result_list, per_pred_key = search_key(tag_info, form_info, 'pdf')

        if per_pred_key > KEYWWORD_EXTRA_PER_THRESHOLD:
            return True, pdf_result_list, per_pred_key, name_form
        else:
            return False, pdf_result_list, per_pred_key, name_form
    else:
        return False, [], None, None


def images_based_document_classifier(pdf_img_list, form_list):
    # ocr
    execute_ok, ocr_df, join_text = execute_ocr(pdf_img_list)
    # key
    num_form, name_form, sh_form = doc_clf(join_text, form_list)

    if name_form != '미분류':
        img_result_list, _, form_info = ocr_keyword_extraction(num_form, ocr_df, sh_form)
        return name_form, img_result_list, form_info
    else:
        return name_form, [], []
