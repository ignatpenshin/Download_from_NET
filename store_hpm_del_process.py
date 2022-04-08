from asyncio.subprocess import DEVNULL
from datetime import datetime, timezone
import pysftp
import sys
import math
import os
from tqdm import tqdm
from pyexif import pyexif
from subprocess import Popen
import shutil


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

#helper storage -> HPM8 
def splitter(s): 
    mew = [x.split('\\')[-2:] for x in s]
    return mew


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


def camera_process(exiftool_path, exiftool_runner, stitch_path, stitch_runner, basic_dir, Hostname, Username, Password, cnopts, \
                    remoteFilePath, remoteFilePath_phone, cameras, phone_list, cam_path):
                    
    created_tracks = []

    with pysftp.Connection(host=Hostname, username=Username, password=Password, cnopts=cnopts) as sftp:
        dir_to_create = ''
        cam_path_way = remoteFilePath + cam_path + "/DCIM"
        sftp.cwd(cam_path_way)
        directory_structure = [x for x in sftp.listdir_attr() if x.filename.startswith('Camera')]
        print('\n', f'------ Download from {cam_path} ------ ', '\n')
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
                if str(cameras[cam_path][0] + file_date[:-7]) != dir_to_create: 
                    #new track dir
                    dir_to_create = str(cameras[cam_path][0] + file_date[:-7])
                    path_log = file_to_folder(cameras[cam_path][0] + file_date)
                    created_tracks.append(path_log)
                    
                    print('\n', f' <<<<< Track {cameras[cam_path][0] + file_date} created >>>>> ', '\n')
                    #load mobile
                    if cameras[cam_path][1] in phone_list:
                        # print('\n'*10, 'YESSSSS', cameras[cam_path.filename][1], phone_list, '\n'*10)
                        phone_path = remoteFilePath_phone + cameras[cam_path][1]
                        # find OutDoorActive gpx
                        gpx_path = phone_path + "/Android/data/com.outdooractive.Outdooractive/files/GPX"
                        sftp.cwd(gpx_path)
                        for gpx in sftp.listdir_attr():
                            if (gpx.filename.endswith(".gpx") or gpx.filename.endswith(".GPX")) and \
                                datetime.fromtimestamp(gpx.st_mtime, tz=timezone.utc).strftime('%Y_%m_%d') == total_date:
                                if not os.path.exists(path_log+"\\_GPS_\\GPXs\\"+gpx.filename):
                                    print('\n', ' --> GPX-file loading: ')
                                    sftp.get(gpx.filename, path_log + \
                                        "\\_GPS_\\GPXs\\" + gpx.filename, callback = lambda x,y: progressbar(x,y)) 
                                    print(gpx.filename)

                        #find emlid data
                        emlid_filepath = phone_path + "/Download/"
                        sftp.cwd(emlid_filepath)
                        for emlid in sftp.listdir_attr():
                            if (emlid.filename.endswith(".zip") or emlid.filename.endswith(".ZIP")) and \
                                emlid.filename.__contains__("RINEX") and \
                                datetime.fromtimestamp(emlid.st_mtime, tz=timezone.utc).strftime('%Y_%m_%d') == total_date:
                                if not os.path.exists(path_log+"\\_GPS_\\ROVER\\"+emlid.filename):
                                    print('\n', ' --> EMLID_RINEX-file loading: ')
                                    sftp.get(emlid.filename, path_log + \
                                        "\\_GPS_\\ROVER\\" + emlid.filename, callback = lambda x,y: progressbar(x,y))      
                                    print(emlid.filename, '\n')  
                    sftp.cwd(cam_path_way + "/" + Camera_n.filename)

                if not os.path.exists(path_log+"\\original\\"+file.filename):
                    sftp.get(file.filename, path_log+"\\original\\"+file.filename, callback = lambda x,y: progressbar(x,y))
                    print(Camera_n.filename, file.filename, file_date)
                os.chdir(basic_dir)
    
    return created_tracks
    


def copy_to_hpm(original_path, processed_path, created_tracks):
    print('\n', '------ STORE -> HPM COPY PROCESS ------ ', '\n')
    hpm_path_orig = [original_path + '\\' + '\\'.join(track) for track in splitter(created_tracks)]
    hpm_path_proc = [processed_path + '\\' + '\\'.join(track) for track in splitter(created_tracks)]
    pairs = [list(tup) for tup in zip(created_tracks, hpm_path_orig)]
    for pair in pairs:
        print(f"{pairs.index(pair)} from {len(pairs)} tracks copied")
        #create dir in original
        if not os.path.exists(pair[1]):
            os.makedirs(pair[1])
            os.chdir(pair[1])
            folder_creator()       
        os.chdir(pair[0])
        for root, dirs, files in os.walk(".", topdown = False):   
            for name in tqdm(files):
                hpm_file = os.path.join(pair[1], root[2:], name)
                store_file = os.path.join(os.path.abspath(root), name)
                if not os.path.exists(hpm_file):
                    shutil.copyfile(store_file, hpm_file)

    #create dir in processed
    for dir in hpm_path_proc:
        if not os.path.exists(dir):
            os.makedirs(dir)
            os.chdir(dir)
            folder_creator()

        # copy _GPS_ data: path_original -> path_processed    
        orig_dir = hpm_path_orig[hpm_path_proc.index(dir)] + "\\_GPS_"
        os.chdir(orig_dir)
        for root, dirs, files in os.walk(".", topdown = False):   
            for name in files:
                orig_gps_file = os.path.join(orig_dir, root[2:], name)
                process_gps_file = os.path.join(dir + "\\_GPS_", root[2:], name)
                if not os.path.exists(process_gps_file):
                    shutil.copyfile(orig_gps_file, process_gps_file)

    return hpm_path_orig, hpm_path_proc


