import getopt
import json
import os
import re
import requests
import sys
import time
import configparser

doc_path = "./Yapi"

index = []
# 基础设置
yapi_host = ""
token = ""
project_id = 0

except_file = []
except_dirs = []
controller_dir = ""

#
cat_name_id = {}
cat_list = []

# 网站上的分类下的接口数组
# 已经填充的映射为分类下
cat_api_dict = {}
path_dict_all = {}


def get_all_cat():
    """
    获取所有的分类
    :return:
    """
    cat_list_resp = json.loads(requests.request("GET", yapi_host + "/api/interface/getCatMenu",
                                                params={'token': token, 'project_id': project_id}).content.decode(
        "utf-8"))
    if cat_list_resp['errcode'] == 0:
        for i in cat_list_resp['data']:
            cat_list.append(i['name'])
            cat_name_id[i['name']] = i['_id']


def get_all_api_by_cat_id(cat_id):
    """
    根据分类id获取当前分类的所有接口
    :param cat_id:
    :return:
    """
    if not cat_api_dict.__contains__(cat_id):
        global path_dict_all
        api_list_resp = requests.request("GET", yapi_host + "/api/interface/list_cat",
                                         params={'token': token, 'catid': cat_id, 'page': 1,
                                                 "limit": 1000}).content.decode(
            "utf-8")
        api_list_resp = json.loads(api_list_resp)
        cat_api_dict[cat_id] = {i["path"]: i for i in api_list_resp['data']['list']}

        path_dict_all = {i["path"]: get_detail_api_by_id(i["_id"]) for i in api_list_resp['data']['list'] if not
        path_dict_all.__contains__(i["path"])}


def get_detail_api_by_id(id):
    """
    根据接口id获取接口的详细配置数据
    :param id:
    :return:
    """
    api_resp = requests.request("GET", yapi_host + "/api/interface/get",
                                params={'token': token, 'id': id}).content.decode(
        "utf-8")

    data = json.loads(api_resp)
    return {i['name']: i for i in data['data']['req_body_form']}


def add_cat(cat_name):
    """
    添加分类
    :param cat_name: 分类名字
    :return: 添加成功返回分类id
    """
    post_json = {'name': cat_name, 'up_time': time.time(), 'token': token, 'project_id': project_id}
    resp_cat = json.loads(
        requests.request("post", yapi_host + "/api/interface/add_cat", json=post_json).content.decode(
            "utf-8"))

    if resp_cat['errcode'] == 0:
        return resp_cat['data']['_id']
    else:
        return -1


def print_json_str(json_):
    """
    打印数据格式化
    :param json_:
    :return:
    """
    print(json.dumps(json_, ensure_ascii=False, indent=2))


"""
    保存或者更新接口
"""


def up_date_or_save(save):
    get_all_api_by_cat_id(save['catid'])
    for i in range(0, len(save['req_body_form'])):
        # 如果原分组下存在该api路径
        if path_dict_all.__contains__(save['path']):
            # 如果存在同一个参数则更新参数数据
            if path_dict_all[save['path']].__contains__(save['req_body_form'][i]["name"]):
                c = {}
                ori = path_dict_all[save['path']][save['req_body_form'][i]["name"]]
                c.update(ori)
                c.update(save['req_body_form'][i])
                save['req_body_form'][i] = c

    if cat_api_dict[save["catid"]].__contains__(save["path"]):
        ori = cat_api_dict[save["catid"]][save["path"]]
        ori.update(save)
        save = ori

    save["req_headers"] = [
        {
            "name": "Content-Type",
            "value": "application/x-www-form-urlencoded"
        }
    ]
    save["req_body_type"] = "form"
    resp = requests.request("post", yapi_host + "/api/interface/save", json=save)
    print("响应结果:",
          json.dumps(json.loads(resp.content.decode("utf-8"))["errmsg"], indent=2, ensure_ascii=False) + "\r\n",
          "保存接口:",
          save['path'] + "\r\n", "保存接口中文名字：",
          save['title'] + "\r\n", "属于模块:", save['catname'] + "\r\n")
    print("----------------------------------------------------" + "\r\n")


def check_ex_dirs(root):
    """
    :param root: 当前路径
    :return: 如果当前路径含有被过滤的目录则返回False
    """
    for i in except_dirs:
        if i in root:
            return False

    return True


