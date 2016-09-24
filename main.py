"""Ad Ops Toolkit.
Usage:
    main.py download (1day|7days|30days) (<start_date>) [<end_date>] [--saveto=<path>]

Note that <start date> is the most recent date, and based on the report duration (1 day, 7 days, 30 days) this program
will go back the duration amount of days until it reaches <end date>

For example 'download 30days 2015-12-31 2015-01-01' will start by downloading 2015-12-31, go back 30 days to download
2015-12-01, 2015-11-01, ... until it reaches 2015-01-05. Note that 2015-01-05 will be the last report downloaded, and
because it's a 30 day report will include data until 2014-12-07
"""
from docopt import docopt
from datetime import datetime, timedelta
from config import settings
import os
import requests
import json
import urllib
import re

AUTH = {'Content-Type': 'application/json', "TTD-Auth": settings['ttd']['token']}
API_BASE = settings['ttd']['api-base']
PARTNER_ID = settings['ttd']['partnerid']

def validate_date(date):
    try:
        datetime.strptime(date, '%Y-%m-%d')
    except ValueError:
        raise ValueError('Incorrect date format; should be: YYYY-MM-DD')

def validate_date_range(start_date, end_date):
    if start_date >= end_date:
        pass
    else:
        raise ValueError('Start Date is past End Date.')

def validate_path(path):
    try:
        os.path.abspath(path)
    except ValueError:
        raise ValueError('Ensure that --saveto= argument is a valid path')

def validate_and_set_parameters(arguments):
    params = {}
    if arguments['1day']:
        params['duration'] = '1day'
    elif arguments['7days']:
        params['duration'] = '7days'
    elif arguments['30days']:
        params['duration'] = '30days'

    validate_date(arguments['<start_date>'])
    params['start_date'] = arguments['<start_date>']
    
    if arguments['<end_date>']:
        validate_date_range(params['start_date'], arguments['<end_date>'])
        validate_date(arguments['<end_date>'])
        params['end_date'] = arguments['<end_date>']
    else:
        params['end_date'] = arguments['<start_date>']

    if arguments['--saveto']:
        validate_path(arguments['--saveto'])
        params['save_path'] = arguments['--saveto']
    return params

def get_advertisers():
    url = ''.join([API_BASE, '/overview/partner/', PARTNER_ID])

    r = requests.get(url, headers=AUTH)
    rsp = r.json()
    all_advertisers = []
    
    for advertiser in rsp['Advertisers']:
        all_advertisers.append(advertiser['AdvertiserId'])
    return all_advertisers

def get_reports(advertisers, timestamp):
    reports = []

    for advertiser in advertisers:
        payload = {"AdvertiserID": advertiser.encode('ascii','ignore'), "ReportDateUTC": timestamp}
        reports.append(requests.post(''.join([API_BASE, '/hdreports']), headers=AUTH, json=payload))
    return reports

def filter_url(reports):
    if params['duration'] == '1day':
        duration = 'OneDay'
    elif params['duration'] == '7days':
        duration = 'SevenDays'
    elif params['duration'] == '30days':
        duration = 'ThirtyDays'

    urls = []
    for report in reports['Result']:
        if report['Duration'] == duration and report['Scope'] == "Advertiser":
            if report['Type'] != "ExcelPivotReports":
                urls.append(report['DownloadUrl'])
    return urls

def get_report_urls(params):

    start_date = datetime.strptime(''.join([params['start_date'], ' 14:00:01.092598']), '%Y-%m-%d %H:%M:%S.%f')
    end_date = datetime.strptime(''.join([params['end_date'], ' 14:00:01.092598']), '%Y-%m-%d %H:%M:%S.%f')
    working_date = start_date
    urls= []
    duration = params['duration']
    if duration == '1day':
        daygap = 1
    elif duration == '7days':
        daygap = 7
    elif duration == '30days':
        daygap = 30

    advertiser_ids = get_advertisers()
    while working_date >= end_date:
        report_urls = get_reports(advertiser_ids, str(working_date))

        for report in report_urls:
            urls.append(filter_url(json.loads(report.text)))
        working_date = working_date - timedelta(days=daygap)

    return urls

def download_reports(urls, duration, savepath):
    searchstring = ''.join(['.*', duration, '/(.*)\?'])
    p = re.compile(searchstring)
    for url in urls:
        for u in url:
            try:
                filename = p.match(u).groups()[0]
                print "-- Downloading: %s" % filename
                filename = urllib.unquote(filename).decode('utf8')
                testfile = urllib.URLopener()
                testfile.retrieve(u, os.path.join(savepath, filename))
            except:
                print "Error downloading: %s" % u

if __name__ == "__main__":
    args = docopt(__doc__, version="Ad Ops Toolkit 0.1")

    if args['download']:
        params = validate_and_set_parameters(args)
        urls = get_report_urls(params)

        duration = params['duration']
        savepath = params['save_path']
        download_reports(urls, duration, savepath)


