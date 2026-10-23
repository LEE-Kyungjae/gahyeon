#!/usr/bin/env python3
"""Summarize opt-in ledger metadata without reading user/tool payloads."""
import re,json,sys
from datetime import datetime
from collections import defaultdict

def summarize(text):
    runs=defaultdict(lambda:{'events':[], 'modelMs':0., 'toolMs':0., 'stages':[]})
    pattern=r'LATENCY_EVENT run=(\S+) event=(\S+) step=(\d+) tool=(\S+) at=(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d(?:\.\d+)?)'
    pending={}
    for run,event,step,tool,stamp in re.findall(pattern,text):
        at=datetime.strptime(stamp, '%Y-%m-%d %H:%M:%S.%f' if '.' in stamp else '%Y-%m-%d %H:%M:%S'); item=runs[run]; item['events'].append((event,at))
        kind='model' if event.startswith('MODEL_CALL') else 'tool'
        key=(run,kind,step,tool)
        if event in ('MODEL_CALL_STARTED','TOOL_CALL_STARTED'):pending[key]=at
        elif event in ('MODEL_CALL_COMPLETED','TOOL_CALL_COMPLETED','TOOL_CALL_FAILED') and key in pending:
            ms=(at-pending.pop(key)).total_seconds()*1000;item[kind+'Ms']+=ms
            item['stages'].append(dict(kind=kind,step=int(step),tool=tool,ms=round(ms,2)))
    for item in runs.values():
        events=item.pop('events');start=next((t for e,t in events if e=='RUN_CREATED'),None);end=next((t for e,t in reversed(events) if e in ('RUN_SUCCEEDED','RUN_FAILED','RUN_CANCELLED')),None)
        item['complete']=bool(start and end)
        item['outcome']=next((e for e,t in reversed(events) if e in ('RUN_SUCCEEDED','RUN_FAILED','RUN_CANCELLED')), 'INCOMPLETE')
        item['totalMs']=round((end-start).total_seconds()*1000,2) if start and end else None
        item['modelMs']=round(item['modelMs'],2);item['toolMs']=round(item['toolMs'],2)
        item['otherMs']=round(item['totalMs']-item['modelMs']-item['toolMs'],2) if item['complete'] else None
    return dict(runs)

if __name__=='__main__':print(json.dumps(summarize(open(sys.argv[1]).read()),indent=2))
