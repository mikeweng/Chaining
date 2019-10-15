import os

RESP_404 = ['favicon.ico']


class SVG(object):
    HEIGHT = 200        # Total Height
    CR = 30             # Circle radius
    PADDING_LR = 20     # Padding Left & Right
    PADDING_CR = 40     # Padding between circles
    COLOR_ERR = 'red'
    COLOR_ARR = 'green'     # Arrow color


class ENV(object):
    PROTOCOL = 'http'
    HEADER_SVC_VISITED = 'X-Svc-Visited'
    HEADER_REQ_LOG = 'X-Svc-Log'
    HEADER_REQ_FMT = 'X-Chain-Fmt'

    SVC_NAME = os.environ.get('FC_SVC_NAME', 'default')
    SVC_SECRET = os.environ.get('FC_SVC_SECRET', 'default_secret')

