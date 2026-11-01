import json
import re
from threading import RLock

from flask import request, session, url_for
from flask_socketio import SocketIO, join_room

from models.user_model import get_by_id

socketio = SocketIO()
_calls = {}
_active_calls = {}
_connected_sids = {}
_calls_lock = RLock()

_CALL_ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{16,64}$")
_MAX_SIGNAL_SIZE = 100_000


def _emit_call_error(message, call_id=None, sid=None):
    payload = {"message": message}
    if call_id:
        payload["call_id"] = call_id
    socketio.emit("call:error", payload, to=sid or request.sid, namespace="/messages")


def _finish_call(call_id, event, reason):
    with _calls_lock:
        call = _calls.pop(call_id, None)
        if not call:
            return
        for user_id in (call["caller_id"], call["callee_id"]):
            if _active_calls.get(user_id) == call_id:
                _active_calls.pop(user_id, None)

        peer_sid = call.get("callee_sid") if event == "call:rejected" else None
        if event == "call:rejected":
            peer_sid = call["caller_sid"]
        elif event == "call:ended":
            peer_sid = (
                call["callee_sid"]
                if request.sid == call["caller_sid"]
                else call["caller_sid"]
            )
        if peer_sid:
            socketio.emit(
                event,
                {"call_id": call_id, "reason": reason},
                to=peer_sid,
                namespace="/messages",
            )
        elif event == "call:ended" and call.get("callee_sid") is None:
            socketio.emit(
                event,
                {"call_id": call_id, "reason": reason},
                to=f"user:{call['callee_id']}",
                namespace="/messages",
            )


def _get_call(data):
    if not isinstance(data, dict):
        return None, None
    call_id = data.get("call_id")
    if not isinstance(call_id, str) or not _CALL_ID_PATTERN.fullmatch(call_id):
        return None, None
    return call_id, _calls.get(call_id)


def _relay_signal(event, data, sender_key, recipient_key):
    with _calls_lock:
        call_id, call = _get_call(data)
        user_id = session.get("user_id")
        if not call or call[sender_key] != user_id or call["status"] != "active":
            _emit_call_error("This call is no longer available.", call_id)
            return
        signal = data.get("signal")
        try:
            if not isinstance(signal, dict) or len(json.dumps(signal)) > _MAX_SIGNAL_SIZE:
                raise ValueError
        except (TypeError, ValueError):
            _emit_call_error("The call signal is invalid.", call_id)
            return
        recipient_sid = call.get(recipient_key)
        if not recipient_sid:
            _emit_call_error("The other person disconnected.", call_id)
            return
        socketio.emit(
            event,
            {"call_id": call_id, "signal": signal},
            to=recipient_sid,
            namespace="/messages",
        )


@socketio.on("connect", namespace="/messages")
def connect_messages(_auth=None):
    user_id = session.get("user_id")
    if not user_id:
        return False
    with _calls_lock:
        _connected_sids.setdefault(user_id, set()).add(request.sid)
    join_room(f"user:{user_id}")


@socketio.on("disconnect", namespace="/messages")
def disconnect_messages(_reason=None):
    user_id = session.get("user_id")
    sid = request.sid
    with _calls_lock:
        if user_id in _connected_sids:
            _connected_sids[user_id].discard(sid)
            if not _connected_sids[user_id]:
                _connected_sids.pop(user_id, None)
        call_id = _active_calls.get(user_id)
        call = _calls.get(call_id) if call_id else None
        is_participant = call and sid in (call["caller_sid"], call.get("callee_sid"))
        callee_went_offline = (
            call
            and call["callee_id"] == user_id
            and call["status"] == "ringing"
            and not _connected_sids.get(user_id)
        )
        if is_participant or callee_went_offline:
            _finish_call(call_id, "call:ended", "connection_lost")


