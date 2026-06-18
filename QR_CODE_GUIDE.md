# 二维码扫描访问指南

## 📱 功能说明

系统现已支持通过**固定URL + 二维码**的方式,让手机用户快速访问报告采集页面。

## 🔗 固定URL格式

```
http://服务器地址/?mode=input
```

**示例**:
- 本地测试: `http://localhost:5000/?mode=input`
- 生产环境: `http://47.104.220.141:80/?mode=input`

## ✨ 使用方式

### 方式1: 直接使用URL

在浏览器中直接输入带参数的URL,即可直接进入报告采集页面。

### 方式2: 生成二维码(推荐)

1. **打开二维码生成器**:
   ```
   http://服务器地址/qr-generator.html
   ```
   
2. **输入服务器地址**:
   - 例如: `http://47.104.220.141:80`
   
3. **点击"生成二维码"**:
   - 系统会自动生成包含 `?mode=input` 参数的二维码
   
4. **下载或分享二维码**:
   - 点击下载按钮保存为PNG图片
   - 或直接截图分享

### 方式3: 手动创建二维码

您也可以使用任何在线二维码生成工具,将以下URL转换为二维码:
```
http://47.104.220.141:80/?mode=input
```

## 🎯 用户体验流程

```
用户扫描二维码
    ↓
浏览器打开URL (带?mode=input参数)
    ↓
JavaScript自动检测URL参数
    ↓
直接跳转到报告采集页面
    ↓
用户填写表单并提交
```

## 📋 技术实现

### 前端URL参数处理

在 `index.html` 中添加了 `handleUrlParams()` 函数:

```javascript
function handleUrlParams() {
  const params = new URLSearchParams(window.location.search);
  const mode = params.get('mode');
  
  if (mode === 'input') {
    // 直接进入报告采集页面
    showPage('report-input');
    // 清除URL参数,避免刷新时重复跳转
    window.history.replaceState({}, '', window.location.pathname);
  }
}
```

### 支持的URL参数

| 参数 | 值 | 说明 |
|------|-----|------|
| mode | input | 直接进入报告采集页面 |
| (未来可扩展) | ... | 其他模式 |

## 💡 应用场景

### 场景1: 门诊患者自助填报

1. 在诊室张贴二维码海报
2. 患者扫码后直接在手机上填写信息
3. 提交后医生即可查看报告

### 场景2: 随访数据采集

1. 通过微信发送二维码给患者
2. 患者在家即可完成数据采集
3. 数据自动同步到系统

### 场景3: 健康筛查活动

1. 活动现场展示二维码
2. 参与者扫码填写健康信息
3. 实时生成健康报告

## 🎨 二维码生成器功能

`qr-generator.html` 提供:

- ✅ 自动填充当前服务器地址
- ✅ 实时预览二维码
- ✅ 一键下载PNG图片
- ✅ 高容错率(H级纠错)
- ✅ 响应式设计,支持移动端

## 🔧 扩展更多模式

如需添加其他快捷入口,只需扩展 `handleUrlParams()` 函数:

```javascript
function handleUrlParams() {
  const params = new URLSearchParams(window.location.search);
  const mode = params.get('mode');
  
  if (mode === 'input') {
    showPage('report-input');
  } else if (mode === 'dashboard') {
    showPage('dashboard');
  } else if (mode === 'list') {
    showPage('report-list');
  }
  // ... 更多模式
}
```

对应的URL:
- 采集页面: `/?mode=input`
- 仪表盘: `/?mode=dashboard`
- 报告列表: `/?mode=list`

## 📊 实际部署示例

### 阿里云服务器 (47.104.220.141)

**二维码生成器URL**:
```
http://47.104.220.141:80/qr-generator.html
```

**采集页面固定URL**:
```
http://47.104.220.141:80/?mode=input
```

**操作步骤**:
1. 访问 `http://47.104.220.141:80/qr-generator.html`
2. 确认服务器地址为 `http://47.104.220.141:80`
3. 点击"生成二维码"
4. 下载并打印二维码海报
5. 在诊室张贴或分享给患者

## ⚠️ 注意事项

1. **确保Nginx已配置**: 需要开放80端口并通过Nginx提供服务
2. **HTTPS建议**: 生产环境建议使用HTTPS,避免浏览器安全警告
3. **二维码尺寸**: 建议生成256x256或更高分辨率的二维码
4. **测试验证**: 生成后用多部手机测试扫描效果
5. **URL稳定性**: 固定URL应长期保持不变

## 🚀 快速开始

**立即体验**:

1. 打开浏览器访问:
   ```
   http://47.104.220.141:80/qr-generator.html
   ```

2. 点击"生成二维码"

3. 用手机微信扫码测试

4. 扫描二维码下载保存

---

**最后更新**: 2026-06-18  
**版本**: v1.0
