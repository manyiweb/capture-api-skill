# API Capture Skill

用于捕获浏览器 HTTP 流量并生成接口自动化测试用例的工具。支持将登录、创建运单等连续操作还原为 Lounger 多步骤 API 场景。

## 快速开始

### 1. 安装依赖

```bash
cd /Users/cwill/Projects/capture-api-skill
uv venv .venv
uv pip install --python .venv/bin/python -r requirements.txt
source .venv/bin/activate
```

后续命令都在这个项目目录执行。每次新开终端，先执行
`source .venv/bin/activate`；提示符前出现 `(.venv)` 后，`python` 就是项目专用 Python。

### 2. 启动代理捕获

```bash
python main.py capture --include-host trackingmore.com
```

`--include-host trackingmore.com` 会保留该域及所有子域的业务 API，并过滤
`OPTIONS` 预检、页面资源和常见第三方遥测。配置浏览器代理为
`localhost:18527`，然后操作 Web 系统。每次启动捕获会默认清空旧数据；如需
继续追加到当前数据库，增加 `--keep-existing`。

### 3. 启动 Web UI 筛选

```bash
python main.py review
```

访问 http://localhost:18528，按业务发生顺序勾选登录、创建运单等接口，填写场景名称后点击生成。

### 使用独立 Chrome（推荐）

另开一个终端，让测试浏览器使用临时 Profile 和捕获代理，不影响日常 Chrome：

```bash
python main.py browser --url <TM后台地址> --proxy-port 18527
```

该 Chrome 不读取日常浏览器的账号、Cookie、插件或历史记录。默认仅测试实例忽略 HTTPS 证书错误；关闭独立 Chrome 后，临时 Profile 会自动删除。若本机无法自动找到 Chrome，可增加 `--chrome-path <可执行文件>`。

### 4. 查看生成产物

生成的代码位于 `output/` 目录：
- `api/` - API 封装函数
- `data/` - 测试数据文件
- `case/` - 测试用例
- `lounger/` - 可直接由 Lounger + pytest 收集的场景项目

Lounger 目录包括：

- `test_dir/test_<场景名>.py`：主要输出，截图风格的纯 Python pytest 场景
- `datas/captured/test_<场景名>.yaml`：按捕获顺序生成的多步骤场景
- `config/config.yaml`：目标 `base_url` 和待注入的登录信息
- `conftest.py`：动态运单号、时间戳等模板函数
- `test_api.py`：Lounger YAML 测试入口

生成器会尝试识别“前一接口响应 → 后续请求”的值传递。例如纯 Python
场景会从登录响应提取 `login_token`，并传给后续 `Authorization`。密码、Cookie、
登录 key/token 和无法关联的鉴权值不会原样写入用例，而会改为 Lounger 配置变量。

运行生成用例：

```bash
cd output/lounger
export LOUNGER_GLOBAL_TEST_CONFIG__LOGIN_USERNAME='your-user'
export LOUNGER_GLOBAL_TEST_CONFIG__LOGIN_PASSWORD='your-password'
pytest -v
```

默认执行 `test_dir/` 下的 Python 用例。如需运行 YAML 版本：

```bash
pytest test_api.py -v
```

### 敏感数据说明

生成阶段会把请求头、query、JSON/form 中的密码、Cookie、Authorization、
Token、API Key、Secret、登录验证码等替换成 Lounger 配置变量。原始值只保留在
本地 `capture.db` 中用于识别接口依赖；该文件和 `output/` 均已加入 `.gitignore`。
启动下一次捕获时默认清空旧数据库。

## 命令参考

```bash
python main.py capture [--port 18527] [--include-host DOMAIN] [--keep-existing]
python main.py browser [--url URL] [--proxy-port 18527]    # 启动独立测试 Chrome
python main.py review [--port 18528] [--db capture.db]     # 启动 Web UI
python main.py clear [--db capture.db]                    # 清空数据
```

## 运行测试

```bash
pytest tests/ -v
```
