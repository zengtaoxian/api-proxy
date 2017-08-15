#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import tornado.options
import tornado.netutil
import tornado.httpserver
import tornado.httpclient
import tornado.ioloop
import tornado.web
import logging
import json
import time
import functools
import hashlib
import util
import convert
import timer

base_cfg = None


def generate_sign(body, auth_key):
    m = hashlib.md5()
    m.update(body)
    m.update(auth_key)
    return m.hexdigest().upper()


class BaseHandler(tornado.web.RequestHandler):
    def data_received(self, chunk):
        pass

    @property
    def session(self):
        return self.application.session

    @property
    def convert(self):
        return self.application.convert

    @property
    def timer(self):
        return self.application.timer

    @staticmethod
    def async_urlopen(url, method, headers=None, body=None, callback=None):
        http_client = tornado.httpclient.AsyncHTTPClient()
        http_client.fetch(request=url, callback=callback, method=method, headers=headers, body=body)

    def send_status(self, call_id, flag, status, timestamp):
        data = self.session[call_id]["data"]
        body = json.dumps(
            {"appId": data["appId"], "callId": data["callId"], "caller": data["aCaller"], "callee": data["aCallee"],
             "status": status, "timestamp": timestamp, "userFlag": flag})
        sign = generate_sign(body, base_cfg["rest_key"])
        url = "http://{0}:{1}/rest/status?sign={2}".format(base_cfg["rest_ip"], base_cfg["rest_port"], sign)

        logging.info(u"send status, url:{0}, call_id:{1}, body:{2}".format(url, call_id, body))
        self.async_urlopen(url=url, method="POST", body=body)

    def send_hangup(self, call_id, status):
        data = self.session[call_id]["data"]
        options = self.session[call_id]["options"]
        generate_status = options.get("generate_status", 0)

        invite_time = self.session[call_id].get("invite_time", 0)
        ring_time = self.session[call_id].get("ring_time", 0)
        answered_time = self.session[call_id].get("answered_time", 0)
        disconnected_time = self.session[call_id].get("disconnected_time", int(time.time()))
        end_reason = self.session[call_id].get("end_reason", 0)

        if 0 == status:
            if generate_status:
                if not invite_time:
                    invite_time = self.session[call_id].get("req_time") + 1

                self.send_status(call_id, 1, 1, invite_time)

                if not ring_time:
                    ring_time = invite_time + 3

                self.send_status(call_id, 1, 2, ring_time)

                if answered_time:
                    self.send_status(call_id, 1, 3, answered_time)

                self.send_status(call_id, 1, 4, disconnected_time)

            sip_code = 200
        else:
            if generate_status:
                self.send_status(call_id, 1, 5, disconnected_time)

            sip_code = 480

        body = json.dumps({"appId": data["appId"], "callId": data["callId"], "addr": base_cfg["listen_ip"],
                           "caller": data["aCaller"], "callee": data["aCallee"],
                           "inviteTime": invite_time, "ringTime": ring_time, "answeredTime": answered_time,
                           "disconnectedTime": disconnected_time, "endReason": end_reason, "sipCode": sip_code,
                           "apiType": data["apiType"], "status": status})
        sign = generate_sign(body, base_cfg["rest_key"])
        url = "http://{0}:{1}/rest/hangup?sign={2}".format(base_cfg["rest_ip"], base_cfg["rest_port"], sign)

        logging.info(u"send hangup, url:{0}, call_id:{1}, body:{2}".format(url, call_id, body))
        self.async_urlopen(url=url, method="POST", body=body)


