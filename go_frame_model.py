import os
import pymysql
import sys
import getopt
import configparser
import re

# 连接database

host = ""
user = ""
password = ""
database = ""
charset = ""
port = 0
# -----------------------------------
# 表名映射字段
table_fields = {}
# 文件参数设置
file_suffix = ""
file_dir = ""
table_prefix = ""
with_model = True
name_space = ""
base_model = ""
prefix = ""
# --------------------
base_model_name = ""


def init_args():
    global host
    global user
    global password
    global database
    global charset
    global port
    # ---------------------------------
    global file_suffix
    global file_dir
    global table_prefix
    global with_model
    global name_space
    global prefix
    # -------------------------- 额外
    global base_model_name
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hf:", ["file="])
        if not opts:
            if os.path.exists("./.model.ini"):
                opts = [('-f', "./.model.ini")]
    except getopt.GetoptError:
        print(sys.argv[0] + ' -f 配置文件路径')
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print(sys.argv[0] + ' -f 配置文件路径')
            print("""
配置文件格式如下：
[mysql]
host = 127.0.0.1 地址
user = root 账号
password = root 密码
database = test 数据库
charset = utf8 编码格式
port = 3306 端口号
[file]
suffix = .class.php 生成文件的后缀
dir = ./Model 生成的模型文件存放的路径
table_prefix = ox_ 数据库需要生成表的前缀或者是含有该字符得
prefix = ox_ 数据库的表前缀（全部的）
model = False/True  生成模型文件是否带Model
namespace = "xxx\\Model" 文件所属命名空间
            """)
            sys.exit()
        elif opt in ("-f", "--file"):
            cf = configparser.ConfigParser()
            try:
                cf.read(arg, encoding='gbk')
                host = cf.get("mysql", "host")
                user = cf.get("mysql", "user")
                password = cf.get("mysql", "password")
                database = cf.get("mysql", "database")
                charset = cf.get("mysql", "charset") if cf.get("mysql", "charset") else "utf8"
                port = int(cf.get("mysql", "port")) if cf.get("mysql", "port") else 3306
                # -----------------------------------------
                file_suffix = cf.get("file", "suffix")
                file_dir = cf.get("file", "dir")
                prefix = cf.get("file", "prefix")
                with_model = True if cf.get("file", "model") else False
                name_space = cf.get("file", "namespace")
                table_prefix = cf.get("file", "table_prefix")
            except configparser.NoSectionError as s:
                print("请在配置文件中配置：[%s]节点" % s.section)
                sys.exit()
            except configparser.NoOptionError as e:
                if e.option != "charset":
                    print("请在[%s]节点中配置：%s 选项" % (e.section, e.option))
                    sys.exit()
                else:
                    charset = "utf8"
    if not opts:
        print("开始配置数据库链接")
        host = input("请输入host地址:")
        while not host:
            host = input("host地址不能为空（重新输入）:")
        user = input("请输入登录用户名:")
        while not user:
            user = input("登录用户名不能为空（重新输入）:")
        password = input("请输入登录密码:")
        database = input("请输入数据库名字:")
        while not database:
            database = input("数据库名字不能为空（重新输入）:")
        port = input("请输入数据库链接端口号:")
        if not port:
            port = 3306
        print("开始配置生成文件的配置")
        file_suffix = input("请输入生成的文件的后缀带（.）:")
        while not file_suffix:
            file_suffix = input("生成的文件的后缀不能为空（重新输入）:")
        file_dir = input("请输入生成的文件存放目录（相对路径）:")
        if not file_dir:
            print("由于目录设置为空，默认为当前目录下")
            file_dir = "./"

        table_prefix = input("请输入数据库的表前缀，可做过滤作用，对某些表生成模型：")
        with_model = input("请输入生成的文件是否带有Model（False/True）：")
        if not with_model:
            with_model = False
        prefix = input("请输入数据库的表前缀：")

        name_space = input("请输入模型文件所属得命名空间：")

        cf = configparser.ConfigParser()
        cf.add_section("mysql")
        cf.add_section("file")
        cf.set("mysql", "host", host)
        cf.set("mysql", "port", str(port))
        cf.set("mysql", "user", user)
        cf.set("mysql", "password", password)
        cf.set("mysql", "database", database)
        cf.set("mysql", "charset", charset)
        cf.set("file", "suffix", file_suffix)
        cf.set("file", "dir", file_dir)
        cf.set("file", "model", str(with_model))
        cf.set("file", "prefix", prefix)
        cf.set("file", "namespace", name_space)
        cf.set("file", "table_prefix", table_prefix)

        with open(file="./..model.ini", mode="w") as f:
            cf.write(f)

    # print((host, user, password, database, port, file_suffix, file_dir, table_prefix, with_model))
    # sys.exit()


