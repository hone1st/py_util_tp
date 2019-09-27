#### 运行环境
```
win10 64
python 3.6.5
```
## git_ftp.py
#### 依赖插件 
```
# pip install gitPython

```

#### 主要实现

```
代码推到git地址仓库。再触发脚本，即可实行仓库代码覆盖服务器的代码。第一次部署的时候，若不想全部覆盖服务器的代码，
可在服务器上保存一个版本记录文件.version里面内容为当前的git版本号。或者上一个版本号。

后续实现：备份服务器的代码。
```

#### 脚本需要的配置信息

```
本地根目录：.ftp_git.ini
[ftp]
user = 用户账号
passwd = 密码
host = ip地址
port = 端口号默认21
[git]
user = 登录账号
passwd = 密码
url = 仓库地址
```

#### ----------------------------
#### model.py 
#### 依赖安装
```
# pip install pymysql
```

#### 主要实现
```
基于thinkphp框架自定义的BaseModel 进行生成模型文件

# 再次生成的话。只会替换里面的字段信息。其他内容保持不变
 protected function generateTableField(): ?array
    {
        return [
            "pid" => self::generateINT(""), # int
            "username" => "名字", # varchar
        ];
    }
# 主要支持
【
INT
VARCHAR
TEXT
LONGTEXT
DATETIME
DECIMAL
】

生成后的文件内容：
<?php

namespace Exam\Model;

use Common\Model\BaseModel;

class ExamModel extends BaseModel
{
    protected $table_name = "exam";
    
    protected function generateTableField(): ?array
    {
        return [
            "pid" => self::generateINT(""), # int
            "username" => "名字", # varchar
        ];
    }
}
```

#### 脚本需要的配置信息
```
本地根目录：.model.ini
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
namespace =  文件所属命名空间
baseModel = Common\\Model\\BaseModel 基类引入
```

#### ----------------------------
#### yapi.py
#### 依赖安装
```
# pip install requests
```
#### 主要实现
```
基于tp框架的无路由设置。自动规则

接口：host+模块+控制器+接口名字.json

规则要求：
控制器类doc加@api 表示所属模块    对应生成Yapi上的分类
控制器方法注释：
/**
 * 接口命名    对应生成Yapi的中文命名
 * @param string $username 用户名 （username）对应接口参数的参数项 和 （用户名）备注项
 * @param string $password 密码
 */
 
方法内不可以用/**/ 进行注释

其他如果在网站上编辑内容。均不做覆盖。保留，只有接口名字。参数。参数备注 才做替换

本地删除的接口不会在对应的yapi网站上删除该文档接口。需要手动删除
```
#### 脚本需要的配置信息
```
本地根目录：.yapi.ini：
[Yapi]
project_id= yapi项目对应的id值
token= yapi项目对应的token值
except= 过滤文件用|作为分隔符带文件后缀
controller= 请输入存放控制文件的文件的目录 【目录名字即可】
except_dirs= 过滤目录用|作为分隔   【目录名字即可】
yapi_host= yapi部署的域名
```

#### 运行脚本-h 提示  -f 配置文件地址 即可读取自定义位置文件名字的配置信息

#### 打包需要依赖
```
# pip installer pyinstaller

不同操作系统生成对应的二进制文件。生成的二进制文件存放当前目录的dist目录下
# pyinstaller -F xx.py
```