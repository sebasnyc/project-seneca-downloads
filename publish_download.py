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
        notes.write_text(f'''Seneca {version} — Second brain & School day

Keep a connected local notebook and fit studying around real classes. The four-action main menu stays simple; the new workflows live inside Courses and Today.

- **Second brain:** tagged notes, basic [[Note title]] links, backlinks, selected source associations, original/recent saved versions, topic/prerequisite maps and a dated timeline. Ambiguous links are not guessed; prerequisite cycles are rejected. Explicitly attached tutor interpretations are labeled separately from student notes and use Seneca’s math formatting.
- **Visual study boards:** native movable cards/groups, directional labeled connections, Undo and reviewed JSON Canvas import/export. Markdown notes can be imported/exported. File/link cards remain inert references. These are original Seneca implementations, not bundled proprietary or AGPL application code.
- **School day:** manually add dated weekly classes or review a selected .ics calendar for the next 16 weeks. Common daily/weekly recurrence, weekday/week-start rules, exclusions and IANA timezones are supported. Unsupported events and changed individual occurrences are reported for manual review. No calendar-account access or background sync is required. Optional class quiet mode suppresses companion distraction during saved meetings.
- **After class and catch-up:** a short check-in becomes a dated connected note. Checklist, draggable board and calendar views share the same assignments. Catch-up plans use explicit available hours, avoid classes, include buffers/breaks, retain deadlines/completed blocks and report work that cannot fit. Replacement blocks require approval; overdue work is labeled late. Timed and manually reported completion remain distinct.
- **Personal touches:** subtle gold/cyan/pearl accents, a saved resting pose and optional effort milestones. All accents are available, earned milestones stay earned, and quiet/reduced-motion controls remain respected.

Ask tutor opens/resumes a conversation for the chosen note and selected sources while preserving other chats/drafts. Nothing is sent automatically: cloud sharing still uses Seneca’s privacy checks and exact request review. The whole notebook is never silently uploaded. Local organization and planning require no paid API.

Notes, boards, classes, captures, planned blocks and unfinished drafts are included in the Windows-protected profile and validated password backups. Restore remaps relationships and retains existing work. Shared course packs continue to exclude personal second-brain/school-day collections by default. Open-format exports contain readable study content and should be reviewed before sharing.

Download **{setup}** to install, or **{portable}** for a portable copy. Installed copies update through **Help & About → Updates**; quit Seneca before manual installation. Existing keys, connections and study data stay outside the installation folder. Python and Node are not required.

Automated Windows Server 2022 checks cover 138 Python tests, 13 avatar tests, actual frozen study/school workflows, timezone resources, encrypted backups/profile reload, upgrade from 0.10.1, relaunch/reinstall and uninstall preservation. Physical Windows 11 interactions, live audio/model quality and every third-party calendar dialect remain separate hands-on checks.

**Unsigned prototype:** Windows may show a publisher/reputation warning. SHA256SUMS.txt and build-info.json document integrity and provenance.

Seneca is by Sebastian Canales, its original artist and art rights holder. PolyForm Noncommercial 1.0.0, required project-credit notices and bundled third-party notices apply. Source development stays private.
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