def search_file():
    for root, dirs, files in os.walk("./"):
        if root.endswith(controller_dir) and check_ex_dirs(root):
            # 获取模块名字
            en_module_name = os.path.dirname(root).split("\\")[-1].replace("./", "")
            deal_file(files, en_module_name, root)

    if index:
        file_name = time.strftime("%Y-%m-%d_%H_%M_%S")
        json.dump(index, open(doc_path + "/" + file_name + ".json", "w+", encoding="utf-8"),
                  ensure_ascii=False, indent=4)
        get_all_cat()

    for json_ in index:

        if cat_list.__contains__(json_['name']):
            cat_id = cat_name_id[json_['name']]
        else:
            cat_id = add_cat(json_['name'])
            cat_name_id[json_['name']] = cat_id
        if cat_id == -1:
            continue

        for save in json_['list']:
            save['token'] = token
            save['catid'] = cat_id
            save['catname'] = json_['name']
            save['project_id'] = project_id
            save['dataSync'] = "good"
            up_date_or_save(save)


def get_params(line):
    params = str(re.findall(r'\(([^`]*?)\)', line)[0])
    ret_params = []
    if len(params) is not 0:
        params = params.replace("\n", "")
        params = params.replace("  ", "")
        """
            {
            "required": "1",
            "_id": "5d6f765d43dacf409afecc91",
            "name": "activity_id",
            "type": "text",
            "desc": "主活动Id"
          }
        """
        for i in params.split(","):
            t = ""
            i = i.replace("string", "").replace("int", "").replace("array", "").replace("$", " ").strip(" ")
            if i.count("=") > 0:
                i = i.split("=")[0].strip(" ")
            ps = re.findall(r'@param[^(`\r\n)]+' + i + r'[^(`\r\n)]+', line)
            if ps:
                t = str(ps[0]).split(i)[-1].strip(" ")
            ret_params.append({
                "required": 1,
                "name": i,
                "type": "text",
                "desc": t
            })
    return ret_params


def deal_hash_comment(param, en_module_name, controller_name, api):
    value = []
    for line in param:
        if "protected function" in line or "@api" in line or "private function" in line:
            continue
        compile_str = r'[^/*\n\(\s\+\)]+[\s]*?[^/*\n\(\s\+\)]+'
        cn_api_name = re.findall(compile_str, line)[0]
        en_api_name = re.findall(r'function\s*?([^-~\s]*?)\(', str(line))[0]
        desc = str(re.findall(r'\s+\/\*[^`]+\*\/', line)[0]).lstrip("\n")
        value.append(
            {
                'title': cn_api_name,
                'status': "done",
                # "req_body_is_json_schema": F,
                # "res_body_is_json_schema": False,
                "method": "POST",
                "path": "/" + en_module_name + "/" + controller_name + "/" + en_api_name + ".json",
                "res_body_type": "json",
                'add_time': time.time(),  # 添加时间
                'up_time': time.time(),  # 更新时间
                "req_body_form": get_params(line),
                "desc": desc
            })
    return {
        'name': api,
        'add_time': time.time(),  # 添加时间
        'up_time': time.time(),  # 更新时间
        'list': value
    }


def mkdir_path(path):
    if not os.path.exists(path):
        os.mkdir(path)


def deal_file(files, en_module_name, root):
    for file in files:
        if not except_file.__contains__(file) and str(file).endswith("php"):
            with open(root + "/" + file, "r", encoding="utf-8") as f:
                content = f.read()
                ori_api = re.findall(r'@api.*?[a-zA-Z\u4e00-\u9fa5]+', content)
                if len(ori_api) > 0:
                    api = ori_api[0].split("@api")[-1].strip(" ")
                    content = content.split(ori_api[0])[-1]
                    """
                        'name': api,
                        'add_time': time.time(),  # 添加时间
                        'up_time': time.time(),  # 更新时间
                        'list': [
                                    {
                                        'title': cn_api_name,  api的中文说明
                                        'status': "done",   完成状态
                                        "req_body_is_json_schema": True,
                                        "res_body_is_json_schema": True,
                                        "method": "POST",  提交方式json
                                        "path": "/" + en_module_name + "/" + controller_name + "/" + en_api_name + ".json", api路径
                                        "res_body_type": "json",  响应体类型
                                        'add_time': time.time(),  # 添加时间
                                        'up_time': time.time(),  # 更新时间
                                        "req_body_form": [
                                            {
                                                "required": 1,  是否必须
                                                "name": 参数,
                                                "type": "text",  参数类型  text/file
                                                "desc": 参数描述
                                            }                                        
                                        ],
                                        "desc": desc  api的注释
                                    }
                                ]
                    """
                    temp = deal_hash_comment(re.findall(r'\s+\/\*\*[^`]*?\)', content), en_module_name,
                                             file.replace("Controller.class.php", "").replace(".php", "").replace(
                                                 ".class.php", ""),
                                             api)
                    if len(temp) > 1:
                        index.append(temp)


