from collections import namedtuple
from datetime import datetime, timezone
import pysftp
import sys
import math
import time
import os


if not os.path.exists("TRACKS"):
    os.mkdir("TRACKS")
os.chdir("TRACKS")
basic_dir = os.getcwd()


def folder_creator():
    GPS = "_GPS_"
    if os.path.exists(GPS) == False:
        os.mkdir(GPS)
    if os.path.exists("original") == False:
        os.mkdir("original")
    if os.path.exists("instaOne") == False:
        os.mkdir("instaOne")

    os.chdir(GPS)
    if os.path.exists("BASE") == False:
        os.mkdir("BASE")
    if os.path.exists("GPXs") == False:
        os.mkdir("GPXs")
    if os.path.exists("ROVER") == False:
        os.mkdir("ROVER")
    if os.path.exists("_extend") == False:
        os.mkdir("_extend")


def file_to_folder(file_d):
    basic = os.getcwd()
    if not os.path.exists(str(file_d)):
        os.mkdir(file_d)
    os.chdir(file_d)
    folder_creator()
    path_log = os.path.dirname(os.getcwd())
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

cameras = { 'Cam1-64Gb':'i31_', 
            'Cam2-64Gb':'i32_', 
            'Cam3-64Gb':'i33_'}

Hostname = "192.168.10.166"
Username = "pesh"
Password = "Pass1528"

cnopts = pysftp.CnOpts()
cnopts.hostkeys = None


# Camera scan for new photos 
with pysftp.Connection(host=Hostname, username=Username, password=Password, cnopts=cnopts) as sftp:

    print("Connection successfully established ... ")
    remoteFilePath = "/media/pesh/"
    sftp.cwd(remoteFilePath)
    cam_list = [x for x in sftp.listdir_attr() if x.filename in cameras.keys()]

    for cam_path in cam_list:

        dir_to_create = ''

        cam_path_way = remoteFilePath + cam_path.filename + "/DCIM"
        sftp.cwd(cam_path_way)
        directory_structure = [x for x in sftp.listdir_attr() if x.filename.startswith('Camera')]

        for Camera_n in directory_structure:
            sftp.cwd(cam_path_way + "/" + Camera_n.filename)
            for file in [x for x in sorted(sftp.listdir_attr(),  
                                key = lambda f: f.st_mtime) if x.filename.startswith('IMG') 
                                                and (x.filename.endswith('.insp') or x.filename.endswith('.jpg'))]:

                file_date = datetime.fromtimestamp(file.st_mtime, tz=timezone.utc).strftime('%Y%m%d_%H%M%S')
                total_date = datetime.fromtimestamp(file.st_mtime, tz=timezone.utc).strftime('%Y_%m_%d')

                if not os.path.exists(total_date):
                    os.mkdir(total_date)
                os.chdir(total_date)

                if str(cameras[cam_path.filename] + file_date[:-7]) != dir_to_create: 
                    dir_to_create = str(cameras[cam_path.filename] + file_date[:-7])
                    path_log = file_to_folder(cameras[cam_path.filename] + file_date)               
                     

                if not os.path.exists(path_log+"\\original\\"+file.filename):
                    sftp.get(file.filename, path_log+"\\original\\"+file.filename, callback = lambda x,y: progressbar(x,y))
                
                print(Camera_n.filename, file.filename, file_date)

                os.chdir(basic_dir)
    sftp.close()
        