def connect_mysql():
    global connect
    try:
        connect = pymysql.connect(host=host, user=user, password=password, database=database, charset=charset,
                                  port=port)
        print(connect)
        # if not isinstance(connect, pymysql.Connection):
        #     raise pymysql.MySQLError("链接失败!!!")
    except Exception as e:
        print(e.args)
        sys.exit()


def get_all_table():
    sql = "select table_name from information_schema.tables where table_schema='%s' and table_type='base table';" % database
    db = connect.cursor()
    db.execute(query=sql)
    for table_name in db.fetchall():
        get_table_all_cols(table_name[0])


def get_table_all_cols(table_name):
    if not str(table_name).startswith(table_prefix):
        return

    sql = "select * from information_schema.columns where table_schema='%s' and table_name='%s'" % (
        database, table_name)
    db = connect.cursor(cursor=pymysql.cursors.DictCursor)
    db.execute(query=sql)
    # 字段映射字段属性
    fields_sx = {}
    for col in db.fetchall():
        # if col['COLUMN_NAME'] not in ("id", "created_at", "updated_at", "is_delete"):
        length = re.findall(r'\d+', col["COLUMN_TYPE"])
        fields_sx[col['COLUMN_NAME']] = {
            "name": col['COLUMN_NAME'],  # 字段名字
            "default": col['COLUMN_DEFAULT'] if col["COLUMN_DEFAULT"] else "",  # 字段默认值
            "type": col["DATA_TYPE"],  # 字段类型
            "comment": col["COLUMN_COMMENT"],  # 字段备注
            "length": length[0] if length else 0
        }

    table_fields[table_name] = fields_sx


def get_fields_lines(fields):
    """
    :param fields:
    :return:
       	Id        int       `json:"id" comment:"主键id"`
        Pid       int       `json:"pid" comment:"父id"`
        Password  string    `json:"password" comment:"登录密码"`
        HeaderImg string    `json:"header_img" comment:"头像"`
        LawFirmId string    `json:"law_firm_id" comment:"企业名字"`
        Token     string    `json:"token" comment:"登录凭证"`
        RoleId    int       `json:"role_id" comment:"角色id 关联role表"`
        AdminId   int       `json:"admin_id" comment:"管理员id"`
        StartTime time.Time `json:"start_time" comment:"服务开始时间"`
        EndTime   time.Time `json:"end_time" comment:"服务结束时间"`
        IsDelete  int       `json:"is_delete" comment:"1为已删除数据 0为未删除"`
        CreatedAt time.Time `json:"created_at" comment:"创建时间"`
        UpdatedAt time.Time `json:"updated_at" comment:"插入时间"`
    """
    field_list = []
    for field, sx in fields.items():
        type_f = str(sx["type"]).upper()
        types = ""
        if "INT" in type_f:
            types = "int"
        elif "VARCHAR" in type_f or "LONGTEXT" in type_f:
            types = "string"
        elif "DATETIME" in type_f or "TIMESTAMP" in type_f:
            types = "gtime.Time"
        v_f = """%s %s  `json:"%s" comment:"%s"`
        """ % (deal_field(field), types, field, sx["comment"])
        field_list.append(v_f)
    return "".join(field_list)


def deal_field(field):
    d = ""
    for i in field.split("_"):
        d += i.capitalize()
    return d


model_files = {}


def generate_file():
    if not os.path.exists(file_dir):
        os.makedirs(name=file_dir)

    for table, fields in table_fields.items():
        table = table.replace(prefix, "")
        model_name = deal_field(table)
        content = """package model

import (
    "github.com/gogf/gf/os/gtime"
    )

const %s = TablePrefix + "%s"

type %s struct {
        %s
}
        """ % (model_name + "Table", table, model_name, get_fields_lines(fields))
        model_files[table] = content
        # if len(model_files) >= 1:
        #     break


def make_file():
    for file, content in model_files.items():
        file_path = file_dir + "/" + file + file_suffix
        if os.path.exists(file_path):
            with open(file=file_path, mode="r", encoding="utf-8") as f:
                ori_content = f.read()
                if ori_content != content and ori_content:
                    ori = re.findall(r'protected function generateTableField[^~}]+', ori_content)
                    new = re.findall(r'protected function generateTableField[^~}]+', content)

                    # 替换generateTableField
                    if ori and ori != new and new:
                        ori_content = ori_content.replace(ori[0], new[0])

                    ori_table_name = re.findall(r'protected \$table_name[^~;]+;', ori_content)
                    new_table_name = re.findall(r'protected \$table_name[^~;]+;', content)

                    # 替换table_name参数的值
                    if ori_table_name and ori_table_name != new_table_name and new_table_name:
                        ori_content = ori_content.replace(ori_table_name[0], new_table_name[0])

                    content = ori_content
        with open(file=file_path, mode="w", encoding="utf-8") as f:
            f.write(content)
        print("已经生成model文件：", file_path)


if __name__ == "__main__":
    init_args()
    connect_mysql()
    get_all_table()
    generate_file()
    make_file()
    input("已完成：请按enter键结束：Press <enter>")
