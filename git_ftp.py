import configparser
import getopt
import os
import sys
from ftplib import FTP, error_perm
import git


class GitUtil(object):
    user = None
    passwd = None
    git_url = None
    dir_name = None
    repo = git.Repo

    def __init__(self, **kwargs):
        user = kwargs.pop("user")
        passwd = kwargs.pop("passwd")
        git_url = kwargs.pop("git_url")
        if passwd and user and git_url:
            self.passwd = passwd
            self.user = user
            git_url = str(git_url).replace("http://", "")
            self.dir_name = git_url.split("/")[-1].split(".")[0]
            self.git_url = git_url
        else:
            raise Exception("(user,passwd,git_url)必须全部传")

        self.__user_login()

    def __user_login(self):
        temp_dir = os.getenv('TEMP') + "/" + self.dir_name
        if os.path.exists(temp_dir + "/" + ".git"):
            self.repo = git.Repo.init(temp_dir)
            # 强制更新最新代码 覆盖本地的
            self.repo.git.execute('git reset --hard origin/master')
            print("git目录已经存在!")
            return
        try:
            self.repo = git.Repo.clone_from("http://%s:%s@%s" % (self.user, self.passwd, self.git_url),
                                            to_path=temp_dir)
            print("克隆成功!")
        except Exception as e:
            raise Exception("克隆出错：%s" % e.args)

    def get_diff_file(self, old_version):
        new_version = self.get_current_version()
        resp = self.repo.git.execute("git diff -no-pager --name-only %s %s" % (old_version, new_version))
        if len(resp) is 0:
            return None
        return resp.split("\n")

    def get_current_version(self):
        return self.repo.head.log_entry(-1).newhexsha


class FtpUtil(object):
    ftp = FTP()
    log = ""
    list_name = []
    dict_dir = {}
    cur_dir = ""

    def __init__(self, host, user, pwd, port=21):
        self.ftp.connect(host=host, port=port)
        self.ftp.login(user=user, passwd=pwd)
        self.ftp.set_pasv(False)

    def get_remote_name(self, line):
        file_name = str(line).split(" ")[-1]
        if file_name not in [".", ".."]:
            type_file = line[0]
            self.dict_dir[self.cur_dir].append([type_file, file_name])

    def remote_local_same(self, remote_path, local_path):
        try:
            remote_size = self.ftp.size(remote_path)
        except Exception as e:
            remote_size = -1
        try:
            local_size = os.path.getsize(local_path)
        except Exception as e:
            local_size = -1
        print("ftp目录的文件【%s】大小为【%s】" % (remote_path, remote_size))
        print("本地目录的文件【%s】大小为【%s】" % (local_path, local_size))
        print("------------------------------------")
        if remote_size == local_size:
            return 1
        else:
            return 0

    def down_file(self, remote_path, local_path):
        if not self.remote_local_same(remote_path, local_path):
            if not os.path.exists(os.path.dirname(local_path)):
                os.makedirs(os.path.dirname(local_path))
            local_fp = open(local_path, 'wb')
            self.ftp.retrbinary("RETR " + remote_path, local_fp.write)
            local_fp.close()

    def down_files(self, remote_path, local_path):
        try:
            self.ftp.cwd(remote_path)
        except error_perm as e:
            return
        print("------------------------------------")
        print("ftp目录切换到：%s" % self.ftp.pwd())
        try:
            self.cur_dir = self.ftp.pwd()
            self.dict_dir[self.cur_dir] = []
            self.ftp.dir(self.get_remote_name)
            for i in self.dict_dir[self.ftp.pwd()]:
                local_ = os.path.join(local_path, i[1])
                if i[0] == "-":
                    self.down_file(i[1], local_)
                elif i[0] == "d":
                    self.down_files(i[1], local_)
            self.ftp.cwd('..')
        except Exception as e:
            print("超时ing......。正在重新连接！")
            self.down_files("./", "./")
            self.list_name = []
            self.dict_dir = {}
            self.cur_dir = ""
        print("回到目录【%s】" % self.ftp.pwd())
        print("------------------------------------")

    def read_version_file(self):
        self.ftp.cwd("/")
        fp = open("./.version", "wb")
        try:
            self.ftp.retrbinary("RETR .version", fp.write)
        except error_perm as e:
            if "550" in e.__str__():
                return 0
        finally:
            fp.close()
        if os.path.getsize("./.version") == 0:
            return 0
        return 1

    def upload_file(self, local_path, remote_path):
        print("-----------------------")
        print("即将上传的文件为：【%s】" % local_path)
        self.ftp.cwd("/")
        fp = open(local_path, "rb")
        buf_size = 1024
        try:
            self.ftp.storbinary("STOR %s" % remote_path, fp, buf_size)
            print("文件为：【%s】" % local_path, "已经上传成功!")
        except error_perm as e:
            print("出错文件：【%s】" % remote_path + "\r\n", "出错原因：【%s】" % e.args)
        finally:
            fp.close()
            print("-------------------------------------")


