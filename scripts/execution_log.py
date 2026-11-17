"""Persist subprocess output, elapsed/CPU time and GNU time's peak process RSS."""
import datetime
import json
import resource as usage
import shutil
import subprocess
import sys
import time
from pathlib import Path


def run_stage(logs, name, command, **kwargs):
    logs = Path(logs)
    logs.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    event = {'stage': name, 'command': list(map(str, command)),
             'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat()}
    print(json.dumps(event), flush=True)
    resource = logs / (name + '.resource.json')
    fmt = '{"elapsed_s":%e,"user_s":%U,"system_s":%S,"max_rss_kib":%M,"cpu":"%P","fs_inputs":%I,"fs_outputs":%O}'
    gnu_time = shutil.which('gtime')
    if not gnu_time and shutil.which('time') == '/usr/bin/time' and sys.platform != 'darwin':
        gnu_time = '/usr/bin/time'
    before = usage.getrusage(usage.RUSAGE_CHILDREN)
    with (logs / (name + '.stdout.log')).open('w') as out, (logs / (name + '.stderr.log')).open('w') as err:
        prefix = [gnu_time, '-f', fmt, '-o', str(resource)] if gnu_time else []
        result = subprocess.run([*prefix, *map(str, command)], stdout=out, stderr=err, **kwargs)
    if not gnu_time:
        after = usage.getrusage(usage.RUSAGE_CHILDREN)
        elapsed = time.monotonic() - started
        resource.write_text(json.dumps({
            'elapsed_s': round(elapsed, 3),
            'user_s': round(after.ru_utime - before.ru_utime, 3),
            'system_s': round(after.ru_stime - before.ru_stime, 3),
            'max_rss_kib': after.ru_maxrss if sys.platform != 'darwin' else round(after.ru_maxrss / 1024),
            'cpu': None,
            'fs_inputs': None,
            'fs_outputs': None,
        }))
    event.update(returncode=result.returncode, elapsed_s=round(time.monotonic()-started, 3))
    try:
        event['resources'] = json.loads(resource.read_text().splitlines()[-1])
    except (ValueError, FileNotFoundError):
        event['resources'] = None
    with (logs / 'events.jsonl').open('a') as out:
        out.write(json.dumps(event) + '\n')
    print(json.dumps(event), flush=True)
    result.check_returncode()
    return result
