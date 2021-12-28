import json
import uuid
from enum import Enum, IntEnum
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import NoResultFound

from .db import engine


class InvalidToken(Exception):
    """指定されたtokenが不正だったときに投げる"""


class SafeUser(BaseModel):
    """token を含まないUser"""

    id: int
    name: str
    leader_card_id: int

    class Config:
        orm_mode = True


def create_user(name: str, leader_card_id: int) -> str:
    """Create new user and returns their token"""
    token = str(uuid.uuid4())
    # NOTE: tokenが衝突したらリトライする必要がある.
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "INSERT INTO `user` (name, token, leader_card_id) VALUES (:name, :token, :leader_card_id)"
            ),
            {"name": name, "token": token, "leader_card_id": leader_card_id},
        )
        # print(result)
    return token


def _get_user_by_token(conn, token: str) -> Optional[SafeUser]:
    result = conn.execute(
        text("SELECT `id`, `name`, `leader_card_id` FROM `user` WHERE `token`=:token"),
        dict(token=token),
    )
    try:
        row = result.one()
    except NoResultFound:
        return None
    return SafeUser.from_orm(row)


def get_user_by_token(token: str) -> Optional[SafeUser]:
    with engine.begin() as conn:
        return _get_user_by_token(conn, token)


def update_user(token: str, name: str, leader_card_id: int) -> None:
    # このコードを実装してもらう
    with engine.begin() as conn:
        # TODO: 実装
        result = conn.execute(
            text(
                "UPDATE `user` SET `name` = :name, `leader_card_id` = :leader_card_id WHERE `token`=:token "
            ),
            dict(name=name, leader_card_id=leader_card_id, token=token),
        )
        return
        pass


# 以下\roomリクエスト用の関数群
# sqlのtableに関して
# rooms | CREATE TABLE `rooms` (
#  `id` bigint NOT NULL AUTO_INCREMENT,
#  `live_id` int NOT NULL,
#  `status` int NOT NULL,
#  PRIMARY KEY (`id`)
#)
# members | CREATE TABLE `members` (
#  `room_id` bigint NOT NULL,
#  `user_id` bigint NOT NULL,
#  `difficulty` int NOT NULL,
#  `score` bigint DEFAULT NULL,
#  `judge0` bigint DEFAULT NULL, //perfect
#  `judge1` bigint DEFAULT NULL, //great
#  `judge2` bigint DEFAULT NULL, //good
#  `judge3` bigint DEFAULT NULL, //bad
#  `judge4` bigint DEFAULT NULL, //miss
#  PRIMARY KEY (`room_id`,`user_id`)
#) 

class Livedifficulty(enum):
    normal = 1
    hard = 2


class JoinRoomResult(enum):
    Ok = 1
    RoomFull = 2
    Disbanded = 3
    OtherError = 4


class WaitRoomStatus(enum):
    Waiting = 1
    LiveStart = 2
    Dissolution = 3

class RoomInfo(BaseModel):
    room_id: int
    live_id: int
    joined_user_count : int
    max_user_count: int

class RoomUser(BaseModel):
    user_id: int
    name: str 
    leader_card_id: int
    select_difficulty:LiveDifficulty
    is_me: bool
    is_host: bool

class ResultUser(BaseModel):
    user_id: int
    judge_count_list: list[int]
    score: int
def new_room(uid: int , lid: int) -> int:
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "INSERT INTO `rooms` (live_id, status) VALUES (:lid, 1)"
            ),
            {"lid":lid},
        )
    return result.lastrowid

def append_member(rid:int, uid:int, dif: int) -> JoinRoomResult:
    with engine.begin() as conn:
        result = conn.execute(
            text("SELECT * FROM `rooms` WHERE `id` = :room_id"),
            {"room_id":rid}
        )
        if(result.one() is NULL):
            return JoinRoomResult(4)
        if(result.one().state == 1):
            result = conn.execute(
                text("SELECT COUNT(*) FROM `members` WHERE `room_id` = :roomid")
                {"room_id":rid}
            )
            if(result == 4):
                return JoinRoomResult(2)
            conn.execute(
                text(
                    "INSERT INTO `members` (room_id, user_id, difficulty) VALUES (:room_id, :user_id, :difficulty)"
                ),
                {"room_id": rid, "user_id": uid, "difficulty":dif},
            )
            return JoinRoomResult(1)
        return JoinRoomResult(3)