def init_config():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hf:", ["file="])
        if not opts:
            if os.path.exists("./.ftp_git.ini"):
                opts = [('-f', ".ftp_git.ini")]
    except getopt.GetoptError:
        print(sys.argv[0] + ' -f 配置文件路径')
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print(sys.argv[0] + ' -f 配置文件路径')
            print("""
配置文件格式如下：
[ftp]
user = 用户账号
passwd = 密码
host = ip地址
port = 端口号默认21
[git]
user = 登录账号
passwd = 密码
url = 仓库地址
            """)
            sys.exit()
        elif opt in ("-f", "--file"):
            cf = configparser.ConfigParser()
            try:
                cf.read(arg, encoding='gbk')
                ftp_user = cf.get("ftp", "user")
                ftp_passwd = cf.get("ftp", "passwd")
                host = cf.get("ftp", "host")
                port = cf.get("ftp", "port")

                git_user = cf.get("git", "user")
                git_passwd = cf.get("git", "passwd")
                url = cf.get("git", "url")
            except configparser.NoSectionError as s:
                print("请在配置文件中配置：[%s]节点" % s.section)
                sys.exit()
            except configparser.NoOptionError as e:
                print("请在[%s]节点中配置：%s 选项" % (e.section, e.option))
                sys.exit()
    if not opts:
        print("开始配置ftp信息")
        ftp_user = input("请输入ftp登录账号：")
        while not ftp_user:
            ftp_user = input("ftp登录账号不能为空（重新输入）:")
        ftp_passwd = input("请输入ftp登录密码：")
        while not ftp_passwd:
            ftp_passwd = input("ftp登录密码不能为空（重新输入）:")

        host = input("请输入ftp的连接ip地址：")
        if not host:
            host = input("ftp的连接ip地址不能为空（重新输入）:")
        port = input("请输入ftp连接的端口号地址（默认21）：")
        if not port:
            port = "21"

        print("开始配置git信息")
        git_user = input("请输入git的对应地址仓库需要的用户名：")
        while not git_user:
            git_user = input("git的对应地址仓库需要的用户名不能为空（重新输入）:")

        git_passwd = input("请输入git的对应地址仓库需要的密码：")
        if not git_passwd:
            git_passwd = input("git的对应地址仓库需要的密码不能为空（重新输入）:")

        url = input("请输入git的对应地址：")
        if not url:
            url = input("git的对应地址不能为空（重新输入）:")

        cf = configparser.ConfigParser()
        cf.add_section("ftp")
        cf.add_section("git")
        cf.set("ftp", "host", host)
        cf.set("ftp", "passwd", ftp_passwd)
        cf.set("ftp", "user", ftp_user)
        cf.set("ftp", "port", port)
        cf.set("git", "user", git_user)
        cf.set("git", "passwd", git_passwd)
        cf.set("git", "url", url)

        with open(file="./.ftp_git.ini", mode="w") as f:
            cf.write(f)
    return host, port, ftp_user, ftp_passwd, url, git_user, git_passwd


if __name__ == "__main__":
    """
        加载配置
    """
    host, port, ftp_user, ftp_passwd, url, git_user, git_passwd = init_config()

    git_util = GitUtil(user=git_user, git_url=url, passwd=git_passwd, port=port)
    ftp_util = FtpUtil(host, ftp_user, ftp_passwd)
    code = ftp_util.read_version_file()
    file_dir_local = os.getenv('TEMP') + "/" + git_util.dir_name
    if code == 1:
        with open(".version", "r") as r:
            line = r.read()
        # 获取到不同的文件路径
        file_paths = git_util.get_diff_file(line)
        if file_paths is None:
            print("本地文件和线上对比：文件无变化！")
        else:
            for file in file_paths:
                ftp_util.upload_file(file_dir_local + "/" + file, file)
    else:
        # 如果不存在版本记录文件。那就全部覆盖
        for root, dirs, files in os.walk(file_dir_local):
            for name in files:
                if ".git" not in root:
                    ftp_util.upload_file("/".join((root, name)), name)

    # 最后都要用最新的版本记录覆盖线上的版本记录文件
    cur_version = git_util.get_current_version()
    with open(".version", "w") as w:
        w.write(cur_version)

    ftp_util.upload_file(".version", ".version")
    print("已经完成覆盖!当前版本为：%s" % cur_version)
    input("已完成：请按enter键结束：Press <enter>")
