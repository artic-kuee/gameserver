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
#  `host` bigint NOT NULL,
#  `count` int NOT NULL,
#  PRIMARY KEY (`id`)
# )
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
# )


class LiveDifficulty(Enum):
    normal = 1
    hard = 2


class JoinRoomResult(Enum):
    Ok = 1
    RoomFull = 2
    Disbanded = 3
    OtherError = 4


class WaitRoomStatus(Enum):
    Waiting = 1
    LiveStart = 2
    Dissolution = 3


class RoomInfo(BaseModel):
    room_id: int
    live_id: int
    joined_user_count: int
    max_user_count: int


class RoomUser(BaseModel):
    user_id: int
    name: str
    leader_card_id: int
    select_difficulty: LiveDifficulty
    is_me: bool
    is_host: bool


class ResultUser(BaseModel):
    user_id: int
    judge_count_list: list[int]
    score: int


def append_member(rid: int, uid: int, dif: int) -> JoinRoomResult:
    with engine.begin() as conn:
        result = conn.execute(
            text("SELECT * FROM `rooms` WHERE `id` = :room_id"), {"room_id": rid}
        )
        res = result.one()
        if res is None:
            return JoinRoomResult(4)
        if res.count == 4:
            return JoinRoomResult(2)
        if res.status == 1:
            conn.execute(
                text(
                    "INSERT INTO `members` (room_id, user_id, difficulty) VALUES (:room_id, :user_id, :difficulty)"
                ),
                {"room_id": rid, "user_id": uid, "difficulty": dif},
            )
            conn.execute(
                text("UPDATE `rooms` SET `count` = :count WHERE `id` = :room_id"),
                {"count": res.count + 1,"room_id": rid},
            )
            return JoinRoomResult(1)
    return JoinRoomResult(3)


def new_room(uid: int, lid: int, dif: int) -> int:
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "INSERT INTO `rooms` (live_id, status, host, count) VALUES (:lid, 1, :user_id, 0)"
            ),
            {"lid": lid, "user_id": uid},
        )
        rid = result.lastrowid
    print(append_member(rid, uid, dif))
    return rid


def get_rooms(lid: int) -> list[RoomInfo]:
    with engine.begin() as conn:
        if lid == 0:
            result = conn.execute(
                text("SELECT * FROM `rooms` WHERE `status` = 1 AND `count` < 4")
            )
        else:
            result = conn.execute(
                text(
                    "SELECT * FROM `rooms` WHERE `status` = 1 AND `count` < 4 AND `live_id` = :live_id"
                ),
                {"live_id": lid},
            )
    res = list([])
    rows = result.fetchall()
    for row in rows:
        res.append(
            RoomInfo(
                room_id=row.id,
                live_id=row.live_id,
                joined_user_count=row.count,
                max_user_count=4,
            )
        )
    return res


class RoomWaitResponse(BaseModel):
    status: WaitRoomStatus
    room_user_list: list[RoomUser]


def get_members(rid: int, uid: int) -> RoomWaitResponse:
    with engine.begin() as conn:
        result = conn.execute(
            text("SELECT * FROM `members` WHERE `room_id` = :room_id"), {"room_id": rid}
        )
        res = list([])
        rows = result.fetchall()

        hres = conn.execute(
            text("SELECT * FROM `rooms` WHERE `id` = :rid"), {"rid": rid}
        )
        hrow = hres.one()
        host = hrow.host
        for row in rows:
            isme = 0
            ishost = 0
            if row.user_id == uid:
                isme = 1
            if row.user_id == host:
                ishost = 1
            ures = conn.execute(
                text("SELECT * FROM `user` WHERE `id` = :uid"), {"uid": row.user_id}
            )
            user = ures.one()
            res.append(
                RoomUser(
                    user_id=row.user_id,
                    name=user.name,
                    leader_card_id=user.leader_card_id,
                    select_difficulty=LiveDifficulty(row.difficulty),
                    is_me=isme,
                    is_host=ishost,
                )
            )
    return RoomWaitResponse(status=hrow.status, room_user_list=res)


def vs_start(rid: int, uid: int) -> None:
    with engine.begin() as conn:
        hres = conn.execute(
            text("SELECT * FROM `rooms` WHERE `id` = :rid"), {"rid": rid}
        )
        hrow = hres.one()
        host = hrow.host
        if uid != host:
            return
        result = conn.execute(
            text("UPDATE `rooms` SET `status` = 2 WHERE id = :rid"), {"rid": rid}
        )
    return


def set_score(rid: int, uid: int, judge: list[int], score: int) -> None:
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "UPDATE `members` SET `score` = :score, `judge0` = :j0, `judge1` = :j1, `judge2` = :j2, `judge3` = :j3, `judge4` = :j4 WHERE `room_id` = :rid AND `user_id` = :uid"
            ),
            {
                "score": score,
                "j0": judge[0],
                "j1": judge[1],
                "j2": judge[2],
                "j3": judge[3],
                "j4": judge[4],
                "rid": rid,
                "uid": uid,
            },
        )
    return


def get_score(rid: int) -> list[ResultUser]:
    with engine.begin() as conn:
        result = conn.execute(
            text("SELECT * FROM `members` WHERE `room_id` = :rid AND `score` IS NULL"),
            {"rid": rid},
        )
        try: 
            result.one()
        except:
            pass
        else: 
            print("hoge")
            return list([])
        res = conn.execute(
            text("SELECT * FROM `members` WHERE `room_id` = :rid"), {"rid": rid}
        )
    rows = res.fetchall()
    res = list([])
    for row in rows:
        judge = list([row.judge0, row.judge1, row.judge2, row.judge3, row.judge4])
        res.append(
            ResultUser(user_id=row.user_id, judge_count_list=judge, score=row.score)
        )
    return res


def leave_room(rid: int, uid: int):
    with engine.begin() as conn:
        hres = conn.execute(
            text("SELECT * FROM `rooms` WHERE `id` = :rid"), {"rid": rid}
        )
        if hres.one().host == uid:
            conn.execute(
                text("UPDATE `rooms` SET `status` = 3 WHERE `id` = :room_id"),
                {"room_id": rid},
            )
        conn.execute(
            text("DELETE FROM `members` WHERE `room_id` = :rid AND `user_id` = :uid"),
            {"rid": rid, "uid": uid},
        )
        res = conn.execute(
            text("SELECT * FROM `rooms` WHERE id = :room_id"),
            {"room_id": rid},
        )
        count = res.fetchall()[0].count
        if count == 1:
            conn.execute(
                text("DELETE FROM `rooms` WHERE `id` = :room_id"), {"room_id": rid}
            )
        conn.execute(
            text("UPDATE `rooms` SET `count` = :dec WHERE id = :room_id"),
            {"dec": count - 1, "room_id": rid},
        )
