from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, LogoutView
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views import generic

from DocSigningSystem import db_data
from warehouse import utils
from warehouse.models import Log, ArticulRoster
from django.http import HttpResponse
import csv
class Index(generic.TemplateView):
    template_name = 'index.html'


class Login(LoginView):
    def form_valid(self, form):
        Log.objects.create(operation='Login',
                           log={'пользователь': self.request.POST.get('username'),
                                'IP адрес': self.request.META.get('REMOTE_ADDR', 'Unknown IP'),
                                'браузер': self.request.META.get('HTTP_USER_AGENT', 'Unknown Browser')
                                }
                           )
        return super().form_valid(form)


class Logout(LogoutView):
    def dispatch(self, request, *args, **kwargs):
        Log.objects.create(operation='Logout',
                           log={'пользователь': self.request.user.email,
                                'IP адрес': self.request.META.get('REMOTE_ADDR', 'Unknown IP'),
                                'браузер': self.request.META.get('HTTP_USER_AGENT', 'Unknown Browser')
                                }
                           )
        return super().dispatch(request, *args, **kwargs)


def get_cuman_articul(request, part_no):
    adjusted = utils.remove_prefix(part_no)
    item = ArticulRoster.objects.filter(Q(part_no__iexact=adjusted) |
                                        Q(analog_1__iexact=adjusted) |
                                        Q(analog_2__iexact=adjusted) |
                                        Q(analog_3__iexact=adjusted)).first()
    if item and item.cuman_articul:
        return JsonResponse({'cuman_article': item.cuman_articul})
    else:
        return JsonResponse({'cuman_article': 'Артикул не найден в реестре'})


class UserListView(LoginRequiredMixin, generic.ListView):
    template_name = 'main/user_list.html'
    model = get_user_model()
    context_object_name = 'users'
    paginate_by = 20

    def get_queryset(self):
        return self.model.objects.filter(is_in_user_list=True).order_by('second_name')


@login_required
def user_search(request):
    search_input = request.GET.get('user_search') or ''
    if search_input:
        try:
            users = get_user_model().objects.filter(
                Q(first_name__icontains=search_input) |
                Q(second_name__icontains=search_input) |
                Q(last_name__icontains=search_input) |
                Q(email__icontains=search_input) |
                Q(second_email__icontains=search_input) |
                Q(personal_phone_number__icontains=search_input) |
                Q(service_phone_number__icontains=search_input) |
                Q(job_position__icontains=search_input) |
                Q(dept_no__name__icontains=search_input), is_in_user_list=True,
            )
            return render(request, 'main/user_list.html', context={'users': users})
        except AttributeError:
            pass


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
        #stats = db_data.get_stats(rows_history)
        stats = db_data.get_stats(rows)
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
            excel_file = db_data.get_report_data(start_date, end_date, serial_num)
        elif start_date and end_date:
            excel_file = db_data.get_report_data(start_date=start_date, end_date=end_date)
        elif serial_num:
            excel_file = db_data.get_report_data(serial_num=serial_num)
        elif serial_num_history:
            excel_file = db_data.get_data_excel_history(serial_num_history=serial_num_history)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="output.csv"'
        if serial_num_history:
            writer = csv.writer(response)
            writer.writerow(['Serial_Number', 'Test_Name', 'Date', 'Time', 'Result', 'Status'])
            for row in excel_file:
                writer.writerow(row)
        else:
            test_names = {'led', 'wan', 'lan1', 'lan2', 'lan3', 'lan4',
                          'wifi_2g_1', 'wifi_2g_2', 'wifi_2g_3', 'wifi_2g_4',
                          'wifi_2g_5', 'wifi_2g_6', 'wifi_2g_7', 'wifi_2g_8', 'wifi_2g_9', 'reset_test', 'wifi_2g_10',
                          'wifi_2g_11', 'wifi_5g_36', 'wifi_5g_40', 'wifi_5g_44',
                          'wifi_5g_48', 'processes_test', 'mac_address_test'}
            for row in excel_file:
                test_results = row[1]  # Assuming the test results are in the second column
                if isinstance(test_results, dict):
                    test_names.update(test_results.keys())
                else:
                    print(f"Test results for serial number {serial_num} is not in the expected format.")
            test_names = sorted(test_names)
            csv_writer = csv.writer(response)
            header_row = ['Serial Number'] + sum([[f'{name}'] for name in test_names], [])
            csv_writer.writerow(header_row)
            for row in excel_file:
                serial_number = row[0]
                test_results = row[1]
                data_row = [serial_number]

                if isinstance(test_results, dict):
                    for test_name in test_names:
                        if test_name in test_results:
                            test_data = test_results[test_name]
                            test_info = f"{test_data.get('date', '')}, {test_data.get('time', '')}, {test_data.get('result', '')}, {test_data.get('status', '')}"
                            data_row.append(test_info)
                        else:
                            data_row.append('')  # If test data is not available, populate empty value
                else:
                    # If test_results is not a dictionary, populate empty values for all test names
                    data_row.extend([''] * len(test_names))
                csv_writer.writerow(data_row)
        return response

def custom_404_view(request, exception):
    return render(request, 'exception_pages/404.html', status=404)


def custom_500_view(request):
    return render(request, 'exception_pages/500.html', status=500)


def custom403(request):
    return render(request, 'exception_pages/403.html')
