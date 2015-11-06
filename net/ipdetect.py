#!/usr/bin/env python

import subprocess
import sys
import re

def check_ip_format(ip_str):
    pattern = r"\b(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
    if re.match(pattern, ip_str):
      return True
    else:
      return False

def ip_to_int(ip_str):
    return sum([256**j*int(i) for j, i in enumerate(ip_str.split('.')[::-1])])

def int_to_ip(ip_int):
    return '.'.join([str(ip_int/(256**i)%256) for i in range(3, -1, -1)])

def is_can_reach(ip_str):
    return (True if not subprocess.call(['ping -c 1 -w 1 %s > /dev/null' % ip_str], shell=True) else False)

def thread_test(ips):
    from threading import Thread
    from Queue import Queue
    import thread

    print_lock = thread.allocate_lock()

    def print_result(ip):
        print_lock.acquire()
        print 'ip: %s' % ip
        print_lock.release()
      
    def todo(index, queue):
        while True:
            ip = queue.get()
            if is_can_reach(ip):
                print_result(ip)
            queue.task_done()

    queue = Queue()

    for i in range(len(ips)):
        t = Thread(target=todo, args=(i, queue))
        t.setDaemon(True)
        t.start()

    for ip in ips:
        queue.put(ip)

    queue.join()

if __name__ == '__main__':

    if len(sys.argv) < 3:
        print "Usage: %s <start_ip> <end_ip>" % sys.argv[0]
        exit()

    try:
        start_ip = sys.argv[1]
        end_ip = sys.argv[2]

        if not check_ip_format(start_ip):
            raise Exception("<start_ip> is not valid ip address!")
        
        if not check_ip_format(end_ip):
            raise Exception("<end_ip> is not valid ip address!")

        start_ip_int = ip_to_int(start_ip)
        end_ip_int = ip_to_int(end_ip)

        if start_ip_int > end_ip_int:
            raise Exception("<start_ip> big then <end_ip>!")

        ips = [int_to_ip(ip) for ip in range(start_ip_int, end_ip_int + 1)]
        thread_test(ips)
        print 'Done!'

    except Exception as e:
        print e

    except KeyboardInterrupt:
        pass

