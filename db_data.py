import pandas as pd
import csv
import psycopg2
import json
from datetime import date, datetime
#JSON Encoder
class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)

#Function for getting result from db for history
def get_history_for_single(serial_num = None):
    try:
        conn = psycopg2.connect(
            dbname="devices",
            user="dssadmin",
            password="dssadmin",
            host="10.10.2.180"
        )
        cursor = conn.cursor()
        query_ten = """
            SELECT test_name, test_date, test_time, test_result, test_status 
            FROM public.test_results_new
            WHERE serial_num LIKE %s 
            ORDER BY test_name asc, test_date asc, test_time asc;"""
        cursor.execute(query_ten, (serial_num,))
        rows = cursor.fetchall()

    except psycopg2.Error:
        return None

    else:
        if conn:
            conn.close()

    return rows

#Function for parsing data from db for history
def parse_data(rows):
    parsed_data = {}

    for entry in rows:
        category, date, time, result, status = entry
        date_str = date.strftime('%Y-%m-%d')

        try:
            tmp = float(status)
        except ValueError:
            if "Mbit/s" not in status and "mbit/s" not in status and "Mbps" not in status and "mbps" not in status and "sec" not in status and "Sec" not in status:
                entry_data = f'{date_str} {time} {"+" if result else "-"}'
            else:
                entry_data = f'{date_str} {time} {"+" if result else "-"} {status}'
        else:
            entry_data = f'{date_str} {time} {"+" if result else "-"} {status}'
        if category not in parsed_data:
            parsed_data[category] = {'strings': [], 'result': True}

        parsed_data[category]['strings'].append(entry_data)
        parsed_data[category]['result'] = result

    return parsed_data

#Get_report_date is function to output rows
def get_report_data(start_date = None, end_date = None, serial_num = None):
    rows_global = ()
    if serial_num:
        serial_num = '%' + serial_num + '%'
    try:
        conn = psycopg2.connect(
            dbname="devices",
            user="dssadmin",
            password="dssadmin",
            host="10.10.2.180"
        )
        cursor = conn.cursor()
        #For history of tests
        #For avoiding empty results
        if not serial_num and start_date and end_date:
            second_query = """
                            WITH RankedTestResults AS (
                                SELECT
                                    serial_num,
                                    test_name,
                                    test_date,
                                    test_time,
                                    test_result,
                                    test_status,
                                    ROW_NUMBER() OVER (PARTITION BY serial_num, test_name ORDER BY test_date DESC, test_time DESC) AS rnk
                                FROM
                                    public.test_results_new
                            )
                            SELECT 
                                serial_num 
                            FROM 
                                RankedTestResults
                            WHERE 
                                rnk = 1
                                AND test_date BETWEEN %s AND %s
                            GROUP BY
                                serial_num
                            ORDER BY
                                MAX(test_date || ' ' || test_time) DESC"""
            cursor.execute(second_query, (start_date, end_date))
            second_rows = cursor.fetchall()
            serial_nums_tuple = tuple(row[0] for row in second_rows)
            query = """
                    WITH RankedTestResults AS (
                        SELECT
                            serial_num,
                            test_name,
                            test_date,
                            test_time,
                            test_result,
                            test_status,
                            ROW_NUMBER() OVER (PARTITION BY serial_num, test_name ORDER BY test_date DESC, test_time DESC) AS rnk
                        FROM
                            public.test_results_new
                    )
                    SELECT
                        serial_num,
                        jsonb_object_agg(
                            test_name,
                            jsonb_build_object(
                                'date', test_date,
                                'time', test_time,
                                'result', test_result,
                                'status', test_status   
                            )
                        ) AS test_results
                    FROM
                        RankedTestResults
                    WHERE
                        rnk = 1
                        AND serial_num IN %s
                        
                    GROUP BY
                        serial_num
                    ORDER BY
                        MAX(test_date || ' ' || test_time) DESC;
                    """
            cursor.execute(query, (serial_nums_tuple,))
            rows = cursor.fetchall()
            rows_global = rows
        #For all other cases
        else:
            third_query = """
                        WITH RankedTestResults AS (
                            SELECT
                                serial_num,
                                test_name,
                                test_date,
                                test_time,
                                test_result,
                                test_status,
                                ROW_NUMBER() OVER (PARTITION BY serial_num, test_name ORDER BY test_date DESC, test_time DESC) AS rnk
                            FROM
                                public.test_results_new
                        )
                        SELECT
                            serial_num,
                            jsonb_object_agg(
                                test_name,
                                jsonb_build_object(
                                    'date', test_date,
                                    'time', test_time,
                                    'result', test_result,
                                    'status', test_status   
                                )
                            ) AS test_results
                        FROM
                            RankedTestResults
                        WHERE
                            rnk = 1
                            AND (%s IS NULL OR test_date BETWEEN %s AND %s)
                            AND (%s IS NULL OR serial_num LIKE %s)
                        GROUP BY
                            serial_num
                        ORDER BY    
                            MAX(test_date || ' ' || test_time) DESC;
                        """
            cursor.execute(third_query, (start_date, start_date, end_date, serial_num, serial_num))
            rows = cursor.fetchall()
            rows_global = rows


    except psycopg2.Error:
        return None

    else:
        if conn:
            conn.close()
    #For removing all status values except the speed
    for x in rows_global:
        test_results = x[1]
        for y in test_results.items():
            try:
                tmp = float(y[1]["status"])
            except:
                if "Mbit/s" not in y[1]["status"] and "mbit/s" not in y[1]["status"] and "Mbps" not in y[1]["status"] and "mbps" not in y[1]["status"] and "sec" not in y[1]["status"] and "Sec" not in y[1]["status"]:
                    y[1]["status"] = ""
    return rows_global

