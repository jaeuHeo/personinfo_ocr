def select_personinfo_form_query(table, cols='*', where_col=None):
    if table == 'base':
        if where_col is not None:
            query = f"""select {str(cols)} from personinfo.personinfo_form_base where {str(where_col)} = %({str(where_col)})s order by num_doc ASC;"""
        else:
            query = f"""select {str(cols)} from personinfo.personinfo_form_base order by num_doc ASC;"""

    elif table == 'info':
        if where_col is not None:
            query = f"select {str(cols)} from personinfo.personinfo_form_info where {str(where_col)} = %({str(where_col)})s order by num_doc ,num_area;"
        else:
            query = f"select {str(cols)} from personinfo.personinfo_form_info  order by num_doc ,num_area;"

    return query


def insert_personinfo_image_query(cols=()):
    query = "insert into personinfo.personinfo_image" + str(cols) + " values (%s,%s);"
    return str(query)
