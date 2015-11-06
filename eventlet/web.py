#!/use/bin/env python

import eventlet as api

def httpd(writer, reader):
    request = ''
    while True:
        chunk = reader.readline()
        if not chunk:
            break

        request += chunk
        if chunk == '\r\n':
            break

    data = 'Hello world!\r\n'
    writer.write('HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n%s' % (len(data), data))
    writer.close()
    reader.close()

def main():
    try:
        server = api.listen(('0.0.0.0', 8080))
        print 'Server started at 0.0.0.0:8080 ...'

        pool = api.GreenPool(1000)

        while True:
            conn, addr = server.accept()
            print 'client %s connected' % repr(addr)

            writer = conn.makefile('w')
            reader = conn.makefile('r')

            pool.spawn_n(httpd, writer, reader)
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()


