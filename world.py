from sanic import Sanic
from data.penguin import Penguin
from data.buddy import BuddyList, BuddyListCollection
from data.item import Item, ItemCollection, PenguinItemCollection
from data.room import PenguinIglooRoom, IglooFurniture,PenguinIgloo, Location, IglooCollection
from data import db
from secrets import token_hex
from hashlib import md5
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, ClassVar
import aioredis
import socketio
import asyncio
import bcrypt
import json
import time
import random
mgr = socketio.AsyncRedisManager('redis://')
sio = socketio.AsyncServer(client_manager=mgr,async_mode='sanic', cors_allowed_origins="*")
app = Sanic()
sio.attach(app)

penguins = {}
igloos = {}
@dataclass
class penguin:
    sid: str
    room: int
    x: int
    y: int
    logged_in: bool
    data: Penguin
    timer: asyncio.Task
    buddies: dict = field(default_factory=dict)

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
    
    await redis.delete('html5.players')

async def send_packet(action, params, sid):
    packet = {}
    packet["action"] = action
    packet["params"] = params
    packet = json.dumps(packet)
    #print(packet)
    loop = asyncio.get_running_loop()

    await sio.emit('p', packet)
   
   
async def send_packet_except(action, params, sid):
    packet = {}
    packet["action"] = action
    packet["params"] = params
    packet = json.dumps(packet)
    #print(packet)
    loop = asyncio.get_running_loop()

    await sio.emit('p', packet, include_self=False)

async def buddy_prompt(sid):
    await send_packet_client("buddy:request_buddy", packet, sid)

async def create_temporary_room(sid, penguin_id):
    igloo = await PenguinIglooRoom.load(parent=Penguin.on(Penguin.igloo == PenguinIglooRoom.id)) \
        .where(PenguinIglooRoom.penguin_id == penguin_id).gino.first()
    if igloo is not None:
        igloos[penguin_id] = igloo
    return igloo

#
async def request_buddy(sid, id: int):
    data = await Penguin.query.where(Penguin.sid == sid).gino.first()
    req = await Penguin.query.where(Penguin.id == id).gino.first()
    req_sid = req.sid
    packet = [data.id, str(data.id), data.nickname] 
    await send_packet_client("buddy:request_buddy", packet, req_sid)
    #"params":[1460811,"{f044bc20-8a23-f984-ea8e-abf96b2b5f19}","Boris124"]}
   
async def add_buddy(sid, id: int):
    data = await Penguin.query.where(Penguin.sid == sid).gino.first()
    req = await Penguin.query.where(Penguin.id == id).gino.first()
    req_sid = req.sid
    player_data = get_player_data(data)
    packet = [player_data['id'], str(player_data['id']), player_data['nickname'], False] 
    await BuddyList.create(penguin_id=id, buddy_id=data.id)
    await BuddyList.create(penguin_id=data.id, buddy_id=id)
    await send_packet_client("buddy:add_buddy", packet, req_sid)
   
   #{"action":"buddy:add_buddy","params":["1460811"]} from the accepter/ (SEND)
   #{"action":"buddy:add_buddy","params":[7184835,"{ecf97ecd-ae01-19f0-1c64-cb10d87850be}","P7184835",false]} to the other party(RECEIVE)
   
async def penguin_action(sid,action,param):
    p = get_player_by_sid(sid)
    packet = [p.data.id, action, param]
    await send_packet_client("player:action", packet, p.room)
    #{"action":"player:action","params":[7184835,"snowball",{"x":514.6666666666666,"y":749.7142857142857}]}
   
async def handle_emote(sid, emote_id):
    p = get_player_by_sid(sid)
    packet = [p.data.id, emote_id]
    await send_packet_client("player:emote", packet, p.room)
    #42["p","{\"action\":\"player:emote\",\"params\":[7184835,\"e0008\"]}"]
   
   
