#!/usr/bin/env python

import asyncio, json, logging, websockets, uuid, threading, socket
from numbers import Number

logging.basicConfig(level=logging.INFO)
USERS = set()
server_port = 1300

remote = '192.168.1.63'

if socket.gethostname() == 'mcbk.local':
    remote = 'localhost'


def userToJSON(user):
    _u = {'type': 'user', 'uuid': user.uuid, 'port': user.service_port}
    if user['custom_fields']:
        for custom_field in user['custom_fields']:
            if hasattr(user, custom_field):
                _u[custom_field] = user[custom_field]
    return _u


def usersToJSON():
    result = []
    for user in USERS:
        if hasattr(user, 'name'):
            result.append(userToJSON(user))
    return result


async def notify_users():
    if USERS:
        message = json.dumps({'type': 'users', 'users': usersToJSON()})
        await asyncio.wait([user.send(message) for user in USERS])


async def get_user(uuid):
    if USERS:
        for user in USERS:
            if user.uuid == uuid:
                return user


def handle(user):
    try:
        for message in user.messages:
            print(message)
    except Exception as exc:
        logging.error(exc)


async def register(user):
    user.uuid = str(uuid.uuid1())
    user.service_port = 1301 + len(USERS)
    user.custom_fields = set()
    USERS.add(user)
    logging.info("Register: " + str(user.uuid))
    msg = json.dumps({'type': 'settings', 'uuid': user.uuid, 'port': user.service_port})
    await user.send(msg)
    # user.thread = threading.Thread(target=handle, args=(user,), daemon=True)
    # user.thread.start()
    await notify_users()


async def unregister(user):
    logging.info("Unregister: " + str(user.uuid))
    USERS.remove(user)
    await notify_users()


def parse(message):
    return json.loads(message)


async def serve(websocket, path):
    try:
        await register(websocket)
        async for message in websocket:
            logging.info(message)
            try:
                data = parse(message)
                if data['type'] == "name":
                    websocket.name = data['name']
                    websocket.custom_fields.add('name')
                    await notify_users()
                elif data['type'] == "status":
                    websocket.custom_fields.add('status')
                    websocket.status = data['status']

                    if isinstance(data['queue'], (list, dict)):
                        websocket.custom_fields.add('queue')
                        websocket.queue = data['queue']

                    if isinstance(data['current'], (list, dict)):
                        websocket.custom_fields.add('current')
                        websocket.current = data['current']
                    await notify_users()

                if data['type'] == "command":
                    if not data['uuid']:
                        return
                    user = await get_user(data['uuid'])
                    if user:
                        logging.info("Sending to " + user['name'] + " " + message)
                        await user.send(message)
                    else:
                        logging.info("User not found by uuid " + data['uuid'])
                        await websocket.send("User not found by uuid " + data['uuid'])
            except Exception as pex:
                logging.error("Parsing Exception", pex)

    except Exception as ex:
        logging.error(ex)
    finally:
        # pass
        await unregister(websocket)


asyncio.get_event_loop().run_until_complete(websockets.serve(serve, host=remote, port=server_port))
logging.info("Server started on port " + str(server_port))
asyncio.get_event_loop().run_forever()
