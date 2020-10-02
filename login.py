from sanic import Sanic
from data.penguin import Penguin
from data.buddy import BuddyList, BuddyListCollection
from data import db
from secrets import token_hex
from hashlib import md5
from crumbs import blizzard
import aioredis
import socketio
import asyncio
import bcrypt
import json
import time


sio = socketio.AsyncServer(async_mode='sanic', cors_allowed_origins="*")
app = Sanic()
sio.attach(app)

@app.listener('before_server_start')
async def start_services(sanic, loop):
    await db.set_bind('postgresql://{}:{}@{}/{}'.format(
        'postgres', 'password',
        'localhost',
        'houdini'))
    global redis
    redis = await aioredis.create_redis_pool(
        f'redis://localhost:6379',
        minsize=5, 
        maxsize=10
    )
  
def generate_random_key():
    return token_hex(8)
       
def hash(undigested):
    if type(undigested) == str:
        undigested = undigested.encode('utf-8')
    elif type(undigested) == int:
        undigested = str(undigested).encode('utf-8')
    return md5(undigested).hexdigest()       

async def send_packet(action, params):
    #packet = f"{action,params}"
    packet = {}
    packet["action"] = action
    packet["params"] = params
    packet = json.dumps(packet)
    print(packet)
    await sio.emit('p', packet)

async def send_packet_client(action, params,sid):
    packet = {}
    packet["action"] = action
    packet["params"] = params
    packet = json.dumps(packet)
    print(packet)
    await sio.emit('p', packet, room=sid)

@sio.event
async def p(sid,message):
    loop = asyncio.get_event_loop()
    username = message['params'][0].lower()
    data = await Penguin.query.where(Penguin.username == username).gino.first()
    await Penguin.update.values(sid=sid).where(Penguin.id == data.id).gino.status()
    if not data:
        return await send_packet_client("engine:prompt",["login","Penguin not Found ?"], sid)
    password = message['params'][1]
    correctpw = await loop.run_in_executor(None, bcrypt.checkpw, password.encode('utf-8'), data.password.encode('utf-8'))
    if not correctpw:
        return await send_packet_client("engine:prompt",["login","Incorrect Password\n Please try again thank you :)"], sid)
    playerdata = {}
    actiontype = {}
    random_key = generate_random_key()
    key = hash(random_key[::-1])
    actiontype['type'] = "none"
    actiontype['data'] = "{}"
    playerdata['id'] = data.id
    playerdata['swid'] = data.id
    playerdata['username'] = data.username
    playerdata['nickname'] = data.nickname
    playerdata['moderator'] = data.moderator
    playerdata['rank'] = 0
    playerdata['color'] = 1
    playerdata['head'] = data.head
    playerdata['face'] = data.face
    playerdata['neck'] = data.neck
    playerdata['body'] = data.body
    playerdata['hand'] = data.hand
    playerdata['feet'] = data.feet
    playerdata['photo'] = data.photo
    playerdata['pin'] = data.flag
    playerdata['action'] = actiontype
    playerdata['isMascot'] = False
    playerdata['giftId'] = 0
    playerdata['coins'] = data.coins
    playerdata['minutesPlayed'] = data.minutes_played
    playerdata['age'] = data.age
    server = {}
    await get_buddies(data)
    server['blizzard'] = blizzard
    data = [data.id, data.nickname, key, playerdata, server, int(round(time.time() * 1000)), 8,"[^A-Za-z!\" ?😂🤣🤡🥺❤️💞💅]+"] 
    await send_packet_client("login:u",data,sid)
    tr = redis.multi_exec()
    tr.setex(f'{key}', 3600, username)
    await tr.execute()
    #await sio.emit('p',data)
    print(password)
    print(message)

async def get_buddies(data):
    buddy_worlds = []
    world_populations = []
    if await redis.scard('html5.players'):
        async with db.transaction():
            buddies = BuddyList.select('buddy_id').where(BuddyList.penguin_id == data.id).gino.iterate()
            if not buddies:
                blizzard['buddy_online'] = False
            tr = redis.multi_exec()
            async for buddy_id, in buddies:
                tr.sismember('html5.players', buddy_id)
            online_buddies = await tr.execute()
            if any(online_buddies):
                blizzard['buddy_online'] = True


@sio.event
def disconnect(sid):
    print('Client disconnected')


if __name__ == '__main__':
    app.run(host='0.0.0.0',port=7070)