async def send_room_packet(action, params, room_id):
    packet = {}
    packet["action"] = action
    packet["params"] = params
    packet = json.dumps(packet)
    print(packet)
    loop = asyncio.get_running_loop()
    p = get_player_by_sid(sid)
    await sio.emit('p', packet, room=room_id)
   
async def send_packet_client(action, params,sid):
    packet = {}
    packet["action"] = action
    packet["params"] = params
    packet = json.dumps(packet)
    print(packet)
    loop = asyncio.get_running_loop()
    await sio.emit('p', packet, room=sid)
    
def get_player_by_sid(sid):
    for penguin in penguins.values():
        if penguin.sid == sid:
            return penguin  
    
    
async def world_login(sid, key):
    tr = redis.multi_exec()
    tr.get(f'{key}')
    tr.delete(f'{key}')
    username, _ = await tr.execute()
    server_key = f'html5.players'
    if username is None:
        return await send_packet("engine:prompt",["login","Fuck You"], sid)
    loop = asyncio.get_running_loop()
    username = username.decode()
    data = await Penguin.query.where(Penguin.username == username).gino.first()
    await Penguin.update.values(sid=sid).where(Penguin.id == data.id).gino.status()
    await redis.sadd(server_key, data.id)
    if data.id in penguins:
        return await send_packet("engine:prompt",["logout","Fuck You"], sid)
    playerdata = get_player_data(data)
    penguin_id = data.id
    penguins[data.id] = penguin(
    sid=sid,
    room=100,
    x=random.randrange(490,1000),
    y=random.randrange(700,1020),
    data=data,
    logged_in = False,
    timer = loop.call_later(60000, inactivity, sid)
    )
    print(penguins)
    packet = [data.id, data.nickname, playerdata] 
    await send_packet_client("world:auth", packet, sid)
    
async def handle_move(sid,x,y):
    p = get_player_by_sid(sid)
    p.x, p.y = x, y
    packet = [p.data.id, x, y]
    await send_packet("player:move",packet, sid)
    
async def get_inventory(sid):   
    p = get_player_by_sid(sid)
    inventory = await PenguinItemCollection.get_collection(p.data.id)
    items = [item for item in inventory]
    await send_packet_client("inventory:get_inventory", [items], sid)
 
async def handle_send_message(sid, message):
    p = get_player_by_sid(sid)
    message = [p.data.id, message]
    await send_packet("player:message", message, sid)
    #{"action":"","params":[1460811,"test"]}
 
async def get_current_players(sid):
    p = get_player_by_sid(sid)
    for penguin in penguins.values():
        if penguin.room == p.room:
            p = get_player_by_sid(penguin.sid)
            if not p.data:
                p = get_player_by_sid(sid)
                packet = [x, y, p.data.id, p.data.nickname, player_data] 
                return await send_packet_client("navigation:add_player", packet, penguin.room)
            player_data = get_player_data(p.data)
            packet = [penguin.x, penguin.y, player_data['id'], player_data['nickname'], player_data] 
            await send_packet_client("navigation:add_player", packet, penguin.room)
        
    
async def get_buddies(sid):
        buddies = {}
        p = get_player_by_sid(sid)
        friends = await BuddyListCollection.get_collection(p.data.id)
        for buddy in friends.values():
            data = await Penguin.query.where(Penguin.id == buddy.buddy_id).gino.first()
            friend_obj = {}
            friend_obj['nickname'] = data.nickname
            friend_obj['swid'] = data.id
            friend_obj['isPending'] = 0
            friend_obj['online'] = True if data.id in penguins else False
            friend_obj['isMascot'] = False
            p.buddies[buddy.buddy_id] = friend_obj
        packet = [p.buddies]
        await send_packet_client("buddy:get_buddies", packet, sid)
    
