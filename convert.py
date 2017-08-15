#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import os
import util
import logging
import time
import re


class Convert:
    def __init__(self):
        self.api = {}
        self.load_mod()
        self.variable = {
            "now": self.variable_now,
            "ignore": self.variable_ignore
        }
        logging.info("load, api:{0}, variable:{1}".format(self.api, self.variable))

    @staticmethod
    def variable_now():
        return str(int(time.time()))

    @staticmethod
    def variable_ignore():
        return "[\s\S]*?"

    @staticmethod
    def load_msg(file_dir):
        msg_cfg = {}
        msg_list = os.listdir(file_dir)
        for msg in msg_list:
            msg_units = msg.split(".json")
            if len(msg_units) > 1:
                msg_name = msg_units[0]
                msg_cfg[msg_name] = util.load_cfg(os.path.join(file_dir, msg))
        return msg_cfg

    def load_api(self):
        api_cfg = {}
        api_dir = "mod"
        api_list = os.listdir(api_dir)
        for api in api_list:
            if os.path.isdir(os.path.join(api_dir, api)):
                self.api[api] = self.load_msg(os.path.join(api_dir, api))
        return api_cfg

    def load_mod(self):
        self.load_api()

    def msg_valid(self, api, msg):
        api_cfg = self.api.get(api, None)
        if not (api_cfg and api_cfg.get(msg, None)):
            self.load_mod()
            logging.info("reload, api:{0}".format(self.api))
            api_cfg = self.api.get(api, None)
            if not(api_cfg and api_cfg.get(msg, None)):
                return False
        return True

    def variable_convert(self, msg_fmt):
        for vk, vv in self.variable.items():
            fmt = "$#{0}#$".format(vk)
            if msg_fmt.count(fmt) > 0:
                msg_fmt = msg_fmt.replace(fmt, vv())
        return msg_fmt

    @staticmethod
    def quote_convert(msg_fmt, msg_body):
        for ck, cv in msg_body.items():
            fmt = "$&{0}&$".format(ck)
            if msg_fmt.count(fmt) > 0:
                msg_fmt = msg_fmt.replace(fmt, cv)
        return msg_fmt

    @staticmethod
    def function_convert(api, msg, msg_fmt):
        fun_fmts = re.findall(r"\$\!.*?\!\$", msg_fmt)
        for fun_fmt in fun_fmts:
            fun = fun_fmt[2:-2]
            fun_str = '__import__("mod.{0}.function").{0}.function.{1}_{2}'.format(api,
                                                                                   msg, fun)
            res = eval(fun_str)
            msg_fmt = msg_fmt.replace(fun_fmt, res)
        return msg_fmt

    @staticmethod
    def format_parse(api, msg, msg_fmt, msg_body):
        arg_keys = []
        arg_vals = []
        msg_args = {}

        # keys
        fmts = re.findall(r"\$[&!].*?[&!]\$", msg_fmt)
        for fmt in fmts:
            if fmt[1] == '&' and fmt[-2] == '&':
                # quote
                arg_keys.append(fmt)
            elif fmt[1] == '!' and fmt[-2] == '!':
                # function
                arg_keys.append(fmt)
            msg_fmt = msg_fmt.replace(fmt, "(.*?)")

        # vals
        match_vals = re.match(msg_fmt, msg_body)
        if match_vals:
            for match_val in match_vals.groups():
                arg_vals.append(match_val)

        args_dict = dict(zip(arg_keys, arg_vals))
        for k, v in args_dict.items():
            if k[1] == '&':
                # quote
                msg_args[k[2:-2]] = v
            elif k[1] == '!':
                # function
                fun_name = k[2:-2]
                fun_str = '__import__("mod.{0}.function").{0}.function.{1}_{2}("{3}")'.format(api,
                                                                                              msg, fun_name, v)
                msg_args[fun_name] = eval(fun_str)
            else:
                logging.error("fmt is error, k:{0}, v:{1}.".format(k, v))

        return msg_args

    def get_options(self, api, msg):
        if not self.msg_valid(api, msg):
            logging.error("msg_valid is error, api:{0}, msg:{1}.".format(api, msg))
            return None

        options = self.api[api][msg]["options"]

        return options

    def build_send_body(self, api, msg, origin_body):
        if not origin_body or not self.msg_valid(api, msg):
            logging.error("msg_valid is error, api:{0}, msg:{1}.".format(api, msg))
            return None

        send_msg = self.api[api][msg]["send"]

        # variable convert
        variable_msg = self.variable_convert(str(send_msg))

        # quote convert
        quote_body = self.quote_convert(variable_msg, origin_body)

        # function convert
        function_body = self.function_convert(api, msg, quote_body)

        return function_body

    def parse_recv_body(self, api, msg, origin_body):
        if not origin_body or not self.msg_valid(api, msg):
            logging.error("msg_valid is error, api:{0}, msg:{1}.".format(api, msg))
            return None

        recv_msg = self.api[api][msg]["recv"]["body"]

        # variable convert
        variable_msg = self.variable_convert(str(recv_msg))

        # format parse
        msg_args = self.format_parse(api, msg, variable_msg, origin_body)

        return msg_args