def stitching(original_tracks, process_tracks, stitch_path, stitch_runner, exiftool_path, exiftool_runner):
    #stitching
    for path in original_tracks:
        print("Stitching track {} / {}".format(original_tracks.index(path) + 1, len(original_tracks)))
        os.chdir(path+"\original")
        for photo in tqdm(os.listdir()):
            
            if photo.endswith(".jpg"):
                photo_link = process_tracks[original_tracks.index(path)]+"\\instaOne\\"+photo
            if photo.endswith(".insp"):
                photo_link = process_tracks[original_tracks.index(path)]+"\\instaOne\\"+photo.replace(".insp", ".jpg")
            if not os.path.exists(photo_link):
                cmd_stitch = " -inputs {} -output {} -stitch_type optflow -enable_flowstate open flowstate \
                    -output_size 6080x3040 -disable_cuda 0".format(path+"\\original\\"+photo, photo_link)
                Popen(stitch_path+stitch_runner+cmd_stitch, shell=False, stderr=DEVNULL, stdout=DEVNULL).wait() 
                # add exif
                f = " -F" #to solve problems
                cmd_exif = " -overwrite_original -tagsfromfile {} \"-all:all>exif:all\" {}".format(path+"\\original\\"+photo, photo_link)
                if photo.endswith(".insp"):
                    cmd_exif = " -ExtractEmbedded" + cmd_exif
                Popen(exiftool_path + exiftool_runner + f + cmd_exif, shell=False, stderr=DEVNULL, stdout=DEVNULL).wait() 
    

def main(argv):

    #storage (Curinsta2)
    storage_path = "V:\\Insta-One-X2-mosvelo2022"
    storage_dir = "velo_mos_original"

    #HPM8 storage
    original_path = "D:\\Curinsta2\\original\\2022-mos_velo"
    processed_path = "D:\\Curinsta2\\processed\\2022-mos-velo"

    #Ubuntu PC
    Hostname = "192.168.10.114"
    Username = "pesh"
    Password = "Pass1528"

    #Ubuntu -> phone
    phone_dict = {"vel1": "sftp:host=10.64.12.136,port=2222,user=vel1",
                  "vel2": "sftp:host=10.64.12.175,port=2222,user=vel2",
                  "vel3": "sftp:host=10.64.12.182,port=2222,user=vel3"}

    #Ubuntu -> cameras
    cameras = { 'Cam1-64Gb':['i31_', phone_dict["vel1"]], 
                'Cam2-64Gb':['i32_', phone_dict["vel2"]], 
                'Cam3-64Gb':['i33_', phone_dict["vel3"]]}


    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None


    # Camera scan for new photos 
    with pysftp.Connection(host=Hostname, username=Username, password=Password, cnopts=cnopts) as sftp:

        print("Connection successfully established ... ")
        remoteFilePath = "/media/pesh/" #sftp usb-connected camera folders
        sftp.cwd(remoteFilePath)
        cam_list = [x for x in sftp.listdir_attr() if x.filename in cameras.keys()]

        remoteFilePath_phone = "/run/user/1000/gvfs/" #sftp virtual phone folders
        sftp.cwd(remoteFilePath_phone)
        phone_list = [x.filename for x in sftp.listdir_attr() if x.filename in phone_dict.values()]

        stitch_path = "Z:\Bike_processing_Ignat\MediaSDK_bin\\"
        stitch_runner = "stitcherSDKDemo.exe"

        exiftool_path = "Z:\Bike_processing_Ignat\exiftool\\"
        exiftool_runner = "exiftool.exe"

        if argv == None:
            for cam_path in cam_list:
                os.system("start cmd /c " + 'store_hpm_del_process.py ' + cam_path.filename)
        
        else:
            
            #storage
            os.chdir(storage_path)
            
            if not os.path.exists(storage_dir):
                os.mkdir(storage_dir)
            os.chdir(storage_dir)
            basic_dir = os.getcwd()

            print(argv)
            #From cameras/phones to STORE
            created_tracks = camera_process(exiftool_path, exiftool_runner, stitch_path, stitch_runner, basic_dir, Hostname, Username, Password, cnopts, \
                    remoteFilePath, remoteFilePath_phone, cameras, phone_list, argv)

            #From STORE copy to hpm8 (original)
            original_tracks, process_tracks = copy_to_hpm(original_path, processed_path, created_tracks)
            

            # stitch from hpm_original -> hpm_processed 
            stitching(original_tracks, process_tracks, stitch_path, stitch_runner, exiftool_path, exiftool_runner)

            # processing ????



if __name__ == "__main__":
    
    if len(sys.argv) == 1:
        main(None)
    else:
        main(sys.argv[1])

    
        
