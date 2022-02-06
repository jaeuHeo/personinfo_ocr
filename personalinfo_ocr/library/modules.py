# -*- coding: utf-8 -*-
import re

def _make_value_list(form,test_info,form_sh,test_df):
    val_append_dic = {'relation': form['keyword'], 'name': '', 'personNum': ''}
    for test in test_info:  # test's cols are [form_keyword,['x1', 'y1', 'x3', 'y3', 'ocr', 'img_shape_x', 'img_shape_y']]
        if len(test[0]) > 0:
            if form['keyword'] == test[0]:
                cr_name, cr_personNum = form['cr_value']
                val_append_dic = _find_value_box(test,form,form_sh,test_df,val_append_dic,form_cr_val={'name':cr_name, 'personNum':cr_personNum})

                # else:
                #     val_append_list = {'relation': form['keyword'], 'valwords': []}
                #     val_text_list = []
                #     pred_val_box = find_value_box(test, form, form_sh, text_h, form_cr_val=form['cr_value'])
                #
                #     # pred_val_box_list.append(pred_val_box)
                #
                #     for ids, tbox in enumerate(test_df.values.tolist()):
                #         if IoU(tbox[0:4], pred_val_box) >= 0.8:
                #             val_text = tbox[4]
                #             val_text_list.append(val_text)
                #
                #     if val_text_list not in val_append_list['valwords']:
                #         if len(val_text_list) > 0:
                #             val_text_list = ''.join(val_text_list)
                #
                #     val_append_list['valwords'] = val_text_list
                if val_append_dic['name'].replace(' ','') != '' or val_append_dic['personNum'].replace(' ','') != '':
                    val_append_dic['personNum'] = re.sub('[^0-9]', ' ', val_append_dic['personNum'])
                    val_append_dic['personNum'] = ' '.join(val_append_dic['personNum'].split())
                    # val_append_dic['personNum'] = ' '.join(val_append_dic['personNum'])
                    return val_append_dic

                # else:
                #     return None



def _find_value_box(test,form,form_sh,test_df,val_append_dic,form_cr_val:dict) -> dict:

    text_h = (test[1][3] - test[1][1]) / test[1][6]
    for val, box in form_cr_val.items():

        pred_val_box = [
            (test[1][0] / test[1][5] + (box['p1'][0] - form['cr_keyword']['p1'][0]) / form_sh[1]) * test[1][5] - (text_h / 2 * test[1][6]),
            (test[1][1] / test[1][6] + (box['p1'][1] - form['cr_keyword']['p1'][1]) / form_sh[0] - text_h / 4) * test[1][6],

            (test[1][2] / test[1][5] + (box['p3'][0] - form['cr_keyword']['p3'][0]) / form_sh[1]) * test[1][5] + (text_h / 2 * test[1][6]),
            (test[1][3] / test[1][6] + (box['p3'][1] - form['cr_keyword']['p3'][1]) / form_sh[0] + text_h / 4) * test[1][6]
        ]

        val_text_list = []
        for ids, tbox in enumerate(test_df.values.tolist()):
            if IoU(tbox[0:4], pred_val_box) >= 0.8:
                # val_text = tag_df.loc[ids,'ocr']
                val_text = tbox[4]

                if val_text not in val_text_list:
                    val_text_list.append(val_text)

        if len(val_text_list) > 0:
            val_append_dic[val] = ' '.join(val_text_list)

    return val_append_dic


def IoU(box1, box2):  # box2가 regist (기준)
    # box = (x1, y1, x2, y2)
    box1_area = (box1[2] - box1[0] + 1) * (box1[3] - box1[1] + 1)
    box2_area = (box2[2] - box2[0] + 1) * (box2[3] - box2[1] + 1)

    # obtain x1, y1, x2, y2 of the intersection
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[2], box2[2])
    y2 = min(box1[3], box2[3])

    # compute the width and height of the intersection

    # w,h = 0,0

    w = max(0, x2 - x1 + 1)
    h = max(0, y2 - y1 + 1)

    inter = w * h
    #     iou = inter / (box1_area + box2_area - inter)
    iou = inter / box1_area
    #     if inter > 0 and inter <= box1_area and inter/box2_area >=0.8:
    #         iou = 1

    return iou