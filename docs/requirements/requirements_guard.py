#!/usr/bin/env python3
"""Local traceability checker. Does not run or certify KGnote product tests.
Python 3.10+; standard library only; no network or repository mutation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SEMANTIC_FIELDS = ('title','source_refs','basis','obligation','forbidden_substitute','acceptance','scenario_ids','priority_proposal','decision_state','area')
GLOBAL_IDS = ('KG-WF-01','KG-WF-02','KG-WF-03','KG-MEM-06','KG-KNOW-03','KG-PLAT-05','KG-GOV-07')


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(obj, dict):
        raise ValueError(f'{path.name}: expected a JSON object')
    return obj


def duplicates(values: list[str]) -> set[str]:
    seen, repeated = set(), set()
    for value in values:
        if value in seen:
            repeated.add(value)
        seen.add(value)
    return repeated


def inspect(ledger: dict, sources: dict, scenarios: dict, original: Path | None = None, repo: Path | None = None) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    reqs, ss, sc = ledger.get('requirements', []), sources.get('sources', []), scenarios.get('scenarios', [])
    if not reqs or not isinstance(reqs, list):
        return ['requirements must be a non-empty array'], []
    for label, records in [('requirement', reqs),('source', ss),('scenario', sc)]:
        if any(not isinstance(r, dict) or not isinstance(r.get('id'), str) for r in records):
            return [f'{label}: every record needs a string id'], []
        for rid in sorted(duplicates([r['id'] for r in records])):
            errors.append(f'duplicate {label}: {rid}')
    req_ids, src_ids, scenario_ids = ({r['id'] for r in xs} for xs in (reqs,ss,sc))
    def check_file(path_string: str, label: str) -> None:
        if repo is None:
            return
        root = repo.resolve()
        p = (root / path_string).resolve()
        if not p.is_relative_to(root):
            errors.append(f'{label}: path escapes repository')
        elif not p.is_file():
            errors.append(f'{label}: file does not exist: {path_string}')
    for r in reqs:
        rid=r['id']
        for f in ('title','obligation','forbidden_substitute','area','basis','decision_state'):
            if not isinstance(r.get(f), str) or not r[f].strip():
                errors.append(f'{rid}: missing {f}')
        if not isinstance(r.get('revision'), int) or isinstance(r.get('revision'), bool) or r['revision'] < 1:
            errors.append(f'{rid}: invalid revision')
        for f, allowed in [('source_refs',src_ids),('scenario_ids',scenario_ids)]:
            refs=r.get(f)
            if not isinstance(refs,list) or not refs or any(not isinstance(x,str) for x in refs):
                errors.append(f'{rid}: missing/invalid {f}')
            else:
                for missing in set(refs)-allowed:
                    errors.append(f'{rid}: dangling {f}: {missing}')
        ac=r.get('acceptance',{})
        if not isinstance(ac,dict) or any(not ac.get(k) for k in ('positive','negative')):
            errors.append(f'{rid}: acceptance needs positive AND negative conditions')
        delivery=r.get('delivery',{})
        status=delivery.get('status')
        allowed_statuses={'unverified','not_implemented','partial','reported_implemented','implemented','automated_verified','human_accepted'}
        if status not in allowed_statuses:
            errors.append(f'{rid}: unsupported delivery status')
        for field in ('implementation_refs','test_refs','evidence_refs'):
            if not isinstance(delivery.get(field),list):
                errors.append(f'{rid}: {field} must be an array')
        if status in {'implemented','automated_verified','human_accepted'} and not delivery.get('implementation_refs'):
            errors.append(f'{rid}: implementation claimed without implementation_refs')
        if status in {'automated_verified','human_accepted'} and (not delivery.get('test_refs') or not delivery.get('evidence_refs')):
            errors.append(f'{rid}: verification claimed without test + run evidence')
        if status == 'human_accepted' and not any(isinstance(e,dict) and e.get('kind')=='human_acceptance' and e.get('source_ref') in src_ids for e in delivery.get('evidence_refs',[])):
            errors.append(f'{rid}: human acceptance has no source-linked decision')
        for field in ('implementation_refs','test_refs','evidence_refs'):
            for ref in delivery.get(field,[]):
                if isinstance(ref,str):
                    check_file(ref,f'{rid}.{field}')
                elif isinstance(ref,dict) and isinstance(ref.get('path'),str):
                    check_file(ref['path'],f'{rid}.{field}')
                else:
                    errors.append(f'{rid}.{field}: invalid file reference')
    covered=set()
    for row in ledger.get('source_section_disposition',[]):
        sec=row.get('section')
        if sec in covered:
            errors.append(f'duplicate source section disposition: {sec}')
        covered.add(sec)
        if row.get('disposition') not in {'mapped','context_only','historical','superseded','open'} or not row.get('rationale'):
            errors.append(f'section {sec}: needs explicit disposition and rationale')
        if row.get('disposition')=='mapped' and not row.get('requirement_ids'):
            errors.append(f'section {sec}: mapped without requirement_ids')
        for rid in row.get('requirement_ids',[]):
            if rid not in req_ids:
                errors.append(f'section {sec}: dangling requirement: {rid}')
        for sid in row.get('source_ids',[]):
            if sid not in src_ids:
                errors.append(f'section {sec}: dangling source: {sid}')
    if covered != set(range(1,28)):
        errors.append('original sections 01–27 are not all dispositioned exactly once')
    for case in sc:
        for f in ('given','when','then','must_fail_if'):
            if not isinstance(case.get(f),str) or not case[f].strip():
                errors.append(f"{case['id']}: missing {f}")
        for sid in case.get('source_refs',[]):
            if sid not in src_ids:
                errors.append(f"{case['id']}: dangling source: {sid}")
        run_status=case.get('run_status')
        if run_status not in {'not_run','automated_partial','automated_pass','automated_fail','manual_pass','manual_fail'}:
            errors.append(f"{case['id']}: unsupported run_status")
        binding=case.get('test_binding')
        if run_status!='not_run' and not binding:
            errors.append(f"{case['id']}: execution claimed without binding")
        if binding is not None:
            if not isinstance(binding,dict) or not isinstance(binding.get('test_refs'),list) or not binding.get('test_refs'):
                errors.append(f"{case['id']}: test_binding needs non-empty test_refs")
            else:
                for ref in binding['test_refs']:
                    if not isinstance(ref,dict) or not isinstance(ref.get('path'),str) or not isinstance(ref.get('selector'),str):
                        errors.append(f"{case['id']}: invalid test reference")
                    else:
                        check_file(ref['path'],f"{case['id']}.test_binding")
            evidence=binding.get('evidence_refs') if isinstance(binding,dict) else None
            if run_status!='not_run' and (not isinstance(evidence,list) or not evidence):
                errors.append(f"{case['id']}: executed scenario needs evidence_refs")
            for ref in evidence or []:
                if not isinstance(ref,str):
                    errors.append(f"{case['id']}: invalid scenario evidence reference")
                else:
                    check_file(ref,f"{case['id']}.test_binding")
    if original:
        data=original.read_bytes()
        if hashlib.sha256(data).hexdigest()!=sources.get('original_file_sha256'):
            errors.append('original source checksum mismatch; do not silently reanchor')
        else:
            ls=data.decode('utf-8').splitlines()
            for s in ss:
                if s.get('type')!='original_dialogue':
                    continue
                loc=s.get('locator',{})
                a,b=loc.get('start_line'),loc.get('end_line')
                if not isinstance(a,int) or not isinstance(b,int) or not (1<=a<=b<=len(ls)):
                    errors.append(f"{s['id']}: invalid original line range")
                elif s.get('excerpt') not in '\n'.join(ls[a-1:b]):
                    errors.append(f"{s['id']}: excerpt does not match source range")
    else:
        warnings.append('Raw attachment not supplied: run --original PATH to check original hash and excerpt anchors.')
    if repo is None:
        warnings.append('No repository supplied: product implementation/test artifact paths have NOT been inspected.')
    warnings.append('Structural traceability only: a PASS does NOT prove semantic completeness, real test execution, UI fitness, or learning effectiveness.')
    return errors,warnings


def compare(base:dict, candidate:dict) -> list[dict]:
    b={r['id']:r for r in base['requirements']}; c={r['id']:r for r in candidate['requirements']}
    changes=[]
    for rid in sorted(set(b)-set(c)):
        changes.append({'id':rid,'kind':'removed_requirement','action':'retain old ID and create a source-linked decision; do not silently delete'})
    for rid in sorted(set(c)-set(b)):
        changes.append({'id':rid,'kind':'added_requirement','action':'confirm source and proposed/adopted status'})
    for rid in sorted(set(b)&set(c)):
        fields=[f for f in SEMANTIC_FIELDS if b[rid].get(f)!=c[rid].get(f)]
        if fields:
            changes.append({'id':rid,'kind':'semantic_fields_changed','fields':fields,'revision_increased':c[rid].get('revision',0)>b[rid].get('revision',0),'action':'impact review required; this checker cannot approve the change'})
    return changes


def compare_catalog(base:dict, candidate:dict, collection:str, fields:tuple[str,...] | None) -> list[dict]:
    b={r['id']:r for r in base[collection]}; c={r['id']:r for r in candidate[collection]}
    changes=[]
    for rid in sorted(set(b)-set(c)):
        changes.append({'id':rid,'kind':f'removed_{collection}_record','action':'review required'})
    for rid in sorted(set(c)-set(b)):
        changes.append({'id':rid,'kind':f'added_{collection}_record','action':'review source and scope'})
    for rid in sorted(set(b)&set(c)):
        keys=fields if fields is not None else tuple(sorted(set(b[rid])|set(c[rid])))
        changed=[k for k in keys if b[rid].get(k)!=c[rid].get(k)]
        if changed:
            changes.append({'id':rid,'kind':f'{collection}_content_changed','fields':changed,'action':'inspect supporting source and affected requirements'})
    return changes


def render(root:Path, ledger:dict, sources:dict, cases:dict) -> None:
    source_map={s['id']:s for s in sources['sources']}
    grouped=defaultdict(list)
    for r in ledger['requirements']: grouped[r['area']].append(r)
    out=['# KGnote 整合需求與追溯清單','', '> GENERATED FROM requirements.json — 不要手改此檔以建立第二份真相。', '', '本檔是候選整合基線；來源明示的意圖與本次治理/實作提案分開。所有產品 delivery 初始為 unverified，不表示未實作，也不表示已驗證。', '', '## 原始 27 節處置', '', '| 節 | 處置 | 需求 ID | 解讀與限制 |','|---|---|---|---|']
    for row in ledger['source_section_disposition']:
        out.append(f"| {row['section']:02d} | {row['disposition']} | {', '.join(row['requirement_ids']) or '—'} | {row['rationale']} |")
    for area,items in grouped.items():
        out+=['',f'## {area}','']
        for r in items:
            out += [f"### {r['id']} · {r['title']}", '',f"**必須保留：** {r['obligation']}", '',f"**不得拿來替代：** {r['forbidden_substitute']}", '', f"**驗收：** {r['acceptance']['positive']}", '', f"**情境：** {', '.join(r['scenario_ids'])}。**依據類別：** {r['basis']}。**採納標記：** {r['decision_state']}。**交付：** {r['delivery']['status']}。", '', '**來源：**']
            for sid in r['source_refs']:
                s=source_map[sid]; loc=s.get('locator',{})
                where=f"原始對話 §{s['section']:02d}，{s['speaker']}，L{loc['start_line']}–L{loc['end_line']}" if s.get('type')=='original_dialogue' else s['title']
                out.append(f"- `{sid}`：{where}")
            out.append('')
    (root/'REQUIREMENTS_TRACE.md').write_text('\n'.join(out).rstrip('\n')+'\n',encoding='utf-8')
    out=['# KGnote 黃金驗收情境','', '> GENERATED FROM scenarios.json。以下是驗收規格，不是已綁定或已執行的產品測試。', '', '同一情境可以覆蓋多個需求。工程測試與人工閱讀效果的 rubric 要分開；不以資料格式通過代替畫面語意驗收。']
    for s in cases['scenarios']:
        related=[r['id'] for r in ledger['requirements'] if s['id'] in r['scenario_ids']]
        out += ['',f"## {s['id']} · {s['title']}", '', f"**Given：** {s['given']}", '',f"**When：** {s['when']}", '',f"**Then：** {s['then']}", '',f"**以下狀況必須判失敗：** {s['must_fail_if']}", '',f"需求：{', '.join(related)}", '', f"驗證方法：{s['verification_method']}；狀態：{s['run_status']}；test binding：{json.dumps(s['test_binding'],ensure_ascii=False) if s['test_binding'] else '未綁定'}。"]
    (root/'ACCEPTANCE_SCENARIOS.md').write_text('\n'.join(out)+'\n',encoding='utf-8')
    out=['# 來源索引與角色分界','', '本公開索引保留 stable source IDs 與來源角色，但不重製私人對話、私人學習紀錄、原始機器路徑或未授權附件。產品語意以 linked normalized requirements、決策與驗收情境為準。', '',f"公開 normalized catalog SHA-256：`{sources['original_file_sha256']}`", '', 'withheld source anchor 不是公開引文或獨立事實查核；原始私人來源只存在於 repository 外的受控復原備份。']
    for s in sources['sources']:
        out+=['',f"## {s['id']} · {s['title']}",'',f"角色：{s['speaker']}；類型：{s['type']}。",'']
        if s.get('locator'): out += [f"定位：`{json.dumps(s['locator'],ensure_ascii=False)}`",'']
        if s.get('excerpt'): out += ['公開安全摘錄：','', '```text',s['excerpt'],'```','']
        if s.get('quote'): out += [f"> {s['quote']}",'']
        if s.get('summary'): out += [s['summary'],'']
        if s.get('url'): out += [f"官方參考：{s['url']}",'']
        out += [s['scope_note']]
    (root/'SOURCE_INDEX.md').write_text('\n'.join(out)+'\n',encoding='utf-8')
    requirement_by_scenario=defaultdict(list)
    for r in ledger['requirements']:
        for scenario_id in r['scenario_ids']:
            requirement_by_scenario[scenario_id].append(r)
    out=['# Source → Requirement → Scenario → Test / Result Matrix','', '> GENERATED FROM requirements.json, sources.json, and scenarios.json. Do not edit this view by hand.', '', '| Source(s) | Requirement | Delivery | Scenario | Run | Actual product test(s) | Evidence |', '|---|---|---|---|---|---|---|']
    for case in cases['scenarios']:
        binding=case.get('test_binding') or {}
        tests='<br>'.join(f"`{ref['path']}::{ref['selector']}`" for ref in binding.get('test_refs',[])) or '—'
        evidence='<br>'.join(f"`{ref}`" for ref in binding.get('evidence_refs',[])) or '—'
        for r in requirement_by_scenario[case['id']]:
            sources_text='<br>'.join(f"`{sid}`" for sid in r['source_refs'])
            out.append(f"| {sources_text} | `{r['id']}` {r['title']} | `{r['delivery']['status']}` | `{case['id']}` {case['title']} | `{case['run_status']}` | {tests} | {evidence} |")
    (root/'TRACEABILITY_MATRIX.md').write_text('\n'.join(out)+'\n',encoding='utf-8')


def packet(ledger:dict,sources:dict,scenarios:dict,areas:list[str],ids:list[str]) -> str:
    wanted=set(ids)
    for r in ledger['requirements']:
        if r['area'] in areas: wanted.add(r['id'])
    if not wanted: raise ValueError('Choose --area or --id; do not silently dump the entire ledger')
    all_ids={r['id'] for r in ledger['requirements']}
    if wanted-all_ids: raise ValueError('Unknown requirement IDs: '+', '.join(sorted(wanted-all_ids)))
    wanted.update(GLOBAL_IDS)
    selected=[r for r in ledger['requirements'] if r['id'] in wanted]
    checksum=hashlib.sha256(json.dumps({'ledger':ledger,'sources':sources,'scenarios':scenarios},sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()
    out=['# 任務 Context Packet','',f"Baseline：`{ledger['baseline_id']}`",f"Requirement/source/scenario bundle SHA-256：`{checksum}`",'', '此 packet 是當前需求的任務切片，不是重新解釋或另建一套產品真相。實作前另讀 DECISIONS_AND_CONFLICTS.md；不可用舊AI提案覆蓋最近使用者澄清。', '', '## 本任務與全域保護需求']
    for r in selected:
        out += ['',f"### {r['id']} r{r['revision']} · {r['title']}",r['obligation'], f"禁止替代：{r['forbidden_substitute']}",f"驗收：{r['acceptance']['positive']}",f"來源：{', '.join(r['source_refs'])}",f"狀態：{r['delivery']['status']}／{r['decision_state']}"]
    case_ids={sid for r in selected for sid in r['scenario_ids']}
    out+=['','## 必讀驗收情境']
    for s in scenarios['scenarios']:
        if s['id'] in case_ids:
            out += ['',f"### {s['id']} · {s['title']}",f"Given：{s['given']}",f"When：{s['when']}",f"Then：{s['then']}",f"失敗條件：{s['must_fail_if']}"]
    src_map={s['id']:s for s in sources['sources']}
    out+=['','## 來源位置']
    for sid in sorted({sid for r in selected for sid in r['source_refs']}):
        s=src_map[sid]
        out += [f"- {sid} [{s['speaker']}] {s['title']} · {json.dumps(s.get('locator',{'url':s.get('url')}),ensure_ascii=False)}"]
    out+=['','## 結案前由執行者補齊','工作樹／基底版本：','本次改動的模組與路徑：','實際測試命令、test ID、結果檔與snapshot：','仍未滿足的需求／沒有執行的驗收：','需求或預設行為變更決策：','可回退方式與下一步：']
    return '\n'.join(out)+'\n'


def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=ROOT)
    sub=p.add_subparsers(dest='command',required=True)
    c=sub.add_parser('check'); c.add_argument('--original',type=Path);c.add_argument('--repo',type=Path)
    sub.add_parser('render')
    q=sub.add_parser('packet'); q.add_argument('--area',action='append',default=[]);q.add_argument('--id',action='append',default=[]);q.add_argument('--output',type=Path)
    d=sub.add_parser('diff');d.add_argument('--base',type=Path,required=True);d.add_argument('--candidate',type=Path,required=True)
    a=p.parse_args()
    try:
        if a.command=='diff':
            changes=compare(load(a.base),load(a.candidate))
            warnings=[]
            for name, collection, fields in [
                ('scenarios.json','scenarios',('title','source_refs','given','when','then','must_fail_if','verification_method')),
                ('sources.json','sources',None),
            ]:
                bp,cp=a.base.parent/name,a.candidate.parent/name
                if not bp.is_file() or not cp.is_file():
                    warnings.append(f'{name}: old/new companion catalogs not both present; full intent delta not checked')
                    continue
                changes.extend(compare_catalog(load(bp),load(cp),collection,fields))
            needs_review=bool(changes or warnings)
            print(json.dumps({'status':'review_required' if needs_review else 'no_semantic_delta','changes':changes,'warnings':warnings},ensure_ascii=False,indent=2))
            return 2 if needs_review else 0
        ledger=load(a.root/'requirements.json'); sources=load(a.root/'sources.json'); cases=load(a.root/'scenarios.json')
        errors,warnings=inspect(ledger,sources,cases,getattr(a,'original',None),getattr(a,'repo',None))
        if errors:
            print(json.dumps({'status':'invalid_traceability','errors':errors,'warnings':warnings},ensure_ascii=False,indent=2))
            return 1
        if a.command=='check':
            print(json.dumps({'status':'structural_traceability_pass','requirements':len(ledger['requirements']),'scenarios':len(cases['scenarios']),'all_product_scenarios_unrun':all(s['run_status']=='not_run' for s in cases['scenarios']),'warnings':warnings},ensure_ascii=False,indent=2))
        elif a.command=='render':
            render(a.root,ledger,sources,cases)
            print('Generated REQUIREMENTS_TRACE.md, ACCEPTANCE_SCENARIOS.md, SOURCE_INDEX.md, TRACEABILITY_MATRIX.md. Product tests were not run.')
        elif a.command=='packet':
            output=packet(ledger,sources,cases,a.area,a.id)
            if a.output:
                a.output.parent.mkdir(parents=True,exist_ok=True)
                a.output.write_text(output,encoding='utf-8')
                print(a.output)
            else: print(output,end='')
        return 0
    except (OSError,UnicodeError,json.JSONDecodeError,ValueError,KeyError,TypeError) as e:
        print(f'Traceability operation failed: {e}',file=sys.stderr)
        return 1

if __name__=='__main__':
    raise SystemExit(main())
