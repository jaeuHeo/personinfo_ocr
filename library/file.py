import os
import glob
from typing import Tuple


# def listdir_fullpath(path:str)-> list:
#     """
#     특정 path에 있는 파일리스트의 fullpath list를 호출합니다.
#     :param path:
#     :return:
#     """
#
#     return [os.path.join(path, f) for f in os.listdir(path)]


def listdir_fullpath(path: str) -> list:
    """
    특정 path에 있는 파일리스트의 fullpath list를 호출합니다.
    :param path:
    :return:
    """
    targetPattern = r'{}/*.*'.format(path)
    return glob.glob(targetPattern)

def split_path(path:str)-> Tuple[str, str]:
    """
    파일명과 확장자를 분리합니다.
    :param path:
    :return:
    """
    filename, file_extension = os.path.splitext(path)
    return filename, file_extension