def init_args():
    global token
    global project_id
    global except_file
    global controller_dir
    global except_dirs
    global yapi_host

    print("""
    格式要求：
    控制器文件类注释 
    /**
        @api 【模块名字】 eg:xx模块
    */
    控制器方法注释：
    /**
     * 【方法中文名字】 eg:登录
     * @param int 【参数】eg:$user_name 【参数备注】eg:用户名字
     */
    注：方法内不能存在/***/ 注释 可//注释
    """)

    try:
        opts, args = getopt.getopt(sys.argv[1:], "hf", ["file="])
        if not opts:
            if os.path.exists("./.yapi.ini"):
                opts = [('-f', "./.yapi.ini")]
    except getopt.GetoptError:
        print("""
            %s -f config
            %s -h
        """ % (sys.argv[0], sys.argv[0]))
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print("""
                project_id：yapi项目对应的id值
                token：yapi项目对应的token值
                except：过滤文件用|作为分隔符带文件后缀
                controller：请输入存放控制文件的文件的目录
                except_dirs：过滤目录用|作为分隔符带文件后缀
                以上均区分大小写
                配置文件示例：
                [Yapi]
                project_id=
                token=
                except=
                controller=
                except_dirs=
                yapi_host=
            """)
            sys.exit()
        elif opt in ("-f", "--file"):
            cf = configparser.ConfigParser()
            try:
                cf.read(arg, encoding='gbk')
                if not os.path.exists(arg):
                    print("目标文件不存在")
                    sys.exit()
                project_id = cf.get("Yapi", "project_id")
                yapi_host = cf.get("Yapi", "yapi_host")
                token = cf.get("Yapi", "token")
                except_file = str(cf.get("Yapi", "except")).split("|")
                controller_dir = cf.get("Yapi", "controller")
                except_dirs = str(cf.get("Yapi", "except_dirs")).split("|")
            except configparser.NoSectionError:
                print("请在配置文件中配置：[Yapi]节点")
            except configparser.NoOptionError as e:
                print("请在[Yapi]节点中配置：" + e.option + "选项")
            if None in (token, project_id, controller_dir):
                print("【project_id|token|controller】中任何一项都不可以为空!")
                sys.exit()

    if not opts:
        yapi_host = input("请输入yapi的基础地址[例:http://yapi.com]：")
        while not yapi_host:
            yapi_host = input("请输入yapi的基础地址[例:http://yapi.com]：")

        token = input("请输入项目对应的token值：")
        while not token:
            token = input("请输入项目对应的token值【不可为空】：")
        project_id = input("请输入项目对应的project_id值：")
        while not project_id:
            project_id = input("请输入项目对应的project_id值【不可为空】：")
        except_file = input("请输入需要过滤文件【用|作为分隔符带文件后缀】：")
        controller_dir = input("请输入存放控制文件的文件的目录：")
        while not controller_dir:
            controller_dir = input("请输入存放控制文件的文件的目录【不可为空】：")
        except_dirs = input("请输入过滤目录【用|作为分隔符带文件后缀】：")

        cf = configparser.ConfigParser()
        cf.add_section("Yapi")
        cf.set("Yapi", "yapi_host", yapi_host)
        cf.set("Yapi", "project_id", project_id)
        cf.set("Yapi", "token", token)
        cf.set("Yapi", "except", except_file)
        cf.set("Yapi", "controller", controller_dir)
        cf.set("Yapi", "except_dirs", except_dirs)

        with open(file="./.yapi.ini", mode="w") as f:
            cf.write(f)

        print("配置文件已生成!文件路径为当前目录下的yapi_config.ini。如需要重新生成!删除该配置文件即可!")


if __name__ == "__main__":
    init_args()
    mkdir_path(doc_path)
    search_file()
    input("已完成：请按enter键结束：Press <enter>")