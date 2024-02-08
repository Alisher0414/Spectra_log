def get_logs(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    serial_num = request.GET.get('serial_num')
    if serial_num: serial_num = '%' + serial_num + '%'
    serial_num_history = request.GET.get('serial_num_history')
    if start_date and end_date and serial_num:

        rows = db_data.get_report_data(start_date,end_date,serial_num)
    elif start_date and end_date:

        rows = db_data.get_report_data(start_date,end_date)
    elif serial_num:

        rows = db_data.get_report_data(serial_num = serial_num)
        rows_history = db_data.get_history(serial_num = serial_num)

    elif serial_num_history:
        raw_data = db_data.get_history_for_single(serial_num_history)
        parsed_data = db_data.parse_data(raw_data)
        rows = [(serial_num_history, parsed_data)]

    else:
        rows = db_data.get_report_data()

    if serial_num and not start_date and not end_date:
        stats = db_data.get_stats(rows_history)
    else:
        stats = db_data.get_stats(rows)
    test_names = ['led', 'wan', 'lan1', 'lan2', 'lan3', 'lan4',
                    'wifi_2g_1', 'wifi_2g_2', 'wifi_2g_3', 'wifi_2g_4',
                  'wifi_2g_5', 'wifi_2g_6', 'wifi_2g_7', 'wifi_2g_8', 'wifi_2g_9', 'reset_test', 'wifi_2g_10',
                  'wifi_2g_11', 'wifi_5g_36', 'wifi_5g_40', 'wifi_5g_44',
                  'wifi_5g_48', 'processes_test', 'mac_address_test']

    paginator = Paginator(rows, 100)

    page = request.GET.get('page')
    try:
        rows = paginator.page(page)
    except PageNotAnInteger:

        rows = paginator.page(1)
    except EmptyPage:

        rows = paginator.page(paginator.num_pages)
    return render(request, 'spectra_log.html', {'rows': rows,'stats': stats,
                                                'names': test_names,'serial_num_history': serial_num_history})


def get_import(request):
    if request.method == "POST":
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        serial_num = request.POST.get('serial_num')
        serial_num_history = request.POST.get('serial_num_history')
        if start_date and end_date and serial_num:
            excel_file = db_data.get_data_excel_mixed(start_date,end_date,serial_num)
        elif start_date and end_date:
            excel_file = db_data.get_data_excel_date(start_date=start_date,end_date=end_date)
        elif serial_num:
            excel_file = db_data.get_data_excel_serial(serial_num=serial_num)
        elif serial_num_history:
            excel_file = db_data.get_data_excel_history(serial_num_history=serial_num_history)

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="output.csv"'
        writer = csv.writer(response)
        writer.writerow(['Serial_Number', 'Test_Name', 'Date', 'Time', 'Result', 'Status'])
        for row in excel_file:
            writer.writerow(row)
        return response