@socketio.on("call:invite", namespace="/messages")
def invite_call(data):
    caller_id = session.get("user_id")
    call_id, _ = _get_call(data)
    callee_id = data.get("to_user_id") if isinstance(data, dict) else None
    call_type = data.get("call_type") if isinstance(data, dict) else None
    if (
        not call_id
        or not isinstance(callee_id, int)
        or isinstance(callee_id, bool)
        or callee_id == caller_id
        or call_type not in {"audio", "video"}
        or not get_by_id(callee_id)
    ):
        _emit_call_error("Choose a valid person to call.", call_id)
        return

    with _calls_lock:
        if call_id in _calls:
            _emit_call_error("This call could not be started.", call_id)
            return
        if caller_id in _active_calls:
            _emit_call_error("You are already in a call.", call_id)
            return
        if callee_id in _active_calls:
            socketio.emit(
                "call:busy",
                {"call_id": call_id},
                to=request.sid,
                namespace="/messages",
            )
            return
        if not _connected_sids.get(callee_id):
            socketio.emit(
                "call:unavailable",
                {"call_id": call_id},
                to=request.sid,
                namespace="/messages",
            )
            return

        caller = get_by_id(caller_id)
        if not caller:
            _emit_call_error("This person is no longer available.", call_id)
            return
        call = {
            "caller_id": caller_id,
            "callee_id": callee_id,
            "call_type": call_type,
            "caller_sid": request.sid,
            "callee_sid": None,
            "status": "ringing",
        }
        _calls[call_id] = call
        _active_calls[caller_id] = call_id
        _active_calls[callee_id] = call_id
        socketio.emit(
            "call:incoming",
            {
                "call_id": call_id,
                "call_type": call_type,
                "from_user_id": caller_id,
                "from_name": caller.get("full_name") or caller.get("username", "Someone"),
                "from_username": caller.get("username", ""),
                "from_avatar_url": (
                    url_for("static", filename=caller["avatar_path"])
                    if caller.get("avatar_path")
                    else ""
                ),
            },
            to=f"user:{callee_id}",
            namespace="/messages",
        )


@socketio.on("call:accept", namespace="/messages")
def accept_call(data):
    call_id, call = _get_call(data)
    user_id = session.get("user_id")
    with _calls_lock:
        if not call or call["callee_id"] != user_id or call["status"] != "ringing":
            _emit_call_error("This incoming call is no longer available.", call_id)
            return
        call["callee_sid"] = request.sid
        call["status"] = "active"
        socketio.emit(
            "call:accepted", {"call_id": call_id}, to=call["caller_sid"], namespace="/messages"
        )
        socketio.emit(
            "call:taken",
            {"call_id": call_id},
            to=f"user:{call['callee_id']}",
            skip_sid=request.sid,
            namespace="/messages",
        )


@socketio.on("call:reject", namespace="/messages")
def reject_call(data):
    with _calls_lock:
        call_id, call = _get_call(data)
        if not call or call["callee_id"] != session.get("user_id") or call["status"] != "ringing":
            _emit_call_error("This incoming call is no longer available.", call_id)
            return
        _finish_call(call_id, "call:rejected", "declined")


@socketio.on("call:cancel", namespace="/messages")
def cancel_call(data):
    with _calls_lock:
        call_id, call = _get_call(data)
        if not call or call["caller_id"] != session.get("user_id") or call["status"] != "ringing":
            _emit_call_error("This call can no longer be canceled.", call_id)
            return
        _finish_call(call_id, "call:ended", "canceled")


@socketio.on("call:end", namespace="/messages")
def end_call(data):
    with _calls_lock:
        call_id, call = _get_call(data)
        if not call or session.get("user_id") not in (call["caller_id"], call["callee_id"]):
            _emit_call_error("This call is no longer available.", call_id)
            return
        _finish_call(call_id, "call:ended", "ended")


@socketio.on("call:offer", namespace="/messages")
def relay_offer(data):
    _relay_signal("call:offer", data, "caller_id", "callee_sid")


@socketio.on("call:answer", namespace="/messages")
def relay_answer(data):
    _relay_signal("call:answer", data, "callee_id", "caller_sid")


@socketio.on("call:ice", namespace="/messages")
def relay_ice_candidate(data):
    with _calls_lock:
        call_id, call = _get_call(data)
        user_id = session.get("user_id")
        if not call or call["status"] != "active":
            _emit_call_error("This call is no longer available.", call_id)
            return
        if user_id == call["caller_id"]:
            recipient_sid = call.get("callee_sid")
        elif user_id == call["callee_id"]:
            recipient_sid = call["caller_sid"]
        else:
            _emit_call_error("You are not part of this call.", call_id)
            return
        signal = data.get("signal")
        try:
            if not isinstance(signal, dict) or len(json.dumps(signal)) > _MAX_SIGNAL_SIZE:
                raise ValueError
        except (TypeError, ValueError):
            _emit_call_error("The call signal is invalid.", call_id)
            return
        if not recipient_sid:
            _emit_call_error("The other person disconnected.", call_id)
            return
        socketio.emit(
            "call:ice",
            {"call_id": call_id, "signal": signal},
            to=recipient_sid,
            namespace="/messages",
        )
