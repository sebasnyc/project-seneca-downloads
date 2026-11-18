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
        notes.write_text(f'''Seneca {version} — Windows & macOS

This release brings Seneca's existing second-brain and school-day features to Mac with the same codebase and version as Windows.

- **Windows:** choose **{setup}**, or **{portable}**. Existing installed copies use their Windows-only automatic updater. Windows never selects Mac ZIPs.
- **Mac:** choose **Seneca-{version}-macOS-arm64.zip** for Apple Silicon or **Seneca-{version}-macOS-x86_64.zip** for Intel, when listed below. Requires macOS 14+. Expand the ZIP and move Seneca.app to Applications. Mac builds are added only after their architecture-specific checks pass.
- **Mac updates:** Help & About → Updates checks and verifies the ZIP for this processor. Save it, quit Seneca and replace the app manually. No Windows installer is selected or executed on Mac.
- **Saved data:** Windows keeps its DPAPI-protected profile. Mac keeps an authenticated encrypted profile in ~/Library/Application Support/Seneca and its encryption key in Keychain. Replacing the app preserves both. Do not delete the data folder or Keychain item; an updated unsigned build may ask for Keychain access again. Password backups transfer study data without provider keys.
- **Same student tools:** linked notes/backlinks, preserved original writing with separate AI interpretations, boards/maps/timeline, timetable/check-ins, assignment views and reviewed class-aware catch-up plans. Local organization requires no paid API. AI and voice remain opt-in and reviewed.
- **Mac differences:** per-user login startup after moving to Applications; Windows window/taskbar perching, global quick-help and Defender/connection queries are unavailable. Local file hashes remain available.

**Prototype signing:** Windows is unsigned. Mac uses ad-hoc integrity signing, without Developer ID or notarization. If macOS blocks it, review System Settings → Privacy & Security → Open Anyway. Never disable Gatekeeper. Physical device, microphone/speaker and model acceptance remain separate from CI fixtures.

Platform-specific checksums and build-info files document provenance. The source remains in the original private repository; this public repository distributes downloads only. Seneca is by Sebastian Canales, its original artist and art rights holder. PolyForm Noncommercial 1.0.0 and bundled notices apply.
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
