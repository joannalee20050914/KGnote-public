"""Append-only reading context and exact-resume projection."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Mapping

REQUEST_VERSION="kgnote.resume-context-save-request.v1"
EVENT_VERSION="kgnote.resume-context-event.v1"
EVENT_ID=re.compile(r"resume_[a-f0-9]{32}")
_WRITE_LOCK=threading.Lock()

@dataclass(frozen=True,repr=False)
class ContinuityResult:
    status: Literal["ready","recorded","unchanged","conflict","rejected","failed"]
    _payload_json: str=field(default="{}",repr=False)
    problem_code: str|None=None
    @property
    def payload(self)->dict[str,Any]: return json.loads(self._payload_json)

def _result(status:str,payload:Mapping[str,Any]|None=None,problem:str|None=None)->ContinuityResult:
    return ContinuityResult(status,json.dumps(payload or {},ensure_ascii=False,sort_keys=True,separators=(",",":")),problem)

def _safe(value:Any)->bool: return isinstance(value,str) and 0<len(value)<=300 and not any(c in value for c in "\x00/\\")
def _time(value:Any)->bool:
    try: return isinstance(value,str) and dt.datetime.fromisoformat(value.replace("Z","+00:00")).tzinfo is not None
    except ValueError: return False

def validate_resume_request(value:Any)->str|None:
    required={"schema_version","event_id","learning_unit_id","unit_slug","source_scope","structural_breadcrumb","selected","unresolved_question","occurred_at"}
    if not isinstance(value,Mapping) or set(value)!=required: return "invalid_resume_request"
    if value["schema_version"]!=REQUEST_VERSION or not EVENT_ID.fullmatch(str(value["event_id"])): return "invalid_resume_identity"
    if not _safe(value["learning_unit_id"]) or not re.fullmatch(r"[a-z][a-z0-9-]{0,63}",str(value["unit_slug"])): return "invalid_resume_reference"
    scope=value["source_scope"]
    if not isinstance(scope,Mapping) or set(scope)!={"source_id","locator"} or not _safe(scope["source_id"]) or not re.fullmatch(r"L\d+-L\d+",str(scope["locator"])): return "invalid_resume_scope"
    breadcrumb=value["structural_breadcrumb"]
    if not isinstance(breadcrumb,list) or not breadcrumb or len(breadcrumb)>20: return "invalid_resume_breadcrumb"
    if any(not isinstance(item,Mapping) or set(item)!={"node_id","title"} or not _safe(item["node_id"]) or not isinstance(item["title"],str) or not item["title"].strip() or len(item["title"])>300 for item in breadcrumb): return "invalid_resume_breadcrumb"
    selected=value["selected"]
    if selected is not None and (not isinstance(selected,Mapping) or set(selected)!={"kind","id","label"} or selected["kind"] not in {"structure","concept","claim","gloss"} or not _safe(selected["id"]) or not isinstance(selected["label"],str) or not selected["label"].strip()): return "invalid_resume_selection"
    question=value["unresolved_question"]
    if question is not None and (not isinstance(question,str) or not question.strip() or len(question)>2000): return "invalid_resume_question"
    return None if _time(value["occurred_at"]) else "invalid_resume_time"

def _dir(root:Path,create:bool)->Path|None:
    path=root/"resume-contexts"
    if path.exists(): return path if path.is_dir() and not path.is_symlink() else None
    if not create:return path
    try:path.mkdir(mode=0o700,parents=True)
    except OSError:return None
    return path

def _write(path:Path,record:Mapping[str,Any])->bool:
    fd,name=tempfile.mkstemp(prefix=f".{path.stem}.",dir=path.parent); temp=Path(name)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as handle: json.dump(record,handle,ensure_ascii=False,sort_keys=True,indent=2);handle.write("\n");handle.flush();os.fsync(handle.fileno())
        os.replace(temp,path)
        directory_descriptor=os.open(path.parent,os.O_RDONLY)
        try:os.fsync(directory_descriptor)
        finally:os.close(directory_descriptor)
        return True
    except OSError:return False
    finally:temp.unlink(missing_ok=True)

def record_resume_context(root:str|os.PathLike[str],request:Any)->ContinuityResult:
    problem=validate_resume_request(request)
    if problem:return _result("rejected",problem=problem)
    root_path=Path(root);record={**request,"schema_version":EVENT_VERSION}
    with _WRITE_LOCK:
        directory=_dir(root_path,True)
        if directory is None:return _result("failed",problem="resume_directory_failed")
        path=directory/f"{request['event_id']}.json"
        if path.exists():
            try:existing=json.loads(path.read_text(encoding="utf-8"))
            except (OSError,UnicodeError,json.JSONDecodeError):return _result("failed",problem="resume_read_failed")
            return _result("unchanged",{"context":existing}) if existing==record else _result("conflict",problem="resume_event_conflict")
        return _result("recorded",{"context":record}) if _write(path,record) else _result("failed",problem="resume_write_failed")

def latest_resume_context(root:str|os.PathLike[str],learning_unit_id:str)->ContinuityResult:
    if not _safe(learning_unit_id):return _result("rejected",problem="invalid_learning_unit")
    directory=_dir(Path(root),False)
    if directory is None:return _result("rejected",problem="unsafe_resume_directory")
    if not directory.exists():return _result("ready",{"context":None})
    matches=[]
    try:paths=sorted(directory.iterdir())
    except OSError:return _result("failed",problem="resume_list_failed")
    for path in paths:
        if path.is_symlink() or not path.is_file() or not EVENT_ID.fullmatch(path.stem):continue
        try:record=json.loads(path.read_text(encoding="utf-8"))
        except (OSError,UnicodeError,json.JSONDecodeError):return _result("failed",problem="resume_read_failed")
        if record.get("schema_version")!=EVENT_VERSION:return _result("failed",problem="resume_read_failed")
        if record.get("learning_unit_id")==learning_unit_id:matches.append(record)
    matches.sort(key=lambda item:(item["occurred_at"],item["event_id"]),reverse=True)
    return _result("ready",{"context":matches[0] if matches else None})

__all__=["ContinuityResult","EVENT_VERSION","REQUEST_VERSION","latest_resume_context","record_resume_context","validate_resume_request"]
