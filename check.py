#coding=utf-8

import os
import sys
import zipfile
import shutil
import glob
import argparse
sys.path.append(os.path.dirname(__file__))
import StatusCodeObjProcess as SC
import json

#to use module in parent folder
import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir) 
import model_process as mp


TMP_PATH = None

def resetLocalEnvironment(use_local_environment):
    global TMP_PATH
    # #local path
    if use_local_environment == "local":
        TMP_PATH = "./tmp"
    # server path
    else:
        TMP_PATH = "/tmp/obj_process_tmp/"

def is_zip_file(file):
    return zipfile.is_zipfile(file)

def get_unused_path(path):
    if path == "." or path == "..":
        return path
    ret = path
    append = 1
    while os.path.exists(ret):
        ret = (path + "-{}").format(append)
        append = append + 1
    return ret

def unzip_resource(zFile, dst="./tmp"):
    print("unzip_resource")
    if not zipfile.is_zipfile(zFile):
        return
    f = zipfile.ZipFile(zFile)
    path = get_unused_path(dst)
    os.makedirs(path)
    f.extractall(path)
    f.close()
    return path

def write_dir_to_zip(rootDir, outZip, noRootDir=True):
    absPath = os.path.abspath(rootDir)
    absDir, _ = os.path.split(absPath)
    absPathLen = len(absPath)
    absDirLen = len(absDir)
    with zipfile.ZipFile(outZip, 'w') as f:
        for dirpath, dirnames, filenames in os.walk(absPath):
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                if noRootDir:
                    if path.startswith(absPath):
                        zipPath = path[absPathLen+1:]
                else:
                    if path.startswith(absDir):
                        zipPath = path[absDirLen+1:]
                f.write(path, zipPath, zipfile.ZIP_DEFLATED)

def zip_resource(dst, files):
    if len(files) == 0:
        return
    with zipfile.ZipFile(dst, 'w') as zf: 
        for sn, fn in files.items():
            if os.path.exists(fn):
                zf.write(fn, sn, zipfile.ZIP_DEFLATED)

def color_print(content, color="white"):
    cv = 37
    cr = color.lower()
    if cr.startswith("r"):
        cv = 31
    elif cr.startswith("g"):
        cv = 32
    elif cr.startswith("b"):
        cv = 34
    elif cr.startswith("y"):
        cv = 33
    elif cr.startswith("bl"):
        cv = 30
    else:
        fmt = "\033[1;"+str(cv)+";40m"+content+"\033[0m"
        print(fmt)
        return
    fmt = "\033[1;"+str(cv)+"m"+content+"\033[0m"
    print(fmt)

def get_mtls(objFile):
    mtls = []
    with open(objFile, "r", errors='ignore') as f:
        lines = f.readlines()
        for line in lines:
            if line.find("usemtl") == -1:
                continue
            subs = line.split(" ")
            if len(subs) < 2 or len(subs[1]) == 0:
                continue
            mtls.append(subs[1].strip("\n"))
    return mtls

def check_f(line):
    fs = line[2:].strip("\n").split(" ")
    cnt = 0
    for f in fs:
        if len(f.strip()) == 0:
            continue
        ids = f.split("/")
        for i in ids:
            if float(i.strip()) < 0:
                return False
        cnt += 1
    if cnt != 3:
        return False
    return True

def all_v_in_1(line):
    pstr = line[2:].strip("\n").split(" ")
    if len(pstr) == 0:
        return False
    for point in pstr:
        p = point.strip()
        if len(p) > 0 and abs(float(p)) > 1.0:
            return False
    return True

def check_obj(objFile):
    fInTriangle = True
    allVertIn1 = True
    with open(objFile, "r", errors='ignore') as f:
        lines = f.readlines()
        for line in lines:
            if line.find("f ") == 0:
                if not check_f(line):
                    fInTriangle = False
                    break
            if line.find("v ") == 0:
                if not all_v_in_1(line):
                    allVertIn1 = False
    ok = fInTriangle and not allVertIn1
    if not ok:
        print("obj file:{} f:{} v:{}".format(objFile, ok, allVertIn1))

    return ok

def get_objs(resPath):
    objFind = os.path.join(resPath, "*.obj")
    objs = glob.glob(objFind)
    ret = []
    for o in objs:
        if o.rfind("virtual_foot.obj") != -1:
            continue
        ret.append(o)
    return ret

def copy_if_not_exit(dst, src):
    if not os.path.exists(src):
        return
    if not os.path.isdir(dst):
        return
    _, file = os.path.split(src)
    dstFile = os.path.join(dst, file)
    if os.path.exists(dstFile):
        return
    shutil.copy(dstFile, src)

def gen_texture_names(mtl, model, mirrorPath=None):
    base = "{}_{}_Base.png".format(model, mtl)
    rma = "{}_{}_RMA.png".format(model, mtl)
    normal = "{}_{}_Normal.png".format(model, mtl)
    if mirrorPath is not None:
        base = os.path.join(mirrorPath, base)
        rma = os.path.join(mirrorPath, rma)
        normal = os.path.join(mirrorPath, normal)
    return base, rma, normal

def check_mtl(path, mtl, name="model", checkRight=False):
    base, rma, normal = gen_texture_names(mtl, name)
    files = [base, rma]
    if os.path.isdir(os.path.join(path, "mirrorx")) and checkRight:
        base_r, rma_r, normal_r = gen_texture_names(mtl, name, "mirrorx")
        files.append(base_r)
        files.append(rma_r)
        if os.path.isfile(normal) != os.path.isfile(normal_r):
            return False
    for file in files:
        filePath = os.path.join(path, file)
        if not os.path.isfile(filePath):
            return False
    return True

