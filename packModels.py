#-*- coding: UTF-8 -*-
# chexueji
# 遍历所有鞋模文件夹，都打成zip，这个文件针对新模型。
# 2020.10-2020.12

import os
import sys
import shutil
import zipfile
import math
sys.path.append(os.path.dirname(__file__))
from check import *
import StatusCodeObjProcess as SC

import json


#to use module in parent folder
import os,sys,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir) 
import model_process as mp

majorVersion = "2"
minorVersion = "0"

FLOAT_MAX = sys.float_info.max #最大值
FLOAT_MIN = sys.float_info.min #最小值

TMP_PATH = None
MODEL_TXT_PATH = "obj_process/model.txt"
VIRTUL_FOOT_BASE_JPG_PATH = "obj_process/virtualFoot_Base.jpg"
SERVER_TOOLS_PATH = "/home/admin/tm-venus/tools/"

def resetLocalEnvironment(use_local_environment):
    global TMP_PATH
    global MODEL_TXT_PATH
    global VIRTUL_FOOT_BASE_JPG_PATH
    global SERVER_TOOLS_PATH
    # #local path
    if use_local_environment == "local":
        TMP_PATH = "./tmp"
    # server path
    else:
        TMP_PATH = "/tmp/obj_process_tmp/"
        MODEL_TXT_PATH =  SERVER_TOOLS_PATH + "obj_process/model.txt"
        VIRTUL_FOOT_BASE_JPG_PATH = SERVER_TOOLS_PATH + "obj_process/virtualFoot_Base.jpg"


def load_mesh(fpath):
    before_v = []
    vts = []
    faces = []
    after_v = []
    lines = open(fpath, 'r', encoding='ISO-8859-1').read().split('\n')
    idx = 0
    for idx in range(len(lines)):
        line = lines[idx]
        if line[:2] == 'v ':
            break
        before_v.append(line)

    count = idx
    for idx in range(count, len(lines)):
        line = lines[idx]
        if line[:2] != 'v ':
            break
        vts.append(line)

    count = idx
    for idx in range(count, len(lines)):
        after_v.append(lines[idx])

    for line in lines:
        if line[:1] == 'f':
            faces.append(line)

    verts = [line[1:].split() for line in vts]
    verts = [[float(v[0]), float(v[1]), float(v[2])] for v in verts]

    return '\n'.join(before_v), verts, '\n'.join(after_v)


def save_mesh(before_v, verts, after_v, save_to):
    vts = '\n'.join(['v {} {} {}'.format(v[0], v[1], v[2]) for v in verts])
    open(save_to, 'w', encoding="utf-8").write(before_v + '\n' + vts + '\n' + after_v)
    return


def scale_mesh(src_fold, fname, save_to):
    scale = 1000.0
    before_v, v, after_v = load_mesh(os.path.join(src_fold, fname))
    x_max, y_max, z_max = FLOAT_MIN, FLOAT_MIN, FLOAT_MIN
    x_min, y_min, z_min = FLOAT_MAX, FLOAT_MAX, FLOAT_MAX
    for vi in v:
        x_min = min(x_min, vi[0])
        y_min = min(y_min, vi[1])
        z_min = min(z_min, vi[2])
        x_max = max(x_max, vi[0])
        y_max = max(y_max, vi[1])
        z_max = max(z_max, vi[2])

        vi[0] = format(vi[0] * scale, '.6f')
        vi[1] = format(vi[1] * scale, '.6f')
        vi[2] = format(vi[2] * scale, '.6f')

    box_x = x_max - x_min
    box_y = y_max - y_min
    box_z = z_max - z_min
    box_diagonal = math.sqrt(box_x * box_x + box_y * box_y + box_z * box_z)
    if box_diagonal > 5.2:
        color_print(fname + "模型已缩放过!!!","red")
    else:
        save_mesh(before_v, v, after_v, os.path.join(src_fold, save_to))
    return

