#!/usr/bin/env python
# -*- coding: UTF-8 -*-

import threading
import heapq
import time


class Timer:
    def __init__(self):
        self.cid_hash = {}
        self.item_heapq = []

        # 1s
        self.timer = threading.Timer(1, self.timeout_callback)
        self.timer.start()

    def timeout_callback(self):
        i = 0
        cur = int(time.time())
        while len(self.item_heapq) and i < 50:
            item = self.item_heapq[0]
            expire = item[0]
            cid = item[1]
            callback = item[2]
            if cur < expire:
                break

            callback(cid)
            self.cid_hash.pop(cid)
            heapq.heappop(self.item_heapq)
            i += 1

        # 1s
        self.timer = threading.Timer(1, self.timeout_callback)
        self.timer.start()

    def add_item(self, timeout, cid, callback):
        res = 0
        item = self.cid_hash.get(cid)
        if item:
            self.item_heapq.remove(item)
            res = 1
        item = [timeout + int(time.time()), cid, callback]
        self.cid_hash[cid] = item
        heapq.heappush(self.item_heapq, item)
        return res

    def del_item(self, cid):
        item = self.cid_hash.get(cid)
        if not item:
            return -1
        self.item_heapq.remove(item)
        return 0