async def handle_join_room(sid, room_id, x, y):
    sio.enter_room(sid, room_id)
    s = {}
    s['type'] = "room"
    p = get_player_by_sid(sid)
    await send_packet_client("navigation:join_room",[room_id, x, y, s], room_id)
    player_data = get_player_data(p.data)
    p = get_player_by_sid(sid)
    p.x = x
    p.y = y
    await send_packet_client("navigation:add_player",[x, y, p.data.id, p.data.nickname, player_data], room_id)
    if p.logged_in:
        sio.leave_room(sid, p.room)
        await send_packet_client("navigation:remove_player", [p.data.id], p.room)
        p.room = room_id
        return
    [await send_packet_client("buddy:notify_online",[p.data.id] , peng.sid) for peng in penguins.values() if p.data.id in peng.buddies]
    p.logged_in = True
    
async def join_igloo(sid, id):
    s = {}
    iglooData = {}
    p = penguins[id]
    penguin = get_player_by_sid(sid)
    await create_first_igloo(id)
    penguin.x = 700
    penguin.y = 480
    s['type'] = "igloo"
    igloo_ids = await IglooCollection.get_collection()
    igloo = await create_temporary_room(sid, id)
    iglooData['iglooId'] = igloo.external_id
    igloo_furniture = IglooFurniture.query.where(IglooFurniture.igloo_id == igloo.id).gino
    async with db.transaction():
        furniture_string = ','.join([f"{furniture.furniture_id}: [{'iglooId':{igloo.external_id},'furnitureId':'{furniture.furniture_id}','x':{furniture.x},'y':{furniture.y},'frame':{furniture.frame},'rotation':{furniture.rotation}}]"
        async for furniture in igloo_furniture.iterate()])
    iglooData['furniture'] = {} if furniture_string == '' else furniture_string
    iglooData['ownerId'] = p.data.id
    iglooData['ownerNickname'] = p.data.nickname
    iglooData['type'] = igloo.type
    iglooData['name'] = igloo_ids[igloo.type].name.replace('Igloo', '').strip().lower()
    iglooData['floor'] = igloo.flooring
    iglooData['music'] = str(igloo.music)
    iglooData['location'] = igloo.location
    iglooData['locked'] = int(igloo.locked)
    s['iglooData'] = iglooData
    sio.leave_room(sid, penguin.room)
    await send_packet_client("navigation:remove_player", [penguin.data.id], penguin.room)
    penguin.room = igloo.external_id
    sio.enter_room(sid, igloo.external_id)
    await send_packet_client("navigation:join_room",[igloo.external_id, 700,480, s] , igloo.external_id)
    player_data = get_player_data(penguin.data)
    #{"action": "navigation:join_room", "params": [2101, 700, 480, {"type": "igloo", "iglooData": {"iglooId": 2101, "furniture": {}, "ownerId": 101, "ownerNickname": "Basil", "type": 1, "name": "basic", "floor": 0, "music": 0, "location": 1, "locked": 1}}]}
    #{'action': 'navigation:join_room', 'params': [2719, 700, 480, {'type': 'igloo', 'iglooData': {'iglooId': 2719, 'furniture': {}, 'ownerId': 7184835, 'ownerNickname': 'Bllinol', 'type': 1, 'name': 'basic', 'floor': 0, 'music': '0', 'location': 1, 'locked': 0}}]}
    await send_packet_client("navigation:add_player",[700,480, penguin.data.id, penguin.data.nickname, player_data] , igloo.external_id)
    #{"action": "navigation:join_room", "params": [2101, 700, 480, {"type": "igloo", "iglooData": {"iglooId": 2101, "furniture": {"furniture": ""}, "ownerId": 101, "ownerNickname": "Basil", "type": 1, "name": "Basic", "floor": 0, "music": 0, "location": 1, "locked": 1}}]}
    #{"action":"navigation:join_room","params":[2719,700,480,{"type":"igloo","iglooData":{"iglooId":2719,"furniture":"furniture":{}]},"ownerId":7184835,"ownerNickname":"Bllinol","type":1,"name":"basic","floor":0,"music":"0","location":1,"locked":0}}]}
   
async def create_first_igloo(penguin_id):
    igloo = await PenguinIglooRoom.query.where(PenguinIglooRoom.penguin_id == penguin_id).gino.scalar()
    if igloo is None:
        igloo = await PenguinIglooRoom.create(penguin_id=penguin_id, type=1, flooring=0, location=1)
   
