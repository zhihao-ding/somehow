#!/usr/bin/env python

import os
import time

import eventlet
from eventlet import tpool
from eventlet import greenpool

def _thread_done(gt, *args, **kwargs):
    """Callback function to be passed to GreenThread.link() when we spawn()
    Calls the :class:`ThreadGroup` to notify if.

    """
    kwargs['group'].thread_done(kwargs['thread'])


class Thread(object):
    """Wrapper around a greenthread, that holds a reference to the
    :class:`ThreadGroup`. The Thread will notify the :class:`ThreadGroup` when
    it has done so it can be removed from the threads list.
    """
    def __init__(self, thread, group):
        self.thread = thread
        self.thread.link(_thread_done, group=group, thread=self)

    def stop(self):
        self.thread.kill()

    def wait(self):
        return self.thread.wait()

    def link(self, func, *args, **kwargs):
        self.thread.link(func, *args, **kwargs)

class ThreadGroup(object):
    """The point of the ThreadGroup class is to:

    * keep track of timers and greenthreads (making it easier to stop them
      when need be).
    * provide an easy API to add timers.
    """
    def __init__(self, thread_pool_size=10):
        self.pool = greenpool.GreenPool(thread_pool_size)
        self.threads = []
        self.timers = []

    def add_dynamic_timer(self, callback, initial_delay=None,
                          periodic_interval_max=None, *args, **kwargs):
        timer = loopingcall.DynamicLoopingCall(callback, *args, **kwargs)
        timer.start(initial_delay=initial_delay,
                    periodic_interval_max=periodic_interval_max)
        self.timers.append(timer)

    def add_timer(self, interval, callback, initial_delay=None,
                  *args, **kwargs):
        pulse = loopingcall.FixedIntervalLoopingCall(callback, *args, **kwargs)
        pulse.start(interval=interval,
                    initial_delay=initial_delay)
        self.timers.append(pulse)

    def add_thread(self, callback, *args, **kwargs):
        gt = self.pool.spawn(callback, *args, **kwargs)
        th = Thread(gt, self)
        self.threads.append(th)
        return th

    def thread_done(self, thread):
        self.threads.remove(thread)

    def _stop_threads(self):
        current = threading.current_thread()

        # Iterate over a copy of self.threads so thread_done doesn't
        # modify the list while we're iterating
        for x in self.threads[:]:
            if x is current:
                # don't kill the current thread.
                continue
            try:
                x.stop()
            except eventlet.greenlet.GreenletExit:
                pass
            except Exception as ex:
                LOG.exception(ex)

    def stop_timers(self):
        for x in self.timers:
            try:
                x.stop()
            except Exception as ex:
                LOG.exception(ex)
        self.timers = []

    def stop(self, graceful=False):
        """stop function has the option of graceful=True/False.

        * In case of graceful=True, wait for all threads to be finished.
          Never kill threads.
        * In case of graceful=False, kill threads immediately.
        """
        self.stop_timers()
        if graceful:
            # In case of graceful=True, wait for all threads to be
            # finished, never kill threads
            self.wait()
        else:
            # In case of graceful=False(Default), kill threads
            # immediately
            self._stop_threads()

    def wait(self):
        for x in self.timers:
            try:
                x.wait()
            except eventlet.greenlet.GreenletExit:
                pass
            except Exception as ex:
                LOG.exception(ex)
        current = threading.current_thread()

        # Iterate over a copy of self.threads so thread_done doesn't
        # modify the list while we're iterating
        for x in self.threads[:]:
            if x is current:
                continue
            try:
                x.wait()
            except eventlet.greenlet.GreenletExit:
                pass
            except Exception as ex:
                LOG.exception(ex)

class RBD:

    def __init__(self, seed):
        self._seed = seed

    def go(self):
        for i in xrange(5):
            print 'go seed:', self._seed
            time.sleep(1)

def RBDProxy(seed):
    return tpool.Proxy(RBD(seed))

if __name__ == '__main__':
    try:
        eventlet.monkey_patch()

        tg = ThreadGroup(3)
        tg.add_thread(RBDProxy(1).go)
        tg.add_thread(RBDProxy(2).go)
        tg.add_thread(RBDProxy(3).go)
        tg.add_thread(RBDProxy(4).go)
        tg.add_thread(RBDProxy(5).go)
        tg.add_thread(RBDProxy(6).go)
        tg.add_thread(RBDProxy(7).go)
        tg.add_thread(RBDProxy(8).go)

        while True:
            time.sleep(1000)
    except:
        pass
