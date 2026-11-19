"""Publish only one verified, processor-specific Mac binary archive."""
import hashlib,io,json,os,re,tempfile,urllib.request,zipfile
from pathlib import Path
from publish_download import gh,allowed_url,Redirect,REPO,MAX_BYTES


def release_data(tag, draft_only):
    endpoint = f'repos/{REPO}/releases'
    if draft_only:
        view = json.loads(gh('release', 'view', tag, '--json', 'databaseId,isDraft'))
        if view['isDraft'] is not True:
            raise ValueError('Expected an unpublished draft.')
        return json.loads(gh('api', f"{endpoint}/{view['databaseId']}"))
    return json.loads(gh('api', f'{endpoint}/tags/{tag}'))


def main():
    version=os.environ['SENECA_VERSION'];arch=os.environ['SENECA_ARCH'];url=os.environ['SENECA_ARCHIVE_URL'];expected=os.environ['SENECA_ARCHIVE_SHA']
    print('::add-mask::'+url,flush=True)
    if arch not in {'arm64','x86_64'} or not re.fullmatch(r'\d+\.\d+\.\d+',version) or not re.fullmatch(r'[0-9a-f]{64}',expected) or not allowed_url(url):raise ValueError('Invalid Mac build inputs.')
    if os.environ['GH_REPO']!=REPO:raise ValueError('Wrong repository.')
    repo=json.loads(gh('api',f'repos/{REPO}'));assert not repo['private'] and repo['full_name']==REPO
    name=f'Seneca-{version}-macOS-{arch}.zip';tag='v'+version
    draft_only = os.environ.get('SENECA_DRAFT_ONLY') == 'true'
    release = release_data(tag, draft_only)
    if release['draft'] != draft_only or release['prerelease']:
        raise ValueError('Unexpected release state.')
    if any(a['name']==name for a in release['assets']):raise ValueError('Mac asset already published; use a new version.')
    with tempfile.TemporaryDirectory() as tmp:
        root=Path(tmp);outer=root/'artifact.zip';digest=hashlib.sha256();count=0
        with urllib.request.build_opener(Redirect()).open(url,timeout=120) as response,outer.open('xb') as target:
            while chunk:=response.read(1024*1024):
                count+=len(chunk)
                if count>MAX_BYTES:raise ValueError('Build archive too large.')
                target.write(chunk);digest.update(chunk)
        if digest.hexdigest()!=expected:raise ValueError('Build archive checksum mismatch.')
        with zipfile.ZipFile(outer) as z:
            assert z.namelist()==[name] and z.getinfo(name).file_size<=MAX_BYTES
            z.extract(name,root)
        path=root/name
        with zipfile.ZipFile(path) as z:
            assert all(not n.startswith('/') and '..' not in Path(n).parts and '\\' not in n for n in z.namelist())
            info=json.loads(z.read('build-info.json'))
            assert info['version']==version and info['architecture']==arch and info['platform']=='macOS' and re.fullmatch(r'[0-9a-f]{40}',info['commit'])
            assert info['bundle_id']=='org.senecaproject.Seneca' and not info['notarized'] and not info['developer_id_signed']
            for n in ['LICENSE.md','NOTICE.txt']:assert z.read(n)==Path(n).read_bytes()
            import plistlib
            bundle=plistlib.loads(z.read('Seneca.app/Contents/Info.plist'))
            assert bundle['CFBundleIdentifier']==info['bundle_id'] and bundle['CFBundleShortVersionString']==version
            assert info['minimum_macos']==bundle['LSMinimumSystemVersion'] and tuple(map(int,info['minimum_macos'].split('.'))) >= (14,0,0)
        sha=hashlib.file_digest(path.open('rb'),'sha256').hexdigest()
        checksum=root/f'SHA256SUMS-macOS-{arch}.txt';checksum.write_text(sha+'  '+name+'\n')
        provenance=root/f'build-info-macOS-{arch}.json';provenance.write_text(json.dumps(info,indent=2)+'\n')
        paths=[path,checksum,provenance]
        gh('release','upload',tag,*(str(p) for p in paths))
        current = release_data(tag, draft_only)
        for p in paths:
            matches=[a for a in current['assets'] if a['name']==p.name];assert len(matches)==1
            assert matches[0]['size']==p.stat().st_size and matches[0]['digest']=='sha256:'+hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
        print('Verified public Mac assets:',arch,version,sha)

if __name__=='__main__':main()