def process(src_fold, model, vfoot):
    model_path = os.path.join(src_fold, model)
    vfoot_path = os.path.join(src_fold, vfoot)
    vfoot_pic = os.path.join(src_fold, "virtualFoot_Base.jpg")

    scale_mesh(src_fold, model, 'model.obj')
    scale_mesh(src_fold, vfoot, 'virtual_foot.obj')
    return

def zip_resource(dst, files):
    if len(files) == 0:
        return
    with zipfile.ZipFile(dst, 'w') as zf: 
        for sn, fn in files.items():
            if os.path.exists(fn):
                zf.write(fn, sn, zipfile.ZIP_DEFLATED)

def pack_resource(dst, resource):
    objs = get_objs(resource)
    for o in objs:
        mtls = get_mtls(o)
        path, model_file = os.path.split(o)
        model, _ = os.path.splitext(model_file)
        res_dic = {model_file:o}
        # if os.path.isfile(os.path.join(path, "top.png")):
        #     res_dic["top.png"] = os.path.join(path, "top.png")
        if os.path.isfile(os.path.join(path, model+".mtl")):
            res_dic[model+".mtl"] = os.path.join(path, model+".mtl")
        if os.path.isfile(os.path.join(path, "virtual_foot.obj")):
            res_dic["virtual_foot.obj"] = os.path.join(path, "virtual_foot.obj")
        if os.path.isfile(os.path.join(path, "virtualFoot_Base.jpg")):
            res_dic["virtualFoot_Base.jpg"] = os.path.join(path, "virtualFoot_Base.jpg")
        if os.path.isfile(os.path.join(path, "model.txt")):
            res_dic["model.txt"] = os.path.join(path, "model.txt")
        for m in mtls:
            base_l = model + "_" + m + "_Base.png"
            p_base_l = os.path.join(path, base_l)
            if not os.path.isfile(p_base_l):
                raise Exception("obj文件中所使用材质名不符合规范，与本地纹理中材质命名不一致!!! 请检查obj文件中材质命名:", m)
            res_dic[base_l] = p_base_l
            rma_l = model + "_" + m + "_RMA.png"
            p_rma_l = os.path.join(path, rma_l)
            if not os.path.isfile(p_rma_l):
                raise Exception("obj文件中所使用材质名不符合规范，与本地纹理中材质命名不一致!!! 请检查obj文件中材质命名:", m)
            res_dic[rma_l] = p_rma_l
            normal_l = model + "_" + m + "_Normal.png"
            p_normal_l = os.path.join(path, normal_l)
            if os.path.isfile(p_normal_l):
                res_dic[normal_l] = p_normal_l
            top = "top.png"
            p_top = os.path.join(path, top)
            if os.path.isfile(p_top):
                res_dic[top] = p_top
            base_r = os.path.join("mirrorx", base_l)
            p_base_r = os.path.join(path, base_r)
            if os.path.isfile(p_base_r):
                res_dic[base_r] = p_base_r
            rma_r = os.path.join("mirrorx", rma_l)
            p_rma_r = os.path.join(path, rma_r)
            if os.path.isfile(p_rma_r):
                res_dic[rma_r] = p_rma_r
            normal_r = os.path.join("mirrorx", normal_l)
            p_normal_r = os.path.join(path, normal_r)
            if os.path.isfile(p_normal_r):
                res_dic[normal_r] = p_normal_r
        zip_resource(dst, res_dic)

