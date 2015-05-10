import http.cookiejar
import os
import re
import sys
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
import subprocess
from configparser import SafeConfigParser
from urllib.parse import urlparse
from tempfile import TemporaryDirectory

import lxml
from bs4 import BeautifulSoup

from crunchy.decoder import CrunchyDecoder
from crunchy.common import move_ask_overwrite


class CrunchyDownloader(object):

    def __init__(self, config_path):
        self.config_path = config_path
        self.config()

    def config(self):
        # Windows doesn't support binaries without .exe extension, sigh...
        rtmpdump_bin = 'rtmpdump'
        if sys.platform.startswith('win32'):
            rtmpdump_bin = 'rtmpdump.exe'

        config = SafeConfigParser(
            defaults={'video_quality': 'highest',
                      'language': 'English',
                      'result_path': '.',
                      'retry': '3',
                      'rtmpdump_path': rtmpdump_bin})
        config.read(os.path.join(self.config_path, 'settings.ini'))

        quality = config.get('DEFAULT', 'video_quality')
        if quality == 'android':  # Doesn't work?
            self.video_format = '107'
            self.resolution = '71'
        elif quality == '360p':
            self.video_format = '106'
            self.resolution = '60'
        elif quality == '480p':
            self.video_format = '106'
            self.resolution = '61'
        elif quality == '720p':
            self.video_format = '106'
            self.resolution = '62'
        elif quality == '1080p':
            self.video_format = '108'
            self.resolution = '80'
        elif quality == 'highest':
            self.video_format = '0'
            self.resolution = '0'
        else:
            sys.exit("Invalid 'video_quality' option in 'settings.ini'!")

        lang = config.get('DEFAULT', 'language')
        if lang == 'Espanol_Espana':
            self.lang = 'Espanol (Espana)'
        elif lang == 'Francais':
            self.lang = 'Francais (France)'
        elif lang == 'Portugues':
            self.lang = 'Portugues (Brasil)'
        elif lang == 'English':
            self.lang = 'English|English (US)'
        else:
            sys.exit("Invalid 'language' option in 'settings.ini'!")

        self.result_path = os.path.expanduser(config.get('DEFAULT', 'result_path'))
        if not os.path.isdir(self.result_path):
            sys.exit("Path {} don't exist or isn't a directory!".format(self.result_path))

        try:    
            self.retry = int(config.get('DEFAULT', 'retry'))
        except ValueError:
            sys.exit("Invalid 'retry' option in 'settings.ini!'")

        self.rtmpdump_path = os.path.expanduser(config.get('DEFAULT', 'rtmpdump_path'))
        try:
            # rtmpdump doesn't have a --version, sigh... At least -h return 0.
            subprocess.check_output([self.rtmpdump_path, '-h'], stderr=subprocess.STDOUT)
        except OSError:
            sys.exit("Could not start 'rtmpdump' from path '{}'. Check if 'rtmpdump' is installed and is in "
                     "your PATH or check 'rtmpdump_path' option in 'settings.ini'!".format(self.rtmpdump_path))
        
        try:
            cookies_file = 'cookies.txt'
            self.cookies_path = os.path.join(self.config_path, cookies_file)
            http.cookiejar.MozillaCookieJar(self.cookies_path).load()
        except http.cookiejar.LoadError:
            sys.exit("Invalid '{0}' file. Run '{1} -l' to remake '{0}' file.".format(cookies_file, sys.argv[0]))
        except IOError:
            sys.exit("Inexistent '{0}' file. Did you run '{1} -l' first?".format(cookies_file, sys.argv[0]))

    def _get_player_revision(self, url):
        html = self._get_html(url)
        try:
            player_revision = re.findall(r'flash\\/(.+)\\/StandardVideoPlayer.swf', html).pop()
        except IndexError:
            url = url+'?skip_wall=1'  # Perv
            html = self._get_html(url)
            try:
                player_revision = re.findall(r'flash\\/(.+)\\/StandardVideoPlayer.swf', html).pop()
            except IndexError:
                # Update every so often, only used when the original page is region-locked
                # In these cases you can use a proxy like Tor
                player_revision = '20140102185427.932a69b4165d0ca944236b7ca43ae8e5'
        return player_revision

    def _get_html(self, url):
        urlparse(url)
        try:
            if sys.argv[2] == 'proxy':
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": "127.0.0.1:8118"}))
            else:
                opener = urllib.request.build_opener()
        except IndexError:
            opener = urllib.request.build_opener()
        opener.addheaders = [('Referer', 'http://crunchyroll.com/'), ('Host', 'www.crunchyroll.com'),
                             ('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:26.0) Gecko/20100101 Firefox/26.0)')]
        res = opener.open(url).read()
        return res.decode(encoding='UTF-8')

    def _get_xml(self, req, media_id):
        url = 'http://www.crunchyroll.com/xml/'
        if req == 'RpcApiSubtitle_GetXml':
            data = {'req': 'RpcApiSubtitle_GetXml', 'subtitle_script_id': media_id}
        elif req == 'RpcApiVideoPlayer_GetStandardConfig':
            data = {'req': 'RpcApiVideoPlayer_GetStandardConfig', 'media_id': media_id,
                    'video_format': self.video_format, 'video_quality': self.resolution, 'auto_play': '1',
                    'show_pop_out_controls': '1', 'current_page': 'http://www.crunchyroll.com/'}
        else:
            data = {'req': req, 'media_id': media_id, 'video_format': self.video_format,
                    'video_encode_quality': self.resolution}
        cookie_jar = http.cookiejar.MozillaCookieJar(self.cookies_path)
        cookie_jar.load()
        cookie = urllib.request.HTTPCookieProcessor(cookie_jar)
        try:
            if sys.argv[2] == 'proxy':
                opener = urllib.request.build_opener(urllib.request.ProxyHandler({"http": "127.0.0.1:8118"}), cookie)
            else:
                opener = urllib.request.build_opener(cookie)
        except IndexError:
            opener = urllib.request.build_opener(cookie)
        opener.addheaders = [('Referer', 'http://static.ak.crunchyroll.com/flash/' +
                              self.player_revision+'/StandardVideoPlayer.swf'),
                             ('Host', 'www.crunchyroll.com'), ('Content-type', 'application/x-www-form-urlencoded'),
                             ('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; rv:26.0) Gecko/20100101 Firefox/26.0)')]
        req = urllib.request.Request(url, urllib.parse.urlencode(data).encode(encoding='UTF-8'))
        res = opener.open(req).read().decode(encoding='UTF-8')
        return res

    def _get_video_url(self, url):  # Experimental, although it does help if you only know the program page.
        res = self._get_html(url)
        slist = re.findall('<a href="#" class="season-dropdown content-menu block text-link strong(?: open| ) '
                           'small-margin-bottom" title="(.+?)"', res)
        if slist != []:  # Multiple seasons
            if len(re.findall('<a href=".+episode-(01|1)-(.+?)"', res)) > 1:  # dirty hack, I know
                print(list(reversed(slist)))
                seasonnum = int(input('Season number: '))
                # seasonnum = sys.argv[3]
                epnum = input('Episode number: ')
                # epnum = sys.argv[2]
                seasonnum = slist[seasonnum]
                if url.endswith('/'):
                    return url+re.findall('<a href=".+episode-(0'+epnum+'|'+epnum+')-(.+?)"',
                                          res)[slist.index(seasonnum)][1]
                else:
                    return url+'/'+re.findall('<a href=".+episode-(0'+epnum+'|'+epnum+')-(.+?)"',
                                              res)[slist.index(seasonnum)][1]
            else:
                print(list(reversed(re.findall('<a href=".+episode-(.+?)-', res))))
                epnum = input('Episode number: ')
                # epnum = sys.argv[2]
                if url.endswith('/'):
                    url = url+re.findall('<a href=".+episode-(0'+epnum+'|'+epnum+')-(.+?)"', res).pop()[1]
                else:
                    url = url+'/'+re.findall('<a href=".+episode-(0'+epnum+'|'+epnum+')-(.+?)"', res).pop()[1]
                print(url)
                return url
        else:
            print(re.findall('<a href=".+episode-(.+?)-', res))
            epnum = input('Episode number: ')
            # epnum = sys.argv[2]
            if url.endswith('/'):
                url = url+re.findall('<a href=".+episode-(0'+epnum+'|'+epnum+')-(.+?)"', res).pop()[1]
            else:
                url = url+'/'+re.findall('<a href=".+episode-(0'+epnum+'|'+epnum+')-(.+?)"', res).pop()[1]
            print(url)
            return url

    def get_video(self, page_url, subtitles_only=False, video_only=False):
        # http://www.crunchyroll.com/miss-monochrome-the-animation/episode-2-645085
        # page_url = 'http://www.crunchyroll.com/media-645085'
        if page_url.startswith('www'):
            page_url = 'http://'+page_url
        try:
            int(page_url)
            page_url = 'http://www.crunchyroll.com/media-'+page_url
        except ValueError:
            try:
                int(page_url[-6:])
            except ValueError:
                page_url = self._get_video_url(page_url)
        self.player_revision = self._get_player_revision(page_url)
        media_id = page_url[-6:]
        xmlconfig = BeautifulSoup(self._get_xml('RpcApiVideoPlayer_GetStandardConfig', media_id), 'xml')
        # xmlmeta = BeautifulSoup(self._get_xml('RpcApiVideoPlayer_GetMediaMetadata', media_id), 'xml')
        if '<code>4</code>' in xmlconfig:  # This is in VideoEncode_GetStreamInfo, but better to nip it in the bud early
            print('Video not available in your region.')
            sys.exit()
        vid_id = xmlconfig.find('media_id').string

        title = re.findall('<title>(.+?)</title>', self._get_html(page_url)).pop().replace('Crunchyroll - Watch ', '')
        title = title.replace('/', ' - ').replace(':', '-').replace('?', '.').replace('"', '\'').strip()

        # Normally 'RpcApiVideoEncode_GetStreamInfo' but some episodes f*ck up and show 1080p no matter the settings
        # xmlstream = BeautifulSoup(self._get_xml('RpcApiVideoPlayer_GetStandardConfig', media_id), 'xml')
        try:
            host = xmlconfig.find('host').string
        except AttributeError:
            print('Downloading 2 minute preview.')
            # xmlmeta = BeautifulSoup(self._get_xml('RpcApiVideoPlayer_GetMediaMetadata', media_id), 'xml')
            media_id = xmlconfig.find('media_id').string
            xmlconfig = BeautifulSoup(self._get_xml('RpcApiVideoEncode_GetStreamInfo', media_id), 'xml')
            try:
                host = xmlconfig.find('host').string
            except AttributeError:
                sys.exit(xmlconfig.find('msg').string)

        host_grr = re.search('fplive\.net', host)  # There was a time when fplive videos couldn't be downloaded, so...
        if host_grr:
            url1 = re.findall('.+/c[0-9]+', host).pop()
            url2 = re.findall('c[0-9]+\?.+', host).pop()
        else:
            url1 = re.findall('.+/ondemand/', host).pop()
            url2 = re.findall('ondemand/.+', host).pop()
        filename = xmlconfig.find('file').string

        xmllist = self._get_xml('RpcApiSubtitle_GetListing', media_id)
        xmllist = xmllist.replace('><', '>\n<')

        if '<media_id>None</media_id>' in xmllist:
            print('The video has hardcoded subtitles.')
            hardcoded = True
        else:
            try:
                sub_id = re.findall("id=([0-9]+)' title='.+" +
                                    self.lang.replace('(', '\(').replace(')', '\)')+"'", xmllist).pop()
                hardcoded = False
            except IndexError:
                try:
                    sub_id = re.findall("id\=([0-9]+)' title='.+English", xmllist).pop()  # Default back to English
                    print('Language not found, reverting to English')
                    hardcoded = False
                except IndexError:
                    print('The video\'s subtitles cannot be found, or are region-locked.')
                    hardcoded = True
                    
        if video_only:
            print('The video subtitles are not being downloaded at the request of the user.')
            hardcoded = True

        with TemporaryDirectory() as tmpdir:
            if not hardcoded:
                xmlsub = self._get_xml('RpcApiSubtitle_GetXml', sub_id)
                formattedSubs = CrunchyDecoder().return_subs(xmlsub)
                try:
                    with open(os.path.join(tmpdir, title+'.ass'), 'wb') as subfile:
                        subfile.write(formattedSubs.encode('utf-8-sig'))
                except IOError:
                    title = title.split(' - ', 1)[0]  # Episode name too long, splitting after episode number
                    with open(os.path.join(tmpdir, title+'.ass'), 'wb') as subfile:
                        subfile.write(formattedSubs.encode('utf-8-sig'))
                move_ask_overwrite(subfile.name, os.path.join(self.result_path, title+'.ass'))
            print("Subtitles for '{}' have been downloaded".format(title))
            # Exit this function if user asked only for subtitles.
            if subtitles_only:
                return None

            print('Downloading video...')
            video_path = os.path.join(tmpdir, title+'.flv')
            cmd = [self.rtmpdump_path, '-r', url1, '-a', url2, '-f', 'WIN 11,8,800,50', '-m', '15', '-W',
                   'http://static.ak.crunchyroll.com/flash/'+self.player_revision+'/ChromelessPlayerApp.swf',
                   '-p', page_url, '-y', filename, '-o', video_path]

            for i in range(self.retry+1):
                try:
                    subprocess.check_call(cmd)
                    move_ask_overwrite(video_path, os.path.join(self.result_path, title+'.flv'))
                    print("Video '{}' has been downloaded".format(title))
                    break
                except subprocess.CalledProcessError:
                    if i < self.retry:
                        print('Video failed to download, trying again. ({}/{})'.format(i+1, self.retry))
                    else:
                        sys.exit('Video failed to download too many times. Giving up...')
