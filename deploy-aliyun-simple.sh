#!/bin/bash
# ============================================
# 荟城减重 WSP 系统 - 阿里云简化部署脚本
# ============================================

set -e

# 服务器配置
SERVER_HOST="47.104.220.141"
SERVER_PORT="2023"
SERVER_USER="deployer"
SERVER_PASSWORD="Jjk@ynxt2026"
DEPLOY_DIR="/home/deployer/huicheng-wsp"

echo "======================================"
echo "  荟城减重 WSP 系统 - 阿里云部署"
echo "======================================"
echo ""

# 打包代码(排除不必要的文件)
echo "📦 步骤1: 打包代码..."
tar czf /tmp/huicheng-wsp-deploy.tar.gz \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.venv' \
    --exclude='venv' \
    --exclude='logs' \
    --exclude='data' \
    --exclude='.env' \
    --exclude='node_modules' \
    .

echo "✅ 打包完成"
echo ""

# 上传到服务器
echo "📤 步骤2: 上传代码到服务器..."
sshpass -p "${SERVER_PASSWORD}" scp -P ${SERVER_PORT} -o StrictHostKeyChecking=no \
    /tmp/huicheng-wsp-deploy.tar.gz \
    ${SERVER_USER}@${SERVER_HOST}:/tmp/

echo "✅ 上传完成"
echo ""

# 在服务器上解压并部署
echo "🚀 步骤3: 在服务器上部署..."
sshpass -p "${SERVER_PASSWORD}" ssh -p ${SERVER_PORT} -o StrictHostKeyChecking=no ${SERVER_USER}@${SERVER_HOST} << 'ENDSSH'
#!/bin/bash
set -e

cd /home/deployer

# 创建目录
mkdir -p huicheng-wsp

# 解压代码
echo "📂 解压代码..."
tar xzf /tmp/huicheng-wsp-deploy.tar.gz -C huicheng-wsp/
rm /tmp/huicheng-wsp-deploy.tar.gz

cd huicheng-wsp

echo "✅ 当前目录: $(pwd)"
echo ""

# 检查Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose未安装"
    exit 1
fi

echo "✅ Docker: $(docker --version)"
echo "✅ Docker Compose: $(docker-compose --version)"
echo ""

# 创建.env
if [ ! -f .env ]; then
    echo "📝 创建.env..."
    cp .env.example .env
    
    # 生成SECRET_KEY
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || openssl rand -hex 32)
    sed -i "s/SECRET_KEY=.*/SECRET_KEY=${SECRET_KEY}/" .env
    
    echo "✅ .env已创建"
else
    echo "✅ .env已存在"
fi

echo ""

# 创建目录
echo "📁 创建目录..."
mkdir -p logs data/mysql-backup data/uploads ssl
echo "✅ 目录创建完成"
echo ""

# 停止旧服务
echo "🛑 停止旧服务..."
docker-compose down 2>/dev/null || true
echo ""

# 启动服务
echo "🚀 启动服务..."
docker-compose up -d --build

echo ""
echo "⏳ 等待服务启动(30秒)..."
sleep 30

# 检查状态
echo ""
echo "📊 服务状态:"
docker-compose ps

echo ""
echo "🔍 健康检查..."

# 检查MySQL
if docker-compose exec -T mysql mysqladmin ping -h localhost -u root -p${MYSQL_ROOT_PASSWORD:-root123456} 2>/dev/null | grep -q "alive"; then
    echo "✅ MySQL 正常"
else
    echo "⚠️  MySQL 可能还在启动"
fi

# 检查Web
if curl -s http://localhost:5000/api/dashboard > /dev/null 2>&1; then
    echo "✅ Web应用 正常"
else
    echo "⚠️  Web应用 可能还在启动"
fi

echo ""
echo "======================================"
echo "  ✅ 部署完成！"
echo "======================================"
echo ""
echo "📱 访问: http://47.104.220.141:5000"
echo ""
echo "📋 常用命令:"
echo "   cd /home/deployer/huicheng-wsp"
echo "   docker-compose logs -f     # 查看日志"
echo "   docker-compose restart     # 重启"
echo "   docker-compose down        # 停止"
echo ""
echo "🔐 重要: 请立即修改.env中的密码!"
echo ""

ENDSSH

# 清理本地临时文件
rm -f /tmp/huicheng-wsp-deploy.tar.gz

echo ""
echo "✅ 部署脚本执行完成!"
echo ""
echo "📱 访问地址: http://47.104.220.141:5000"
echo ""
echo "📋 SSH登录: ssh -p 2023 deployer@47.104.220.141"
echo ""