def zip_file(zip_file_name, output):

    statusCode = {
        "success": True,
        "msgInfo": "obj pack passed.",
        "msgCode": SC.OBJ_PACK_SUCCESS
    }

    if not zip_file_name.endswith(".zip"):
        SC.setStatusCode(SC.OBJ_PACK_INPUT_NOT_ZIP, statusCode)
        return statusCode

    if not output.endswith(".zip"):
        SC.setStatusCode(SC.OBJ_PACK_OUTPUT_NOT_ZIP, statusCode)
        return statusCode

    statusCode = check_zip(zip_file_name, TMP_PATH)
    tmp_dirname = None
    if statusCode["success"]:
        tmp_dirname = statusCode["zip_unfold_path"]
        print("after check,tmp_dirname:"+tmp_dirname)
    
    if tmp_dirname == None:
        color_print("############ End #################", "green")  
        SC.setStatusCode(SC.OBJ_PACK_CHECK_ZIP_ERROR, statusCode)
        return statusCode

    
    statusCode = {
        "success": True,
        "msgInfo": "obj pack passed.",
        "msgCode": SC.OBJ_PACK_SUCCESS
    }

    _, file_name_with_ext = os.path.split(zip_file_name)
    file_name, _ = os.path.splitext(file_name_with_ext)
    try:
        print("tmp_dirname")
        print(tmp_dirname)        
        process(tmp_dirname, 'model.obj', 'virtual_foot.obj')
        print("after process")
        print("tmp_dirname:"+tmp_dirname)
        # print("parent:"+parent)
        # vfoot_tex = os.path.join(parent, tmp_dirname)
        vfoot_tex = os.path.join(tmp_dirname, "virtualFoot_Base.jpg")
        # print("vfoot_tex:" + vfoot_tex)
        # print("os.getcwd():"+os.getcwd())
        if not os.path.isfile(vfoot_tex):
            shutil.copy(VIRTUL_FOOT_BASE_JPG_PATH, tmp_dirname)
        shutil.copy(MODEL_TXT_PATH, tmp_dirname)

        with open(MODEL_TXT_PATH) as f:
            modelConfig = json.load(f)
        modelVersion = modelConfig["version"]
        global majorVersion, minorVersion
        majorVersion, minorVersion = modelVersion.split(".")


    except:
        shutil.rmtree(tmp_dirname)
        color_print("遇到错误! 文件名:" + file_name, "red")
        color_print("############ End #################", "green")
        SC.setStatusCode(SC.OBJ_PACK_ENCOUNTER_ERROR, statusCode)
        return statusCode

    color_print("打包模型文件:" + file_name, "green")
    try:
       pack_resource(tmp_dirname + ".zip", tmp_dirname)
    except Exception as err:
        shutil.rmtree(tmp_dirname)
        color_print(str(err).replace("(", "").replace(")", "").replace(",", "").replace("'", ""), "red")
        color_print("打包遇到错误！文件名:" + file_name, "red")
        color_print("############ End #################", "green")  
        SC.setStatusCode(SC.OBJ_PACK_ENCOUNTER_ERROR1, statusCode)
        return statusCode

    # shutil.move(tmp_dirname + ".zip", file_name + ".zip")
    shutil.move(tmp_dirname + ".zip", output)
    shutil.rmtree(tmp_dirname)
    color_print("打包成功! 文件名:" + file_name, "green")
    color_print("############ End #################", "green")  
    return statusCode      

if __name__ == '__main__':
    parser = mp.ArgumentParserForBlender(description="AR Glass Auto Placement")
    parser.add_argument('--input', '-i', help="zip path to be import", required=True)
    parser.add_argument('--output', '-o', help="output path")
    parser.add_argument('--info', '-f', help="result info file path")
    parser.add_argument('--local', '-l', help="whether use local environment")
    args = parser.parse_args()

    input = args.input
    output = args.output
    info_path = args.info
    use_local_environment = args.local
    print ("obj packModels, use local:"+use_local_environment)
    resetLocalEnvironment(use_local_environment)
    
    color_print("############ Start ###############", "green")  
    color_print("正在处理模型:" + input, "green")
    statusCode=zip_file(input, output)

    statusCode["majorVersion"] = majorVersion
    statusCode["minorVersion"] = minorVersion

    with open(info_path, 'w') as fp:
        json.dump(statusCode, fp)

