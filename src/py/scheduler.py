#!/usr/bin/env python3
import threading, logging
import socketserver, sched, time, json
from datetime import datetime

logger = logging.getLogger("server")
server_thread = None
queue_thread = None
queue = sched.scheduler(time.time)
events = []

UTF8 = "utf-8"
HOST = 'localhost'
PORT = 9000


class Event:
    def __init__(self, msg, priority=100):
        self.priority = priority
        self.msg = msg
        self.id = msg['id']
        self._put_to_queue()

    def infinity_loop(self) -> object:
        self._put_to_queue(True)
        try:
            self.action()
        except Exception as err:
            logger.error("Exception occurred while executing action %s", err)
        finally:
            pass

    def _put_to_queue(self, first=False):
        if not self.msg['time']:
            return
        delay = convert_time(self.msg['time'])
        if delay <= 0:
            return
        self.event = queue.enter(delay, self.priority, self.infinity_loop)
        self.event_id = self.event[0]

        if not first:
            next_time = time.asctime(time.localtime(time.time() + delay))
            logger.info("Event registered. Repeat every %s second(s). Next start at %s. %s", delay, next_time, self.event)

    def update(self, msg):
        try:
            logger.info("Event unregistered. %s", self.event)
            queue.cancel(self.event)
        except Exception as ex:
            pass
        self.msg = msg
        self.id = msg['id']
        if self.msg['time']:
            self._put_to_queue()

    def action(self):
        logger.info("Command: %s %s", self.msg['cmd'], self.msg['args'])


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    pass


class TCPHandler(socketserver.BaseRequestHandler):
    def handle(self):
        try:
            self.data = self.request.recv(1024).strip()
            msg = json.loads(self.data.decode(UTF8))
            status = 400
            responseData = ''

            if 'type' not in msg.keys():
                logger.warning("Not valid request type received: %s", msg)

            if 'time' in msg.keys() and 'cmd' in msg.keys() and msg['type'] == 'event' and msg['cmd'] and msg['args']:
                status = 200
                ev: Event = self.getEventById(msg['id'])
                if ev is None:
                    ev = Event(self.toMessage(msg['id'], msg['time'], msg['cmd'], msg['args']))
                    events.append(ev)
                    status = 201
                else:
                    ev.update(self.toMessage(msg['id'], msg['time'], msg['cmd'], msg['args']))

                responseData = json.dumps(ev.id)
            elif msg['type'] == 'service':
                if 'attr' in msg.keys():
                    result = getattr(self, msg['cmd'])(msg['attr'])
                else:
                    result = getattr(self, msg['cmd'])()
                # self.request.sendall(bytes(json.dumps(result) + "\n", UTF8))
                status = 200
                responseData = json.dumps(result)
            else:
                logger.warning("Not valid event: %s %s %s %s", msg['id'], msg['time'], msg['cmd'], msg['args'])
                status = 203
                # self.request.sendall(bytes('203' + "\n", UTF8))

            cur_thread = threading.current_thread()
            response = bytes("{}-{}: {}".format(status, cur_thread.name, responseData), UTF8)
            self.request.sendall(response)

        except Exception as e:
            logger.error("Exception occurred while handling request:", e)
            self.request.sendall(bytes('400' + "\n", UTF8))
        finally:
            # queue.run()

            pass

    def getEventById(self, key):
        try:
            for e in events:
                if e.id == key:
                    return e
        except Exception as e:
            logger.error('Error getting event by ID: ', e)
        return None

    def toMessage(self, id, time, cmd, args):
        return {"id": id, "time": time, "cmd": cmd, "args": args}

    def status(self):
        state = []
        for el in queue.queue:
            state.append(el[0])
        return state

    def start(self, eventId):
        return 200


def enable_logging(logFileName='server.log'):
    ###############################
    # Configuration:
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler(logFileName)
    FORMAT = '%(asctime)s %(levelname)s: %(message)s'
    fh.setFormatter(logging.Formatter(FORMAT))
    logger.addHandler(fh)
    logging.basicConfig(level=logging.INFO, format=FORMAT)
    # ch = logging.
    # logger.addHandler(ch)
    ###############################


def queue_failsafe():
    while True:
        try:
            queue.run()
        except Exception as e:
            logger.error("Exception occurred while executing queue. %s", e)
        finally:
            time.sleep(0.5)


def convert_time(value):
    if ':' in value:
        d, m, y = (datetime.now().day, datetime.now().month, datetime.now().year)
        return round(time.mktime(
            time.strptime(str(y) + '-' + str(m) + '-' + str(d) + ' ' + value, '%Y-%m-%d %H:%M')) - time.time())
    else:
        arr = value.split(' ')
        sec, mins, hours = (int(arr[0]), int(arr[1]), int(arr[2]))
        return 60 * 60 * hours + 60 * mins + sec


if __name__ == "__main__":
    enable_logging()
    while True:
        try:
            with ThreadedTCPServer((HOST, PORT), TCPHandler) as server:

                server_thread = threading.Thread(target=server.serve_forever, daemon=True)
                queue_thread = threading.Thread(target=queue_failsafe, daemon=True)
                server_thread.start()
                queue_thread.start()
                logger.info("Scheduler started.")

                server_thread.join()
                logger.debug("Scheduler restarting...")
        except Exception as e:
            logger.error("Scheduler error: %s", e)
        finally:
            pass
