from data import AbstractDataCollection, db
from functools import cached_property


class PenguinIgloo(db.Model):
    __tablename__ = 'penguin_igloo'

    penguin_id = db.Column(db.ForeignKey('penguin.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True,
                           nullable=False)
    igloo_id = db.Column(db.ForeignKey('igloo.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True,
                         nullable=False)

class Location(db.Model):
    __tablename__ = 'location'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    cost = db.Column(db.Integer, nullable=False, server_default=db.text("0"))
    patched = db.Column(db.Boolean, nullable=False, server_default=db.text("false"))
    legacy_inventory = db.Column(db.Boolean, nullable=False, server_default=db.text("false"))
    vanilla_inventory = db.Column(db.Boolean, nullable=False, server_default=db.text("false"))

class Igloo(db.Model):
    __tablename__ = 'igloo'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    cost = db.Column(db.SmallInteger, nullable=False, server_default=db.text("0"))
    patched = db.Column(db.Boolean, nullable=False, server_default=db.text("false"))
    legacy_inventory = db.Column(db.Boolean, nullable=False, server_default=db.text("false"))
    vanilla_inventory = db.Column(db.Boolean, nullable=False, server_default=db.text("false"))


class IglooCollection(AbstractDataCollection):
    __model__ = Igloo
    __indexby__ = 'id'
    __filterby__ = 'id'

    @cached_property
    def legacy_inventory(self):
        return [item for item in self.values() if item.legacy_inventory]

    @cached_property
    def vanilla_inventory(self):
        return [item for item in self.values() if item.vanilla_inventory]
        
class RoomMixin:

    id = None
    max_users = None

    def __init__(self, *args, **kwargs):
        self.penguins_by_id = {}
        self.penguins_by_username = {}
        self.penguins_by_character_id = {}

        self.igloo = isinstance(self, PenguinIglooRoom)

        self.tables = {}
        self.waddles = {}
        
class PenguinIglooRoom(db.Model, RoomMixin):
    __tablename__ = 'penguin_igloo_room'

    id = db.Column(db.Integer, primary_key=True,
                   server_default=db.text("nextval('\"penguin_igloo_room_id_seq\"'::regclass)"))
    penguin_id = db.Column(db.ForeignKey('penguin.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    type = db.Column(db.ForeignKey('igloo.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    flooring = db.Column(db.ForeignKey('flooring.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    music = db.Column(db.SmallInteger, nullable=False, server_default=db.text("0"))
    location = db.Column(db.ForeignKey('location.id', ondelete='CASCADE', onupdate='CASCADE'), nullable=False)
    locked = db.Column(db.Boolean, nullable=False, server_default=db.text("true"))
    competition = db.Column(db.Boolean, nullable=False, server_default=db.text("false"))

    internal_id = 2000
    name = 'Igloo'
    member = False
    max_users = 80
    required_item = None
    game = False
    blackhole = False
    spawn = False
    stamp_group = None

    @property
    def external_id(self):
        return self.penguin_id + PenguinIglooRoom.internal_id

    def __init__(self, *args, **kwargs):
        RoomMixin.__init__(self, *args, **kwargs)
        super().__init__(*args, **kwargs)

class Furniture(db.Model):
    __tablename__ = 'furniture'

    id = db.Column(db.Integer, primary_key=True)
    vanilla_inventory = db.Column(db.Boolean, nullable=False, server_default=db.text("false"))


class IglooFurniture(db.Model):
    __tablename__ = 'igloo_furniture'

    igloo_id = db.Column(db.ForeignKey('penguin_igloo_room.id', ondelete='CASCADE', onupdate='CASCADE'),
                         primary_key=True, nullable=False, index=True)
    furniture_id = db.Column(db.ForeignKey('furniture.id', ondelete='CASCADE', onupdate='CASCADE'), primary_key=True,
                             nullable=False)
    x = db.Column(db.SmallInteger, primary_key=True, nullable=False, server_default=db.text("0"))
    y = db.Column(db.SmallInteger, primary_key=True, nullable=False, server_default=db.text("0"))
    frame = db.Column(db.SmallInteger, primary_key=True, nullable=False, server_default=db.text("0"))
    rotation = db.Column(db.SmallInteger, primary_key=True, nullable=False, server_default=db.text("0"))
    
    
class PenguinIglooRoomCollection(AbstractDataCollection):
    __model__ = PenguinIglooRoom
    __indexby__ = 'id'
    __filterby__ = 'penguin_id'


