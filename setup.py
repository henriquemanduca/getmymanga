from setuptools import setup

setup(
    name='getmymanga', #the name of the deb package
    version='0.9', #version
    author='Manduca',#your name
    author_email='hms2@pm.me', # your email
    description='A way to download mangas from internet',#description
    scripts=['main.py'], # the main script
    #data_files=[('/etc/systemd/system', ['eshare.service']), ('/etc/eshare', ['eshare.conf'])], #where the files will be stored
    install_requires=['asyncio'], #dependencies
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Operating System :: POSIX :: Linux",
    ], #other informations for the package
)