def get_history(start_date=None, end_date=None, serial_num=None):
    rows_global = ()
    if serial_num:
        serial_num = '%' + serial_num + '%'
    try:
        conn = psycopg2.connect(
            dbname="devices",
            user="dssadmin",
            password="dssadmin",
            host="10.10.2.180"
        )
        cursor = conn.cursor()
        if not serial_num and start_date and end_date:
            fifth_query = """
                            WITH RankedTestResults AS (
                                SELECT
                                    serial_num,
                                    test_name,
                                    test_date,
                                    test_time,
                                    test_result,
                                    test_status,
                                    ROW_NUMBER() OVER (PARTITION BY serial_num, test_name ORDER BY test_date DESC, test_time DESC) AS rnk
                                FROM
                                    public.test_results_new
                            )
                            SELECT 
                                serial_num 
                            FROM 
                                RankedTestResults
                            WHERE 
                                rnk = 1
                                AND test_date BETWEEN %s AND %s
                            GROUP BY
                                serial_num
                            ORDER BY
                                MAX(test_date || ' ' || test_time) DESC"""
            cursor.execute(fifth_query, (start_date, end_date))
            second_rows = cursor.fetchall()
            serial_nums_tuple = tuple(row[0] for row in second_rows)
            sixth_query = """
                    WITH RankedTestResults AS (
                        SELECT
                            serial_num,
                            test_name,
                            test_date,
                            test_time,
                            test_result,
                            test_status,
                            ROW_NUMBER() OVER (PARTITION BY serial_num, test_name ORDER BY test_date DESC, test_time DESC) AS rnk
                        FROM
                            public.test_results_new
                    )
                    SELECT
                        serial_num,
                        jsonb_object_agg(
                            test_name,
                            jsonb_build_object(
                                'date', test_date,
                                'time', test_time,
                                'result', test_result,
                                'status', test_status   
                            )
                        ) AS test_results
                    FROM
                        RankedTestResults
                    WHERE
                        rnk = 1
                        AND serial_num IN %s

                    GROUP BY
                        serial_num
                    ORDER BY
                        MAX(test_date || ' ' || test_time) DESC;
                    """
            cursor.execute(sixth_query, (serial_nums_tuple,))
            rows = cursor.fetchall()
            rows_global = rows
        else:
            seventh_query = """
                        WITH RankedTestResults AS (
                            SELECT
                                serial_num,
                                test_name,
                                test_date,
                                test_time,
                                test_result,
                                test_status,
                                ROW_NUMBER() OVER (PARTITION BY serial_num, test_name ORDER BY test_date DESC, test_time DESC) AS rnk
                            FROM
                                public.test_results_new
                        )
                        SELECT
                            serial_num,
                            jsonb_object_agg(
                                test_name,
                                jsonb_build_object(
                                    'date', test_date,
                                    'time', test_time,
                                    'result', test_result,
                                    'status', test_status   
                                )
                            ) AS test_results
                        FROM
                            RankedTestResults
                        WHERE
                            rnk = 1
                            AND (%s IS NULL OR test_date BETWEEN %s AND %s)
                            AND (%s IS NULL OR serial_num LIKE %s)
                        GROUP BY
                            serial_num
                        ORDER BY
                            MAX(test_date || ' ' || test_time) DESC;
                        """
            cursor.execute(seventh_query, (start_date, start_date, end_date, serial_num, serial_num))
            rows = cursor.fetchall()
            rows_global = rows

    except psycopg2.Error:
        return None

    else:
        if conn:
            conn.close()
    for x in rows_global:
        test_results = x[1]
        for y in test_results.items():
            try:
                tmp = float(y[1]["status"])
            except:
                if "Mbit/s" not in y[1]["status"] and "mbit/s" not in y[1]["status"] and "Mbps" not in y[1]["status"] and "mbps" not in y[1]["status"] and "sec" not in y[1]["status"] and "Sec" not in y[1]["status"]:
                    y[1]["status"] = ""

    return rows_global

#Function for getting data for excel
def get_data_excel_history(serial_num_history):
    rows_global_2 = ()
    try:
        conn = psycopg2.connect(
            dbname="devices",
            user="dssadmin",
            password="dssadmin",
            host="10.10.2.180"
        )
        cursor = conn.cursor()
        twelvth_query = """                                
                            SELECT
                                serial_num,
                                test_name,
                                test_date,
                                test_time,
                                test_result,
                                test_status
                            FROM
                                public.test_results_new
                            WHERE 
                                serial_num = %s
                            ORDER BY
                                serial_num, test_name, test_date DESC, test_time DESC;
                                    """
        cursor.execute(twelvth_query, (serial_num_history,))
        rows = cursor.fetchall()
        rows_global_2 = rows
    except psycopg2.Error:
        return None
    else:
        if conn:
            conn.close()
    return rows_global_2

if __name__ == '__main__':
    print("Wassap body")
#Function for getting statistics
def get_stats(rows):
    if rows is None:
        return {'Total': 0, 'True': 0, 'False': 0}
    total_rows = 0
    j = 0
    failed = 0
    for x in rows:
        j = 0
        total_rows = total_rows + 1
        test_results = x[1]
        for y in test_results.items():
            if y[1]["result"] == 0 and y[0] != 'distance_test' and y[0] != 'usb':
                j = j + 1
                # print(x[0])
        if j > 0:
            failed = failed + 1;
    success = total_rows - failed
    my_information = {'Total': total_rows, 'True': success, 'False': failed}
    return my_information
