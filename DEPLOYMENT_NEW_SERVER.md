# 新服务器部署指南 - 47.104.228.147

## 📋 服务器信息

- **外网IP**: 47.104.228.147
- **内网IP**: 172.17.0.24
- **SSH端口**: 2026
- **系统**: CentOS 8
- **部署用户**: deployer / Jjk@ynxt2026
- **Root用户**: root / Jjk@xhis2022%.

## ✅ 已完成的部署步骤

### 1. 环境准备 (已完成)

```bash
# 使用root登录并创建deployer用户
ssh -p 2026 root@47.104.228.147

# 创建deployer用户
useradd -m -s /bin/bash deployer
echo "deployer:Jjk@ynxt2026" | chpasswd
usermod -aG docker deployer

# 安装Docker和Docker Compose
yum install -y git
curl -fsSL https://get.docker.com | sh -s docker --mirror Aliyun
systemctl start docker
systemctl enable docker
```

### 2. 应用部署 (进行中)

```bash
# 上传代码到服务器
cd /Users/admin/Documents/projects/Pauline/huicheng-wsp
tar czf /tmp/huicheng-wsp-deploy.tar.gz --exclude='.venv' --exclude='__pycache__' --exclude='.git' .
scp -P 2026 /tmp/huicheng-wsp-deploy.tar.gz deployer@47.104.228.147:/home/deployer/

# 在服务器上解压并部署
ssh -p 2026 deployer@47.104.228.147
cd /home/deployer
mkdir -p huicheng-wsp
tar xzf huicheng-wsp-deploy.tar.gz -C huicheng-wsp
cd huicheng-wsp

# 创建.env配置文件
cat > .env << 'EOF'
MYSQL_ROOT_PASSWORD=Huicheng@Root@2026!Secure
MYSQL_USER=wsp_user
MYSQL_PASSWORD=Wsp@App@2026!Secure
EOF

# 构建并启动服务
mkdir -p logs/nginx
docker build --no-cache -t huicheng-wsp-web .
docker compose up -d
```

### 3. Docker容器架构

```
┌─────────────┐
│   Nginx     │ ← 80端口 (反向代理)
│  (alpine)   │
└──────┬──────┘
       │ proxy_pass
       ↓
┌─────────────┐
│    Flask    │ ← 5000端口 (内部,不对外)
│   (web)     │
└──────┬──────┘
       │ pymysql
       ↓
┌─────────────┐
│   MySQL     │ ← 3306端口 (数据库)
│   (8.0)     │
└─────────────┘
```

## 🔗 访问地址

部署完成后,可以通过以下地址访问:

- **Web应用**: http://47.104.228.147:80
- **信息采集页面**: http://47.104.228.147:80/?mode=input
- **二维码生成器**: http://47.104.228.147:80/qr-generator.html

## ⚠️ 重要:阿里云安全组配置

**必须开放以下端口才能外网访问:**

1. 登录 https://ecs.console.aliyun.com
2. 找到IP为 `47.104.228.147` 的实例
3. 进入 "安全组" > "配置规则"
4. 添加入方向规则:

| 授权策略 | 协议类型 | 端口范围 | 授权对象 | 描述 |
|---------|---------|---------|---------|------|
| 允许 | TCP | 80/80 | 0.0.0.0/0 | Web访问(HTTP) |
| 允许 | TCP | 2026/2026 | 0.0.0.0/0 | SSH登录 |
| 允许 | TCP | 3306/3306 | 0.0.0.0/0 | MySQL(可选) |

5. 保存并等待1-2分钟生效

## 🔍 故障排查

### 检查容器状态

```bash
ssh -p 2026 deployer@47.104.228.147
cd /home/deployer/huicheng-wsp
docker compose ps
```

### 查看应用日志

```bash
# Web应用日志
docker logs huicheng-wsp-web --tail 50

# Nginx日志
docker logs huicheng-wsp-nginx --tail 50

# MySQL日志
docker logs huicheng-wsp-mysql --tail 50
```

### 测试API

```bash
# 测试仪表盘
curl http://localhost:80/api/dashboard

# 测试信息采集页面
curl http://localhost:80/?mode=input
```

### 重启服务

```bash
cd /home/deployer/huicheng-wsp
docker compose restart
```

### 重新构建镜像

```bash
cd /home/deployer/huicheng-wsp
docker compose down
docker build --no-cache -t huicheng-wsp-web .
docker compose up -d
```

## 📝 常用命令

```bash
# SSH登录
ssh -p 2026 deployer@47.104.228.147

# 查看容器状态
docker compose ps

# 查看实时日志
docker compose logs -f

# 停止所有服务
docker compose down

# 启动所有服务
docker compose up -d

# 重启单个服务
docker compose restart web

# 查看磁盘使用
docker system df

# 清理未使用的镜像
docker image prune -a
```

## 🚀 部署验证清单

- [ ] Docker和Docker Compose已安装
- [ ] 代码已上传到服务器
- [ ] .env配置文件已创建
- [ ] Docker镜像构建成功
- [ ] 三个容器都在运行(mysql, web, nginx)
- [ ] 本地可以访问 http://localhost:80
- [ ] 阿里云安全组已开放80端口
- [ ] 外网可以访问 http://47.104.228.147:80
- [ ] 信息采集页面正常 (?mode=input)
- [ ] 二维码生成功能正常

## 📞 支持

如果遇到问题,请检查:
1. 容器是否正常运行: `docker compose ps`
2. 应用日志是否有错误: `docker logs huicheng-wsp-web`
3. 阿里云安全组是否正确配置
4. 防火墙是否阻止了端口访问
