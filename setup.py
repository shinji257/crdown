import os
from setuptools import setup

def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read().replace('#','')

setup(
    name = "crdown",
    version = "0.6.4.1",
    author = "Thiago Kenji Okada (edit Robert Pendell)",
    author_email = "thiago.mast3r@gmail.com (edit shinji@elite-systems.org)",
    description = ("Crunchyroll video downloader."),
    license = "Creative Commons Attribution-ShareAlike 3.0 Unported",
    keywords = "video crunchyroll downloader",
    url = 'https://github.com/m45t3r/crdown',
    packages=["crunchy"],
    package_dir={"":"src"},
    scripts=['src/crdown'],
    install_requires=("appdirs", "beautifulsoup4", "pycrypto", "lxml"),
    long_description=read('README.rst'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Topic :: Utilities",
        "Environment :: Console",
        "Operating System :: POSIX",
        "Operating System :: Microsoft :: Windows",
        "Programming Language :: Python :: 3.2",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Multimedia :: Video",
        "Topic :: Utilities",
    ],
)
