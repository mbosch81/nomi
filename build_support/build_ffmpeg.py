"""Build pinned LGPL-only FFmpeg tools; end users need no installation."""
from pathlib import Path
import hashlib
import json
import os
import platform
import shutil
import shlex
import subprocess
import tarfile
from urllib.request import urlopen

VERSION = '9.0.2'
SHA256 = '8c3850283eb25fa026482078a04051e0be17347b09ef81a0849bec15a96e002e'
FLAGS = [
    '--disable-everything', '--disable-autodetect', '--disable-network',
    '--disable-gpl', '--disable-nonfree', '--disable-version3',
    '--disable-doc', '--disable-debug', '--disable-shared', '--enable-static',
    '--disable-x86asm', '--disable-hwaccels', '--enable-ffmpeg', '--enable-ffprobe',
    '--enable-avcodec', '--enable-avformat', '--enable-avfilter', '--enable-swscale',
    '--enable-protocol=file,pipe', '--enable-demuxer=mov,matroska,avi,mpegts,image2',
    '--enable-decoder=h264,hevc,mpeg4,mjpeg,prores,vp8,vp9,wrapped_avframe',
    '--enable-parser=h264,hevc,mpeg4video,vp8,vp9',
    '--enable-filter=scale,format,select,fps,transpose,trim,setpts,color,testsrc',
    '--enable-encoder=mjpeg', '--enable-muxer=image2,image2pipe,avi', '--enable-indev=lavfi',
]


def build():
    root = Path(__file__).resolve().parent.parent
    work = root / 'work'
    work.mkdir(exist_ok=True)
    archive = work / f'ffmpeg-{VERSION}.tar.xz'
    if not archive.exists() or hashlib.sha256(archive.read_bytes()).hexdigest() != SHA256:
        with urlopen(f'https://ffmpeg.org/releases/ffmpeg-{VERSION}.tar.xz', timeout=60) as response:
            payload = response.read()
        if hashlib.sha256(payload).hexdigest() != SHA256:
            raise ValueError('FFmpeg source checksum mismatch')
        archive.write_bytes(payload)
    source = work / f'ffmpeg-{VERSION}-{platform.machine()}'
    destination = root / 'nomi' / 'bin' / 'ffmpeg'
    destination.mkdir(parents=True, exist_ok=True)
    windows = platform.system() == 'Windows'
    suffix = '.exe' if windows else ''
    flags = FLAGS + (['--target-os=mingw32', '--extra-ldflags=-static'] if windows else [])
    recipe = {'version': VERSION, 'sha256': SHA256, 'flags': flags, 'arch': platform.machine(), 'os': platform.system()}
    stamp = destination / 'build.json'
    if not all((destination / (name + suffix)).is_file() for name in ('ffmpeg', 'ffprobe')) or not stamp.exists() or json.loads(stamp.read_text()) != recipe:
        if source.exists():shutil.rmtree(source)
        source.mkdir()
        with tarfile.open(archive) as handle:
            # Strip one archive root while retaining tar's path/symlink safeguards.
            handle.extractall(source, filter='data')
        directory = source / f'ffmpeg-{VERSION}'
        env = dict(os.environ)
        if platform.system() == 'Darwin':env['MACOSX_DEPLOYMENT_TARGET'] = '13.3'
        log = work / 'ffmpeg-compile.log'
        if windows:
            env['CHERE_INVOKING'] = '1'
        commands = [['./configure', *flags], ['make', '-j', str(min(os.cpu_count() or 2, 8))]]
        with log.open('w', encoding='utf-8') as output:
            for command in commands:
                if windows:
                    # CreateProcess searches System32 before PATH for bare names, where
                    # bash.exe may be the unrelated WSL launcher. Resolve MSYS2 explicitly.
                    bash = env.get('NOMI_BUILD_BASH') or shutil.which('bash')
                    if not bash:raise ValueError('MSYS2 bash is required for the Windows build')
                    command = [bash, '-lc', shlex.join(command)]
                result = subprocess.run(command, cwd=directory, env=env, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
                output.write(result.stdout)
                output.flush()
                if result.returncode:
                    print('\n'.join(result.stdout.splitlines()[-80:]), flush=True)
                    # Configure's compiler probe details help diagnose native CI builds.
                    config_log = directory / 'ffbuild/config.log'
                    if config_log.is_file():
                        print('\n'.join(config_log.read_text(errors='replace').splitlines()[-60:]), flush=True)
                    result.check_returncode()
        for name in ('ffmpeg', 'ffprobe'):
            shutil.copy2(directory / (name + suffix), destination / (name + suffix))
        shutil.copy2(directory / 'COPYING.LGPLv2.1', destination / 'COPYING.LGPLv2.1')
        stamp.write_text(json.dumps(recipe, indent=2)+'\n')
    license_text = subprocess.check_output([str(destination / ('ffmpeg' + suffix)), '-L'], stderr=subprocess.STDOUT, text=True)
    if 'GNU Lesser General Public' not in license_text or 'version 2.1' not in license_text or '--enable-gpl' in license_text or '--enable-nonfree' in license_text:
        raise ValueError('Unexpected FFmpeg licensing configuration')
    shutil.copy2(archive, destination / archive.name)
    return destination


if __name__ == '__main__':print(build())