def check_texture_files(path, mtl, name):
    base, rma, normal = gen_texture_names(mtl, name)
    base_r, rma_r, normal_r = gen_texture_names(mtl, name, "mirrorx")
    exists = []
    needs = [base, rma]
    all = [base, rma, base_r, rma_r, normal, normal_r, "top.png"]
    for file in all:
        full_path = os.path.join(path, file)
        if os.path.isfile(full_path):
            exists.append(file)
    ok = True
    for need in needs:
        if need not in exists:
            ok = False
            break
    return exists, ok;

def get_model_name(objFile):
    path, obj = os.path.split(objFile)
    model, _ = os.path.splitext(obj)
    return model, path

def check_resource(objFile, statusCode):
    if not os.path.isfile(objFile):
        print("{} not found ".format(objFile))
        SC.setStatusCode(SC.OBJ_CHECK_NO_OBJ_FILE_FOUND, statusCode)
        return statusCode
    if not check_obj(objFile):
        print("obj file: {} not ok".format(objFile))
        SC.setStatusCode(SC.OBJ_CHECK_OBJ_FILE_NOT_OK, statusCode)
        return statusCode
    model, path = get_model_name(objFile)
    mtls = get_mtls(objFile)
    if len(mtls) == 0:
        print("There is no mtl in {}".format(objFile))
        SC.setStatusCode(SC.OBJ_CHECK_NO_MTL_FOUND, statusCode)
        return statusCode
    for mtl in mtls:
        if not check_mtl(path, mtl, model):
            print("mtl:{} resorce in {} not match!".format(mtl, objFile))

            SC.setStatusCode(SC.OBJ_CHECK_MTL_RESOURCE_NOT_MATCH, statusCode)
            return statusCode

    return statusCode

def list_dir(folder):
    ret = []
    fs = glob.glob(os.path.join(folder,"*"))
    for f in fs:
        _, n = os.path.split(f)
        ret.append(n)
    return ret

def check_resource_folder(folder, statusCode):

    objs = get_objs(folder)
    if len(objs) == 0:
        color_print("没有发现模型obj文件！", "red")
        SC.setStatusCode(SC.OBJ_CHECK_NO_OBJ_FILE_FOUND, statusCode)
        return statusCode
    if len(objs) > 1:
        color_print("一个资源中发现多个obj文件，当前不支持多个obj文件，除了model.obj之外的其它obj不会被使用", "y")
        SC.setStatusCode(SC.OBJ_CHECK_MORE_THAN_ONE_OBJ_FILE_FOUND, statusCode)
        return statusCode
    model_obj = None
    for obj in objs:
        p, f = os.path.split(obj)
        if f == "model.obj":
            model_obj = obj
            break
    if model_obj is None:
        color_print("资源根目录没有发现名为model.obj的文件!", "r")
        files = list_dir(folder)
        print("根目录下有:{}".format(files))
        SC.setStatusCode(SC.OBJ_CHECK_NO_MODEL_OBJ_FOUND, statusCode)
        return statusCode
    return check_resource(model_obj, statusCode)

def check_zip(zip_file, tmpPath):
    global TMP_PATH
    statusCode = {
        "success": True,
        "msgInfo": "obj check passed.",
        "msgCode": SC.OBJ_CHECK_SUCCESS,
        "zip_unfold_path": zip_file
    }
    if not os.path.exists(zip_file):
        SC.setStatusCode(SC.OBJ_CHECK_ERROR_INPUT_FILE_NOT_EXIST, statusCode)
        print("指定的路径不存在!\n")
        return statusCode
    if is_zip_file(zip_file):
        print("解压缩文件...")
        try:
            zip_file = unzip_resource(zip_file, tmpPath)
            statusCode["zip_unfold_path"] = zip_file
            print("完成")
        except:
            SC.setStatusCode(SC.OBJ_CHECK_ERROR_UNZIP_ERROR, statusCode)
            print("解压出错!\n".format(e))
            return statusCode
    if not os.path.isdir(zip_file):
        print("指定的路径:{}不是文件夹也不是zip包".format(zip_file))
        SC.setStatusCode(SC.OBJ_CHECK_ERROR_INPUT_NOT_ZIP_NOT_FOLDER, statusCode)
        return statusCode
    statusCode = check_resource_folder(zip_file, statusCode)
    if statusCode["success"]:
        color_print("检查通过\n", "g")
        return statusCode
    else:
        if os.path.isdir(zip_file):
            shutil.rmtree(zip_file)
        color_print("资源存在错误\n", "g")

        # SC.setStatusCode(SC.OBJ_CHECK_RESOURCE_HAS_ERROR, statusCode)
        return statusCode    

if __name__ == "__main__":

    parser = mp.ArgumentParserForBlender(description="AR Glass Auto Placement")
    parser.add_argument('--input', '-i', help="zip path to be import", required=True)
    # parser.add_argument('--output', '-o', help="output path")
    parser.add_argument('--info', '-f', help="result info file path")
    parser.add_argument('--local', '-l', help="whether use local environment")
    args = parser.parse_args()

    input = args.input
    # output = args.output
    info_path = args.info
    use_local_environment = args.local
    print ("obj packModels, use local:"+use_local_environment)
    resetLocalEnvironment(use_local_environment)
    
    # if len(sys.argv) <= 1 or len(sys.argv[1].strip()) == 0:
    #     print("请在参数中指定要检查的资源路径，比如:python check.py c:\\shoes\\0234325.zip")
    #     print("-如果指定zip包，会被解压到当前路径下的tmp文件夹再处理\n-如果指定文件夹，则直接检查其内容\n")
    #     exit()

    res_name = os.path.basename(input)
    resource = os.path.abspath(input)

    statusCode = check_zip(resource, TMP_PATH)

    with open(info_path, 'w') as fp:
        json.dump(statusCode, fp)

