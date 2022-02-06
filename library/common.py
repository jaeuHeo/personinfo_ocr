# -*- coding: utf-8 -*-
import os
import pwd
import json
import shutil
import requests
import datetime
from typing import Union, Optional
from pytz import timezone, utc

from django.db import connection
from django.http import HttpResponse
from django.conf import settings
from rest_framework.response import Response


class Message:
    """
    return_response 함수의 공통 메시지
    """
    message_200 = 'Success.'
    message_201 = 'Data is inserted.'
    message_203 = 'Non Authoritative Information'
    message_204 = 'Data does not exist.'
    message_400 = 'Parameter is not valid.'
    message_401 = 'Your token is not valid or does not exist.'
    message_404 = 'Data does not exist.'
    message_500 = 'Internal server error.'
    message_9999 = 'service updating'


def get_params(request)->dict:

    if request.method == 'GET':
        return request.query_params.dict()
    else:
        return request.data


def handle_textfile(method,txt_path,result_data=[]):

    if method == "POST":
        with open(txt_path, 'w') as f:
            f.write(json.dumps(result_data))
        chmod(txt_path)

    elif method == "GET":
        with open(txt_path, 'r') as f:
            lines = f.readlines()
        dict_collection = [json.loads(line) for line in lines]

        return dict_collection[0]


def remove_file(method,folder_path:str,txt_path:str='',file_list:list=[],pdf_extract_path:str=None):
    if method == "POST":
        if os.path.isdir(folder_path):
            if len(file_list) > 0:
                for file in file_list:
                    os.remove(file)
            if os.path.isdir(pdf_extract_path):
                shutil.rmtree(pdf_extract_path)

    elif method == "GET":
        if os.path.isdir(folder_path):
            shutil.rmtree(folder_path)
        if os.path.isfile(txt_path):
            os.remove(txt_path)


def return_response(
        status_code: int,
        data:Union[dict, list, str]=None,
        message:str=None,
        return_json:bool=False,
        response_type:str = 'rest_framework'
)-> Union[Response, HttpResponse]:
    """
    API Response 형식을 만들어주는 함수
        - Format: {"status": status, "message": message, "data": data}
    :param status_code: http response status
    :param data: response data
    :param message: response message
    :param return_json: return json 변환 여부
    :param response_type: response type 지정 (rest_framework, http)
    :return:
    """
    status_code_string = str(status_code)

    if not message:
        if hasattr(Message, "message_"+status_code_string):
            message = getattr(Message, "message_"+status_code_string)

    if status_code == 1111:
        message = '문서 분류 실패'
        data = {}
    elif status_code == 1112:
        message = '가족관계 데이터 추출 실패'
        data = {}

    response = {"resultCode": status_code, "resultMsg": message, "resultData": data}

    if return_json:
        response = json.dumps(response)

    if response_type == 'rest_framework':
        return Response(response)
    else:
        return HttpResponse(response, content_type="application/json")


def name_to_json(cursor):
    """
    cursor.fetchall() 함수로 받아온 쿼리 결과를 json 형식으로 만들어 반환해주는 함수입니다.
    :param cursor: SQL 연결 변수
    :return: JSON 쿼리 결과 LIST
    """
    row = [dict((cursor.description[i][0], value)
                for i, value in enumerate(row)) for row in cursor.fetchall()]
    return row


def db_execute(
        query:str,
        params:Union[dict, tuple, list],
        execute_type:str ='select',
        executemany:bool = False
)-> Optional[list]:
    """
    django.db connection 및 execute 해주는 함수입니다.
    :param query: 실행시킬 sql query 입니다.
    :param params: sql에 전달될 param 입니다.
    :param execute_type: 실행시킬 sql 명령어 타입으로 (select, delect, update, insert) 4가지를 지원합니다.
    :param executemany: 한개의 query문에 여러개의 param 데이터를 실행시킬지 여부입니다.
    :return:
    """
    with connection.cursor() as cur:
        if executemany:
            cur.executemany(query, params)
        else:
            cur.execute(query, params)
        if execute_type == 'select':
            data = name_to_json(cur)
            return data
        else:
            cur.execute('commit;')


def request_common_session_api(
        authorization:str,
        cno:str) -> dict:
    """
    inner gw를 통해 session에 등록되어 있는 user 정보를 가져옵니다.
    :param authorization: authorization
    :param cno: cno
    :return:
    """
    headers = {'Authorization': authorization}
    params = {'cno': cno}
    request_url = settings.INNER_URL + '/common/session'
    res = requests.get(request_url, params=params, headers=headers)

    session_info = json.loads(res.text)
    return session_info


def get_date()-> str:
    """
    현재 시간을 리턴합니다.
    :return:
    """
    KST = timezone('Asia/Seoul')
    now = datetime.datetime.utcnow()
    kst_now = utc.localize(now).astimezone(KST)

    return str(kst_now).split('.')[0]


def chmod(path, mode=0o777):
    os.chmod(path, mode)