class RequestHandler(BaseHandler):
    def send_resp(self, resp_code, call_id=None):
        time_array = time.localtime(time.time())
        create_date = time.strftime("%Y%m%d%H%M%S", time_array)
        resp_body = {"createDate": create_date, "addr": base_cfg.get("listen_ip"), "respCode": str(resp_code)}
        if call_id:
            resp_body["callId"] = call_id
        self.finish(resp_body)

    def get(self, *args, **kwargs):
        unit = self.request.path.split('/')
        if len(unit) < 3:
            logging.error("path is error, url:{0}.".format(self.request.path))
            self.send_error(400)
            return None

        msg = unit[2]
        logging.info(u"recv {0} req, url:{1}, arguments:{2}".format(msg, self.request.path, self.request.arguments))

        time_array = time.localtime(time.time())
        create_date = time.strftime("%Y%m%d%H%M%S", time_array)

        data_arg = self.get_argument("data", "").encode("utf-8")
        data = json.loads(data_arg)
        if not len(data):
            logging.error("data not found.")
            self.send_resp(2)
            return None

        orig_sign = self.get_argument("sign", "")
        if not len(orig_sign):
            logging.error("sign not found.")
            self.send_resp(1)
            return None

        new_sign = generate_sign(data_arg, base_cfg["auth_key"])
        if new_sign != orig_sign:
            logging.error("sign not match, orig:{0}, new:{1}.".format(orig_sign, new_sign))
            self.send_resp(1)
            return None

        call_id = data.get("callId", None)
        if not call_id:
            logging.error("callId not found.")
            self.send_resp(1)
            return None

        if not data.get("appId", None):
            logging.error("appId not found.")
            self.send_resp(1, call_id)
            return None

        brand = data.get("brand", "")
        if not len(brand):
            self.send_resp(1, call_id)
            return None

        if not data.get("aCaller", None):
            logging.error("aCaller not found.")
            self.send_resp(1, call_id)
            return None

        if not data.get("aCallee", None):
            logging.error("aCallee not found.")
            self.send_resp(1, call_id)
            return None

        if not data.get("svrType", None):
            logging.error("svrType not found.")
            self.send_resp(1, call_id)

        api_type = data.get("apiType", None)
        if not api_type:
            logging.error("apiType not found.")
            self.send_resp(1, call_id)
            return None

        if not data.get("playTimes", None):
            logging.error("playTimes not found.")
            self.send_resp(1, call_id)
            return None

        if not data.get("reqType", None):
            logging.error("reqType not found.")
            self.send_resp(1, call_id)
            return None

        try:
            # save request data
            self.session[call_id] = {"data": data}

            # set request time
            self.session[call_id]["req_time"] = int(time.time())

            # set request timeout time
            self.timer.add_item(base_cfg.get("request_timeout", 5), call_id, self.request_timeout)

            # get options
            options = self.convert.get_options(api_type, msg)
            self.session[call_id]["options"] = options

            send_body = eval(self.convert.build_send_body(api_type, msg, data))

            callback = functools.partial(self.on_response, api_type, msg, call_id)

            self.async_urlopen(send_body["url"], send_body["method"], send_body["head"], send_body["body"],
                               callback)

            logging.info(u"send request, api_type:{0}, url:{1}, body:{2}".format(api_type, send_body["url"],
                                                                                 send_body["body"]).encode("utf-8"))

            self.send_resp(0, call_id)
        except Exception, e:
            logging.error("e:{0}".format(e))

    def on_response(self, api_type, msg, call_id, response):
        resp_body = response.body
        logging.info(
            "recv {0} resp, api_type:{1}, call_id:{2}, resp_body:{3}".format(msg, api_type, call_id, resp_body))
        recv_args = self.convert.parse_recv_body(api_type, msg, resp_body)
        if recv_args and (recv_args.get("result", None) == '0'):
            # save response args
            for k, v in recv_args.items():
                self.session[call_id][k] = v

            # set max allow timeout time
            self.timer.add_item(base_cfg.get("max_allow_timeout", "7200"), call_id, self.max_allow_timeout)

            logging.info("add session, api_type:{0}, call_id:{1}".format(api_type, call_id))

    def request_timeout(self, call_id):
        logging.error("session request timeout, call_id:{0}".format(call_id))

        options = self.session[call_id]["options"]
        generate_status = options.get("generate_status", 0)

        # failed
        if not generate_status:
            self.send_status(call_id, 1, 5, int(time.time()))

        # no ring
        self.send_hangup(call_id, 2)

    def max_allow_timeout(self, call_id):
        logging.warn("session max allow timeout, call_id:{0}".format(call_id))

        options = self.session[call_id]["options"]
        generate_status = options.get("generate_status", 0)

        # disconnected
        if not generate_status:
            self.send_status(call_id, 1, 5, int(time.time()))

        # success
        self.send_hangup(call_id, 0)


class StatusHandler(BaseHandler):
    def post(self, *args, **kwargs):
        unit = self.request.path.split('/')
        if len(unit) < 4:
            logging.error("path is error, url:{0}.".format(self.request.path))
            self.send_error(400)
            return None

        msg = unit[2]
        api_type = unit[3]

        logging.info(
            u"recv {0} req, url:{1}, arguments:{2}, body:{3}".format(msg, self.request.path, self.request.arguments,
                                                                     self.request.body))

        try:
            recv_args = self.convert.parse_recv_body(api_type, msg, self.request.body)
            call_id = recv_args.get("callId")
            status = recv_args.get("status")
            timestamp = recv_args.get("timestamp")
            if status == 1:
                self.session[call_id]["invite_time"] = timestamp
            elif status == 2:
                self.session[call_id]["ring_time"] = timestamp
            elif status == 3:
                self.session[call_id]["answered_time"] = timestamp
            elif status == 4 or status == 5:
                self.session[call_id]["disconnected_time"] = timestamp

            send_body = eval(self.convert.build_send_body(api_type, msg, self.session[call_id]["data"]))
            self.finish(send_body["body"])

            self.send_status(call_id, 1, status, timestamp)
        except Exception, e:
            logging.error("e:{0}".format(e))


class HangupHandler(BaseHandler):
    def post(self, *args, **kwargs):
        hangup_body = self.request.body
        logging.info("path:{0}, arguments:{1}, body:{2}".format(self.request.path, self.request.arguments, hangup_body))

        unit = self.request.path.split('/')
        if len(unit) < 4:
            logging.error("path is error.")

        msg = unit[2]
        api_type = unit[3]

        try:
            recv_args = self.convert.parse_recv_body(api_type, msg, hangup_body)
            call_id = recv_args.get("callId")
            status = recv_args.get("status")

            send_body = eval(self.convert.build_send_body(api_type, msg, self.session[call_id]["data"]))
            self.finish(send_body["body"])

            self.send_hangup(call_id, status)
        except Exception, e:
            logging.error("e:{0}".format(e))


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/api/request", RequestHandler),
            (r"/api/status", StatusHandler),
            (r"/api/hangup/(.*)", HangupHandler)
        ]

        settings = {
            "debug": True,
        }

        self.session = {}
        self.convert = convert.Convert()
        self.timer = timer.Timer()

        tornado.web.Application.__init__(self, handlers, **settings)


if __name__ == "__main__":
    base_cfg = util.load_cfg("base.json")

    tornado.options.parse_command_line()
    sockets = tornado.netutil.bind_sockets(port=base_cfg.get("listen_port", 8998),
                                           address=base_cfg.get("listen_ip", "0.0.0.0"),
                                           backlog=base_cfg.get("backlog", 150000))
    server = tornado.httpserver.HTTPServer(Application(), no_keep_alive=True, xheaders=True)
    server.add_sockets(sockets)
    tornado.ioloop.IOLoop.instance().start()
