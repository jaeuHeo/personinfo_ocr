import re

from bs4 import BeautifulSoup


def html_parser(html):
    tag_info=[]

    bs = BeautifulSoup(html, 'html.parser')

    # print(bs.find_all('div'))
    # print(len(bs.find_all('div'))) # if len(bs.find_all('div')) < 16:
    # tags = bs.find_all('div')
    for idx, tag in enumerate(bs.find_all()):

        if tag.text and tag.get('style') is not None:
            tag_text = tag.text
            tag_text = re.sub("[()\n\ue000]", "", tag_text)

            tag_bbox = [int(re.sub(r'[^0-9]', '', stlist)) for stlist in tag.get('style').split(';')[3:7]]
            if len(tag_bbox) > 0:
                tag_bbox[2], tag_bbox[3] = tag_bbox[0] + tag_bbox[2], tag_bbox[1] + tag_bbox[3]
            #     print(tag_text, tag_bbox)
                tag_bbox.append(tag_text)
                tag_info.append(tag_bbox)

    return tag_info
