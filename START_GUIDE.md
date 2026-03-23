# API Capture Skill - 启动指南

## 问题说明

在 Windows 上，mitmproxy 的 Python API 存在事件循环兼容性问题，导致 `python main.py capture` 命令无法正常工作。

## 解决方案

我们提供了**两种启动方式**，推荐使用方式 1（最简单）：

---

## 方式 1: 使用启动脚本（推荐）⭐

### Windows 用户

**双击运行**：
```
start_capture.bat
```

或者在 PowerShell 中运行：
```powershell
cd D:\capture-api-skill
.\start_capture.bat
```

### Linux/Mac 用户

```bash
cd D:/capture-api-skill
chmod +x start_capture.sh
./start_capture.sh
```

---

## 方式 2: 使用 mitmdump 命令

直接在命令行运行：

```powershell
cd D:\capture-api-skill
mitmdump -s mitm_script.py --listen-port 8080
```

---

## 启动成功后

你会看到类似的输出：
```
========================================
  API Capture Skill - 代理启动
========================================

[信息] 启动代理服务器...
[信息] 监听地址: localhost:8080
[信息] 数据库: D:\capture-api-skill\capture.db

[提示] 请配置浏览器代理为 localhost:8080
[提示] 按 Ctrl+C 停止捕获

========================================

[INFO] 数据库已连接: D:\capture-api-skill\capture.db
[INFO] 代理已启动，开始捕获流量...
[INFO] 按 Ctrl+C 停止捕获
```

---

## 配置浏览器代理

### Chrome/Edge

1. 打开设置 → 系统 → 打开代理设置
2. 手动代理配置：
   - HTTP 代理：`localhost`
   - 端口：`8080`
3. 保存设置

### Firefox

1. 设置 → 网络设置 → 手动代理配置
2. HTTP 代理：`localhost`，端口：`8080`
3. 勾选"也将此代理用于 HTTPS"

---

## 捕获流量

配置好代理后：
1. 访问你的 Web 系统
2. 正常操作（登录、下单等）
3. 终端会实时显示捕获的请求：
   ```
   [CAPTURED] POST /api/user/login -> 200
   [CAPTURED] GET /api/products/list -> 200
   [CAPTURED] POST /api/order/create -> 200
   ```

---

## 停止捕获

按 `Ctrl+C` 停止代理服务器

---

## 查看和生成测试用例

停止捕获后，启动 Web UI：

```powershell
cd D:\capture-api-skill
python main.py review
```

然后访问 `http://localhost:8888` 进行筛选和生成。

---

## 故障排查

### 问题 1: 找不到 mitmdump 命令

**解决方案**：
```powershell
pip install mitmproxy
```

### 问题 2: 端口 8080 被占用

**解决方案**：使用其他端口
```powershell
mitmdump -s mitm_script.py --listen-port 8081
```

### 问题 3: 浏览器无法访问网站

**解决方案**：
1. 检查代理配置是否正确
2. 确认代理服务器正在运行
3. 尝试访问 `http://mitm.it` 安装证书（HTTPS 需要）

---

## 完整使用流程

```powershell
# 1. 启动代理（新终端窗口）
cd D:\capture-api-skill
.\start_capture.bat

# 2. 配置浏览器代理为 localhost:8080

# 3. 操作 Web 系统，观察终端输出

# 4. 停止捕获（Ctrl+C）

# 5. 启动 Web UI（同一终端）
python main.py review

# 6. 浏览器访问 http://localhost:8888

# 7. 勾选接口，点击"生成用例"

# 8. 查看生成的文件
dir output\api
dir output\data
dir output\case
```

---

## 注意事项

- ✅ 代理会捕获所有经过的流量
- ✅ 自动过滤静态资源和无关请求
- ✅ 实时显示捕获的 API 请求
- ⚠️ HTTPS 网站需要安装 mitmproxy 证书
- ⚠️ 使用完毕后记得关闭浏览器代理
