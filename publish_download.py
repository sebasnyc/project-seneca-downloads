"""Maintainer-dispatched binary publishing; contains no Seneca app source."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.request
from urllib.parse import urlsplit
import zipfile

REPO = 'sebasnyc/project-seneca-downloads'
MAX_BYTES = 512*1024*1024


def gh(*args):
    return subprocess.check_output(['gh', *args], text=True)


def allowed_url(value):
    url = urlsplit(value)
    return (url.scheme == 'https' and url.hostname and url.hostname.endswith('.oaiusercontent.com')
            and url.username is None and url.password is None and url.port in (None,443))


class Redirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        if not allowed_url(newurl): raise ValueError('Untrusted build download redirect.')
        return super().redirect_request(request, fp, code, message, headers, newurl)


def main():
    version = os.environ['SENECA_VERSION']
    url = os.environ['SENECA_ARCHIVE_URL']
    expected = os.environ['SENECA_ARCHIVE_SHA']
    # The link grants temporary access only to binaries intended for this public release.
    print('::add-mask::'+url, flush=True)
    if not re.fullmatch(r'\d+\.\d+\.\d+',version) or not re.fullmatch(r'[0-9a-f]{64}',expected) or not allowed_url(url):
        raise ValueError('Invalid version, archive URL or digest.')
    if os.environ['GH_REPO'] != REPO: raise ValueError('Wrong release destination.')
    repo = json.loads(gh('api',f'repos/{REPO}'))
    if repo['private'] or repo['full_name'] != REPO: raise ValueError('Expected the public downloads repository.')
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary); archive = root/'build.zip'
        digest = hashlib.sha256(); count = 0
        with urllib.request.build_opener(Redirect()).open(url,timeout=120) as response, archive.open('xb') as target:
            while chunk := response.read(1024*1024):
                count += len(chunk)
                if count > MAX_BYTES: raise ValueError('Build archive too large.')
                digest.update(chunk); target.write(chunk)
        if digest.hexdigest() != expected: raise ValueError('Build archive checksum mismatch.')
        setup = f'Seneca-{version}-Windows-x64-Setup.exe'
        portable = f'Seneca-{version}-Windows-x64-Portable.zip'
        names = [f'installer/output/{setup}',f'dist/{portable}','dist/SHA256SUMS.txt','dist/build-info.json']
        with zipfile.ZipFile(archive) as zipped:
            if set(zipped.namelist()) != set(names): raise ValueError('Archive must contain only the four release files.')
            if any(i.file_size > MAX_BYTES for i in zipped.infolist()): raise ValueError('Release file too large.')
            zipped.extractall(root)
        info = json.loads((root/'dist/build-info.json').read_text())
        if info['version'] != version: raise ValueError('Build version does not match.')
        paths = [root/n for n in names]
        checks = {}
        for line in paths[2].read_text().splitlines():
            sha,name = line.split()
            if name in checks or not re.fullmatch(r'[0-9a-f]{64}',sha): raise ValueError('Invalid checksum manifest.')
            checks[name] = sha
        if set(checks) != {setup,portable}: raise ValueError('Unexpected checksum entries.')
        for path in paths[:2]:
            with path.open('rb') as stream: digest = hashlib.file_digest(stream,'sha256').hexdigest()
            if digest != checks[path.name]: raise ValueError('Release file checksum mismatch.')
        notes = root/'release-notes.md'
        notes.write_text(f'''Seneca {version} — cleaner menus

The main menu now has four daily choices: **Continue studying**, **My courses**, **Ask Seneca**, and **Settings**. Continue returns to the last course or conversation, and the launcher closes when a study/settings action opens.

Settings is split into **Companion**, **AI & Voice**, and **Privacy & Data**. Movement/perching controls are collapsed by default. Backups live under Privacy & Data; updates, diagnostics and problem reports are under **Help & About**. Syllabus import and revision/study-pack exports are grouped under **Course actions**. Weekly summaries stay in Today. Ctrl+K still finds actions, and Ctrl+Comma opens Settings directly.

Existing study tools, saved connections, API keys, chats, drafts, course work and privacy choices are retained. No new AI requests, background monitoring or data migration is introduced by this layout change.

Download **{setup}** to install, or **{portable}** for a portable copy. Installed copies can update through **Help & About → Updates**. Quit Seneca before manual installation; portable replacement remains manual. Python and Node are not required.

Automated Windows Server 2022 checks cover 125 Python tests, the actual frozen app, navigation and study workflows, encrypted-data restoration, upgrade from 0.10.0, relaunch/reinstall and uninstall preservation. Physical Windows 11 and live audio/model acceptance remain separate hands-on checks.

**Unsigned prototype:** Windows may show a publisher/reputation warning. SHA256SUMS.txt and build-info.json document integrity and provenance.

Seneca is by Sebastian Canales, its original artist and art rights holder. PolyForm Noncommercial 1.0.0, required project-credit notices and bundled third-party notices apply. Application source development remains private.
''',encoding='utf-8')
        tag = 'v'+version
        lookup = subprocess.run(['gh','release','view',tag,'--json','isDraft'],capture_output=True,text=True)
        if lookup.returncode == 0:
            if not json.loads(lookup.stdout)['isDraft']: raise ValueError('This version is already published.')
        else:
            gh('release','create',tag,'--draft','--title',f'Seneca {version}','--notes-file',str(notes),'--target','main')
        gh('release','upload',tag,'--clobber',*(str(p) for p in paths))
        releases = json.loads(gh('api',f'repos/{REPO}/releases?per_page=100'))
        published = next(r for r in releases if r['tag_name'] == tag)
        if not published['draft']: raise ValueError('Expected an unpublished draft.')
        assets = published['assets']
        if {(a['name'],a['size']) for a in assets} != {(p.name,p.stat().st_size) for p in paths}:
            raise ValueError('Uploaded asset sizes do not match.')
        for asset in assets:
            path = next(p for p in paths if p.name == asset['name'])
            with path.open('rb') as stream: digest = hashlib.file_digest(stream,'sha256').hexdigest()
            if asset.get('digest') != 'sha256:'+digest: raise ValueError('Uploaded asset digest does not match.')
        gh('release','edit',tag,'--draft=false','--latest','--notes-file',str(notes))
        print(f'https://github.com/{REPO}/releases/tag/{tag}')


if __name__ == '__main__': main()
