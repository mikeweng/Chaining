import logging
import requests
import json
import base64
from chain.config import RESP_404, SVG, ENV
from flask import Flask, request, jsonify

svc_name = ENV.SVC_NAME
svc_secret = ENV.SVC_SECRET

logging.basicConfig(format='%(asctime)s [%(levelname)s] %(message)s', level=logging.DEBUG)
log = logging.getLogger(svc_name)
app = Flask(svc_secret)


def _svc_log(svc=svc_name, status=None):
    return {'service_name': svc, 'status': status}


def _svc_log_header(hops_path, next_hops, received_header):
    hops_log = []
    if received_header:     # Process previous hops
        log_byte = base64.b64decode(received_header)
        hops_log = json.loads(log_byte)

    if len(hops_path) == 1:
        # Requesting coming directly from user, supplement request path for user
        hops_log.append(_svc_log(svc_name))

    if len(next_hops) == 0:
        hops_log[-1]['status'] = 200
        return hops_log, None
    # Append current outgoing pending request
    hops_log.append(_svc_log(next_hops[0]))
    return hops_log, base64.b64encode(json.dumps(hops_log).encode('utf-8'))


def _p_hops(recv_header, req_subdir):
    next_hops = req_subdir.split('/') if req_subdir else []
    log.debug(f'Future Hops to visit: {next_hops}')
    hops_log = []
    if recv_header:     # Decode Previous Hops Log
        log_byte = base64.b64decode(recv_header)
        hops_log = json.loads(log_byte)

    hops_log.append(_svc_log(svc_name))

    if len(next_hops) == 0:     # Final request hop
        return hops_log, [], None

    next_hop_host = next_hops[0]
    if app.debug:
        next_hop_host = request.host    # Debugging map all 'microservices' to local
        if request.path == '/dead':
            next_hop_host = '34.95.119.80/bar-api.bar'

    next_hop_subdir = '/'.join(next_hops[1:])
    next_hop_url = f'{ENV.PROTOCOL}://{next_hop_host}/{next_hop_subdir}'
    return hops_log, next_hops, next_hop_url


def _get_fmt(hops_log, user_request_fmt):
    if user_request_fmt:    # Respect user hard code
        return user_request_fmt
    return 'html' if len(hops_log) == 1 else 'json'


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def entry(path: str):
    log.debug(f'Request /{path} from {request.remote_addr}')
    if path in RESP_404:
        return '', 404
    hops_log, next_hops, next_hop_url = _p_hops(request.headers.get(ENV.HEADER_REQ_LOG, ''), path)

    fmt = _get_fmt(hops_log, request.headers.get(ENV.HEADER_REQ_FMT, ''))

    if not next_hop_url:    # Final hop
        hops_log[-1]['status'] = 200
        return _materialize_response(None, hops_log, fmt=fmt)

    next_hop_resp = None
    next_hop_resp_code = 200
    try:
        resp = requests.get(
            next_hop_url,
            headers={ENV.HEADER_REQ_LOG: base64.b64encode(json.dumps(hops_log).encode('utf-8'))},
            timeout=len(next_hops) + 1
        )
        next_hop_resp = resp.json()
    except requests.exceptions.ConnectionError:
        log.info(f'Connection Failed when connecting to {next_hop_url}')
        next_hop_resp_code = 503
    except requests.exceptions.Timeout:
        log.info(f'Connection Timeout when connecting to {next_hop_url}')
        next_hop_resp_code = 408

    log.debug(f'Next Hop {next_hop_resp_code} Response {next_hop_resp}')
    hops_log.append(_svc_log(next_hops[0], next_hop_resp_code))
    return _materialize_response(next_hop_resp, hops_log, fmt=fmt)


@app.route('/xkcd')
def xkcd():
    """Getting current XKCD comic"""
    log.debug("Retrieving current XKCD comic")
    try:
        resp = requests.get("https://xkcd.com/info.0.json")
    except requests.exceptions.ConnectionError:
        return f'XKCD not reachable..'
    ret = resp.json()
    img = ret.get('img', '')
    title = ret.get('safe_title', "Loading...")
    return f'<html><head></head><body><h3>{title}</h3><img src="{img}"></body></html>'


def _materialize_response(next_hop_resp, hops_log, fmt='json'):
    if not next_hop_resp:
        secret = svc_secret if hops_log[-1]['status'] == 200 else 'error'
    else:
        secret = next_hop_resp.get('service_secret', 'error')
        hops_log = next_hop_resp.get('service_log', [])

    if fmt == 'html':
        return f"""
        <html><body>

        <div style="display: flex; flex-direction: column">
        <center><h4>{secret}</h4></center>
        {__generate_svg(hops_log)}
        </div>

        </body></html>"""
    else:       # default to json
        return jsonify(service_secret=secret, service_log=hops_log)


def __generate_svg(hop_path):
    nodes = [('user', None)]
    for i in hop_path:
        nodes.append((i['service_name'], i['status']))

    width = 2 * SVG.CR * len(nodes) + SVG.PADDING_LR * 2 + SVG.PADDING_CR * (len(nodes) - 1)
    xys = []
    for i, node in enumerate(nodes):
        x = SVG.PADDING_LR + SVG.CR + (2 * SVG.CR + SVG.PADDING_CR) * i
        y = int(SVG.HEIGHT / 2)
        xys.append((x, y, node))

    resp = f"""
    <svg width="{width}" height="{SVG.HEIGHT}" style="margin: 0 auto;">
      <marker id="arrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="rgb(65,141,85)" />
      </marker>
      <marker id="arrowerr" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="red" />
      </marker>
      <rect width="{width}" height="{SVG.HEIGHT}" style="fill:rgb(230,230,230)" />
    """

    network_path = []
    for i, (x, y, (node, status)) in enumerate(xys):
        resp += f"""<circle cx="{x}" cy="{y}" r="{SVG.CR}" fill="rgb(210,226,241)" />
        <text text-anchor="middle" x="{x}" y="{y}" fill="rgb(102,102,102)">{node}</text>
        """
        if i < len(xys) - 1:
            nx, ny, _ = xys[i + 1]
            mid_circle = int((nx - x)/2)
            _, _, (_, next_status) = xys[i + 1]
            if next_status is None or next_status == 200:
                arrow_color = SVG.COLOR_ARR
                arrow_id = 'url(#arrow)'
            else:
                arrow_color = SVG.COLOR_ERR
                arrow_id = 'url(#arrowerr)'

            network_path.append(
                f"""<path d="M {x} {y - SVG.CR} q {mid_circle} -{SVG.CR} {nx - x} {ny - y}" 
                stroke="{arrow_color}" stroke-width="2" fill="None" marker-end="{arrow_id}" />"""
            )
            network_path.append(
                f"""<path d="M {x} {y + SVG.CR} q {mid_circle} {SVG.CR} {nx - x} {ny - y}" 
                stroke="{arrow_color}" stroke-width="2" fill="None" marker-start="{arrow_id}" />"""
            )

    resp += ''.join(network_path)
    resp += "</svg>"
    return resp
