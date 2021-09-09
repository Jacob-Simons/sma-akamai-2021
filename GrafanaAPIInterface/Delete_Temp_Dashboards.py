import csv
from tempfile import NamedTemporaryFile
import shutil
import API_Processor
import datetime
import time

EVEN_LOG_NAMAE = 'temp_dash_log_even.csv'
ODD_LOG_NAME = 'temp_dash_log_odd.csv'
log_file = ""
DAY_SEC = 86400
api = API_Processor.GrafanaAPIProcessor()

while True:
    temp_log = NamedTemporaryFile(mode='w', delete=False)
    if int(datetime.datetime.now().strftime('%d')) % 2 == 0:
        log_file = EVEN_LOG_NAMAE
    else:
        log_file = ODD_LOG_NAME
    print(log_file)

    with open(log_file, newline='') as read_log, temp_log:
        log_reader = csv.reader(read_log, delimiter=',')
        log_writer = csv.writer(temp_log, delimiter=',')
        for row in log_reader:
            if len(row) != 0:
                print(row[1])
                calc_time = row[1]
                time_obj = datetime.datetime.strptime(calc_time, '%Y-%m-%d %H:%M:%S.%f')
                tdelta = datetime.datetime.now() - time_obj

                if tdelta.days > 7:
                    api.delete_dash(True, row[0])
                else:
                    log_writer.writerow(row)
        shutil.move(temp_log.name, log_file)

    time.sleep(DAY_SEC)




