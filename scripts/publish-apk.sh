#!/bin/bash
# Run on Olamidepanel with a verified signed APK and the deployed store catalog path.
set -euo pipefail
apk=${1:?Usage: publish-apk.sh signed-AIMS.apk store-catalog.json store-download-directory}
catalog=${2:?Catalog path required}
store_dir=${3:?Store download directory required}
command -v apksigner >/dev/null
apksigner verify "$apk"
install -d -m 755 /opt/aims/static/downloads "$store_dir"
install -m 644 "$apk" /opt/aims/static/downloads/AIMS.apk
install -m 644 "$apk" "$store_dir/AIMS.apk"
python3 - "$catalog" <<'PY'
import json,sys,pathlib,shutil,datetime,os
p=pathlib.Path(sys.argv[1]);data=json.loads(p.read_text())
items=data if isinstance(data,list) else data.get('apps')
if not isinstance(items,list):raise SystemExit('Unsupported catalog schema. No catalog change made.')
entry={'id':'aims','name':'AIMS — Africa Identity Management System','description':'One Identity. A World of Possibilities.','website':'https://identity.africandroid.world/','download':'https://identity.africandroid.world/download','platform':'Android','icon':'https://identity.africandroid.world/static/logo.png'}
idx=next((i for i,x in enumerate(items) if x.get('id')=='aims'),None)
if idx is None:items.append(entry)
else:items[idx]=entry
shutil.copy2(p,str(p)+'.backup-'+datetime.datetime.now().strftime('%Y%m%d%H%M%S'))
tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2));os.replace(tmp,p)
print('Catalog updated. Verify the store UI and download link.')
PY