async def inactivity(sid):
    await send_packet_client("engine:prompt",["logout","Your penguin has been idle for 10\n minutes, therefore it has been\n disconnected."], sid)
    await disconnect_handle(sid)
    
@sio.event
async def p(sid,message):
    if "world:auth" in message['action']:
        key = message['params'][0]
        await world_login(sid,key)
        #await sio.emit('p',data)
        print(message)
    elif "engine:get_crumbs" in message['action']:
        await send_crumbs(message['params'][0], sid)
    elif "buddy:get_buddies" in message['action']:
        await get_buddies(sid)
    elif "inventory:get_inventory" in message['action']:
        await get_inventory(sid)
    elif "navigation:join_room" in message['action']:
        await handle_join_room(sid, message['params'][0], message['params'][1],message['params'][2])
    elif "navigation:join_igloo" in message['action']:
        await join_igloo(sid, message['params'][0])
    elif "navigation:get_players" in message['action']:
        await get_current_players(sid)
    elif "player:move" in message['action']:
        x = message['params'][0]
        y = message['params'][1]
        await handle_move(sid,x,y)
        #{"action":"player:move","params":[6069980,836,839]}
    elif "player:message" in message['action']:
        await handle_send_message(sid, message['params'][0])
    elif "buddy:request_buddy" in message['action']:
        await request_buddy(sid, message['params'][0])
    elif "buddy:add_buddy" in message['action']:
        await add_buddy(sid, message['params'][0])
    elif "player:emote" in message['action']:
        await handle_emote(sid, message['params'][0])
    elif "player:action" in message['action']:
        await penguin_action(sid, message['params'][0],message['params'][1]) 
    loop = asyncio.get_running_loop()
    p = get_player_by_sid(sid)
    if p is not None:
        p.timer.cancel()
    p.timer = loop.call_later(10*60, inactivity, sid)
        

@sio.event
async def disconnect(sid):
    print('someone shitted')
    await disconnect_handle(sid)

async def disconnect_handle(sid):
    p = get_player_by_sid(sid)
    if p.data is not None:
        packet = [p.data.id]
        [await send_packet_client("buddy:notify_offline",[p.data.id] , peng.sid) for peng in penguins.values() if p.data.id in peng.buddies]
        await send_packet_client("navigation:remove_player",packet, p.room)
        penguins.pop(p.data.id)
        await redis.srem('html5.players', p.data.id)
        await Penguin.update.values(sid=None).where(Penguin.id == p.data.id).gino.status()
 
        
async def send_crumbs(stuff, sid):
    with open(f'crumbs/{stuff}_crumbs.json') as f:
        packet = json.load(f)
    gamedata = json.dumps(packet)
    packet = [stuff, gamedata] 
    await send_packet("engine:get_crumbs",packet, sid)
    
def get_player_data(data):
    playerdata = {}
    actiontype = {}
    actiontype['type'] = "none"
    actiontype['data'] = "{}"
    playerdata['id'] = data.id
    playerdata['swid'] = data.id
    playerdata['username'] = data.username
    playerdata['nickname'] = data.nickname
    playerdata['moderator'] = data.moderator
    playerdata['rank'] = int(data.age/146)
    playerdata['color'] = data.color
    playerdata['head'] = data.head
    playerdata['face'] = data.face
    playerdata['neck'] = data.neck
    playerdata['body'] = data.body
    playerdata['hand'] = data.hand
    playerdata['feet'] = data.feet
    playerdata['photo'] = data.photo
    playerdata['pin'] = data.flag
    playerdata['action'] = actiontype
    playerdata['isMascot'] = True if data.id in range(40) else False
    playerdata['giftId'] = 0
    playerdata['coins'] = data.coins
    playerdata['minutesPlayed'] = data.minutes_played
    playerdata['age'] = data.age
    return playerdata
    
    
if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5000)
