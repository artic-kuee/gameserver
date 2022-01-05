from enum import Enum
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from . import model
from .model import (
    JoinRoomResult,
    LiveDifficulty,
    ResultUser,
    RoomUser,
    RoomWaitResponse,
    SafeUser,
    WaitRoomStatus,
    append_member,
    get_score,
    leave_room,
)

app = FastAPI()

# Sample APIs


@app.get("/")
async def root():
    return {"message": "Hello World"}


# User APIs


class UserCreateRequest(BaseModel):
    user_name: str
    leader_card_id: int


class UserCreateResponse(BaseModel):
    user_token: str


@app.post("/user/create", response_model=UserCreateResponse)
def user_create(req: UserCreateRequest):
    """新規ユーザー作成"""
    token = model.create_user(req.user_name, req.leader_card_id)
    return UserCreateResponse(user_token=token)


bearer = HTTPBearer()


def get_auth_token(cred: HTTPAuthorizationCredentials = Depends(bearer)) -> str:
    assert cred is not None
    if not cred.credentials:
        raise HTTPException(status_code=401, detail="invalid credential")
    return cred.credentials


@app.get("/user/me", response_model=SafeUser)
def user_me(token: str = Depends(get_auth_token)):
    user = model.get_user_by_token(token)
    if user is None:
        raise HTTPException(status_code=404)
    # print(f"user_me({token=}, {user=})")
    return user


class Empty(BaseModel):
    pass


@app.post("/user/update", response_model=Empty)
def update(req: UserCreateRequest, token: str = Depends(get_auth_token)):
    """Update user attributes"""
    # print(req)
    model.update_user(token, req.user_name, req.leader_card_id)
    return {}


# Room APIs


class RoomCreateRequest(BaseModel):
    live_id: int
    select_difficulty: LiveDifficulty


class RoomCreateResponce(BaseModel):
    room_id: int


@app.post("/room/create", response_model=RoomCreateResponce)
def create(
    req: RoomCreateRequest, token: str = Depends(get_auth_token)
) -> RoomCreateResponce:
    user = model.get_user_by_token(token)
    return RoomCreateResponce(
        model.new_room(user.id, req.live_id, req.select_difficulty.value)
    )


class RoomListRequest(BaseModel):
    live_id: int


class RoomListResponce(BaseModel):
    room_info_list: List[int]


@app.post("/room/list", response_model=RoomListResponce)
def list(req: RoomListRequest) -> RoomListResponce:
    return model.get_rooms(req.live_id)


class RoomJoinRequest(BaseModel):
    room_id: int
    select_difficulty: LiveDifficulty


@app.post("/room/join", response_model=JoinRoomResult)
def join(req: RoomJoinRequest, token: str = Depends(get_auth_token)) -> JoinRoomResult:
    user = model.get_user_by_token(token)
    return model.append_member(req.room_id, user.id, req.select_difficulty)


class RoomWaitRequest(BaseModel):
    room_id: int


@app.post("/room/wait", response_model=RoomWaitResponse)
def wait(
    req: RoomWaitRequest, token: str = Depends(get_auth_token)
) -> RoomWaitResponse:
    user = model.get_user_by_token(token)
    return model.get_members(req.room_id, user.id)


class RoomStartRequest(BaseModel):
    room_id: int


@app.post("/room/start", response_model=None)
def start(req: RoomStartRequest, token: str = Depends(get_auth_token)) -> None:
    user = model.get_user_by_token(token)
    model.vs_start(req.room_id, user.id)
    return


class RoomEndRequest(BaseModel):
    room_id: int
    judge_count_list: List[int]
    score: int


@app.post("/room/end", response_model=None)
def end(req: RoomEndRequest, token: str = Depends(get_auth_token)) -> None:
    user = model.get_user_by_token(token)
    model.set_score(req.room_id, user.id, req.judge_count_list, req.score)
    return


class RoomResultRequest(BaseModel):
    room_id: int


class RoomResultResponce(BaseModel):
    result_user_list: List[ResultUser]


@app.post("/room/result", response_model=RoomResultResponce)
def result(req: RoomResultRequest) -> RoomResultResponce:
    return RoomResultResponce(result_user_list=model.get_score(req.room_id))


class RoomLeaveRequest(BaseModel):
    room_id: int


@app.post("/room/leave", response_model=None)
def leave(req: RoomLeaveRequest, token: str = Depends(get_auth_token)) -> None:
    user = model.get_user_by_token(token)
    model.leave_room(req.room_id, user.id)
    return
