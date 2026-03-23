# 浏览器代理配置详细指南

## 代理信息

- **地址**：`localhost` 或 `127.0.0.1`
- **端口**：`18527`

---

## Chrome / Edge 浏览器

### 步骤 1: 打开代理设置

**方法 A - 通过设置页面**：
1. 点击浏览器右上角的 `⋮` (三个点)
2. 选择"设置"
3. 在左侧菜单选择"系统"
4. 点击"打开您计算机的代理设置"

**方法 B - 直接访问**：
- 在地址栏输入：`chrome://settings/system` (Chrome)
- 或：`edge://settings/system` (Edge)
- 点击"打开您计算机的代理设置"

### 步骤 2: 配置代理（Windows）

1. 在"代理"设置页面，找到"手动设置代理"
2. 打开"使用代理服务器"开关
3. 填写代理信息：
   ```
   地址：localhost
   端口：18527
   ```
4. （可选）在"请勿对以下条目开头的地址使用代理服务器"中添加：
   ```
   localhost;127.0.0.1
   ```
   这样访问本地服务时不会经过代理
5. 点击"保存"

### 步骤 3: 验证配置

1. 打开浏览器
2. 访问任意网站（如 `http://example.com`）
3. 查看代理服务器终端，应该看到捕获的请求

---

## Firefox 浏览器

### 步骤 1: 打开网络设置

1. 点击右上角的 `☰` (三条横线)
2. 选择"设置"
3. 滚动到页面底部
4. 找到"网络设置"部分
5. 点击"设置..."按钮

### 步骤 2: 配置代理

1. 选择"手动代理配置"
2. 填写 HTTP 代理信息：
   ```
   HTTP 代理：localhost
   端口：18527
   ```
3. ✅ **重要**：勾选"也将此代理用于 HTTPS"
4. （可选）在"不使用代理"中添加：
   ```
   localhost, 127.0.0.1
   ```
5. 点击"确定"

### 步骤 3: 验证配置

访问任意网站，查看代理终端是否有输出。

---

## 使用浏览器扩展（推荐）

### 为什么使用扩展？

- ✅ 快速切换代理开关
- ✅ 不影响系统其他应用
- ✅ 可以设置规则（哪些网站走代理）
- ✅ 更方便管理

### 推荐扩展：Proxy SwitchyOmega

#### 安装

1. **Chrome/Edge**：
   - 访问 Chrome 应用商店
   - 搜索"Proxy SwitchyOmega"
   - 点击"添加到 Chrome/Edge"

2. **Firefox**：
   - 访问 Firefox 附加组件商店
   - 搜索"Proxy SwitchyOmega"
   - 点击"添加到 Firefox"

#### 配置

1. 安装后点击扩展图标
2. 选择"选项"
3. 点击"新建情景模式"
4. 输入名称（如"API Capture"）
5. 选择"代理服务器"
6. 配置代理：
   ```
   协议：HTTP
   代理服务器：localhost
   代理端口：18527
   ```
7. 点击左侧"应用选项"保存

#### 使用

- 点击扩展图标
- 选择"API Capture"情景模式
- 代理即刻生效
- 再次点击可切换回"直接连接"

---

## 验证代理是否生效

### 方法 1: 访问测试网站

配置好代理后，访问以下网站：

```
http://httpbin.org/ip
```

**代理生效**：
```json
{
  "origin": "127.0.0.1"
}
```

**代理未生效**：
```json
{
  "origin": "你的真实IP"
}
```

### 方法 2: 查看代理终端

启动代理后（`.\start_simple.bat`），访问任何网站。

**代理正常工作**：终端显示
```
[CAPTURED] GET /api/test -> 200
[CAPTURED] POST /api/login -> 200
```

**代理未工作**：终端无任何输出

### 方法 3: 浏览器开发者工具

1. 按 `F12` 打开开发者工具
2. 切换到"Network"（网络）标签
3. 访问任意网站
4. 查看请求是否通过代理（会显示代理信息）

---

## 常见问题

### Q1: 配置代理后无法访问网站

**原因**：代理服务器未启动

**解决**：
```powershell
cd D:\capture-api-skill
.\start_simple.bat
```

确保看到"代理已启动"的提示。

### Q2: 只想捕获特定网站的流量

**解决**：使用 Proxy SwitchyOmega 扩展

1. 创建"自动切换"规则
2. 添加规则：
   ```
   条件类型：域名通配符
   条件设置：*.example.com
   情景模式：API Capture
   ```
3. 其他网站自动使用直接连接

### Q3: 使用完毕后如何关闭代理

**Chrome/Edge**：
1. 打开代理设置
2. 关闭"使用代理服务器"开关

**Firefox**：
1. 打开网络设置
2. 选择"不使用代理"

**使用扩展**：
- 点击扩展图标
- 选择"直接连接"

### Q4: HTTPS 网站无法访问

**原因**：简单代理不支持 HTTPS 拦截（需要证书）

**解决**：
- 只捕获 HTTP 网站
- 或使用 mitmproxy（需要安装证书）

---

## 完整使用流程

### 1. 启动代理

```powershell
cd D:\capture-api-skill
.\start_simple.bat
```

等待看到：
```
[INFO] 代理已启动，开始捕获流量...
```

### 2. 配置浏览器代理

按照上述步骤配置浏览器代理：
- 地址：`localhost`
- 端口：`18527`

### 3. 访问目标网站

打开浏览器，访问你要测试的 Web 系统。

### 4. 观察捕获

终端会实时显示捕获的请求：
```
[CAPTURED] POST /api/user/login -> 200
[CAPTURED] GET /api/products/list -> 200
```

### 5. 停止捕获

在代理终端按 `Ctrl+C`

### 6. 关闭浏览器代理

将浏览器代理设置改回"不使用代理"或"直接连接"

### 7. 查看和生成测试用例

```powershell
python main.py review
```

访问 `http://localhost:18528`，勾选接口并生成测试用例。

---

## 提示和技巧

### 技巧 1: 使用浏览器配置文件

为测试创建单独的浏览器配置文件：

**Chrome**：
```powershell
chrome.exe --user-data-dir="C:\ChromeProxy" --proxy-server="localhost:18527"
```

这样不影响日常使用的浏览器。

### 技巧 2: 使用命令行启动

**Chrome**：
```powershell
"C:\Program Files\Google\Chrome\Application\chrome.exe" --proxy-server="localhost:18527"
```

**Edge**：
```powershell
"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe" --proxy-server="localhost:18527"
```

### 技巧 3: 快速切换

使用 Proxy SwitchyOmega 扩展，设置快捷键：
- 选项 → 快捷键
- 设置切换代理的快捷键（如 `Alt+Shift+P`）

---

## 安全提示

⚠️ **使用完毕后记得关闭代理**

如果忘记关闭代理：
- 代理服务器停止后，浏览器将无法访问网站
- 可能影响其他应用的网络连接

✅ **建议**：
- 使用浏览器扩展，方便快速切换
- 或创建单独的浏览器配置文件用于测试
