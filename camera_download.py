from collections import namedtuple
from datetime import datetime, timezone
import pysftp
import sys
import math
import time
import os


def create_dir(file_d):
    basic = os.getcwd()
    if not os.path.exists(str(file_d)):
        os.mkdir(file_d)
    os.chdir(file_d)
    path_log = os.path.dirname(os.getcwd()) + '\\' + file_d + '\\'
    os.chdir(basic)
    return path_log

def progressbar(x, y):
    ''' progressbar for the pysftp
    '''
    bar_len = 60
    filled_len = math.ceil(bar_len * x / float(y))
    percents = math.ceil(100.0 * x / float(y))
    bar = '=' * filled_len + '-' * (bar_len - filled_len)
    filesize = f'{math.ceil(y/1024):,} KB' if y > 1024 else f'{y} byte'
    sys.stdout.write(f'[{bar}] {percents}% {filesize}\r')
    sys.stdout.flush()


Hostname = "192.168.31.136"
Username = "pi"
Password = "12345678"

cnopts = pysftp.CnOpts()
cnopts.hostkeys = None


#Camera scan for new photos 
with pysftp.Connection(host=Hostname, username=Username, password=Password, cnopts=cnopts) as sftp:
    print("Connection successfully established ... ")
    remoteFilePath = '/media/pi/disk/DCIM'
    sftp.cwd(remoteFilePath)
    directory_structure = [x for x in sftp.listdir_attr() if x.filename.startswith('Camera')] 

    for cam_path in directory_structure:
        with sftp.cd(cam_path.filename):

            for file in [x for x in sorted(sftp.listdir_attr(),  
                                key = lambda f: f.st_mtime) if x.filename.startswith('IMG') 
                                                and (x.filename.endswith('.insp') or x.filename.endswith('.jpg'))]:

                file_date = datetime.fromtimestamp(file.st_mtime, tz=timezone.utc).strftime('%Y_%m_%d')
                path_log = create_dir(file_date)              
                if not os.path.exists(path_log+file.filename):
                    sftp.get(file.filename, path_log+file.filename, callback = lambda x,y: progressbar(x,y))
                print(cam_path.filename, file.filename, file_date)
            sftp.cwd(remoteFilePath)
    
    sftp.close()
        
