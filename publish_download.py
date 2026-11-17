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
        notes.write_text(f'''Seneca {version} — Windows x64 prototype\n\nDownload **{setup}** below for installation, or **{portable}** for a portable copy. Python and Node are not required.\n\nQuit older Seneca copies before installing. Version 0.7.2 adds Windows-protected saved connections, API keys, chat/drafts and companion preferences, a normal taskbar entry, and automatic hash-verified updates from this public channel. Installed copies save before updating and restart afterward. Portable updates are installed manually. Older versions did not save session data, so enter your connection once after upgrading from 0.7.1 or earlier.\n\nAutomated Windows Server 2022 checks cover the actual frozen app, native taskbar window, Windows DPAPI, separate-process restoration, installer replacement and uninstall. Hands-on Windows 11 DPI/perching, real audio and live tutoring quality remain separate acceptance checks.\n\n**Unsigned prototype:** Windows may display a publisher/reputation warning. Check SHA256SUMS.txt and build-info.json for download integrity and provenance.\n\nSeneca is by Sebastian Canales, the original artist and art rights holder. PolyForm Noncommercial 1.0.0 and the required owner/project-credit notices apply; third-party components retain their own notices bundled with the app. Source development stays private.\n''')
        tag = 'v'+version
        lookup = subprocess.run(['gh','release','view',tag,'--json','isDraft'],capture_output=True,text=True)
        if lookup.returncode == 0:
            if not json.loads(lookup.stdout)['isDraft']: raise ValueError('This version is already published.')
        else:
            gh('release','create',tag,'--draft','--title',f'Seneca {version}','--notes-file',str(notes),'--target','main')
        gh('release','upload',tag,'--clobber',*(str(p) for p in paths))
        assets = json.loads(gh('release','view',tag,'--json','assets'))['assets']
        if {(a['name'],a['size']) for a in assets} != {(p.name,p.stat().st_size) for p in paths}:
            raise ValueError('Uploaded asset sizes do not match.')
        for asset in assets:
            path = next(p for p in paths if p.name == asset['name'])
            with path.open('rb') as stream: digest = hashlib.file_digest(stream,'sha256').hexdigest()
            if asset.get('digest') != 'sha256:'+digest: raise ValueError('Uploaded asset digest does not match.')
        gh('release','edit',tag,'--draft=false','--latest','--notes-file',str(notes))
        print(f'https://github.com/{REPO}/releases/tag/{tag}')


if __name__ == '__main__': main()
