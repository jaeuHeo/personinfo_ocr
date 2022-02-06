# -*- coding: utf-8 -*-
import os
import time
import uuid
import json
import psycopg2

from django.conf import settings
from rest_framework.decorators import api_view

import middleware
from library.common import get_params, return_response, db_execute, remove_file, chmod
from library.file import listdir_fullpath, split_path
from personalinfo_ocr.querys import select_personinfo_form_query, insert_personinfo_image_query
from personalinfo_ocr.library.utils import merging_ocr_data, resultprocess_extractor, extract_pdf_pages, get_pdf_num_of_pages
from personalinfo_ocr.library.doc_classifier import pdf_based_document_classifier, images_based_document_classifier


@api_view(['GET'])
def get_alive_check(request):
    """
    alive_check
    :param request:
    :return:
    """
    return return_response(status_code=200)


@api_view(['GET'])
def get_unique_key(request):
    """
    unique key를 생성합니다.
    :param request:
    :return:
    """
    key = str(uuid.uuid4())
    # path = os.path.join(settings.FILES_PATH, key)
    # os.makedirs(path)
    # chmod(path)

    return return_response(status_code=200, data={'key':key})


@api_view(['POST'])
def upload_file(request):
    """
    파일을 업로드 받고 저장합니다.
    :param request:
    :return:
    """
    data = get_params(request)
    key = data.get('key', None)
    file = request.FILES.get('file', None)
    # save_path = os.path.join(settings.FILES_PATH, key)
    middleware.KIBANA_DIC[request.META['access_id']] = key
    company_no = 9
    # file_path = save_path + '/'+ file.name
    # default_storage.save(save_path, file)
    # with open(file_path, 'wb') as w:
    #
    #     for chunk in file.chunks():
    #         w.write(chunk)
    #
    # chmod(file_path)
    insert_data = (key,psycopg2.Binary(file))

    conn = Connection()
    cur = conn.cursor()
    query = insert_personinfo_image_query(cols="(key, image_byte)")
    print(query)
    # query = select_personinfo_form_query(table='base', cols='*', where_col="company_no")
    db_execute(query, params={'company_no': company_no})
    return return_response(status_code=200,data={})


@api_view(['POST','GET'])
def extractor(request):

    data = get_params(request)
    key = data.get('key',None)
    company_no = 9

    # folder_path = os.path.join(settings.FILES_PATH, key)
    middleware.KIBANA_DIC[request.META['access_id']] = key

    # txt_path = os.path.join(settings.FILES_PATH, key + '.txt')

    if request.method == "POST":
        # file_list = listdir_fullpath(folder_path)

        # if len(file_list) >= 5:
        #     return return_response(status_code=500, message = '페이지 수가 너무 많습니다.')

        # file = file_list[0]

        filename, extension = split_path(file)
        full_file_path = filename+extension

        query = select_personinfo_form_query(table='base', cols='*', where_col="company_no")
        rows = db_execute(query, params={'company_no': company_no})
        form_list = [[row['num_doc'], row['name_doc'], json.loads(row['shape_doc'])] for row in rows]
        pdf_extract_path = os.path.join(folder_path, 'pdf')

        success_cls = False
        pdf_result_list = []
        if extension.lower() == '.pdf':
            num_pages = get_pdf_num_of_pages(full_file_path)
            if num_pages > 1:
                extract_pdf_pages(file, filename+'_0'+extension, 0,file_list)
            file_list = listdir_fullpath(folder_path)
            file = file_list[0]
            filename, extension = split_path(file)
            full_file_path = filename + extension

            os.makedirs(pdf_extract_path, exist_ok=True)
            chmod(pdf_extract_path)

            success_cls, pdf_result_list, per_absent, name_form = pdf_based_document_classifier(full_file_path, pdf_extract_path, form_list)

            if success_cls:
                path_list = [folder_path, txt_path, pdf_extract_path]
                result_data = [name_form, pdf_result_list]
                result_dic = resultprocess_extractor(request, path_list = path_list, file_list = file_list, result_data = result_data)
                if len(result_dic['data']) == 0:
                    return return_response(status_code=1112)
                else:
                    return return_response(status_code=200, data={})

        if success_cls == False:
            if extension.lower() == '.pdf':
                img_list = listdir_fullpath(pdf_extract_path)
            else:
                img_list = listdir_fullpath(folder_path)

            name_form, img_result_list, form_info = images_based_document_classifier(img_list, form_list)

            print(f'이 문서는 {name_form} 입니다' + '\n')

            if name_form == '미분류':
                remove_file(method='GET', folder_path = folder_path, txt_path =  txt_path, file_list=file_list, pdf_extract_path=pdf_extract_path)
                return return_response(status_code=1111)

            if name_form == '가족관계증명서':
                if extension.lower() == '.pdf':
                    result_list = merging_ocr_data(form_info, pdf_result_list, img_result_list)
                else:
                    result_list = img_result_list
            else:
                result_list = img_result_list

            path_list = [folder_path, txt_path, pdf_extract_path]
            result_data = [name_form, result_list]
            result_dic = resultprocess_extractor(request, path_list=path_list, file_list=file_list, result_data=result_data)

            if len(result_dic['data']) == 0:
                remove_file('GET', folder_path, txt_path, file_list, pdf_extract_path)
                return return_response(status_code=1112)
            else:
                return return_response(status_code=200, data={})

    elif request.method == "GET":
        path_list = [folder_path, txt_path, '']
        result_dic = resultprocess_extractor(request,path_list)

        return return_response(status_code=200, data=result_dic)

