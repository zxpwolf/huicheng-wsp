# 阿里云服务器外网访问问题排查

## 当前状态

✅ **Docker容器已运行**:
- huicheng-wsp-web (端口5000)
- huicheng-wsp-mysql (端口3306)

✅ **端口监听正常**: 5000端口已在服务器上监听

❌ **外网无法访问**: 通过 `http://47.104.220.141:5000` 无法访问

## 问题原因分析

### 1. 应用内部错误 (已修复)
- 缺少 `cryptography` Python包
- 导致MySQL认证失败
- **解决方案**: 在requirements.txt中添加cryptography并重新构建镜像

### 2. 阿里云安全组未开放5000端口 (最可能的原因)

阿里云ECS实例默认只开放部分端口(如22、80、443),需要在控制台手动配置安全组规则。

## 解决方案

### 步骤1: 登录阿里云控制台

1. 访问 https://ecs.console.aliyun.com
2. 使用账号登录

### 步骤2: 找到安全组配置

1. 在左侧菜单选择 "实例与镜像" > "实例"
2. 找到IP为 `47.104.220.141` 的实例
3. 点击实例ID进入详情页
4. 切换到 "安全组" 标签页
5. 点击安全组ID进入安全组规则配置

### 步骤3: 添加入方向规则

点击 "手动添加" 或 "快速添加",配置如下规则:

```
授权策略: 允许
优先级: 1
协议类型: TCP
端口范围: 5000/5000
授权对象: 0.0.0.0/0  (允许所有IP访问)
描述: WSP报告系统Web访问
```

**或者**,如果想限制特定IP访问,可以将授权对象改为:
```
授权对象: 你的办公网IP/32
```

### 步骤4: 保存并验证

1. 点击 "保存" 
2. 等待1-2分钟让规则生效
3. 在浏览器访问: `http://47.104.220.141:5000`

## 其他检查项

### 检查防火墙状态

```bash
# SSH登录服务器
ssh -p 2023 deployer@47.104.220.141

# 检查firewalld状态
sudo systemctl status firewalld

# 如果防火墙开启,添加端口规则
sudo firewall-cmd --permanent --add-port=5000/tcp
sudo firewall-cmd --reload
```

### 检查应用是否正常启动

```bash
# 查看容器日志
docker logs huicheng-wsp-web --tail 50

# 测试本地访问
curl http://localhost:5000/api/dashboard
```

## 推荐的部署架构

生产环境建议使用Nginx作为反向代理:

1. **优势**:
   - 支持HTTPS/SSL
   - 更好的性能
   - 可以隐藏实际端口
   - 支持域名访问

2. **配置示例**:
   ```nginx
   server {
       listen 80;
       server_name 47.104.220.141;
       
       location / {
           proxy_pass http://localhost:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

3. **只需开放80端口**(更安全):
   - 安全组开放80端口
   - 访问: `http://47.104.220.141`

## 安全建议

⚠️ **重要**: 

1. **不要长期暴露5000端口**: Flask开发服务器不适合直接对外提供服务
2. **使用Nginx反向代理**: 更安全和高效
3. **配置HTTPS**: 保护数据传输安全
4. **限制访问IP**: 如果可能,只允许特定IP访问
5. **定期更新密码**: 修改默认数据库密码

## 快速诊断命令

```bash
# 一键检查脚本
sshpass -p "Jjk@ynxt2026" ssh -p 2023 -o StrictHostKeyChecking=no deployer@47.104.220.141 << 'EOF'
echo "=== 容器状态 ==="
docker ps | grep huicheng

echo ""
echo "=== 端口监听 ==="
ss -tlnp | grep 5000

echo ""
echo "=== 应用健康检查 ==="
curl -s http://localhost:5000/api/dashboard | python3 -m json.tool | head -5

echo ""
echo "=== 防火墙状态 ==="
sudo systemctl is-active firewalld || echo "防火墙未运行"
EOF
```

## 联系信息

- 服务器IP: 47.104.220.141
- SSH端口: 2023
- Web端口: 5000
- 部署用户: deployer
- 部署目录: /home/deployer/huicheng-wsp
