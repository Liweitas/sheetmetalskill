"""Persist subprocess output, elapsed/CPU time and GNU time's peak process RSS."""
import datetime
import json
import subprocess
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
    with (logs / (name + '.stdout.log')).open('w') as out, (logs / (name + '.stderr.log')).open('w') as err:
        result = subprocess.run(['/usr/bin/time', '-f', fmt, '-o', str(resource),
                                 *map(str, command)], stdout=out, stderr=err, **kwargs)
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
